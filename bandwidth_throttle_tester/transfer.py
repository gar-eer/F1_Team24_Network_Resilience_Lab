"""Real localhost HTTP origin and upload clients."""
import asyncio
import json
import math
import time

from .throttler import BANDWIDTH_KBPS, validate_settings


MAX_PAYLOAD_BYTES = 32 * 1024 * 1024


async def read_headers(reader):
    block = await reader.readuntil(b'\r\n\r\n')
    lines = block.decode('ascii').split('\r\n')
    fields = dict(line.split(':', 1) for line in lines[1:] if ':' in line)
    return lines[0], {key.lower(): value.strip() for key, value in fields.items()}


class UploadOrigin:
    """Accept one full upload into memory and acknowledge its received size."""

    def __init__(self, timeout_s=120):
        self.received = b''
        self.timeout_s = timeout_s

    async def handle(self, reader, writer):
        try:
            request, fields = await asyncio.wait_for(read_headers(reader), 5)
            length = int(fields.get('content-length', '-1'))
            if request != 'POST /upload HTTP/1.1' or not 0 < length <= MAX_PAYLOAD_BYTES:
                raise ValueError('Invalid upload request')
            body = await asyncio.wait_for(reader.readexactly(length), self.timeout_s)
            self.received = body
            status, value = '200 OK', {'received_bytes': len(body)}
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


async def upload_to_origin(payload, port, chunk_bytes=4096):
    """Send real bytes and require an HTTP acknowledgement for the whole body."""
    if type(chunk_bytes) is not int or chunk_bytes <= 0:
        raise ValueError('chunk_bytes must be a positive integer')
    started = time.perf_counter()
    reader, writer = await asyncio.open_connection('127.0.0.1', port)
    try:
        writer.write(
            f'POST /upload HTTP/1.1\r\nHost: 127.0.0.1\r\n'
            f'Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n'.encode()
        )
        for offset in range(0, len(payload), chunk_bytes):
            writer.write(payload[offset:offset + chunk_bytes])
            await writer.drain()
        status, fields = await read_headers(reader)
        body = await reader.readexactly(int(fields['content-length']))
        acknowledgement = json.loads(body)
        if (status != 'HTTP/1.1 200 OK'
                or acknowledgement.get('received_bytes') != len(payload)):
            raise ValueError('Origin did not acknowledge the complete upload')
        return {
            'transferred_bytes': acknowledgement['received_bytes'],
            'elapsed_s': time.perf_counter() - started,
        }
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionError:
            pass


async def run_upload(payload_bytes, chunk_bytes=4096, bandwidth_kbps=BANDWIDTH_KBPS,
                     timeout_s=120, phases=None, strategy='basic', max_retries=5):
    """Run Basic or full-file Retry against one fixed proxy trial schedule."""
    from .proxy import BandwidthProxy

    validate_settings(payload_bytes, bandwidth_kbps, chunk_bytes)
    if strategy not in ('basic', 'retry'):
        raise ValueError('strategy must be basic or retry')
    if type(max_retries) is not int or max_retries < 0:
        raise ValueError('max_retries must be a nonnegative integer')
    if (isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s) or timeout_s <= 0):
        raise ValueError('timeout_s must be a positive finite number')
    if type(payload_bytes) is not int or not 0 < payload_bytes <= MAX_PAYLOAD_BYTES:
        raise ValueError('HTTP payload size must be between 1 byte and 32 MiB')
    payload = (bytes(range(256)) * ((payload_bytes + 255) // 256))[:payload_bytes]
    origin = UploadOrigin(timeout_s)
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
                progress = {'attempt_count': 0, 'retry_count': 0}

                def record(kind, **details):
                    proxy.events.append({
                        'at': time.monotonic() - proxy.started, 'kind': kind, **details,
                    })

                async def attempt_upload():
                    while True:
                        progress['attempt_count'] += 1
                        progress['retry_count'] = progress['attempt_count'] - 1
                        record('upload_attempt', attempt=progress['attempt_count'])
                        try:
                            # Every attempt sends the identical full body from byte zero.
                            return await upload_to_origin(payload, port, chunk_bytes)
                        except (OSError, ValueError, asyncio.IncompleteReadError) as error:
                            reason = str(error) or type(error).__name__
                            record('attempt_failed', attempt=progress['attempt_count'],
                                   error=reason)
                            if strategy == 'basic':
                                raise
                            if progress['retry_count'] >= max_retries:
                                raise RuntimeError(f'Retry budget exhausted: {reason}') from error
                            delay = min(0.25 * 2 ** min(progress['retry_count'], 3), 2)
                            record('retry_scheduled', delay_s=delay,
                                   next_attempt=progress['attempt_count'] + 1)
                            await asyncio.sleep(delay)

                try:
                    result = await asyncio.wait_for(
                        attempt_upload(), timeout_s,
                    )
                    result.update(status='completed', error=None,
                                  elapsed_s=time.perf_counter() - started)
                except (OSError, TimeoutError, ValueError, RuntimeError,
                        asyncio.IncompleteReadError) as error:
                    result = {
                        'transferred_bytes': 0,
                        'elapsed_s': time.perf_counter() - started,
                        'status': 'failed',
                        'error': ('Upload deadline exceeded' if isinstance(error, TimeoutError)
                                  else str(error) or type(error).__name__),
                    }
                result.update(progress, strategy=strategy,
                              max_retries=max_retries if strategy == 'retry' else 0)
                result['proxy_ingress_bytes'] = proxy.ingress_bytes
                result['forwarded_bytes'] = proxy.forwarded_bytes
                result['phases'] = proxy.phases
                result['events'] = list(proxy.events)
                return result
            finally:
                # Close active connections before the server context waits
                # for them; otherwise a paced transfer can outlive its deadline.
                await proxy.close()
