"""Local dashboard/API and serial experiment scheduler (standard library only)."""
import asyncio
import csv
import hashlib
import io
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from .config import validate, number, SCENARIOS
from .metrics import METRICS
from .throttler import Trial, headers, close

STATIC = Path(__file__).parent / 'static'

class Lab:
    def __init__(self):
        self.jobs = {}
        self.payload = None
        self.payload_name = None
        self.task = None
        self.clients = set()

    def active(self):
        return self.task is not None and not self.task.done()

    def start(self, raw):
        if self.active():
            raise ValueError('An experiment is already running. Cancel it before starting another.')
        if not isinstance(raw, dict):
            raise ValueError('Configuration must be an object')
        if raw.get('use_file'):
            if self.payload is None:
                raise ValueError('Choose a file first')
            raw = {**raw, 'size_bytes': len(self.payload)}
        config = validate(raw)
        mode = raw.get('mode', 'compare')
        if mode not in ('compare', 'boundary'):
            raise ValueError('Unknown experiment mode')
        uploaded = raw.get('use_file', False)
        if uploaded and self.payload is None:
            raise ValueError('Choose a file first')
        payload = self.payload if uploaded else bytes(range(256)) * (config['size_bytes'] // 256) + bytes(range(config['size_bytes'] % 256))
        config['size_bytes'] = len(payload)
        cells = [config]
        if mode == 'boundary':
            bands = raw.get('bandwidths', [256, 1024, 2048])
            outages = raw.get('outages', [0, 2, 5])
            if not isinstance(bands, list) or not isinstance(outages, list) or not 1 <= len(bands) <= 6 or not 1 <= len(outages) <= 6:
                raise ValueError('Use 1-6 bandwidths and outage durations')
            bands = sorted(set(number(v, 'Sweep kbps', 8, 100000) for v in bands))
            outages = sorted(set(number(v, 'Outage seconds', 0, 120) for v in outages))
            cells = []
            for band in bands:
                for outage in outages:
                    phases = [{'at': 0, 'kbps': band}]
                    if outage:
                        phases += [{'at': 1, 'kbps': 0}, {'at': 1 + outage, 'kbps': band}]
                    cells.append({**config, 'scenario': 'boundary', 'phases': phases, 'bandwidth_kbps': band, 'outage_s': outage})
        total = len(cells) * len(config['strategies']) * config['trials']
        if total > 300:
            raise ValueError('Limit a sweep to 300 trials')
        job_id = secrets.token_hex(6)
        job = {'id': job_id, 'created_at': datetime.now(timezone.utc).isoformat(), 'mode': mode,
               'status': 'running', 'config': config, 'payload_name': self.payload_name if uploaded else 'Generated deterministic payload',
               'payload_sha256': hashlib.sha256(payload).hexdigest(), 'total': total, 'results': [], 'active': None, 'error': None}
        # Keep the ten most recent jobs; payload data is not retained in result history.
        while len(self.jobs) >= 10:
            del self.jobs[next(iter(self.jobs))]
        self.jobs[job_id] = job
        self.task = asyncio.create_task(self.run(job, payload, cells))
        return job

    async def run(self, job, payload, cells):
        try:
            for config in cells:
                for trial_number in range(1, config['trials'] + 1):
                    for strategy in config['strategies']:
                        trial = Trial(payload, config, strategy, trial_number)
                        job['active'] = trial.result
                        try:
                            await trial.run()
                        finally:
                            job['results'].append(trial.result)
                            job['active'] = None
            job['status'] = 'completed'
        except asyncio.CancelledError:
            job['status'] = 'cancelled'
        except Exception as exc:
            job['status'] = 'failed'
            job['error'] = str(exc)

    def summaries(self, job):
        groups = {}
        for r in job['results']:
            c = r['config']
            key = (r['strategy'], c.get('bandwidth_kbps'), c.get('outage_s'))
            g = groups.setdefault(key, {'strategy': key[0], 'bandwidth_kbps': key[1], 'outage_s': key[2], 'successes': 0, 'trials': 0, 'cancelled': 0})
            if r['status'] == 'cancelled':
                g['cancelled'] += 1
            else:
                g['trials'] += 1
                g['successes'] += int(r['status'] == 'completed' and r['integrity'] is True)
        for g in groups.values():
            g['success_rate'] = g['successes'] / g['trials'] if g['trials'] else None
        return list(groups.values())

    def snapshot(self, job):
        return {**job, 'summaries': self.summaries(job)}

    async def cancel(self):
        if self.active():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                # The task can be cancelled before its coroutine gets its first turn.
                pass
            for job in self.jobs.values():
                if job['status'] == 'running':
                    job['status'] = 'cancelled'

    async def handle(self, reader, writer):
        self.clients.add(asyncio.current_task())
        try:
            async with asyncio.timeout(30):
                request, fields = await headers(reader)
                if len(request) != 3:
                    raise ValueError('Malformed request')
                method, target, _ = request
                host = fields.get('host', '').split(':')[0]
                if host not in ('127.0.0.1', 'localhost'):
                    await self.send(writer, 403, {'error': 'Local host required'})
                    return
                origin = fields.get('origin')
                if origin and origin != 'http://' + fields.get('host', ''):
                    await self.send(writer, 403, {'error': 'Cross-origin requests are disabled'})
                    return
                length = int(fields.get('content-length', 0))
                if length < 0 or length > 32 * 1024**2:
                    raise ValueError('Request limit is 32 MiB')
                if fields.get('transfer-encoding'):
                    raise ValueError('Chunked requests are not supported')
                body = await reader.readexactly(length)
                url = urlsplit(target)
                if method == 'GET' and url.path in ('/', '/app.js', '/theme.js', '/style.css'):
                    name = 'index.html' if url.path == '/' else url.path[1:]
                    mime = {'index.html': 'text/html; charset=utf-8', 'app.js': 'text/javascript; charset=utf-8', 'theme.js': 'text/javascript; charset=utf-8', 'style.css': 'text/css; charset=utf-8'}[name]
                    await self.send(writer, 200, (STATIC / name).read_bytes(), mime)
                elif method == 'GET' and url.path == '/api/meta':
                    await self.send(writer, 200, {'scenarios': SCENARIOS, 'metrics': METRICS})
                elif method == 'POST' and url.path == '/api/payload':
                    if self.active():
                        raise ValueError('Wait for the active experiment before replacing the payload')
                    if not 1024 <= len(body) <= 32 * 1024**2:
                        raise ValueError('File must be between 1 KiB and 32 MiB')
                    self.payload = body
                    self.payload_name = parse_qs(url.query).get('name', ['Selected file'])[0][:200]
                    await self.send(writer, 200, {'name': self.payload_name, 'size_bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
                elif method == 'POST' and url.path == '/api/experiments':
                    raw = json.loads(body)
                    if not isinstance(raw, dict):
                        raise ValueError('Configuration must be an object')
                    job = self.start(raw)
                    await self.send(writer, 202, {'id': job['id']})
                elif method == 'POST' and url.path == '/api/cancel':
                    await self.cancel()
                    await self.send(writer, 200, {'status': 'cancelled'})
                elif method == 'GET' and url.path == '/api/experiments':
                    await self.send(writer, 200, [{'id': j['id'], 'status': j['status']} for j in self.jobs.values()])
                elif method == 'GET' and url.path.startswith('/api/experiments/'):
                    parts = url.path.strip('/').split('/')
                    job = self.jobs.get(parts[2])
                    if job is None:
                        await self.send(writer, 404, {'error': 'Experiment not found (history is session-only)'})
                    elif len(parts) == 4 and parts[3] == 'csv':
                        out = io.StringIO(newline='')
                        keys = ['strategy', 'trial', 'status', 'payload_bytes', 'elapsed_s', 'bytes_sent', 'client_submitted_bytes', 'forwarded_bytes', 'confirmed_bytes', 'retransmission_bytes', 'overhead_percent', 'retry_count', 'useful_kbps', 'integrity', 'expected_sha256', 'actual_sha256', 'recoveries', 'error', 'config']
                        rows = csv.DictWriter(out, fieldnames=keys)
                        rows.writeheader()
                        for r in job['results']:
                            rows.writerow({k: json.dumps(r.get(k)) if isinstance(r.get(k), (dict, list)) else r.get(k) for k in keys})
                        await self.send(writer, 200, out.getvalue().encode(), 'text/csv; charset=utf-8', 'results.csv')
                    else:
                        await self.send(writer, 200, {**self.snapshot(job), 'metric_definitions': METRICS}, download='experiment.json' if url.query == 'download' else None)
                else:
                    await self.send(writer, 404, {'error': 'Not found'})
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            await self.send(writer, 400, {'error': str(exc)})
        except (ConnectionError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, TimeoutError):
            pass
        finally:
            await close(writer)
            self.clients.discard(asyncio.current_task())

    async def send(self, writer, status, body, mime='application/json; charset=utf-8', download=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, allow_nan=False).encode()
        extra = f'Content-Disposition: attachment; filename="{download}"\r\n' if download else ''
        writer.write(f'HTTP/1.1 {status} Result\r\nContent-Type: {mime}\r\nContent-Length: {len(body)}\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n{extra}Connection: close\r\n\r\n'.encode() + body)
        await writer.drain()

async def serve(port=8765):
    lab = Lab()
    server = await asyncio.start_server(lab.handle, '127.0.0.1', port)
    print(f'Network Resilience Lab: http://127.0.0.1:{server.sockets[0].getsockname()[1]}', flush=True)
    try:
        await server.serve_forever()
    finally:
        server.close()
        await lab.cancel()
        for task in list(lab.clients):
            task.cancel()
        await asyncio.gather(*list(lab.clients), return_exceptions=True)
        await server.wait_closed()
