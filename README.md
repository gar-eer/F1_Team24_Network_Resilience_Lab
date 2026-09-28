# Bandwidth Throttle Tester

A Python project for exploring how bandwidth limits affect data transfers.

## Objectives

- Build an initial transfer simulator with configurable bandwidth limits.
- Measure transfer duration and report results for repeatable scenarios.
- Extend the simulator into real local HTTP transfers with controlled outages.
- Compare basic, retry, and resumable upload strategies.
- Add a web dashboard after the networking and measurements are established.

These are development goals; the initial foundation does not implement them yet.

## Development status

Initial project foundation. Transfer simulation, configurable throttling, and
result reporting will be introduced in subsequent milestones.

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

The entry point is currently a placeholder and exits without output. No server
or transfer is started. See the [development guide](docs/DEVELOPMENT.md) for
the initial workflow and planned milestones.

## Structure

```text
main.py                     Application entry point placeholder
bandwidth_throttle_tester/   Python package
docs/                       Development notes
```

See [history reconstruction notes](docs/HISTORY_RECONSTRUCTION.md) for the
provenance of this repository's development timeline.
