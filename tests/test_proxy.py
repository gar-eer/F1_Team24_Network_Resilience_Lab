"""Check measured body pacing over actual loopback connections."""
import asyncio
import time
import unittest


class ProxyTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_duration_changes_with_configured_rate(self):
        from bandwidth_throttle_tester.transfer import run_upload

        durations = {}
        for rate in (128, 256):
            result = await run_upload(8193, chunk_bytes=1000, bandwidth_kbps=rate)
            self.assertEqual(result['transferred_bytes'], 8193)
            self.assertEqual(result['proxy_ingress_bytes'], 8193)
            self.assertEqual(result['forwarded_bytes'], 8193)
            self.assertGreaterEqual(result['elapsed_s'], 8193 * 8 / (rate * 1000))
            durations[rate] = result['elapsed_s']
        self.assertGreater(durations[128], durations[256] + 0.1)

    async def test_concurrent_connections_share_one_bandwidth_allowance(self):
        from bandwidth_throttle_tester.proxy import BandwidthProxy
        from bandwidth_throttle_tester.transfer import UploadOrigin, upload_to_origin

        origin = UploadOrigin()
        origin_server = await asyncio.start_server(origin.handle, '127.0.0.1', 0)
        async with origin_server:
            origin_port = origin_server.sockets[0].getsockname()[1]
            proxy = BandwidthProxy(origin_port, bandwidth_kbps=128)
            proxy_server = await asyncio.start_server(proxy.handle, '127.0.0.1', 0)
            try:
                async with proxy_server:
                    port = proxy_server.sockets[0].getsockname()[1]
                    payload = bytes(range(256)) * 32 + b'x'
                    started = time.perf_counter()
                    results = await asyncio.wait_for(asyncio.gather(
                        upload_to_origin(payload, port), upload_to_origin(payload, port),
                    ), 5)
                    elapsed = time.perf_counter() - started
            finally:
                await proxy.close()
        self.assertGreaterEqual(elapsed, 2 * len(payload) * 8 / 128000)
        self.assertEqual(proxy.forwarded_bytes, 2 * len(payload))
        self.assertEqual(origin.received, payload)
        self.assertTrue(all(r['transferred_bytes'] == len(payload) for r in results))

    async def test_deadline_stops_a_slow_transfer(self):
        from bandwidth_throttle_tester.transfer import run_upload

        started = time.perf_counter()
        result = await run_upload(65536, bandwidth_kbps=1, timeout_s=0.1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'Upload deadline exceeded')
        self.assertLess(time.perf_counter() - started, 2)


if __name__ == '__main__':
    unittest.main()
