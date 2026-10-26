"""Real localhost HTTP origin, shared-rate disruption proxy and upload clients."""
import asyncio
import contextlib
import hashlib
import json
import socket
import time

async def headers(reader):
    block = await reader.readuntil(b'\r\n\r\n')
    if len(block) > 16384:
        raise ValueError('Headers too large')
    lines = block.decode('ascii').split('\r\n')
    fields = dict(line.split(':', 1) for line in lines[1:] if ':' in line)
    return lines[0].split(), {k.lower(): v.strip() for k, v in fields.items()}

async def close(writer):
    writer.close()
    try:
        await asyncio.wait_for(writer.wait_closed(), .25)
    except asyncio.CancelledError:
        writer.transport.abort()
        raise
    except Exception:
        # A close timeout must not replace a cancellation already propagating
        # through the caller's finally block. Abort buffered bytes and preserve it.
        writer.transport.abort()

async def respond(writer, status, value):
    body = json.dumps(value).encode()
    writer.write(f'HTTP/1.1 {status} Result\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode() + body)
    await writer.drain()

class Trial:
    def __init__(self, payload, config, strategy, trial_number=1):
        self.payload, self.config, self.strategy = payload, config, strategy
        self.started = time.monotonic()
        self.data = bytearray()
        self.writers, self.tasks = set(), set()
        self.lock = asyncio.Lock()
        self.pace_credit = 0.0
        self.result = {
            'strategy': strategy, 'trial': trial_number, 'status': 'running', 'elapsed_s': 0,
            'payload_bytes': len(payload), 'bytes_sent': 0, 'client_submitted_bytes': 0,
            'forwarded_bytes': 0, 'confirmed_bytes': 0, 'retry_count': 0,
            'integrity': None, 'expected_sha256': hashlib.sha256(payload).hexdigest(),
            'actual_sha256': None, 'useful_kbps': None, 'overhead_percent': None,
            'transport_overhead': None, 'events': [], 'samples': [], 'recoveries': [],
            'config': config, 'error': None,
        }
        self.phase_index = -1
        self.last_sample_bytes = 0
        self.last_sample_time = 0
        self.origin = self.proxy = None

    def elapsed(self):
        return time.monotonic() - self.started

    def phase(self):
        return next(p for p in reversed(self.config['phases']) if p['at'] <= self.elapsed())

    def event(self, kind, message):
        self.result['events'].append({'at': round(self.elapsed(), 3), 'kind': kind, 'message': message})

    def track(self, handler):
        async def wrapped(reader, writer):
            task = asyncio.current_task()
            self.tasks.add(task)
            self.writers.add(writer)
            try:
                await handler(reader, writer)
            except (ConnectionError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ValueError, OSError):
                pass
            finally:
                await close(writer)
                self.writers.discard(writer)
                self.tasks.discard(task)
        return wrapped

    async def origin_handler(self, reader, writer):
        request, fields = await headers(reader)
        if request[0] == 'GET':
            await respond(writer, 200, {'offset': len(self.data), 'sha256': hashlib.sha256(self.data).hexdigest() if len(self.data) == len(self.payload) else None})
            return
        length = int(fields.get('content-length', '-1'))
        offset = int(fields.get('x-offset', '-1'))
        if not 0 <= length <= len(self.payload) or not 0 <= offset <= len(self.payload) - length:
            await respond(writer, 400, {'error': 'Invalid body or offset'})
            return
        body = await reader.readexactly(length)
        # Complete requests commit atomically. Interrupted chunks never become durable progress.
        if offset == 0:
            self.data.clear()
        if offset != len(self.data):
            await respond(writer, 409, {'error': 'Offset mismatch'})
            return
        self.data.extend(body)
        await respond(writer, 200, {'offset': len(self.data), 'sha256': hashlib.sha256(self.data).hexdigest() if len(self.data) == len(self.payload) else None})

    async def proxy_handler(self, reader, writer):
        request, fields = await headers(reader)
        if self.phase()['kbps'] == 0:
            return
        await asyncio.sleep(self.config['delay_ms'] / 1000)
        if self.phase()['kbps'] == 0:
            return
        upstream_reader, upstream = await asyncio.open_connection('127.0.0.1', self.origin.sockets[0].getsockname()[1])
        self.writers.add(upstream)
        try:
            upstream.write((' '.join(request) + '\r\n' + ''.join(f'{k}: {v}\r\n' for k, v in fields.items()) + '\r\n').encode())
            remaining = int(fields.get('content-length', '0'))
            while remaining:
                body = await reader.read(min(4096, remaining))
                if not body:
                    return
                self.result['bytes_sent'] += len(body)
                # Shared scheduler survives reconnects; no per-connection burst allowance.
                async with self.lock:
                    budget = self.pace_credit
                    previous = time.monotonic()
                    while budget < len(body):
                        rate = self.phase()['kbps'] * 1000 / 8
                        if rate == 0:
                            return
                        await asyncio.sleep(min(.02, (len(body) - budget) / rate))
                        now = time.monotonic()
                        budget += (now - previous) * rate
                        previous = now
                    self.pace_credit = min(4096, max(0, budget - len(body)))
                    if self.phase()['kbps'] == 0:
                        return
                    upstream.write(body)
                    await upstream.drain()
                    self.result['forwarded_bytes'] += len(body)
                remaining -= len(body)
            await upstream.drain()
            while body := await upstream_reader.read(16384):
                writer.write(body)
                await writer.drain()
        finally:
            await close(upstream)
            self.writers.discard(upstream)

    async def monitor(self):
        while True:
            elapsed = self.elapsed()
            index = max(i for i, p in enumerate(self.config['phases']) if p['at'] <= elapsed)
            if index != self.phase_index:
                old = self.config['phases'][self.phase_index] if self.phase_index >= 0 else None
                phase = self.config['phases'][index]
                self.phase_index = index
                self.event('network', f"Bandwidth -> {phase['kbps']} kbps" if phase['kbps'] else 'Outage: active connections interrupted')
                if phase['kbps'] == 0:
                    for writer in list(self.writers):
                        writer.transport.abort()
                elif old and old['kbps'] == 0:
                    self.result['recoveries'].append({'restored_at': phase['at'], 'recovery_s': None})
            if elapsed - self.last_sample_time >= .2:
                count = self.result['forwarded_bytes']
                self.result['samples'].append({'at': round(elapsed, 3), 'kbps': (count - self.last_sample_bytes) * 8 / (elapsed - self.last_sample_time) / 1000,
                                               'limit_kbps': self.phase()['kbps'], 'confirmed_bytes': self.result['confirmed_bytes']})
                if len(self.result['samples']) > 9000:
                    self.result['samples'] = self.result['samples'][::2]
                self.last_sample_time, self.last_sample_bytes = elapsed, count
            self.result['elapsed_s'] = elapsed
            self.result['network_kbps'] = self.phase()['kbps']
            await asyncio.sleep(.02)

    async def request(self, offset=None, body=None):
        reader, writer = await asyncio.open_connection('127.0.0.1', self.proxy.sockets[0].getsockname()[1])
        self.writers.add(writer)
        writer.transport.set_write_buffer_limits(high=8192, low=4096)
        writer.get_extra_info('socket').setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8192)
        try:
            method = 'GET' if body is None else 'POST'
            writer.write(f'{method} /upload HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body) if body is not None else 0}\r\nX-Offset: {offset or 0}\r\nConnection: close\r\n\r\n'.encode())
            if body is not None:
                for start in range(0, len(body), 4096):
                    part = body[start:start + 4096]
                    writer.write(part)
                    self.result['client_submitted_bytes'] += len(part)
                    await writer.drain()
            status, fields = await headers(reader)
            response = json.loads(await reader.readexactly(int(fields['content-length'])))
            if status[1] != '200':
                raise ConnectionError(response.get('error', 'Origin error'))
            return response
        finally:
            await close(writer)
            self.writers.discard(writer)

    def acknowledge(self, response):
        previous = self.result['confirmed_bytes']
        self.result['confirmed_bytes'] = response['offset']
        if response['offset'] > previous:
            for recovery in self.result['recoveries']:
                if recovery['recovery_s'] is None:
                    recovery['recovery_s'] = self.elapsed() - recovery['restored_at']
                    self.event('recovery', f"Progress recovered after {recovery['recovery_s']:.2f}s")
        if response['sha256'] is not None:
            self.result['actual_sha256'] = response['sha256']
            self.result['integrity'] = response['sha256'] == self.result['expected_sha256']
            if not self.result['integrity']:
                raise ValueError('SHA-256 mismatch')

    async def upload(self):
        offset = 0
        failures = 0
        need_probe = False
        while offset < len(self.payload):
            try:
                if need_probe:
                    response = await self.request()
                    self.acknowledge(response)
                    offset = response['offset']
                    self.event('resume', f'Server confirmed offset {offset:,} bytes')
                    need_probe = False
                    if offset == len(self.payload):
                        break
                end = min(len(self.payload), offset + self.config['chunk_bytes']) if self.strategy == 'resumable' else len(self.payload)
                response = await self.request(offset, memoryview(self.payload)[offset:end])
                self.acknowledge(response)
                offset = response['offset']
            except (ConnectionError, OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError) as exc:
                self.event('interruption', f'Upload interrupted at {self.result["confirmed_bytes"]:,} confirmed bytes')
                if self.strategy == 'basic' or failures >= self.config['max_retries']:
                    raise ConnectionError('Single upload interrupted' if self.strategy == 'basic' else 'Retry budget exhausted') from exc
                wait = min(.25 * 2**min(failures, 4), 2)
                self.event('backoff', f'Retrying in {wait:.2f}s')
                await asyncio.sleep(wait)
                failures += 1
                self.result['retry_count'] = failures
                if self.strategy == 'retry':
                    offset = 0
                    self.result['confirmed_bytes'] = 0
                    self.event('restart', 'Restarting full file from byte zero')
                else:
                    need_probe = True

    async def run(self):
        monitor = None
        try:
            self.origin = await asyncio.start_server(self.track(self.origin_handler), '127.0.0.1', 0)
            self.proxy = await asyncio.start_server(self.track(self.proxy_handler), '127.0.0.1', 0)
            self.started = time.monotonic()
            monitor = asyncio.create_task(self.monitor())
            self.event('start', f'{self.strategy.title()} upload started')
            async with asyncio.timeout(self.config['deadline_s']):
                await self.upload()
            if not self.result['integrity']:
                raise ValueError('Upload finished without a verified file')
            self.result['status'] = 'completed'
            self.event('complete', 'SHA-256 verified by upload origin')
        except asyncio.CancelledError:
            self.result['status'] = 'cancelled'
            self.event('cancel', 'Trial cancelled; connections and partial data cleared')
            raise
        except Exception as exc:
            self.result['status'] = 'failed'
            self.result['error'] = 'Completion deadline exceeded' if isinstance(exc, TimeoutError) else str(exc)
            self.event('error', self.result['error'])
        finally:
            self.result['elapsed_s'] = self.elapsed()
            if monitor:
                monitor.cancel()
                await asyncio.gather(monitor, return_exceptions=True)
            for server in (self.proxy, self.origin):
                if server:
                    server.close()
            for writer in list(self.writers):
                writer.transport.abort()
            pending = list(self.tasks)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for server in (self.proxy, self.origin):
                if server:
                    await server.wait_closed()
            self.writers.clear()
            self.result['confirmed_bytes'] = len(self.data)
            self.result['retransmission_bytes'] = max(0, self.result['bytes_sent'] - len(self.data))
            if self.result['status'] == 'completed':
                self.result['overhead_percent'] = self.result['retransmission_bytes'] * 100 / len(self.payload)
                self.result['useful_kbps'] = len(self.payload) * 8 / self.result['elapsed_s'] / 1000
            self.data.clear()
        return self.result
