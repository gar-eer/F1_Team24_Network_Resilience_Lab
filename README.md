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
64 KiB transfer at a fixed 512 kbps in 4 KiB chunks and prints the total bytes
and elapsed time. It generates no network traffic and does not change system
bandwidth settings. Configurable settings and real networking will follow.

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

The smoke test checks command-line output and the minimum simulated duration.

## Structure

```text
main.py                     Command-line entry point
bandwidth_throttle_tester/   Python package
docs/                       Development notes
tests/                      Simulator smoke test
```

See [history reconstruction notes](docs/HISTORY_RECONSTRUCTION.md) for the
provenance of this repository's development timeline.
