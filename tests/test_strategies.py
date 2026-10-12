"""Compare single-attempt and full-file retry behavior over real sockets."""
import json
from pathlib import Path
import subprocess
import sys
import unittest


class StrategyTests(unittest.IsolatedAsyncioTestCase):
    async def test_basic_fails_but_retry_restarts_full_file_after_restoration(self):
        from bandwidth_throttle_tester.transfer import run_upload

        settings = dict(payload_bytes=32768, bandwidth_kbps=512, timeout_s=5,
                        phases=[{'at': 0, 'kbps': 512}, {'at': 0.2, 'kbps': 0},
                                {'at': 0.4, 'kbps': 512}])
        basic = await run_upload(**settings, strategy='basic')
        retry = await run_upload(**settings, strategy='retry', max_retries=3)
        self.assertEqual(basic['status'], 'failed')
        self.assertEqual(basic['attempt_count'], 1)
        self.assertEqual(basic['retry_count'], 0)
        self.assertEqual(retry['status'], 'completed')
        self.assertEqual(retry['transferred_bytes'], 32768)
        self.assertGreater(retry['forwarded_bytes'], 32768)
        self.assertGreater(retry['proxy_ingress_bytes'], 32768)
        self.assertEqual(retry['retry_count'], retry['attempt_count'] - 1)
        self.assertGreaterEqual(retry['retry_count'], 1)
        self.assertTrue(any(event['kind'] == 'restored' for event in retry['events']))
        self.assertGreaterEqual(retry['elapsed_s'], 0.4 + 32768 * 8 / 512000)

    async def test_successful_first_attempt_does_not_count_a_retry(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(1025, strategy='retry')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['attempt_count'], 1)
        self.assertEqual(result['retry_count'], 0)

    async def test_retry_budget_limits_total_additional_attempts(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(1024, strategy='retry', max_retries=2,
                                  phases=[{'at': 0, 'kbps': 0}], timeout_s=5)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['attempt_count'], 3)
        self.assertEqual(result['retry_count'], 2)
        self.assertIn('Retry budget exhausted', result['error'])
        delays = [event['delay_s'] for event in result['events']
                  if event['kind'] == 'retry_scheduled']
        self.assertEqual(delays, [0.25, 0.5])

    async def test_deadline_includes_backoff_without_counting_unstarted_retry(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(1024, strategy='retry', max_retries=5,
                                  phases=[{'at': 0, 'kbps': 0}], timeout_s=0.1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'Upload deadline exceeded')
        self.assertEqual(result['attempt_count'], 1)
        self.assertEqual(result['retry_count'], 0)

    async def test_invalid_strategy_settings_are_rejected(self):
        from bandwidth_throttle_tester.transfer import run_upload

        for settings in ({'strategy': 'unknown'}, {'max_retries': -1},
                         {'max_retries': 1.5}, {'max_retries': True}):
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    await run_upload(1024, **settings)


class StrategyCommandTests(unittest.TestCase):
    def test_cli_selects_retry_and_reports_recovery_after_outage(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / 'main.py'), '--strategy', 'retry',
             '--max-retries', '3', '--size-bytes', '8193', '--bandwidth-kbps', '256',
             '--outage-at-s', '0.15', '--outage-duration-s', '0.2', '--json'],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result['strategy'], 'retry')
        self.assertEqual(result['max_retries'], 3)
        self.assertEqual(result['status'], 'completed')
        self.assertGreaterEqual(result['retry_count'], 1)


if __name__ == '__main__':
    unittest.main()
