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
                     timeout_s=120):
    """Route one upload through a paced proxy and private loopback origin."""
    from .proxy import BandwidthProxy

    validate_settings(payload_bytes, bandwidth_kbps, chunk_bytes)
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
        proxy = BandwidthProxy(origin_port, bandwidth_kbps, timeout_s)
        proxy_server = await asyncio.start_server(proxy.handle, '127.0.0.1', 0)
        async with proxy_server:
            try:
                port = proxy_server.sockets[0].getsockname()[1]
                result = await asyncio.wait_for(
                    upload_to_origin(payload, port, chunk_bytes), timeout_s,
                )
                result['proxy_ingress_bytes'] = proxy.ingress_bytes
                result['forwarded_bytes'] = proxy.forwarded_bytes
                return result
            finally:
                # Close active connections before the server context waits
                # for them; otherwise a paced transfer can outlive its deadline.
                await proxy.close()
