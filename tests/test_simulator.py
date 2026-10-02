"""Check the initial simulator through its command-line entry point."""
import pathlib
import re
import subprocess
import sys
import unittest


class SimulatorTests(unittest.TestCase):
    def test_custom_rates_and_partial_chunk(self):
        from bandwidth_throttle_tester.throttler import simulate_transfer

        for rate in (512, 1024):
            with self.subTest(rate=rate):
                transferred, elapsed = simulate_transfer(
                    payload_bytes=8193, bandwidth_kbps=rate, chunk_bytes=4096,
                )
                self.assertEqual(transferred, 8193)
                self.assertGreaterEqual(elapsed, 8193 * 8 / (rate * 1000))

    def test_invalid_settings_are_rejected(self):
        from bandwidth_throttle_tester.throttler import simulate_transfer

        invalid = (
            {'payload_bytes': 0}, {'payload_bytes': -1},
            {'payload_bytes': 1.5}, {'payload_bytes': True},
            {'bandwidth_kbps': 0}, {'bandwidth_kbps': -1},
            {'bandwidth_kbps': float('nan')},
            {'bandwidth_kbps': float('inf')},
            {'chunk_bytes': 0}, {'chunk_bytes': 1.5},
        )
        for settings in invalid:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    simulate_transfer(**settings)

    def test_command_line_accepts_custom_settings_and_rejects_invalid_rate(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / 'main.py'), '--size-bytes', '1025',
             '--bandwidth-kbps', '256', '--chunk-bytes', '512'],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('1025 bytes at 256 kbps', completed.stdout)
        invalid = subprocess.run(
            [sys.executable, str(root / 'main.py'), '--bandwidth-kbps', 'nan'],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertIn('positive finite number', invalid.stderr)

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
