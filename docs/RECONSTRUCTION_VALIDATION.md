# Additional reconstruction validation

The current application is the localhost trial/service implementation, replacing
the earlier prototype CLI. Run the full experiment without the frontend:

```powershell
python -m tests.run_demo
```

It uses a deterministic 2 MiB payload, one independent trial per strategy, and
the `demo` schedule: 2,000 kbps at 0 s, 256 kbps at 3 s, offline at 7 s, and
2,000 kbps restored at 12 s. The deadline is 120 seconds, the default commit
chunk is 32 KiB, and each request has a 20 ms configured delay. All trial data
and hashes are in [raw JSON](../validation/reconstruction-2026-10-29/demo-results.json).

These three 2 MiB demo trials are additional validation, separate from the
27-upload, 0.5 MiB evaluation used by the report. See the
[report experiment index](EXPERIMENTS.md) for that original dataset.

The demo runner writes `validation/demo-results.json` when rerun. The saved
29 October measurements linked here remain in their separate folder.

## Measurements from this reconstruction

Collected on **29 October 2026**, independently of reconstructed Git milestone
dates. These are observations from one local run, not universal expected timings.

| Strategy | Outcome | Seconds | Proxy ingress bytes | Repeated/discarded bytes | Retries | Hash integrity |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| basic | failed | 7.01 | 864,256 | 864,256 | 0 | None |
| retry | completed | 21.39 | 2,961,408 | 864,256 | 5 | True |
| resumable | completed | 20.01 | 2,125,824 | 28,672 | 5 | True |

Basic stops at the outage. Retry resends the full payload after backoff.
Resumable probes the committed offset through the proxy and preserves complete
chunks. The demonstration asserts Basic fails, both recovering strategies verify
their hashes and observe restoration, and Resumable repeats less body data.

## Further collection

Use `Lab.start` with `mode: boundary` for serial bandwidth/outage comparisons;
the frontend exposes these controls. Each cell and
strategy receives fresh services, counters, origin data, retry budget, and clock.
For example:

```python
import asyncio
from bandwidth_throttle_tester.app import Lab

async def compare():
    lab = Lab()
    job = lab.start({'mode': 'boundary', 'size_bytes': 262144,
                     'bandwidths': [256, 1024], 'outages': [0, 2],
                     'trials': 3, 'delay_ms': 0, 'deadline_s': 30})
    await lab.task
    return lab.snapshot(job)

results = asyncio.run(compare())
```

Preserve complete JSON/CSV exports and actual collection date, source revision,
Python version, configuration, and background load. Inspect phase events to see
whether each upload actually reached its outage. Count failed trials in success
rate denominators, exclude cancelled trials, and do not treat short failure time
as fast completion. Use the [report template](EXPERIMENT_REPORT_TEMPLATE.md) and
[metric definitions](METRICS.md).
