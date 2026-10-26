# Using the dashboard

Run `python main.py` and open http://127.0.0.1:8765. Start with generated 2 MiB,
Recovery demo, all three strategies, one trial, and the 120-second deadline.
The comparison normally takes around 45-60 seconds on an otherwise idle machine.

The live chart shows measured forwarded throughput and the scheduled rate.
Confirmed progress means committed chunks or complete full-file requests, so
Basic/Retry may stay at zero until a whole upload is acknowledged. Events expose
outages, backoff, retries, offset probes, recovery, and hash verification.

Click a finished row or use Enter/Space to inspect its timeline, hashes, byte
counters, and exact configuration. Export JSON for full traces or CSV for one
row per finished trial. During execution, exports are only snapshots.

Choose Failure boundaries for a serial grid of bandwidths and outage durations.
Inspect events to distinguish a completed upload that experienced disruption
from a small upload that finished before it. Cancel stops active and queued work.

The responsive layout keeps configuration, monitoring, results, and help usable
at narrower widths. The release's final theme milestone adds light-mode controls.
