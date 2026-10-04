"""Exercise preset selection and machine-readable simulation results."""
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReportingTests(unittest.TestCase):
    def run_cli(self, *arguments):
        # Presets must be found relative to the application, not the caller.
        return subprocess.run(
            [sys.executable, str(ROOT / 'main.py'), *arguments],
            cwd=ROOT / 'docs', capture_output=True, text=True, timeout=10,
        )

    def test_low_bandwidth_preset_produces_complete_json_report(self):
        completed = self.run_cli('--scenario', 'low-bandwidth', '--json')
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result['scenario_id'], 'low-bandwidth')
        self.assertEqual(result['payload_bytes'], 65536)
        self.assertEqual(result['bandwidth_kbps'], 256)
        self.assertEqual(result['transferred_bytes'], 65536)
        self.assertGreaterEqual(result['elapsed_s'], 2.048)
        self.assertEqual(result['status'], 'completed')
        self.assertIsNone(result['error'])
        self.assertEqual(result['mode'], 'simulation')

    def test_explicit_settings_override_preset_defaults(self):
        completed = self.run_cli(
            '--scenario', 'baseline', '--size-bytes', '1025',
            '--bandwidth-kbps', '128', '--chunk-bytes', '512', '--json',
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result['scenario_id'], 'baseline')
        self.assertEqual(result['payload_bytes'], 1025)
        self.assertEqual(result['bandwidth_kbps'], 128)
        self.assertEqual(result['chunk_bytes'], 512)
        self.assertEqual(result['transferred_bytes'], 1025)

    def test_unknown_preset_is_rejected_without_a_result(self):
        completed = self.run_cli('--scenario', 'missing', '--json')
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, '')
        self.assertIn('invalid choice', completed.stderr)


if __name__ == '__main__':
    unittest.main()
