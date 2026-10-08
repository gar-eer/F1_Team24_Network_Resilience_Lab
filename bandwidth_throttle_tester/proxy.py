"""Local HTTP proxy with one shared allowance for upload body forwarding."""
import asyncio

from .throttler import validate_settings
from .transfer import MAX_PAYLOAD_BYTES, read_headers


class BandwidthProxy:
    """Pace body slices across all connections handled by this proxy instance."""

    def __init__(self, origin_port, bandwidth_kbps, timeout_s=120):
        validate_settings(1, bandwidth_kbps, 4096)
        self.origin_port = origin_port
        self.bytes_per_second = bandwidth_kbps * 1000 / 8
        self.timeout_s = timeout_s
        self.lock = asyncio.Lock()
        self.tasks = set()
        self.ingress_bytes = 0
        self.forwarded_bytes = 0

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        upstream = None
        try:
            request, fields = await asyncio.wait_for(read_headers(reader), self.timeout_s)
            remaining = int(fields.get('content-length', '-1'))
            if request != 'POST /upload HTTP/1.1' or not 0 < remaining <= MAX_PAYLOAD_BYTES:
                raise ValueError('Invalid upload request')
            upstream_reader, upstream = await asyncio.open_connection(
                '127.0.0.1', self.origin_port,
            )
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
            for connection in (upstream, writer):
                if connection is not None:
                    connection.close()
                    try:
                        await connection.wait_closed()
                    except ConnectionError:
                        pass
            self.tasks.discard(task)

    async def close(self):
        """Cancel in-flight forwarding before shutting down the trial."""
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
