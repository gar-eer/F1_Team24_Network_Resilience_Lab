# Scenario configuration and transfer reporting

For collection commands and a consistent report format, see the
[experiment guide](EXPERIMENTS.md) and [report template](EXPERIMENT_REPORT_TEMPLATE.md).

## Status

The command loads bundled presets and reports transfer results as text or JSON.
Its default mode now sends real localhost HTTP uploads. The preset inputs are
configuration fixtures, not measured experiment results. Use `--simulate` to
run the earlier delay-based simulator.

HTTP uploads now pass through a body-paced proxy. Preset bandwidth limits are
applied to real forwarding, and `bandwidth_applied` is true in both modes.
The proxy also supports absolute phase schedules with zero kbps representing
offline service. Outages interrupt active connections and reject new ones;
restoration permits new uploads without restarting the phase clock.

```powershell
python main.py --scenario low-bandwidth --json
```

Explicit size and bandwidth options override preset values. Chunk size remains
a separate command-line setting. Without `--scenario`, the identifier is
`custom`. Presets are resolved relative to the application directory, so a
different shell working directory does not change their location.

## Scenario inputs

The [example scenarios](../examples/scenarios.json) describe baseline,
low-bandwidth, and outage conditions using the same payload size.

| Field | Meaning |
| --- | --- |
| `id` | Unique scenario identifier |
| `description` | Human-readable purpose of the scenario |
| `payload_bytes` | Positive integer transfer size; HTTP uploads are limited to 32 MiB |
| `bandwidth_kbps` | Positive, finite bandwidth in decimal kilobits per second |
| `outage_at_s` | Optional nonnegative outage start, in seconds from trial start |
| `outage_duration_s` | Optional positive outage duration; required with an outage start |

A kilobit is 1,000 bits. A KiB is 1,024 bytes. The ideal duration in seconds is
`payload_bytes * 8 / (bandwidth_kbps * 1000)`.

For a 65,536-byte payload, the theoretical duration is 1.024 seconds at 512 kbps
and 2.048 seconds at 256 kbps. These values are calculations, not observed
measurements. A delay-based simulator also includes scheduling overhead.
Paced HTTP uploads also include connection and acknowledgement overhead.

## Result fields

| Field | Meaning |
| --- | --- |
| `mode` | `http` for real uploads, or `simulation` for delay-based accounting |
| `bandwidth_applied` | True: real proxy pacing in HTTP mode, simulated timing otherwise |
| `scenario_id` | Identifier of the selected scenario |
| `strategy` | HTTP-only `basic` (default), `retry`, or `resumable` |
| `attempt_count` | Started HTTP operations: full-file attempts, or Resumable chunks and probes |
| `retry_count` | Recovery operations actually begun after failure and backoff; successful chunks/probes add none |
| `max_retries` | Effective total retry budget; zero for Basic |
| `resume_chunk_bytes` | HTTP commit chunk size used only by Resumable; default 32 KiB |
| `confirmed_bytes` | Latest contiguous origin offset confirmed by an acknowledgement or probe |
| `offset_probe_count` | Resumable offset requests actually begun, including failed probes |
| `payload_bytes` | Requested transfer size |
| `bandwidth_kbps` | Configured bandwidth limit |
| `chunk_bytes` | Maximum application body write size, or simulation step size |
| `transferred_bytes` | Confirmed bytes in HTTP mode, possibly partial on failed Resumable trials; simulated bytes otherwise |
| `proxy_ingress_bytes` | HTTP-only body bytes read by the proxy, excluding headers |
| `forwarded_bytes` | HTTP-only body bytes submitted by the proxy to the origin socket |
| `timeout_s` | HTTP-only upload deadline, excluding service setup and cleanup |
| `phases` | HTTP-only schedule of absolute `at` times and `kbps` limits |
| `events` | Observed phase transitions with scheduled and actual elapsed times |
| `elapsed_s` | Measured monotonic time from start to completion or terminal failure |
| `status` | `completed` after full acknowledgement; `failed` after interruption or timeout |
| `error` | Null on completion, otherwise the failure reason |

HTTP acknowledgement confirms receipt of the full body by the local origin.
It does not establish hash integrity, durable disk storage, or wire overhead.
Simulation counts do not establish network delivery. Hash integrity checks
belong to a later milestone. An interrupted
full-file request receives no acknowledgement, so `transferred_bytes` remains
zero even when the proxy has forwarded part of its body.

Resumable commits contiguous complete HTTP chunks. The origin discards an
incomplete chunk while preserving earlier committed data. A failed Resumable
trial may report nonzero confirmed and transferred bytes without being completed.
Confirmed progress can lag the origin if an acknowledgement is lost; the next
offset probe reconciles that state.

Invalid settings or unknown presets produce a command-line error with exit
status 2 and no result on standard output. They are not counted as completed
transfers. JSON output contains only the result, with no text banner.
HTTP deadlines or connection failures produce a failed result and exit with
status 1. A failed result retains byte counters and phase events observed before
termination. Basic ends immediately on failure. Retry starts fresh full-body
attempts after exponential backoff until completion, budget exhaustion, or the
trial deadline. Terminal failure stops the monitor; later phases are unobserved.

Phase times must begin at zero and strictly increase. Times and rates must be
finite and nonnegative. The command builds a single-outage schedule from
`--outage-at-s` and `--outage-duration-s`; the Python proxy API accepts phase lists.
The delay-based simulator rejects outage schedules instead of silently ignoring
them. Phase event kinds are `started`, `outage`, `restored`, and `rate_changed`.
Event `scheduled_at` is the configured phase time; `at` is when it was applied.

Client event kinds include `upload_attempt`, `attempt_failed`, and `retry_scheduled`.
An attempt event includes its one-based number. A scheduled retry includes the
backoff duration (`delay_s`) and next attempt number. Scheduled retries do not
count as started until their attempt event occurs. Phase events alone include
`scheduled_at`; client event `at` uses the same monotonic trial clock.

Retry backoff is 0.25, 0.5, 1, then 2 seconds, capped at 2 seconds. The retry
budget is global to a trial; it does not reset on restoration or reconnect.
Retry sends the same full body from byte zero. Successful Retry
`elapsed_s` includes earlier failed attempts and backoff, and proxy byte counters
include partial and repeated bodies across those attempts.

Resumable sends sequential chunks and probes `GET /offset` through the proxy
after any failure and backoff. Successful chunks and probes do not increment or
reset the retry budget. Failed probes require another backoff and consume the
same trial budget. `chunk_committed` and `offset_confirmed` events record the
acknowledged offset. Its `attempt_count` includes chunks and probes, so it is
not a cross-strategy count of full-file attempts. All retries remain inside the
same deadline and absolute phase schedule.

## Implementation milestones

1. Fixed-default simulator: implemented.
2. Configurable payload and bandwidth settings with validation: implemented.
3. Named presets and transfer reports: implemented.
4. Real HTTP body delivery and acknowledgement timing: implemented.
5. Shared proxy body pacing, byte counters, and upload deadlines: implemented.
6. Scheduled outages, restoration, and failed-transfer reports: implemented.
7. Explicit Basic and full-file Retry strategies: implemented.
8. Resumable uploads with committed-offset probes: implemented.
