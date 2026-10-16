"""Verify hashes from real origins and the meaning of derived measurements."""
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


class IntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_strategy_verifies_hash_and_reports_measured_metrics(self):
        from bandwidth_throttle_tester.transfer import run_upload

        expected = hashlib.sha256(bytes(range(256)) * 32 + b'\x00').hexdigest()
        for strategy in ('basic', 'retry', 'resumable'):
            with self.subTest(strategy=strategy):
                result = await run_upload(8193, strategy=strategy, resume_chunk_bytes=4096)
                self.assertEqual(result['status'], 'completed')
                self.assertIs(result['integrity'], True)
                self.assertEqual(result['expected_sha256'], expected)
                self.assertEqual(result['actual_sha256'], expected)
                self.assertEqual(result['bytes_sent'], result['proxy_ingress_bytes'])
                self.assertEqual(result['client_submitted_bytes'], 8193)
                self.assertEqual(result['confirmed_bytes'], 8193)
                self.assertEqual(result['retransmission_bytes'], 0)
                self.assertEqual(result['overhead_percent'], 0)
                self.assertAlmostEqual(result['useful_kbps'], 8193 * 8 / result['elapsed_s'] / 1000)
                self.assertIsNone(result['transport_overhead'])

    async def test_corrupted_origin_bytes_fail_verification_for_every_strategy(self):
        from bandwidth_throttle_tester.transfer import UploadOrigin, run_upload

        class CorruptOrigin(UploadOrigin):
            def digest(self):
                if self.total_bytes == len(self.received) and not getattr(self, 'corrupted', False):
                    self.received[0] ^= 1
                    self.corrupted = True
                return super().digest()

        for strategy in ('basic', 'retry', 'resumable'):
            with self.subTest(strategy=strategy):
                with patch('bandwidth_throttle_tester.transfer.UploadOrigin', CorruptOrigin):
                    result = await run_upload(1025, strategy=strategy)
                self.assertEqual(result['status'], 'failed')
                self.assertIs(result['integrity'], False)
                self.assertNotEqual(result['expected_sha256'], result['actual_sha256'])
                self.assertEqual(result['confirmed_bytes'], 1025)
                self.assertEqual(result['retry_count'], 0)
                self.assertIsNone(result['useful_kbps'])
                self.assertIsNone(result['overhead_percent'])
                self.assertIn('SHA-256', result['error'])

    async def test_missing_final_hash_cannot_be_reported_as_completed(self):
        from bandwidth_throttle_tester.transfer import UploadOrigin, run_upload

        class NoHashOrigin(UploadOrigin):
            def digest(self):
                return None

        with patch('bandwidth_throttle_tester.transfer.UploadOrigin', NoHashOrigin):
            result = await run_upload(1025, strategy='resumable')
        self.assertEqual(result['status'], 'failed')
        self.assertIsNone(result['actual_sha256'])
        self.assertIsNone(result['integrity'])
        self.assertIsNone(result['useful_kbps'])

    async def test_incomplete_upload_reports_discarded_work_without_success_metrics(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(65536, bandwidth_kbps=512, phases=[
            {'at': 0, 'kbps': 512}, {'at': 0.15, 'kbps': 0}, {'at': 0.35, 'kbps': 512},
        ])
        self.assertEqual(result['status'], 'failed')
        self.assertIsNone(result['integrity'])
        self.assertIsNone(result['actual_sha256'])
        self.assertEqual(result['confirmed_bytes'], 0)
        self.assertGreater(result['bytes_sent'], 0)
        self.assertEqual(result['retransmission_bytes'], result['bytes_sent'])
        self.assertGreaterEqual(result['client_submitted_bytes'], result['bytes_sent'])
        self.assertIsNone(result['overhead_percent'])
        self.assertIsNone(result['useful_kbps'])

    async def test_origin_exposes_digest_only_after_all_chunks_are_committed(self):
        from bandwidth_throttle_tester.transfer import UploadOrigin, request_origin

        origin = UploadOrigin()
        server = await asyncio.start_server(origin.handle, '127.0.0.1', 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            first = await request_origin(port, 'POST', '/chunk', b'abc', extra_headers={
                'X-Offset': 0, 'X-Total-Bytes': 6,
            })
            self.assertIsNone(first['sha256'])
            probe = await request_origin(port, 'GET', '/offset')
            self.assertIsNone(probe['sha256'])
            final = await request_origin(port, 'POST', '/chunk', b'def', extra_headers={
                'X-Offset': 3, 'X-Total-Bytes': 6,
            })
            self.assertEqual(final['sha256'], hashlib.sha256(b'abcdef').hexdigest())


class IntegrityCommandTests(unittest.TestCase):
    def test_json_result_includes_integrity_and_metric_definitions(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / 'main.py'), '--size-bytes', '1025', '--json'],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIs(result['integrity'], True)
        self.assertEqual(result['actual_sha256'], result['expected_sha256'])
        self.assertIn('bytes_sent', result['metric_definitions'])
        self.assertIn('useful_kbps', result['metric_definitions'])


if __name__ == '__main__':
    unittest.main()
