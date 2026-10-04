# Bandwidth Throttle Tester

A Python project for exploring how bandwidth limits affect data transfers.

## Objectives

- Build an initial transfer simulator with configurable bandwidth limits.
- Measure transfer duration and report results for repeatable scenarios.
- Extend the simulator into real local HTTP transfers with controlled outages.
- Compare basic, retry, and resumable upload strategies.
- Add a web dashboard after the networking and measurements are established.

These describe the overall roadmap; only the initial simulator is implemented.

## Development status

The original delay-based transfer simulator is available. It accounts for a
64 KiB transfer at 512 kbps in 4 KiB chunks by default and prints the total bytes
and elapsed time. It generates no network traffic and does not change system
bandwidth settings. Payload size, bandwidth, and chunk size are configurable.
Real networking will follow.

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

The simulation takes approximately 1.024 seconds plus scheduling overhead.
No server is started. See the [development guide](docs/DEVELOPMENT.md) for
the workflow and planned milestones.

## Validation

```powershell
python -m unittest discover -v
```

The tests check custom settings, partial chunks, invalid input, command-line
output, and minimum simulated durations at different bandwidth limits.

## Configure a simulation

```powershell
python main.py --size-bytes 131072 --bandwidth-kbps 256 --chunk-bytes 4096
python main.py --help
```

Sizes must be positive integers. Bandwidth must be a positive finite number in
decimal kbps. The example has a theoretical duration of 4.096 seconds; actual
runtime also includes scheduling overhead.

## Scenario presets and results

```powershell
python main.py --scenario baseline
python main.py --scenario low-bandwidth --json
python main.py --scenario baseline --size-bytes 8193 --bandwidth-kbps 256
```

Presets are defined in [examples/scenarios.json](examples/scenarios.json).
`baseline` uses 512 kbps and `low-bandwidth` uses 256 kbps; both use 64 KiB
payloads. Explicit command-line settings override preset values. With no preset,
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
tests/                      Simulator smoke test
```

See [history reconstruction notes](docs/HISTORY_RECONSTRUCTION.md) for the
provenance of this repository's development timeline.
