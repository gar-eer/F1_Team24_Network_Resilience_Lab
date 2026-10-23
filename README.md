> Frontend assets arrive in the next milestone. The API and recovery demo are available now.

# Network Resilience Lab

A local upload laboratory that answers: **when connectivity slows or disconnects, does an upload finish correctly, how quickly does durable progress return, and how much application data is wasted?**

The old delay loop and artificial quality scores have been replaced with real HTTP uploads over localhost TCP sockets, a paced disruption proxy, a hash-verifying upload origin, and a live web dashboard. No third-party packages or internet connection are required.

## Run on Windows

Requires Python **3.11 or newer** (tested here on Windows with Python 3.13.13). In PowerShell, from this directory:

```powershell
python main.py
```

Open **http://127.0.0.1:8765**. If Windows uses the Python launcher, `py -3 main.py` also works. Stop the server with Ctrl+C. To use a different dashboard port:

```powershell
python main.py --port 9000
```

The dashboard, proxy and origin bind to **127.0.0.1**. Proxy and origin ports are assigned automatically per trial. No installation step is needed; `requirements.txt` documents the standard-library-only environment. If a sandbox blocks local sockets, run from an ordinary local terminal or grant localhost network permission.

## First experiment

1. Keep **Generate payload**, **2 MiB**, **Recovery demo**, all three strategies, one trial and the 120-second deadline.
2. Select **Start experiment**. Each strategy runs separately from time zero. A full comparison usually takes approximately 45–60 seconds on an otherwise idle machine.
3. Inspect throughput, server-confirmed progress, network limit, retry and recovery events. Basic/Retry commit the whole file only after their request completes, so their confirmed progress stays at zero during an incomplete full-file request. Forwarded bytes and throughput still update live.
4. Click a completed row to inspect its timeline, hashes, byte counters and exact configuration. Export CSV or JSON before stopping the application.
5. Use **Cancel experiment** to stop the current transfer and queued trials. Connections and temporary origin data are cleaned up before cancellation completes.

A file selection sends the actual file into local memory, then the Python upload client uses those exact bytes for all strategies. That initial browser-to-dashboard upload is **outside** experiment timing and bypasses the proxy. Files must be 1 KiB–32 MiB. Generated payloads repeat byte values 0–255 deterministically. Files and partial bodies are never written to disk by the application; only explicit exports persist results.

## Reliable demonstration

| Time from each trial's start | Proxy body bandwidth |
| --- | --- |
| 0–3 seconds | 2,000 kbps (2 Mbps) |
| 3–7 seconds | 256 kbps |
| 7–12 seconds | Offline; close active connections |
| 12 seconds onward | 2,000 kbps |

A 2 MiB payload exceeds the theoretical maximum that can traverse the proxy before the outage (about 878,000 bytes), ensuring the upload reaches every disruption unless it fails or is cancelled first. Smaller user-selected files can finish before disruptions. Phase timestamps are absolute, never relative to a retry.

Run and save the full demonstration independently of the dashboard:

```powershell
python -m tests.run_demo
```

This asserts Basic fails, Retry and Resumable finish with matching hashes, both observe restoration, and Resumable wastes less data. It writes `validation/demo-results.json`, including raw events, measured samples, configuration and definitions. One actual run during implementation produced:

| Strategy | Outcome | End-to-end seconds | Proxy ingress bytes | Repeated/discarded bytes | Retries |
| --- | --- | ---: | ---: | ---: | ---: |
| Basic | Failed on outage | 7.03 | 860,160 | 860,160 | 0 |
| Retry | SHA-256 verified | 21.37 | 2,957,312 | 860,160 | 5 |
| Resumable | SHA-256 verified | 19.98 | 2,125,824 | 28,672 | 5 |

These are measured results for one local run, **not universal guarantees or fixed expected outputs**. Scheduling and machine load affect timing and chunk boundaries.

## Architecture and strategies

```text
Browser dashboard --control/file selection--> Dashboard API (8765)
                                                    |
                                            serial trial scheduler
                                                    |
Python upload client --HTTP/TCP--> disruption proxy --HTTP/TCP--> origin
                                  shared body pacing               |
                                  per-request delay           atomic commit
                                  scheduled outages           SHA-256 response
```

All three networking components use independent real asyncio sockets; the control API stays responsive while experiments run. The origin is reachable only on its trial's ephemeral localhost port. Experiments intentionally route every upload and offset probe through the proxy. The origin's bytearray stores contiguous committed data; reading an incomplete request never commits a partial chunk.

- **Basic:** one full-body HTTP request. A connection failure or origin error ends the trial, without retrying.
- **Retry:** full-body requests from byte zero. Failures trigger exponential backoff (0.25, 0.5, 1, 2 seconds, then capped at 2 seconds) and a configurable **total per-trial** retry budget. The budget does not reset after a successful chunk or probe.
- **Resumable:** sequential chunks (default 32 KiB). After any failure, back off and GET the origin's committed offset **through the proxy**, then continue at that offset. Complete requests commit atomically. Server-confirmed progress survives interruptions; an incomplete chunk is resent. The final response includes the origin's SHA-256, checked against the original payload's hash.

Bandwidth is decimal kbps (`kbps * 1000 / 8` bytes/sec). Upload **body** forwarding is paced in up-to-4 KiB slices by one shared scheduler/lock per trial. Reconnecting or using concurrent connections does not create another rate allowance. Scheduler oversleep credit is shared and capped at one slice; short bursts and approximately 20 ms phase resolution are expected. Control headers and small origin responses are not bandwidth-limited. Delay is one one-way wait before forwarding **each HTTP request**, including probes; it is not a TCP latency or RTT emulator. Large delay settings particularly affect chunked uploads because they make more requests.

An outage aborts active client, proxy and origin sockets, rejects new requests, and discards incomplete request bodies. Recovery allows new connections. This is **proxy-level connection disruption**, not packet-level emulation, genuine packet loss, jitter injection, or modification of the operating system's network settings.

## Scenarios and fairness

Presets include stable 2,048 kbps, sustained 256 kbps, a sudden reduction at t=2s, an outage at t=2–7s, repeated outages at t=2–4s and 6–8s, and the demonstration above. **Edit phase schedule** creates a custom scenario; bandwidth zero means offline. Times must start at zero and strictly increase. Settings have finite numeric bounds, and malformed requests are rejected.

Strategies never compete for the trial's bandwidth. For every trial, the scheduler creates new origin/proxy services, clears committed bytes, resets counters, clock and retry budget, and reuses the identical payload/settings. Trials run serially, in selected strategy order. Python process scheduling, CPU load and thermal/network stack differences remain possible sources of variation; use repeated trials. An experiment is marked completed when its planned trials finish, even when some trials correctly record failure. Failed trials retain an error reason. Cancellation excludes the cancelled trial from success-rate denominators and leaves unstarted trials unrun.

## Failure-boundary experiment

Select **Failure boundaries**, choose generated size or the selected file, a deadline, strategies and number of trials, then enter comma-separated bandwidths and outage durations. Each bandwidth/outage pair receives a fresh scenario: start at the selected rate, disconnect at t=1s for the selected duration, then restore that rate. Zero duration means no outage. Up to six rates, six durations, ten trials per strategy, and **300 total trials** are supported.

The result table shades each strategy/cell's observed verified success rate. The rate is verified successes divided by finished non-cancelled trials for that cell. Unrun cells have no result; cells ending before t=1s did not experience the outage. The deadline includes upload, probing, backoff, request delays and hash verification. A cell can fail due to deadline or retry exhaustion. Sweeps describe **only tested conditions**; they do not establish general reliability guarantees or statistically certain thresholds. Repeat trials and inspect the exported configuration/events when comparing results. Worst-case sweep duration is trial count times deadline, plus bounded cleanup.

## Metric definitions

The UI and JSON export include these definitions as machine-readable metadata (`metrics.py`). Unavailable numeric values are JSON `null`, blank CSV fields or an em dash in the UI.

| Metric | Exact meaning |
| --- | --- |
| Outcome | Completed only after the upload origin's SHA-256 matches the original. Otherwise failed or cancelled. |
| `elapsed_s` | Monotonic seconds from trial start through hash verification or terminal error; socket setup is excluded, request delays/backoff/probes are included. |
| `bytes_sent` | Upload body bytes **read at proxy ingress**, including repeated/discarded bodies. Excludes headers and bytes still in OS/asyncio buffers when the connection closes. This is the primary application bytes-sent observation point. |
| `client_submitted_bytes` | Body bytes submitted by the client to its socket, potentially including buffered bytes that never reached the proxy. Not evidence of wire delivery. |
| `forwarded_bytes` | Body bytes submitted by the proxy to the origin socket. Includes incomplete bodies and retries. HTTP headers excluded. |
| `confirmed_bytes` | Contiguous server-committed payload bytes. During a run, obtained from acknowledgements; at final cleanup, read from actual origin state. Full-file and chunk commits are atomic. |
| `retransmission_bytes` | `max(0, bytes_sent - final confirmed_bytes)`: application-level repeated/discarded work. On failure this includes incomplete, uncommitted data. It does not count bytes still buffered upstream or TCP retransmissions. |
| `overhead_percent` | `100 * retransmission_bytes / payload_bytes` for verified successes; unavailable for failed/cancelled trials. |
| `retry_count` | Additional attempts actually begun after a failed attempt and backoff. Initial attempt, successful chunks and successful offset probes do not add retries. Failure of a probe consumes retry budget. |
| `useful_kbps` | On verified success: `payload_bytes * 8 / elapsed_s / 1000`. Includes recovery time and retries. Unavailable on failure. |
| Throughput trace | Actual body bytes forwarded by the proxy per ~0.2 s sample window, converted to decimal kbps. Short window peaks can exceed the configured limit because forwarding is sliced. Trace is sampled, not invented. |
| `recoveries[].recovery_s` | Time from **scheduled connectivity restoration** to the first subsequent acknowledgement increasing confirmed progress. Includes backoff. For Basic/Retry that acknowledgement is normally full-file completion; for Resumable it is durable chunk progress. `null` if no increasing acknowledgement is observed. Full outages after a terminal failure are unobserved and have no recovery entry. |
| Integrity | SHA-256 calculated independently over original payload and origin-committed data, compared on complete-file acknowledgement. Unavailable for incomplete/unverified files. |
| Success rate | Verified successes / completed non-cancelled trials in each strategy/configuration cell. No confidence interval or arbitrary experience score. |
| Transport overhead | **Unavailable**. TCP/IP headers, TCP retransmissions, actual wire bytes and packet-level loss are not measured. |

CSV exports one row per finished trial, with hashes, all scalar metrics, JSON configuration and recovery observations. JSON includes active/completed state, summaries, payload hash/name, configuration, full event/throughput traces and metric definitions. During a run, exports represent only a snapshot. No fake buffering events or quality scores are produced.

## Validation

```powershell
python -m unittest discover -v
python -m tests.run_demo
```

The integration suite uses actual loopback sockets and wall-clock pacing rather than mocked sleeps. It verifies real proxy bytes and hashes, duration changes under bandwidth limits, aggregate pacing across concurrent reconnects, Basic failure, full restart overhead, chunk resumption, repeated outages, phase changes, bounded retry exhaustion, origin errors, deadlines, cancellation cleanup, API validation, local-origin protection, selected file bytes, exports and repeated sweep scheduling. The duration test allows reasonable scheduler tolerance; it is not a NIC calibration test.

Current validation covers 18 networking/scheduler integration tests and the full recovery demo. See [the validation record](validation/verification.md) and [measured experiments](docs/EXPERIMENTS.md).

## Limits

- This measures application recovery through a localhost user-space proxy; it does not reproduce the entire behavior of a remote mobile network or OS traffic shaper. Ordinary Python scheduling limits precision, especially at very high rates, small payloads and short phases.
- Uploaded payload and origin partial bodies are held in memory, capped at 32 MiB per payload. Origin state lasts for a trial, not a process restart: this version tests connection recovery, not server crash recovery or persistent resumable storage.
- One active experiment per application process. Results are session-only, limited to ten experiments; restarting loses history and file selection. Export anything needed.
- No authentication, TLS or public hosting. The API accepts only localhost hostnames, rejects cross-origin browser writes and binds only to loopback. It is a development tool for a trusted local machine, not a hardened internet-facing server.
- No automatic browser launch, external tools, downloads, analytics, or operating-system network changes. UI assets are served locally.

## Source map

- `main.py` — launch the localhost service.
- `bandwidth_throttle_tester/app.py` — HTTP control/static server, file input, sequential scheduler, sweep, exports.
- `bandwidth_throttle_tester/throttler.py` — real upload origin, proxy, pacing, outage monitor, upload strategies and cleanup.
- `bandwidth_throttle_tester/config.py` — preset phases, validation and bounds.
- `bandwidth_throttle_tester/metrics.py` — exact metric contracts.
- `bandwidth_throttle_tester/static/` — responsive dashboard, live SVG chart and event/result views.
- `tests/test_network.py` — integration tests.
- `tests/run_demo.py` — full demo runner and measured evidence export.

## GitHub and project documentation

- [Architecture](docs/ARCHITECTURE.md) and [development](docs/DEVELOPMENT.md)
- [Experiments](docs/EXPERIMENTS.md), [metrics](docs/METRICS.md), and [boundaries](docs/BOUNDARY_EXPERIMENTS.md)
- [Contributing](CONTRIBUTING.md), [changelog](CHANGELOG.md), and [history provenance](docs/HISTORY_RECONSTRUCTION.md)

The reconstructed allocation is approximately 60% Sreerag Aneesh
([gar-eer](https://github.com/gar-eer)) and 40% Rini Vaishnavi
([rini-7](https://github.com/rini-7)). Each contributor owns their feature merges.
The dates and allocations describe a reconstructed timeline, not verified past
contributions, GitHub PRs, reviews, or approvals.
