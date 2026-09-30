"""Check the initial simulator through its command-line entry point."""
import pathlib
import re
import subprocess
import sys
import unittest


class SimulatorTests(unittest.TestCase):
    def test_default_transfer_reports_size_and_obeys_bandwidth_limit(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / 'main.py')],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('Simulation only', completed.stdout)
        self.assertIn('65536 bytes', completed.stdout)
        self.assertIn('512 kbps', completed.stdout)
        elapsed = re.search(r'Elapsed: ([0-9.]+) s', completed.stdout)
        self.assertIsNotNone(elapsed, completed.stdout)
        # Decimal kbps: 65,536 bytes * 8 / 512,000 bits per second.
        self.assertGreaterEqual(float(elapsed.group(1)), 1.024)


if __name__ == '__main__':
    unittest.main()
