# Development

Use Python 3.11 or newer. The application has no third-party dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe main.py
python -m unittest discover -v
python -m tests.run_demo
```

The service listens on `127.0.0.1:8765`; change its port with `--port`.
The demo writes real results to `validation/demo-results.json`. The tests use
real localhost sockets and elapsed time, so local network permission is needed.
Use repeated experiments for comparisons because machine scheduling affects timing.

Backend code is in `app.py`, `throttler.py`, `config.py`, and `metrics.py`.
The browser assets are in `bandwidth_throttle_tester/static/`. Tests cover real
bytes/hashes, rate changes, outages, retries, offset resumption, global budgets,
cancellation, serial fairness, exports, input validation, and origin guards.

Start focused branches from `main`, include relevant validation in each commit
and PR, and integrate with merge commits. Authors and committers use their own
identities. Contributor-owned merges preserve the intended 60:40 overall
reconstruction allocation. See [contributing](../CONTRIBUTING.md) and
[history provenance](HISTORY_RECONSTRUCTION.md).
