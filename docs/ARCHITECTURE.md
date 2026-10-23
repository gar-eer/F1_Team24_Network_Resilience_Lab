# Architecture

```text
Browser -> localhost dashboard/API -> serial trial scheduler
                                      |
Python upload client -> disruption proxy -> upload origin in memory
```

`app.py` handles control requests, payload selection, one active experiment,
serial comparison/boundary trials, cancellation, session history, and exports.
The HTTP control path remains responsive while upload trials run.

`throttler.py` owns each trial's origin, proxy, client, shared body-rate scheduler,
absolute phase monitor, counters, samples, retry/resume behavior, hash checks,
and cleanup. Origin/proxy use fresh automatically assigned loopback ports.
Complete requests/chunks commit atomically. Offset probes use the same proxy.

`config.py` validates finite bounded settings and supplies presets. `metrics.py`
defines observation points and availability. Static browser assets are separate
from the engine and communicate only with its HTTP API.

Trials share identical payload/settings but no origin state, clocks, or budgets.
This tests connection recovery with an in-memory origin, not durable server-crash
recovery or packet-level emulation. See [metrics](METRICS.md).
