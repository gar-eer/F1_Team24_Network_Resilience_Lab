"""Check committed offsets and resumable recovery over actual HTTP sockets."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import unittest


class ResumableTests(unittest.IsolatedAsyncioTestCase):
    async def test_chunks_commit_exact_bytes_and_probe_reports_the_offset(self):
        from bandwidth_throttle_tester.transfer import UploadOrigin, request_origin

        origin = UploadOrigin()
        server = await asyncio.start_server(origin.handle, '127.0.0.1', 0)
        payload = bytes(range(256)) * 19 + b'last'
        async with server:
            port = server.sockets[0].getsockname()[1]
            initial = await request_origin(port, 'GET', '/offset')
            self.assertEqual(initial['offset'], 0)
            for offset in range(0, len(payload), 4096):
                body = payload[offset:offset + 4096]
                reply = await request_origin(port, 'POST', '/chunk', body, extra_headers={
                    'X-Offset': offset, 'X-Total-Bytes': len(payload),
                })
                self.assertEqual(reply['offset'], offset + len(body))
            with self.assertRaises(ValueError):
                await request_origin(port, 'POST', '/chunk', b'wrong', extra_headers={
                    'X-Offset': 0, 'X-Total-Bytes': len(payload),
                })
            final = await request_origin(port, 'GET', '/offset')
            self.assertEqual(final['offset'], len(payload))
        self.assertEqual(origin.received, payload)

    async def test_incomplete_chunk_preserves_only_previously_committed_bytes(self):
        from bandwidth_throttle_tester.transfer import UploadOrigin, request_origin

        origin = UploadOrigin()
        server = await asyncio.start_server(origin.handle, '127.0.0.1', 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            await request_origin(port, 'POST', '/chunk', b'first', extra_headers={
                'X-Offset': 0, 'X-Total-Bytes': 10,
            })
            _, writer = await asyncio.open_connection('127.0.0.1', port)
            writer.write(b'POST /chunk HTTP/1.1\r\nContent-Length: 5\r\n'
                         b'X-Offset: 5\r\nX-Total-Bytes: 10\r\n\r\nxx')
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            probe = await request_origin(port, 'GET', '/offset')
            self.assertEqual(probe['offset'], 5)
        self.assertEqual(origin.received, b'first')

    async def test_resumption_keeps_progress_and_repeats_less_body_data_than_retry(self):
        from bandwidth_throttle_tester.transfer import run_upload

        settings = dict(payload_bytes=65536, bandwidth_kbps=512, timeout_s=5,
                        max_retries=3,
                        phases=[{'at': 0, 'kbps': 512}, {'at': 0.35, 'kbps': 0},
                                {'at': 0.55, 'kbps': 512}])
        retry = await run_upload(**settings, strategy='retry')
        resumed = await run_upload(**settings, strategy='resumable', resume_chunk_bytes=4096)
        self.assertEqual(retry['status'], 'completed')
        self.assertEqual(resumed['status'], 'completed')
        self.assertEqual(resumed['confirmed_bytes'], 65536)
        self.assertEqual(resumed['transferred_bytes'], 65536)
        self.assertGreaterEqual(resumed['offset_probe_count'], 1)
        self.assertLess(resumed['proxy_ingress_bytes'], retry['proxy_ingress_bytes'])
        self.assertTrue(any(event['kind'] == 'offset_confirmed' and event['offset'] > 0
                            for event in resumed['events']))

    async def test_successful_chunks_do_not_consume_retry_budget(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(8193, strategy='resumable', max_retries=0,
                                  resume_chunk_bytes=4096)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['retry_count'], 0)
        self.assertEqual(result['offset_probe_count'], 0)
        self.assertEqual(result['attempt_count'], 3)
        self.assertEqual(result['confirmed_bytes'], 8193)

    async def test_retry_budget_does_not_reset_after_successful_chunks(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(
            65536, strategy='resumable', resume_chunk_bytes=4096, max_retries=1,
            bandwidth_kbps=512, timeout_s=5,
            phases=[{'at': 0, 'kbps': 512}, {'at': 0.2, 'kbps': 0},
                    {'at': 0.4, 'kbps': 512}, {'at': 1.1, 'kbps': 0},
                    {'at': 1.3, 'kbps': 512}],
        )
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['retry_count'], 1)
        self.assertIn('Retry budget exhausted', result['error'])
        self.assertGreater(result['confirmed_bytes'], 0)
        self.assertLess(result['confirmed_bytes'], 65536)
        self.assertTrue(any(event['kind'] == 'chunk_committed' and event['at'] > 0.4
                            for event in result['events']), result['events'])

    async def test_offset_probes_use_the_offline_proxy_and_consume_retry_budget(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(1024, strategy='resumable', max_retries=1,
                                  phases=[{'at': 0, 'kbps': 0}], timeout_s=5)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['attempt_count'], 2)
        self.assertEqual(result['retry_count'], 1)
        self.assertEqual(result['offset_probe_count'], 1)
        self.assertEqual(result['confirmed_bytes'], 0)
        self.assertIn('Retry budget exhausted', result['error'])


class ResumableCommandTests(unittest.TestCase):
    def test_cli_reports_resumable_strategy_and_final_committed_offset(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / 'main.py'), '--strategy', 'resumable',
             '--resume-chunk-bytes', '1024', '--size-bytes', '8193',
             '--bandwidth-kbps', '256', '--outage-at-s', '0.15',
             '--outage-duration-s', '0.2', '--json'],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result['strategy'], 'resumable')
        self.assertEqual(result['confirmed_bytes'], 8193)
        self.assertEqual(result['resume_chunk_bytes'], 1024)
        self.assertGreaterEqual(result['offset_probe_count'], 1)


if __name__ == '__main__':
    unittest.main()
