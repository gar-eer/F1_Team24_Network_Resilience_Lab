> Historical prototype guide through 18 October. The current backend uses the trial/service API; this guide will be updated with the release documentation.

# Development guide

## Environment

Use Python 3.11 or newer. The project currently uses only the standard library;
there are no packages to install from `requirements.txt`.

Create an isolated environment from the repository directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe main.py
```

Invoking the environment's Python directly does not require activating it.
By default, `main.py` uploads 64 KiB over real localhost HTTP sockets to a
temporary in-memory origin through a paced proxy. Both ports are assigned
automatically. The configured bandwidth limits proxy body forwarding across all
connections sharing that proxy. Payload size is limited to 32 MiB for HTTP uploads.

Use `--simulate` for the earlier delay-based transfer runner. Its default
theoretical duration is 1.024 seconds, plus scheduling overhead.

Run the command-line smoke test with:

```powershell
python -m unittest discover -v
```

The tests check custom settings, invalid inputs, partial chunks, and minimum
durations at different rates. HTTP tests check exact received payload bytes,
partial final write chunks, endpoint rejection, and the default command's report.
Proxy tests also compare measured durations at different rates, check a shared
limit across concurrent connections, and verify that a deadline stops a slow
transfer promptly. The suite requires permission to open localhost sockets.

Override defaults with `--size-bytes`, `--bandwidth-kbps`, and `--chunk-bytes`.
Payload and chunk sizes must be positive integers, and bandwidth must be
positive and finite. For example:

```powershell
python main.py --size-bytes 8193 --bandwidth-kbps 256 --chunk-bytes 4096
```

The final chunk contains only the remaining bytes. A monotonic clock measures
actual elapsed time. HTTP timing includes connection establishment, body writes,
and the origin acknowledgement; origin startup and final cleanup are excluded.
Simulation timing includes sleeps and loop overhead.

The proxy reads body slices of up to 4 KiB, then sleeps for each slice's ideal
duration while holding a shared lock before forwarding it. There is no initial
free burst. Scheduling overhead can reduce achieved throughput. HTTP headers
and origin responses bypass this pacing. Byte counters describe application
bodies at proxy ingress and forwarding, not transport overhead.

`--timeout-s` sets the HTTP deadline (default 120 seconds). Active proxy handlers
are cancelled before server shutdown waits for their connections. A deadline
failure produces a failed result and exits with status 1; invalid input exits with
status 2. This deadline does not apply to `--simulate`.

Select `--scenario baseline` or `--scenario low-bandwidth` to load a bundled
preset. Explicit size and bandwidth options take precedence. Add `--json` for
a structured result. The reporting tests cover preset selection, overrides,
invalid names, and execution from another working directory.

## Scheduled outages

The `outage` preset builds phases at 0 seconds (256 kbps), 0.25 seconds
(offline), and 1.25 seconds (256 kbps). Alternatively, provide both
`--outage-at-s` and `--outage-duration-s` with a nonnegative start and a positive
duration. Outages are supported in HTTP mode only.

One proxy monitor uses absolute monotonic times for the entire trial. An offline
phase aborts both sides of active proxy connections and cancels forwarding
handlers. Incoming connections are rejected until an online phase is applied.
Restoration starts no client attempts by itself. Basic records failure and ends
the trial immediately. Retry follows its backoff schedule and may establish a
fresh connection after restoration.

Failed results retain observed events and application body counters. The origin
commits a full request only after reading its entire body. No incomplete body is
treated as an acknowledged upload. Tests keep a proxy alive across an outage to
check that it rejects offline attempts and accepts fresh uploads on restoration.
Cleanup closes connections and removes cancelled tasks from the handler set.

## Basic and Retry strategies

`--strategy basic` is the default: send the full file once and stop on error.
`--strategy retry` sends the identical full file again from byte zero after each
failed attempt, with backoff delays of 0.25, 0.5, 1, then 2 seconds, capped at 2.
`--max-retries` must be a nonnegative integer (default 5). It limits additional
attempts over the entire trial. A zero budget permits no extra attempts.

Each trial retains one origin, proxy, shared bandwidth allowance, and absolute
phase schedule across all attempts. `--timeout-s` covers all attempts and
backoff. Actual attempts and scheduled retries have separate events; timing out
during backoff does not increment the retry count. Strategy tests exercise
outage recovery, full-file repeated work, exhausted budgets, and deadline expiry
during backoff over real localhost sockets.

## Resumable strategy

`--strategy resumable` sends contiguous HTTP commit chunks (default 32 KiB),
configured with `--resume-chunk-bytes`. The existing `--chunk-bytes` option
controls socket write slices, independently of commit boundaries. The final
commit chunk may be shorter than the configured size.

The origin accepts `POST /chunk` with `X-Offset` and `X-Total-Bytes`. It reads the
entire body before checking the current contiguous offset and committing bytes
to its in-memory buffer. An incomplete or out-of-order chunk cannot overwrite
earlier progress. `GET /offset` reports the committed size. Both endpoints pass
through the same proxy and outage schedule as full-file uploads.

After failure and backoff, the client probes the committed offset before
sending more chunks. It can reconcile a chunk committed by the origin even when
its acknowledgement did not reach the client. Successful chunks and probes do
not consume or reset the retry budget; failed probes consume the same budget.
The deadline includes chunks, probes, failures, and backoff.

Results expose confirmed progress and probe counts. `attempt_count` counts
started HTTP operations, including successful chunks and probes for Resumable.
Only operations begun after failure/backoff add to `retry_count`. Tests check
exact committed bytes, partial chunks, incorrect offsets, interruption recovery,
probes during outages, and a shared retry budget across successful progress.

## Integrity and metrics

SHA-256 verification and derived transfer measurements are implemented. The
origin hashes its complete committed buffer; each strategy verifies the returned
digest against the original source before completion. Incomplete origins return
no final hash. Missing or mismatching hashes are terminal integrity errors.
Corruption tests alter bytes inside an actual origin and exercise all strategies
over real sockets rather than mocking successful network responses.

Client socket submissions and proxy body counters are measured separately.
Origin and proxy handlers are cleaned up before inspecting final committed
bytes. `metrics.py` derives repeated/discarded bytes, useful throughput, and
overhead percentage and supplies the result's metric definitions. See
[METRICS.md](METRICS.md) for availability rules and units.

## Planned milestones

1. Implement the original bandwidth-limited transfer simulator.
2. Add configurable scenarios, timing, and result reporting.
3. Scheduled outages and restoration: implemented.
4. Strategies, integrity checks, recovery observations, and boundary sweeps are implemented.
5. Validate networking behavior and document reproducible experiments.
6. Build the frontend and result visualizations.
7. Add light mode and remember the selected theme.

## Collaboration workflow

Start focused branches from the integrated `main` branch. Keep related changes
in small commits and describe the purpose and validation in each pull request.
Merge completed branches with merge commits to retain integration points.

The planned allocation is approximately 60% backend and networking for Sreerag
Aneesh (`gar-eer`), and 40% frontend, reporting, and documentation for Rini
Vaishnavi (`rini-7`). Occasional supporting work can cross these boundaries.
Review by the other contributor is the intended workflow; a local branch or
commit does not establish that a GitHub review occurred.

See [history reconstruction notes](HISTORY_RECONSTRUCTION.md) for how milestone
dates and contributor assignments should be interpreted.
