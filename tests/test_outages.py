"""Verify interruption and restoration on real localhost connections."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import unittest


class OutageTests(unittest.IsolatedAsyncioTestCase):
    async def wait_for_state(self, proxy, online):
        async def wait():
            while proxy.online != online:
                await asyncio.sleep(0.005)
        await asyncio.wait_for(wait(), 2)

    async def test_outage_interrupts_upload_rejects_connections_and_then_restores(self):
        from bandwidth_throttle_tester.proxy import BandwidthProxy
        from bandwidth_throttle_tester.transfer import UploadOrigin, upload_to_origin

        origin = UploadOrigin()
        server = await asyncio.start_server(origin.handle, '127.0.0.1', 0)
        async with server:
            proxy = BandwidthProxy(server.sockets[0].getsockname()[1], 512, phases=[
                {'at': 0, 'kbps': 512}, {'at': 0.15, 'kbps': 0},
                {'at': 0.65, 'kbps': 512},
            ])
            proxy_server = await asyncio.start_server(proxy.handle, '127.0.0.1', 0)
            async with proxy_server:
                try:
                    await proxy.start()
                    port = proxy_server.sockets[0].getsockname()[1]
                    with self.assertRaises((OSError, asyncio.IncompleteReadError)):
                        await asyncio.wait_for(upload_to_origin(b'x' * 65536, port), 2)
                    self.assertFalse(proxy.online)
                    self.assertEqual(origin.received, b'')
                    self.assertGreater(proxy.forwarded_bytes, 0)
                    with self.assertRaises((OSError, asyncio.IncompleteReadError)):
                        await asyncio.wait_for(upload_to_origin(b'blocked', port), 1)
                    await self.wait_for_state(proxy, True)
                    result = await asyncio.wait_for(upload_to_origin(b'restored', port), 1)
                    self.assertEqual(result['transferred_bytes'], 8)
                    self.assertEqual(origin.received, b'restored')
                    changes = [event for event in proxy.events if event['kind'] != 'started']
                    self.assertEqual([event['kind'] for event in changes], ['outage', 'restored'])
                    self.assertEqual(changes[1]['scheduled_at'], 0.65)
                    self.assertGreaterEqual(changes[1]['at'], 0.65)
                finally:
                    await proxy.close()
            self.assertFalse(proxy.tasks)

    async def test_initial_offline_phase_rejects_uploads(self):
        from bandwidth_throttle_tester.transfer import run_upload

        result = await run_upload(1024, phases=[{'at': 0, 'kbps': 0}], timeout_s=1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['transferred_bytes'], 0)
        self.assertEqual(result['forwarded_bytes'], 0)
        self.assertTrue(result['error'])


class ScheduleTests(unittest.TestCase):
    def test_invalid_phase_schedules_are_rejected(self):
        from bandwidth_throttle_tester.config import validate_phases

        for phases in ([], [{'at': 1, 'kbps': 512}],
                       [{'at': 0, 'kbps': -1}], [{'at': 0, 'kbps': float('nan')}],
                       [{'at': 0, 'kbps': 512}, {'at': 0, 'kbps': 0}],
                       [{'at': 0, 'kbps': 512}, {'at': float('inf'), 'kbps': 0}]):
            with self.subTest(phases=phases):
                with self.assertRaises(ValueError):
                    validate_phases(phases)

    def test_cli_reports_failed_upload_as_json_and_exits_nonzero(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / 'main.py'), '--scenario', 'outage', '--json'],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(completed.returncode, 1, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['transferred_bytes'], 0)
        self.assertGreater(result['forwarded_bytes'], 0)
        self.assertTrue(any(event['kind'] == 'outage' for event in result['events']))
        self.assertTrue(result['error'])


if __name__ == '__main__':
    unittest.main()
