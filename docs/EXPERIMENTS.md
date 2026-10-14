# Running and reporting experiments

This guide covers Basic, full-file Retry, and Resumable HTTP strategies.
Use real HTTP mode for network experiments. The optional `--simulate` mode only
accounts for transfer time and should be reported separately.

## Preparation

Use Python 3.11 or newer from the repository directory. No third-party packages
or internet connection are required. Allow local connections to `127.0.0.1`.

Record the source revision and Python version before collecting results:

```powershell
git rev-parse HEAD
python --version
```

Keep the payload at 65,536 bytes, write chunks at 4,096 bytes, and the deadline
at 120 seconds for the comparison below. Avoid concurrent experiment commands;
each command creates independent proxy and origin services, so their bandwidth
allowances are separate. Record relevant background load or configuration changes.

## Scenarios

| Preset | Payload | Body bandwidth | Disruption | Expected Basic outcome |
| --- | --- | --- | --- | --- |
| `baseline` | 65,536 bytes | 512 kbps | None | Completed; exit 0 |
| `low-bandwidth` | 65,536 bytes | 256 kbps | None | Completed; exit 0 |
| `outage` | 65,536 bytes | 256 kbps | Offline at 0.25 s; restoration scheduled at 1.25 s | Failed on interruption; exit 1 |

The ideal body transfer durations are 1.024 seconds for baseline and 2.048
seconds for low bandwidth. These are calculations, not measured results. Actual
timing includes connection, pacing, scheduling, and acknowledgement overhead.

The outage payload cannot finish before its configured interruption at the
configured rate. Basic stops on failure and its trial is
cleaned up immediately. Restoration after termination is scheduled but unobserved.
The proxy restoration behavior is also checked by automated tests. Retry can
keep a trial alive across restoration. Resumable retains committed chunks and
continues from the server-reported offset.

## Capture one comparison

Run these commands in PowerShell from the repository directory. The `tmp/`
directory is ignored by Git. Use a new filename for each additional trial.

```powershell
New-Item -ItemType Directory -Path 'tmp/experiments' -Force | Out-Null

python main.py --scenario baseline --json | Set-Content -Encoding utf8 'tmp/experiments/baseline-01.json'
$baselineExit = $LASTEXITCODE

python main.py --scenario low-bandwidth --json | Set-Content -Encoding utf8 'tmp/experiments/low-bandwidth-01.json'
$lowBandwidthExit = $LASTEXITCODE

python main.py --scenario outage --json | Set-Content -Encoding utf8 'tmp/experiments/outage-01.json'
$outageExit = $LASTEXITCODE

$baselineExit
$lowBandwidthExit
$outageExit
```

Expected exit codes are 0, 0, and 1. An exit code of 1 for the outage is the
expected experimental outcome. It is not a completed upload. Invalid arguments
exit with code 2 and do not produce a trial result; correct the configuration
before including that run in a comparison. A service setup error can also exit
before a result is available; check for a valid JSON object before reporting it.

Read saved output without depending on PowerShell's output encoding:

```powershell
Get-Content -Raw 'tmp/experiments/baseline-01.json' | ConvertFrom-Json
Get-Content -Raw 'tmp/experiments/outage-01.json' | ConvertFrom-Json
```

Repeat each scenario at least three times, serially, for an exploratory
comparison. Preserve every valid trial, including failures. Record the number
of trials and the range of observed durations; three trials do not establish
general reliability or statistical significance.

## Compare Basic and Retry

The commands above use Basic, the default strategy. Add a separate Retry run:

```powershell
python main.py --scenario outage --strategy retry --max-retries 5 --json | Set-Content -Encoding utf8 'tmp/experiments/outage-retry-01.json'
$retryExit = $LASTEXITCODE
$retryExit
```

Under the default outage schedule and deadline, Retry is expected to complete
after restoration (exit 0), while Basic fails (exit 1). Run each command as a
fresh trial with the same payload, rate, write chunks, phases, and deadline.
Record the strategy, retry budget, actual attempts, and retries for every run.
Retry starts full-file requests from byte zero, so its counters can exceed the
payload size. Inspect recorded events and byte counts rather than assuming a
fixed number of attempts or a universal completion time.

## Compare Resumable

```powershell
python main.py --scenario outage --strategy resumable --resume-chunk-bytes 4096 --json | Set-Content -Encoding utf8 'tmp/experiments/outage-resumable-01.json'
$resumableExit = $LASTEXITCODE
$resumableExit
```

This example uses 4 KiB commit chunks so completed chunks can be acknowledged
before the preset's early outage. The default commit size is 32 KiB; a first
chunk that has not finished before interruption has no committed progress to
preserve. Keep socket write size, payload, rate, phases, deadline, and retry budget
fixed when comparing strategies, and record Resumable's commit size separately.

Inspect `confirmed_bytes`, `offset_probe_count`, and progress events alongside
proxy byte counters. A failed Resumable trial can retain confirmed partial data;
nonzero progress does not make it completed. Successful chunk and probe requests
do not consume retries. `attempt_count` includes these requests for Resumable,
so it is not directly comparable to Basic/Retry full-file attempt counts.
Probe failures count against the same retry budget and remain subject to outages.

## Check each result

- Confirm `mode` is `http` and `bandwidth_applied` is true.
- Record the actual payload, rate, chunks, deadline, and phase schedule from JSON.
- For completed uploads, check that `transferred_bytes` equals `payload_bytes`.
- For interrupted full-file requests, `transferred_bytes` is zero because no full
  request was acknowledged; proxy ingress or forwarding counts may be nonzero.
- Keep the failure reason and observed events for every failed trial.
- Distinguish an event's scheduled time (`scheduled_at`) from its observed time
  (`at`). Do not infer a restoration event merely from a future schedule entry.

The reported counters exclude HTTP headers, TCP/IP overhead, and TCP
retransmissions. Acknowledged size does not establish SHA-256 integrity or durable
disk storage. Those measurements are not implemented at this milestone.

## Report format

Copy the [experiment report template](EXPERIMENT_REPORT_TEMPLATE.md), then fill
it using saved JSON rather than estimated timings. Keep one summary row per
trial and preserve the complete JSON as the source record. Use paths relative
to the report when linking raw results.

For each scenario and strategy, summarize completed and failed trial counts separately.
Calculate a completion fraction only over valid finished trials and name its
denominator. Report observed timings with the outcome they belong to: a failed
upload's short time to interruption is not a faster completed transfer.

Before committing a published report, place its selected raw results beside the
report outside `tmp/` and check that all links resolve. Leave unmeasured values
explicitly unavailable. Use [scenario and metric definitions](SCENARIOS_AND_REPORTING.md)
for field meanings, and the [development guide](DEVELOPMENT.md) for test commands.
