"""Local HTTP proxy with one shared allowance for upload body forwarding."""
import asyncio
import time

from .config import validate_phases
from .throttler import validate_settings
from .transfer import MAX_PAYLOAD_BYTES, read_headers


class BandwidthProxy:
    """Pace body slices across all connections handled by this proxy instance."""

    def __init__(self, origin_port, bandwidth_kbps, timeout_s=120, phases=None):
        validate_settings(1, bandwidth_kbps, 4096)
        self.origin_port = origin_port
        self.bytes_per_second = bandwidth_kbps * 1000 / 8
        self.timeout_s = timeout_s
        self.lock = asyncio.Lock()
        self.tasks = set()
        self.ingress_bytes = 0
        self.forwarded_bytes = 0
        self.phases = validate_phases(
            phases if phases is not None else [{'at': 0, 'kbps': bandwidth_kbps}],
        )
        self.online = self.phases[0]['kbps'] > 0
        self.started = None
        self.monitor_task = None
        self.writers = set()
        self.events = []

    async def start(self):
        """Start one absolute schedule shared by all connection attempts."""
        if self.started is not None:
            return
        self.started = time.monotonic()
        self.apply_phase(self.phases[0], initial=True)
        self.monitor_task = asyncio.create_task(self.monitor())

    def apply_phase(self, phase, initial=False):
        was_online = self.online
        self.online = phase['kbps'] > 0
        self.bytes_per_second = phase['kbps'] * 1000 / 8
        kind = ('outage' if not self.online else 'started' if initial
                else 'restored' if not was_online else 'rate_changed')
        self.events.append({
            'at': time.monotonic() - self.started,
            'scheduled_at': phase['at'], 'kind': kind, 'kbps': phase['kbps'],
        })
        if not self.online:
            for writer in list(self.writers):
                writer.transport.abort()
            for task in list(self.tasks):
                if not task.cancelling():
                    task.cancel()

    async def monitor(self):
        for phase in self.phases[1:]:
            await asyncio.sleep(max(0, self.started + phase['at'] - time.monotonic()))
            self.apply_phase(phase)

    async def handle(self, reader, writer):
        await self.start()
        task = asyncio.current_task()
        self.tasks.add(task)
        self.writers.add(writer)
        upstream = None
        try:
            if not self.online:
                writer.transport.abort()
                return
            request, fields = await asyncio.wait_for(read_headers(reader), self.timeout_s)
            remaining = int(fields.get('content-length', '-1'))
            if request != 'POST /upload HTTP/1.1' or not 0 < remaining <= MAX_PAYLOAD_BYTES:
                raise ValueError('Invalid upload request')
            upstream_reader, upstream = await asyncio.open_connection(
                '127.0.0.1', self.origin_port,
            )
            self.writers.add(upstream)
            upstream.write(
                f'{request}\r\nHost: 127.0.0.1\r\nContent-Length: {remaining}\r\n'
                'Connection: close\r\n\r\n'.encode()
            )
            while remaining:
                body = await asyncio.wait_for(
                    reader.read(min(4096, remaining)), self.timeout_s,
                )
                if not body:
                    return
                self.ingress_bytes += len(body)
                # Hold the shared allowance until the slice is forwarded.
                # Headers and acknowledgement bodies are not rate-limited.
                async with self.lock:
                    if not self.online:
                        return
                    await asyncio.sleep(len(body) / self.bytes_per_second)
                    upstream.write(body)
                    await upstream.drain()
                    self.forwarded_bytes += len(body)
                remaining -= len(body)
            while True:
                response = await asyncio.wait_for(upstream_reader.read(4096), self.timeout_s)
                if not response:
                    break
                writer.write(response)
                await writer.drain()
        except (ValueError, UnicodeError, OSError, TimeoutError,
                asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            # Closing both sides leaves an incomplete request unacknowledged.
            pass
        finally:
            connections = [connection for connection in (upstream, writer)
                           if connection is not None]
            for connection in connections:
                self.writers.discard(connection)
                connection.close()
            try:
                for connection in connections:
                    try:
                        await connection.wait_closed()
                    except ConnectionError:
                        pass
            finally:
                self.tasks.discard(task)

    async def close(self):
        """Cancel in-flight forwarding before shutting down the trial."""
        if self.monitor_task is not None:
            self.monitor_task.cancel()
            await asyncio.gather(self.monitor_task, return_exceptions=True)
        for writer in list(self.writers):
            writer.transport.abort()
        tasks = list(self.tasks)
        for task in tasks:
            if not task.cancelling():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
