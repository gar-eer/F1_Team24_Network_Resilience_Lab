> Historical prototype guide through 18 October. The current backend uses the trial/service API; this guide will be updated with the release documentation.

# Failure-boundary experiments

A boundary sweep repeats real localhost uploads across selected bandwidths and
outage durations. It compares measured outcomes under tested conditions; it does
not establish a universal minimum bandwidth or maximum tolerable outage.

## Run a sweep

From the repository directory in PowerShell:

```powershell
python main.py --boundary --bandwidths 256,512 --outages 0,0.5 --strategies basic,retry,resumable --trials 1 --size-bytes 65536 --resume-chunk-bytes 4096 --timeout-s 10 --json
```

This runs 12 trials serially: two rates, two durations, and three strategies.
Each cell starts online at its selected rate. Positive outage durations add an
offline phase at 1 second and restoration after the selected duration. A zero
duration means no outage. Change the outage start with `--outage-at-s`.

The sweep uses one generated payload size for every strategy. Each trial gets
fresh origin and proxy services, committed data, counters, clock, and retry
budget. The strategies never compete for a shared rate within this comparison.
The write chunk size, Resumable commit size, deadline, and retry budget stay
constant across cells unless you run a separate sweep with different settings.

Use `--strategy retry` for a single strategy or `--strategies basic,retry` for a
subset. These options cannot be combined. Boundary mode defaults to all three
strategies; single-upload mode still defaults to Basic. Boundary mode uses its
own rate and duration axes instead of `--scenario`, `--bandwidth-kbps`, or
`--outage-duration-s` and is unavailable with `--simulate`.

## Limits

| Setting | Allowed values |
| --- | --- |
| Bandwidth axis | 1-6 finite rates, each 8-100,000 decimal kbps |
| Outage duration axis | 1-6 finite durations, each 0-120 seconds |
| Strategies | Unique selection of Basic, Retry, and Resumable |
| Repeats | 1-10 per strategy and cell |
| Total trials | At most 300 after duplicate axis values are removed |
| Payload | 1 byte through 32 MiB |
| Deadline | 0.1-3,600 seconds per trial, including backoff and probes |
| Outage start | 0-3,600 seconds from each trial's start |
| Retry budget | 0-30 additional recovery attempts per trial |

Axes are sorted and deduplicated. All input and total-trial limits are checked
before starting a trial. The maximum trial-time allowance is total trials times
the deadline, with service setup and cleanup in addition; large sweeps can take
substantial time. Begin with a small set of cells.

## Read results

The JSON contains normalized `config`, `total_trials`, complete raw `results`,
and per-cell `summaries`. Every result retains its measured bytes, hashes,
strategy, phase events, recovery observations, cell rate/duration, and one-based
trial number. Failed outcomes remain in the result array.

Each summary identifies a bandwidth, outage duration, and strategy and includes:

- `finished_trials`: trials that returned an outcome for that cell.
- `verified_successes`: completed trials with `integrity` true.
- `failed_trials`: remaining finished trials.
- `success_rate`: verified successes divided by finished trials, as a fraction
  from 0 to 1, including failed outcomes in the denominator.
- `observed_outage_trials`: trials whose event trace actually reached an offline
  phase before termination.

A small upload may finish before its scheduled outage. Such a trial can be a
verified success but does not demonstrate outage resilience. Check
`outage_observed` and `observed_outage_trials` before interpreting the cell.
Long outages may fail because of deadline or retry-budget exhaustion; preserve
the error reason instead of treating every failure as a bandwidth threshold.

An experiment is `completed` when all planned trials finish, even if individual
uploads fail as expected. The command exits 0 for a completed sweep. Invalid
configuration exits 2 before execution. A service setup failure exits 1. This
differs from a single-upload command, which exits 1 for a failed upload.

## Recovery observations

`recoveries` contains entries only for connectivity restorations observed while
the trial was alive. `restored_at` is the scheduled restoration time.
`recovery_s` measures from that scheduled time to the first subsequent client
acknowledgement that increases confirmed progress, including backoff and request
overhead. A repeated offset probe with unchanged progress does not count.

Basic and Retry normally confirm progress only when their full-file request is
acknowledged. Resumable can confirm progress at chunk boundaries or through a
probe discovering a previously unacknowledged commit. A restored connection
alone is not progress recovery. An observed restoration without a later increase
has `recovery_s: null`; a scheduled restoration after trial termination has no
observation entry at all.

## Save and report

```powershell
New-Item -ItemType Directory -Path 'tmp/experiments' -Force | Out-Null
python main.py --boundary --bandwidths 512 --outages 0,0.15 --outage-at-s 0.05 --size-bytes 16384 --resume-chunk-bytes 4096 --timeout-s 3 --json | Set-Content -Encoding utf8 'tmp/experiments/boundary-01.json'
$sweepExit = $LASTEXITCODE
Get-Content -Raw 'tmp/experiments/boundary-01.json' | ConvertFrom-Json
```

Record the source revision, actual collection date, Python version, and relevant
machine load with the output. Repeat cells before drawing conclusions and keep
their raw records. Use the [report template](EXPERIMENT_REPORT_TEMPLATE.md),
[experiment guide](EXPERIMENTS.md), and [metric definitions](METRICS.md).
