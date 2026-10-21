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
    return validate({'scenario':'custom', 'phases': phases or [{'at':0,'kbps':1024}],
                     'delay_ms':0, 'size_bytes':len(PAYLOAD), 'chunk_bytes':16384,
                     'deadline_s':15, 'max_retries':8, **kwargs})

class Transfers(unittest.IsolatedAsyncioTestCase):
    async def test_real_body_and_sha256(self):
        t = Trial(PAYLOAD, config(), 'basic')
        r = await t.run()
        self.assertEqual(r['status'], 'completed', r['error'])
        self.assertEqual(r['bytes_sent'], len(PAYLOAD))
        self.assertEqual(r['forwarded_bytes'], len(PAYLOAD))
        self.assertEqual(r['actual_sha256'], hashlib.sha256(PAYLOAD).hexdigest())
        self.assertEqual(r['retransmission_bytes'], 0)
        self.assertTrue(r['integrity'])
        self.assertEqual(t.data, b'')
        self.assertFalse(t.writers)
        self.assertFalse(t.tasks)

    async def test_bandwidth_measurably_changes_duration(self):
        payload = PAYLOAD[:65536]
        fast = await Trial(payload, config([{'at':0,'kbps':1024}]), 'basic').run()
        slow = await Trial(payload, config([{'at':0,'kbps':256}]), 'basic').run()
        self.assertTrue(fast['integrity'] and slow['integrity'])
        self.assertGreater(slow['elapsed_s'], fast['elapsed_s'] * 2.8)
        self.assertGreater(slow['elapsed_s'], 65536*8/256000*.95)
        self.assertLess(slow['elapsed_s'], 65536*8/256000*1.6)

    async def test_basic_fails_on_connection_interruption(self):
        c = config([{'at':0,'kbps':1024},{'at':.35,'kbps':0},{'at':.8,'kbps':1024}])
        r = await Trial(PAYLOAD,c,'basic').run()
        self.assertEqual(r['status'],'failed')
        self.assertGreater(r['forwarded_bytes'],0)
        self.assertLess(r['forwarded_bytes'],len(PAYLOAD))
        self.assertEqual(r['retry_count'],0)
        self.assertIsNone(r['integrity'])

    async def test_retry_restarts_and_resume_preserves_confirmed_progress(self):
        c = config([{'at':0,'kbps':1024},{'at':.35,'kbps':0},{'at':.8,'kbps':1024}])
        retry = await Trial(PAYLOAD,c,'retry').run()
        resume = await Trial(PAYLOAD,c,'resumable').run()
        for r in (retry,resume):
            self.assertEqual(r['status'],'completed',r['error'])
            self.assertTrue(r['integrity'])
            self.assertGreater(r['retry_count'],0)
            self.assertIsNotNone(r['recoveries'][0]['recovery_s'])
        self.assertGreater(retry['bytes_sent'],len(PAYLOAD))
        self.assertTrue(any(e['kind']=='restart' for e in retry['events']))
        offsets = [e['message'] for e in resume['events'] if e['kind']=='resume']
        self.assertTrue(any('offset 0 ' not in s for s in offsets), offsets)
        self.assertLess(resume['retransmission_bytes'],retry['retransmission_bytes'])
        self.assertEqual(resume['confirmed_bytes'],len(PAYLOAD))

    async def test_shared_limit_across_concurrent_reconnections(self):
        payload=PAYLOAD[:65536]
        t=Trial(payload,config([{'at':0,'kbps':1024}]),'retry')
        t.origin=await asyncio.start_server(t.track(t.origin_handler),'127.0.0.1',0)
        t.proxy=await asyncio.start_server(t.track(t.proxy_handler),'127.0.0.1',0)
        try:
            started=time.monotonic()
            results=await asyncio.gather(t.request(0,payload),t.request(0,payload))
            elapsed=time.monotonic()-started
            self.assertTrue(all(r['sha256']==hashlib.sha256(payload).hexdigest() for r in results))
            self.assertEqual(t.result['forwarded_bytes'],2*len(payload))
            self.assertGreater(elapsed,2*len(payload)*8/1024000*.95)
        finally:
            for s in (t.proxy,t.origin):
                s.close()
                await s.wait_closed()
            for w in list(t.writers):w.transport.abort()
            await asyncio.gather(*list(t.tasks),return_exceptions=True)

    async def test_sudden_reduction_uses_new_limit(self):
        r=await Trial(PAYLOAD[:65536],config([{'at':0,'kbps':1024},{'at':.15,'kbps':128}]),'basic').run()
        self.assertEqual(r['status'],'completed')
        self.assertGreater(r['elapsed_s'],2.5)
        self.assertTrue(any('128 kbps' in e['message'] for e in r['events']))

    async def test_repeated_outages(self):
        c=config([{'at':0,'kbps':1024},{'at':.2,'kbps':0},{'at':.4,'kbps':1024},{'at':.7,'kbps':0},{'at':.9,'kbps':1024}])
        r=await Trial(PAYLOAD,c,'resumable').run()
        self.assertTrue(r['integrity'],r['error'])
        self.assertEqual(len(r['recoveries']),2)
        self.assertTrue(all(v['recovery_s'] is not None for v in r['recoveries']))

    async def test_bounded_retry_exhaustion(self):
        r=await Trial(PAYLOAD,config([{'at':0,'kbps':0}],max_retries=2),'retry').run()
        self.assertEqual(r['status'],'failed')
        self.assertEqual(r['retry_count'],2)
        self.assertIn('budget',r['error'])
        self.assertEqual(r['bytes_sent'],0)

    async def test_basic_does_not_retry_origin_error(self):
        class BrokenOrigin(Trial):
            async def origin_handler(self,reader,writer):
                await headers(reader)
                await respond(writer,503,{'error':'Origin unavailable'})
        r=await BrokenOrigin(PAYLOAD[:4096],config(),'basic').run()
        self.assertEqual(r['status'],'failed')
        self.assertEqual(r['retry_count'],0)

    async def test_deadline_and_cancellation_cleanup(self):
        t=Trial(PAYLOAD,config([{'at':0,'kbps':64}],deadline_s=.2),'resumable')
        r=await t.run()
        self.assertEqual(r['status'],'failed')
        self.assertIn('deadline',r['error'])
        self.assertLess(r['elapsed_s'],1)
        t=Trial(PAYLOAD,config([{'at':0,'kbps':64}]),'retry')
        task=asyncio.create_task(t.run())
        await asyncio.sleep(.15)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await asyncio.wait_for(task,1)
        self.assertEqual(t.result['status'],'cancelled')
        self.assertFalse(t.writers)
        self.assertFalse(t.tasks)
        self.assertEqual(t.data,b'')

class AdditionalNetworking(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_large_buffered_upload_preserves_cancellation(self):
        # A small payload does not exercise the socket-close timeout path.
        trial=Trial(bytes(range(256))*8192,config([{'at':0,'kbps':256}]),'basic')
        task=asyncio.create_task(trial.run())
        await asyncio.sleep(1)
        self.assertGreater(trial.result['forwarded_bytes'],0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task,2)
        self.assertEqual(trial.result['status'],'cancelled')
        self.assertFalse(trial.writers)
        self.assertFalse(trial.tasks)
        self.assertEqual(trial.data,b'')


    async def test_delay_is_applied_to_real_request(self):
        r=await Trial(PAYLOAD[:4096],config([{'at':0,'kbps':100000}],delay_ms=120),'basic').run()
        self.assertTrue(r['integrity'])
        self.assertGreaterEqual(r['elapsed_s'],.12)

    async def test_origin_hash_mismatch_is_failure(self):
        class CorruptOrigin(Trial):
            async def origin_handler(self,reader,writer):
                _, fields=await headers(reader)
                body=await reader.readexactly(int(fields['content-length']))
                self.data.extend(body)
                self.data[0]^=1
                await respond(writer,200,{'offset':len(self.data),'sha256':hashlib.sha256(self.data).hexdigest()})
        r=await CorruptOrigin(PAYLOAD[:8192],config(),'basic').run()
        self.assertEqual(r['status'],'failed')
        self.assertFalse(r['integrity'])
        self.assertIn('SHA-256',r['error'])
        self.assertIsNone(r['useful_kbps'])

class Scheduler(unittest.IsolatedAsyncioTestCase):
    async def test_immediate_cancel_before_first_task_turn(self):
        lab=Lab()
        job=lab.start({})
        await lab.cancel()
        self.assertEqual(job['status'],'cancelled')
        self.assertFalse(lab.active())
        self.assertEqual(job['results'],[])

    async def test_sweep_and_serial_fairness(self):
        lab=Lab()
        job=lab.start({'mode':'boundary','size_bytes':8192,'trials':2,'bandwidths':[1024],
                       'outages':[0,.15],'delay_ms':0,'deadline_s':2})
        await lab.task
        self.assertEqual(job['status'],'completed')
        self.assertEqual(len(job['results']),12)
        self.assertEqual(len(lab.summaries(job)),6)
        self.assertTrue(all(r['integrity'] for r in job['results']))
        self.assertEqual(len({r['expected_sha256'] for r in job['results']}),1)
        self.assertTrue(all(r['events'][0]['at']<.1 for r in job['results']))

    async def test_cancel_and_reject_overlapping_jobs(self):
        lab=Lab()
        job=lab.start({'scenario':'low'})
        with self.assertRaises(ValueError):lab.start({})
        await asyncio.sleep(.1)
        await lab.cancel()
        self.assertEqual(job['status'],'cancelled')
        self.assertEqual(job['results'][0]['status'],'cancelled')
        self.assertEqual(lab.summaries(job)[0]['trials'],0)

    async def test_api_file_selection_exports_validation_and_origin_guard(self):
        lab=Lab()
        server=await asyncio.start_server(lab.handle,'127.0.0.1',0)
        port=server.sockets[0].getsockname()[1]
        async def request(method,path,body=b'',extra=''):
            reader,writer=await asyncio.open_connection('127.0.0.1',port)
            writer.write(f'{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: {len(body)}\r\n{extra}\r\n'.encode()+body)
            await writer.drain()
            status,fields=await headers(reader)
            data=await reader.readexactly(int(fields['content-length']))
            await close(writer)
            return int(status[1]),data
        try:
            self.assertEqual((await request('GET','/api/meta'))[0],200)
            self.assertEqual((await request('POST','/api/experiments',b'[]'))[0],400)
            self.assertEqual((await request('POST','/api/payload',b'x'*8192,'Origin: https://elsewhere.invalid\r\n'))[0],403)
            status,body=await request('POST','/api/payload?name=test.bin',b'abc12345'*1024)
            self.assertEqual(status,200)
            raw=json.dumps({'scenario':'stable','strategies':['resumable'],'use_file':True,'delay_ms':0}).encode()
            status,body=await request('POST','/api/experiments',raw)
            self.assertEqual(status,202)
            job_id=json.loads(body)['id']
            await lab.task
            status,body=await request('GET',f'/api/experiments/{job_id}')
            job=json.loads(body)
            self.assertTrue(job['results'][0]['integrity'])
            self.assertEqual(job['results'][0]['payload_bytes'],8192)
            self.assertEqual(job['payload_name'],'test.bin')
            status,body=await request('GET',f'/api/experiments/{job_id}/csv')
            self.assertEqual(status,200)
            self.assertIn(b'expected_sha256',body)
            self.assertIn(b'resumable',body)
        finally:
            await lab.cancel()
            server.close()
            await server.wait_closed()
            for task in list(lab.clients):task.cancel()
            await asyncio.gather(*list(lab.clients),return_exceptions=True)

class Validation(unittest.TestCase):
    def test_invalid_settings(self):
        for raw in ({'size_bytes':-1},{'trials':1.5},{'deadline_s':float('nan')},
                    {'strategies':[]},{'strategies':['basic','basic']}, {'scenario':'nope'},
                    {'phases':[{'at':1,'kbps':100}]},{'phases':[{'at':0,'kbps':-1}]},
                    {'max_retries':31},{'delay_ms':True}):
            with self.subTest(raw=raw),self.assertRaises(ValueError):validate(raw)

if __name__=='__main__':unittest.main()
