"""Check acknowledgement-based recovery and independent boundary trials."""
import json
from pathlib import Path
import subprocess
import sys
import unittest


class RecoveryDefinitionTests(unittest.TestCase):
    def test_recovery_requires_increased_progress_and_uses_scheduled_restoration(self):
        from bandwidth_throttle_tester.metrics import recovery_observations

        events = [
            {'kind': 'progress', 'at': 0.1, 'confirmed_bytes': 1024},
            {'kind': 'restored', 'at': 2.1, 'scheduled_at': 2},
            {'kind': 'progress', 'at': 2.2, 'confirmed_bytes': 1024},
            {'kind': 'progress', 'at': 2.6, 'confirmed_bytes': 2048},
            {'kind': 'progress', 'at': 2.8, 'confirmed_bytes': 3072},
        ]
        observations = recovery_observations(events)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]['restored_at'], 2)
        self.assertAlmostEqual(observations[0]['recovery_s'], 0.6)

    def test_observed_restoration_without_later_progress_stays_unavailable(self):
        from bandwidth_throttle_tester.metrics import recovery_observations

        self.assertEqual(recovery_observations([]), [])
        result = recovery_observations([
            {'kind': 'restored', 'at': 1.1, 'scheduled_at': 1},
            {'kind': 'upload_attempt', 'at': 1.2},
        ])
        self.assertIsNone(result[0]['recovery_s'])


class RecoveryNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def test_retried_and_resumed_trials_measure_actual_progress_recovery(self):
        from bandwidth_throttle_tester.transfer import run_upload

        settings = dict(payload_bytes=32768, bandwidth_kbps=512, timeout_s=5,
                        resume_chunk_bytes=4096,
                        phases=[{'at': 0, 'kbps': 512}, {'at': 0.2, 'kbps': 0},
                                {'at': 0.4, 'kbps': 512}])
        basic = await run_upload(**settings, strategy='basic')
        self.assertEqual(basic['recoveries'], [])
        for strategy in ('retry', 'resumable'):
            with self.subTest(strategy=strategy):
                result = await run_upload(**settings, strategy=strategy)
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(len(result['recoveries']), 1)
                recovery = result['recoveries'][0]
                self.assertEqual(recovery['restored_at'], 0.4)
                first = next(event for event in result['events']
                             if event['kind'] == 'progress' and event['at'] >= 0.4)
                self.assertAlmostEqual(recovery['recovery_s'], first['at'] - 0.4)
                self.assertGreater(recovery['recovery_s'], 0)

    async def test_deadline_after_restoration_without_progress_has_null_recovery(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(65536, strategy='retry', bandwidth_kbps=1, timeout_s=0.4,
                                  phases=[{'at': 0, 'kbps': 0}, {'at': 0.15, 'kbps': 1}])
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['recoveries']), 1)
        self.assertIsNone(result['recoveries'][0]['recovery_s'])


class BoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_sweep_runs_fresh_trials_and_keeps_failed_cells_in_denominators(self):
        from bandwidth_throttle_tester.experiments import run_boundary

        report = await run_boundary(16384, bandwidths=[512], outages=[0, 0.15],
                                    outage_at_s=0.05, timeout_s=3, resume_chunk_bytes=4096)
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['total_trials'], 6)
        self.assertEqual(len(report['results']), 6)
        self.assertEqual(len(report['summaries']), 6)
        self.assertEqual(len({row['expected_sha256'] for row in report['results']}), 1)
        for row in report['results']:
            self.assertEqual(row['trial'], 1)
            self.assertEqual(row['payload_bytes'], 16384)
            self.assertEqual(row['outage_observed'], row['outage_s'] > 0)
            if row['outage_s']:
                self.assertEqual(row['phases'][1], {'at': 0.05, 'kbps': 0})
                self.assertAlmostEqual(row['phases'][2]['at'], 0.2)
        for cell in report['summaries']:
            expected = 0 if cell['outage_s'] and cell['strategy'] == 'basic' else 1
            self.assertEqual(cell['finished_trials'], 1)
            self.assertEqual(cell['verified_successes'], expected)
            self.assertEqual(cell['success_rate'], expected)

    async def test_repeated_trials_have_independent_numbers_and_summary_counts(self):
        from bandwidth_throttle_tester.experiments import run_boundary

        report = await run_boundary(1024, bandwidths=[512, 1024], outages=[0.1],
                                    outage_at_s=5, strategies=['basic'], trials=2)
        self.assertEqual(report['total_trials'], 4)
        self.assertEqual([row['trial'] for row in report['results']], [1, 2, 1, 2])
        self.assertTrue(all(cell['finished_trials'] == 2 and cell['verified_successes'] == 2
                            for cell in report['summaries']))
        self.assertTrue(all(cell['observed_outage_trials'] == 0 for cell in report['summaries']))

    async def test_invalid_or_excessive_sweeps_are_rejected_before_execution(self):
        from bandwidth_throttle_tester.experiments import run_boundary

        invalid = [
            {'bandwidths': []}, {'bandwidths': [0]}, {'bandwidths': [float('nan')]},
            {'outages': [-1]}, {'outages': [float('inf')]}, {'trials': 0},
            {'strategies': ['basic', 'basic']}, {'timeout_s': 0},
            {'bandwidths': [8, 16, 32, 64, 128, 256],
             'outages': [0, 0.1, 0.2, 0.3, 0.4, 0.5], 'trials': 3},
        ]
        for settings in invalid:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    await run_boundary(1024, **settings)


class BoundaryCommandTests(unittest.TestCase):
    def test_cli_completes_sweep_even_when_individual_trials_fail(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / 'main.py'), '--boundary', '--bandwidths', '512',
             '--outages', '0,0.15', '--strategies', 'basic,retry', '--size-bytes', '8193',
             '--outage-at-s', '0.05', '--timeout-s', '3', '--json'],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report['mode'], 'boundary')
        self.assertEqual(len(report['results']), 4)
        self.assertTrue(any(row['status'] == 'failed' for row in report['results']))


if __name__ == '__main__':
    unittest.main()
