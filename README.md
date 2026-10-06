# Bandwidth Throttle Tester

A Python project for exploring how bandwidth limits affect data transfers.

## Objectives

- Build an initial transfer simulator with configurable bandwidth limits.
- Measure transfer duration and report results for repeatable scenarios.
- Extend the simulator into real local HTTP transfers with controlled outages.
- Compare basic, retry, and resumable upload strategies.
- Add a web dashboard after the networking and measurements are established.

The initial simulator and real localhost HTTP upload engine are implemented.
Proxy pacing, disruptions, recovery strategies, and the dashboard will follow.

## Development status

The default command uploads a deterministic payload to a temporary HTTP origin
on `127.0.0.1`, using real TCP sockets. It reports the origin-acknowledged byte
count and elapsed upload time. The origin uses an automatically assigned port
and stores the body in memory. HTTP payloads are limited to 32 MiB.

HTTP bandwidth pacing is not implemented yet. The configured bandwidth is
reported as metadata with `bandwidth_applied: false`. The earlier delay-based
simulator remains available with `--simulate` and applies the configured timing.

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
output, minimum simulated durations, exact received HTTP bodies, and rejection
of unsupported upload endpoints. Tests require permission to open local sockets.

## Configure a transfer

```powershell
python main.py --size-bytes 131072 --bandwidth-kbps 256 --chunk-bytes 4096
python main.py --simulate --size-bytes 131072 --bandwidth-kbps 256
python main.py --help
```

Sizes must be positive integers. Bandwidth must be a positive finite number in
decimal kbps. The simulation example has a theoretical duration of 4.096 seconds
plus scheduling overhead. The HTTP command currently runs without pacing.

## Scenario presets and results

```powershell
python main.py --scenario baseline
python main.py --scenario low-bandwidth --json
python main.py --scenario baseline --size-bytes 8193 --bandwidth-kbps 256
```

Presets are defined in [examples/scenarios.json](examples/scenarios.json).
`baseline` uses 512 kbps and `low-bandwidth` uses 256 kbps; both use 64 KiB
payloads. Rates affect timing only in simulation mode at this milestone.
Explicit command-line settings override preset values. With no preset,
the result's scenario identifier is `custom` and the usual defaults apply.

Text output includes the scenario, transfer size, bandwidth, elapsed time, and
completion status. `--json` prints only a structured result that can be saved
with shell redirection. Invalid inputs exit with an error instead of producing
a result. See [scenario and result definitions](docs/SCENARIOS_AND_REPORTING.md).

## Structure

```text
main.py                     Command-line entry point
bandwidth_throttle_tester/   Python package
docs/                       Development notes
tests/                      Simulation, reporting, and HTTP tests
```

See [history reconstruction notes](docs/HISTORY_RECONSTRUCTION.md) for the
provenance of this repository's development timeline.
