"""Exercise actual HTTP bodies over loopback TCP sockets."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import unittest


class HttpUploadTests(unittest.IsolatedAsyncioTestCase):
    async def test_origin_receives_exact_payload_with_partial_final_chunk(self):
        from bandwidth_throttle_tester.transfer import UploadOrigin, upload_to_origin

        origin = UploadOrigin()
        server = await asyncio.start_server(origin.handle, '127.0.0.1', 0)
        payload = bytes(range(256)) * 32 + b'last byte'
        async with server:
            port = server.sockets[0].getsockname()[1]
            result = await upload_to_origin(payload, port, chunk_bytes=1000)
        self.assertEqual(origin.received, payload)
        self.assertEqual(result['transferred_bytes'], len(payload))
        self.assertGreater(result['elapsed_s'], 0)

    async def test_origin_rejects_unsupported_endpoint(self):
        from bandwidth_throttle_tester.transfer import UploadOrigin

        origin = UploadOrigin()
        server = await asyncio.start_server(origin.handle, '127.0.0.1', 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            try:
                writer.write(b'POST /wrong HTTP/1.1\r\nContent-Length: 0\r\n\r\n')
                await writer.drain()
                reply = await asyncio.wait_for(reader.read(), 5)
            finally:
                writer.close()
                await writer.wait_closed()
        self.assertTrue(reply.startswith(b'HTTP/1.1 400'))
        self.assertEqual(origin.received, b'')


class HttpCommandTests(unittest.TestCase):
    def test_default_mode_reports_actual_unpaced_http_upload(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / 'main.py'), '--size-bytes', '8193', '--json'],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result['mode'], 'http')
        self.assertEqual(result['payload_bytes'], 8193)
        self.assertEqual(result['transferred_bytes'], 8193)
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(result['bandwidth_applied'])


if __name__ == '__main__':
    unittest.main()
