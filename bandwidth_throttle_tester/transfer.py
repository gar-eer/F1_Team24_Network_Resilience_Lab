"""Real localhost HTTP origin and upload clients."""
import asyncio
import hashlib
import json
import math
import time

from .throttler import BANDWIDTH_KBPS, validate_settings
from .metrics import derive_metrics


MAX_PAYLOAD_BYTES = 32 * 1024 * 1024


class IntegrityError(RuntimeError):
    """A complete body cannot be accepted without the expected origin hash."""

    def __init__(self, actual_sha256):
        self.actual_sha256 = actual_sha256 if isinstance(actual_sha256, str) else None
        super().__init__('SHA-256 verification failed: origin hash missing or mismatching')


def verify_sha256(expected, actual):
    if actual != expected:
        raise IntegrityError(actual)


async def read_headers(reader):
    block = await reader.readuntil(b'\r\n\r\n')
    lines = block.decode('ascii').split('\r\n')
    fields = dict(line.split(':', 1) for line in lines[1:] if ':' in line)
    return lines[0], {key.lower(): value.strip() for key, value in fields.items()}


class UploadOrigin:
    """Commit complete full-file requests or contiguous chunks in memory."""

    def __init__(self, timeout_s=120, expected_bytes=None):
        self.received = bytearray()
        self.timeout_s = timeout_s
        self.total_bytes = expected_bytes
        self.tasks = set()
        self.writers = set()

    def digest(self):
        if self.total_bytes is not None and len(self.received) == self.total_bytes:
            return hashlib.sha256(self.received).hexdigest()
        return None

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        self.writers.add(writer)
        try:
            await self._handle(reader, writer)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass
            finally:
                self.writers.discard(writer)
                self.tasks.discard(task)

    async def close(self):
        for writer in list(self.writers):
            writer.transport.abort()
        tasks = list(self.tasks)
        for task in tasks:
            if not task.cancelling():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle(self, reader, writer):
        try:
            request, fields = await asyncio.wait_for(read_headers(reader), 5)
            if request == 'GET /offset HTTP/1.1':
                if int(fields.get('content-length', '0')) != 0:
                    raise ValueError('Offset probes must not include a body')
                value = {'offset': len(self.received)}
            else:
                length = int(fields.get('content-length', '-1'))
                if not 0 < length <= MAX_PAYLOAD_BYTES:
                    raise ValueError('Invalid body length')
                if request == 'POST /upload HTTP/1.1':
                    if self.total_bytes is not None and length != self.total_bytes:
                        raise ValueError('Unexpected full-file size')
                    body = await asyncio.wait_for(reader.readexactly(length), self.timeout_s)
                    self.received[:] = body
                    self.total_bytes = length
                elif request == 'POST /chunk HTTP/1.1':
                    offset = int(fields.get('x-offset', '-1'))
                    total = int(fields.get('x-total-bytes', '-1'))
                    if (not 0 <= offset < total <= MAX_PAYLOAD_BYTES
                            or offset + length > total
                            or self.total_bytes is not None and total != self.total_bytes):
                        raise ValueError('Invalid chunk size or offset')
                    body = await asyncio.wait_for(reader.readexactly(length), self.timeout_s)
                    # Check again after the read: another request may have committed.
                    if offset != len(self.received):
                        raise ValueError('Chunk does not begin at the committed offset')
                    self.received.extend(body)
                    self.total_bytes = total
                else:
                    raise ValueError('Invalid upload endpoint')
                value = {'received_bytes': len(body), 'offset': len(self.received)}
            value['sha256'] = self.digest()
            status = '200 OK'
        except (ValueError, UnicodeError, asyncio.IncompleteReadError,
                asyncio.LimitOverrunError, TimeoutError):
            status, value = '400 Bad Request', {'error': 'Invalid or incomplete upload'}
        except ConnectionError:
            writer.close()
            return
        try:
            body = json.dumps(value).encode('utf-8')
            writer.write(
                f'HTTP/1.1 {status}\r\nContent-Type: application/json\r\n'
                f'Content-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode()
                + body
            )
            await writer.drain()
        except ConnectionError:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass


async def request_origin(port, method, path, body=b'', chunk_bytes=4096, extra_headers=None,
                         on_submit=None):
    """Exchange one HTTP request with an origin or the trial's proxy port."""
    if type(chunk_bytes) is not int or chunk_bytes <= 0:
        raise ValueError('chunk_bytes must be a positive integer')
    reader, writer = await asyncio.open_connection('127.0.0.1', port)
    try:
        extra = ''.join(f'{key}: {value}\r\n' for key, value in (extra_headers or {}).items())
        writer.write(
            f'{method} {path} HTTP/1.1\r\nHost: 127.0.0.1\r\n'
            f'Content-Length: {len(body)}\r\n{extra}Connection: close\r\n\r\n'.encode()
        )
        for offset in range(0, len(body), chunk_bytes):
            piece = body[offset:offset + chunk_bytes]
            writer.write(piece)
            if on_submit is not None:
                on_submit(len(piece))
            await writer.drain()
        status, fields = await read_headers(reader)
        response = await reader.readexactly(int(fields['content-length']))
        acknowledgement = json.loads(response)
        if status != 'HTTP/1.1 200 OK':
            raise ValueError(f'Origin rejected request: {acknowledgement.get("error", status)}')
        return acknowledgement
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionError:
            pass


async def upload_to_origin(payload, port, chunk_bytes=4096, on_submit=None):
    """Send a full file and verify the independent origin's SHA-256."""
    started = time.perf_counter()
    acknowledgement = await request_origin(port, 'POST', '/upload', payload, chunk_bytes,
                                           on_submit=on_submit)
    if acknowledgement.get('received_bytes') != len(payload):
        raise ValueError('Origin did not acknowledge the complete upload')
    actual = acknowledgement.get('sha256')
    verify_sha256(hashlib.sha256(payload).hexdigest(), actual)
    return {'transferred_bytes': len(payload), 'elapsed_s': time.perf_counter() - started,
            'actual_sha256': actual}


async def run_upload(payload_bytes, chunk_bytes=4096, bandwidth_kbps=BANDWIDTH_KBPS,
                     timeout_s=120, phases=None, strategy='basic', max_retries=5,
                     resume_chunk_bytes=32768):
    """Run Basic, Retry, or Resumable against one fixed proxy trial schedule."""
    from .proxy import BandwidthProxy

    validate_settings(payload_bytes, bandwidth_kbps, chunk_bytes)
    if strategy not in ('basic', 'retry', 'resumable'):
        raise ValueError('strategy must be basic, retry, or resumable')
    if type(max_retries) is not int or max_retries < 0:
        raise ValueError('max_retries must be a nonnegative integer')
    if type(resume_chunk_bytes) is not int or not 0 < resume_chunk_bytes <= MAX_PAYLOAD_BYTES:
        raise ValueError('resume_chunk_bytes must be a positive integer up to 32 MiB')
    if (isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s) or timeout_s <= 0):
        raise ValueError('timeout_s must be a positive finite number')
    if type(payload_bytes) is not int or not 0 < payload_bytes <= MAX_PAYLOAD_BYTES:
        raise ValueError('HTTP payload size must be between 1 byte and 32 MiB')
    payload = (bytes(range(256)) * ((payload_bytes + 255) // 256))[:payload_bytes]
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    origin = UploadOrigin(timeout_s, payload_bytes)
    server = await asyncio.start_server(origin.handle, '127.0.0.1', 0)
    async with server:
        origin_port = server.sockets[0].getsockname()[1]
        proxy = BandwidthProxy(origin_port, bandwidth_kbps, timeout_s, phases)
        proxy_server = await asyncio.start_server(proxy.handle, '127.0.0.1', 0)
        async with proxy_server:
            try:
                await proxy.start()
                port = proxy_server.sockets[0].getsockname()[1]
                started = time.perf_counter()
                progress = {'attempt_count': 0, 'retry_count': 0,
                            'confirmed_bytes': 0, 'offset_probe_count': 0,
                            'client_submitted_bytes': 0, 'expected_sha256': expected_sha256,
                            'actual_sha256': None, 'integrity': None}

                def submitted(size):
                    progress['client_submitted_bytes'] += size

                def verify_complete(reply):
                    progress['actual_sha256'] = reply.get('sha256')
                    verify_sha256(expected_sha256, progress['actual_sha256'])
                    progress['integrity'] = True

                def record(kind, **details):
                    proxy.events.append({
                        'at': time.monotonic() - proxy.started, 'kind': kind, **details,
                    })

                async def recover(error):
                    reason = str(error) or type(error).__name__
                    record('attempt_failed', attempt=progress['attempt_count'], error=reason)
                    if strategy == 'basic':
                        raise error
                    if progress['retry_count'] >= max_retries:
                        raise RuntimeError(f'Retry budget exhausted: {reason}') from error
                    delay = min(0.25 * 2 ** min(progress['retry_count'], 3), 2)
                    record('retry_scheduled', delay_s=delay,
                           next_attempt=progress['attempt_count'] + 1)
                    await asyncio.sleep(delay)
                    # No await separates this increment from the next operation.
                    progress['retry_count'] += 1

                async def attempt_upload():
                    while True:
                        progress['attempt_count'] += 1
                        record('upload_attempt', attempt=progress['attempt_count'])
                        try:
                            # Every attempt sends the identical full body from byte zero.
                            result = await upload_to_origin(payload, port, chunk_bytes, submitted)
                            progress['confirmed_bytes'] = payload_bytes
                            progress['actual_sha256'] = result['actual_sha256']
                            progress['integrity'] = True
                            return result
                        except (OSError, ValueError, asyncio.IncompleteReadError) as error:
                            await recover(error)

                async def resume_upload():
                    offset = 0
                    needs_probe = False
                    while offset < payload_bytes:
                        try:
                            if needs_probe:
                                progress['attempt_count'] += 1
                                progress['offset_probe_count'] += 1
                                record('upload_attempt', attempt=progress['attempt_count'],
                                       operation='offset_probe')
                                reply = await request_origin(port, 'GET', '/offset')
                                committed = reply.get('offset')
                                if (type(committed) is not int
                                        or not progress['confirmed_bytes'] <= committed <= payload_bytes):
                                    raise ValueError('Invalid committed offset from origin')
                                offset = committed
                                progress['confirmed_bytes'] = offset
                                record('offset_confirmed', offset=offset)
                                needs_probe = False
                                if offset == payload_bytes:
                                    verify_complete(reply)
                                    break
                            body = payload[offset:offset + resume_chunk_bytes]
                            progress['attempt_count'] += 1
                            record('upload_attempt', attempt=progress['attempt_count'],
                                   operation='chunk', offset=offset, size_bytes=len(body))
                            reply = await request_origin(
                                port, 'POST', '/chunk', body, chunk_bytes,
                                {'X-Offset': offset, 'X-Total-Bytes': payload_bytes},
                                on_submit=submitted,
                            )
                            if (reply.get('offset') != offset + len(body)
                                    or reply.get('received_bytes') != len(body)):
                                raise ValueError('Origin did not acknowledge the complete chunk')
                            offset += len(body)
                            progress['confirmed_bytes'] = offset
                            record('chunk_committed', offset=offset, size_bytes=len(body))
                            if offset == payload_bytes:
                                verify_complete(reply)
                        except (OSError, ValueError, asyncio.IncompleteReadError) as error:
                            await recover(error)
                            needs_probe = True
                    return {'transferred_bytes': offset}

                try:
                    result = await asyncio.wait_for(
                        resume_upload() if strategy == 'resumable' else attempt_upload(), timeout_s,
                    )
                    result.update(status='completed', error=None,
                                  elapsed_s=time.perf_counter() - started)
                except (OSError, TimeoutError, ValueError, RuntimeError,
                        asyncio.IncompleteReadError) as error:
                    if isinstance(error, IntegrityError):
                        progress['confirmed_bytes'] = payload_bytes
                        progress['actual_sha256'] = error.actual_sha256
                        progress['integrity'] = False if error.actual_sha256 is not None else None
                    result = {
                        'transferred_bytes': progress['confirmed_bytes'],
                        'elapsed_s': time.perf_counter() - started,
                        'status': 'failed',
                        'error': ('Upload deadline exceeded' if isinstance(error, TimeoutError)
                                  else str(error) or type(error).__name__),
                    }
                result.update(progress, strategy=strategy,
                              max_retries=max_retries if strategy != 'basic' else 0,
                              resume_chunk_bytes=resume_chunk_bytes)
                result['proxy_ingress_bytes'] = proxy.ingress_bytes
                result['forwarded_bytes'] = proxy.forwarded_bytes
                result['phases'] = proxy.phases
                result['events'] = list(proxy.events)
            finally:
                # Close active connections before the server context waits
                # for them; otherwise a paced transfer can outlive its deadline.
                await proxy.close()
                await origin.close()
            result.update(derive_metrics(result, payload_bytes, len(origin.received)))
            return result
