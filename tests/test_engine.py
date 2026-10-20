"""Integration tests use real loopback sockets and wall-clock pacing (no mocked sleeps)."""
import asyncio
import hashlib
import json
import time
import unittest
from bandwidth_throttle_tester.config import validate
from bandwidth_throttle_tester.throttler import Trial, respond, headers, close
from bandwidth_throttle_tester.app import Lab
PAYLOAD = bytes(range(256)) * 768

def config(phases=None, **kwargs):
    return validate({'scenario': 'custom', 'phases': phases or [{'at': 0, 'kbps': 1024}], 'delay_ms': 0, 'size_bytes': len(PAYLOAD), 'chunk_bytes': 16384, 'deadline_s': 15, 'max_retries': 8, **kwargs})

class Transfers(unittest.IsolatedAsyncioTestCase):

    async def test_shared_limit_across_concurrent_reconnections(self):
        payload = PAYLOAD[:65536]
        t = Trial(payload, config([{'at': 0, 'kbps': 1024}]), 'retry')
        t.origin = await asyncio.start_server(t.track(t.origin_handler), '127.0.0.1', 0)
        t.proxy = await asyncio.start_server(t.track(t.proxy_handler), '127.0.0.1', 0)
        try:
            started = time.monotonic()
            results = await asyncio.gather(t.request(0, payload), t.request(0, payload))
            elapsed = time.monotonic() - started
            self.assertTrue(all((r['sha256'] == hashlib.sha256(payload).hexdigest() for r in results)))
            self.assertEqual(t.result['forwarded_bytes'], 2 * len(payload))
            self.assertGreater(elapsed, 2 * len(payload) * 8 / 1024000 * 0.95)
        finally:
            for s in (t.proxy, t.origin):
                s.close()
                await s.wait_closed()
            for w in list(t.writers):
                w.transport.abort()
            await asyncio.gather(*list(t.tasks), return_exceptions=True)

class AdditionalNetworking(unittest.IsolatedAsyncioTestCase):

    async def test_cancel_large_buffered_upload_preserves_cancellation(self):
        trial = Trial(bytes(range(256)) * 8192, config([{'at': 0, 'kbps': 256}]), 'basic')
        task = asyncio.create_task(trial.run())
        await asyncio.sleep(1)
        self.assertGreater(trial.result['forwarded_bytes'], 0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)
        self.assertEqual(trial.result['status'], 'cancelled')
        self.assertFalse(trial.writers)
        self.assertFalse(trial.tasks)
        self.assertEqual(trial.data, b'')
