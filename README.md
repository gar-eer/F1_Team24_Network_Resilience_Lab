# Bandwidth Throttle Tester

A Python project for exploring how bandwidth limits affect data transfers.

## Objectives

- Build an initial transfer simulator with configurable bandwidth limits.
- Measure transfer duration and report results for repeatable scenarios.
- Extend the simulator into real local HTTP transfers with controlled outages.
- Compare basic, retry, and resumable upload strategies.
- Add a web dashboard after the networking and measurements are established.

The initial simulator and real localhost HTTP upload engine are implemented.
Bandwidth pacing, scheduled outages, and connection restoration are implemented.
Retry strategies, resumable uploads, and the dashboard will follow.

## Development status

The default command uploads a deterministic payload through a bandwidth-limited
proxy to a temporary HTTP origin. Both bind to `127.0.0.1` on automatically
assigned ports and use real TCP sockets. The origin stores the body in memory.
HTTP payloads are limited to 32 MiB.

The proxy paces upload bodies in slices of up to 4 KiB using one shared allowance
across connections. Headers and responses are not rate-limited. Reports include
proxy ingress, forwarded body bytes, origin-acknowledged bytes, and elapsed time.
This measures application body delivery, not TCP wire traffic or packet loss.
The earlier delay-based simulator remains available with `--simulate`.

## Requirements

- Python 3.11 or newer
- No third-party dependencies at this stage

## Local setup

From the repository directory in PowerShell:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe main.py
```

The HTTP origin exists only for the command's duration. There is no dashboard
or internet dependency. See the [development guide](docs/DEVELOPMENT.md).

## Validation

```powershell
python -m unittest discover -v
```

The tests check custom settings, partial chunks, invalid input, command-line
output, exact received HTTP bodies, rate-dependent upload timing, aggregate
pacing across concurrent connections, outage interruption, restoration, and
deadline cleanup. Tests require permission to open local sockets.

## Configure a transfer

```powershell
python main.py --size-bytes 131072 --bandwidth-kbps 256 --chunk-bytes 4096
python main.py --simulate --size-bytes 131072 --bandwidth-kbps 256
python main.py --help
```

Sizes must be positive integers. Bandwidth must be a positive finite number in
decimal kbps. The simulation example has a theoretical duration of 4.096 seconds
plus scheduling overhead. The paced HTTP upload includes socket, forwarding,
and acknowledgement overhead as well. The default HTTP deadline is 120 seconds;
use `--timeout-s` to change it. It must be a positive finite number and applies
to the upload, excluding service setup and cleanup. Deadline failures exit with
status 1; invalid settings exit with status 2.

## Scenario presets and results

```powershell
python main.py --scenario baseline
python main.py --scenario low-bandwidth --json
python main.py --scenario baseline --size-bytes 8193 --bandwidth-kbps 256
python main.py --scenario outage --json
```

Presets are defined in [examples/scenarios.json](examples/scenarios.json).
`baseline` uses 512 kbps and `low-bandwidth` uses 256 kbps; both use 64 KiB
payloads. Rates affect simulation timing and real proxy body forwarding.
Explicit command-line settings override preset values. With no preset,
the result's scenario identifier is `custom` and the usual defaults apply.

The `outage` preset uses 64 KiB at 256 kbps, disconnects at 0.25 seconds, and
schedules restoration at 1.25 seconds. The current single-attempt client fails
on interruption and ends its trial immediately. It does not wait for restoration
or retry. A running proxy accepts fresh connections after restoration; automatic
client recovery belongs to a later milestone.

Configure an outage directly with:

```powershell
python main.py --outage-at-s 0.25 --outage-duration-s 1 --json
```

Supply both options, with a nonnegative start and a positive duration. They use
absolute seconds from the proxy trial's start. Outage schedules require HTTP
mode. During an outage, active proxy connections are aborted and new connections
are rejected. Incomplete request bodies are not committed by the origin.

Text output includes the scenario, transfer size, bandwidth, elapsed time, and
completion status. `--json` prints only a structured result that can be saved
with shell redirection. Invalid inputs exit with an error instead of producing
a result. See [scenario and result definitions](docs/SCENARIOS_AND_REPORTING.md).
Interrupted uploads and deadline failures produce a failed result, including
observed events and byte counters, and exit with status 1. Completed uploads exit
with status 0. A failed trial stops its schedule, so future restoration events
are not reported as observed.

## Structure

```text
main.py                     Command-line entry point
bandwidth_throttle_tester/   Python package
docs/                       Development notes
tests/                      Simulation, reporting, and HTTP tests
```

See [history reconstruction notes](docs/HISTORY_RECONSTRUCTION.md) for the
provenance of this repository's development timeline.
