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
At this milestone, `main.py` runs a fixed 64 KiB simulation at 512 decimal kbps
and prints the size and elapsed time. The simulator sleeps for each chunk's
ideal transfer duration; it does not send bytes over a network. The theoretical
duration is 1.024 seconds, with actual runtime increased by scheduling overhead.

Run the command-line smoke test with:

```powershell
python -m unittest discover -v
```

The test checks the reported payload, bandwidth, and minimum duration. Real
socket integration tests belong to the later HTTP transfer milestones.

## Planned milestones

1. Implement the original bandwidth-limited transfer simulator.
2. Add configurable scenarios, timing, and result reporting.
3. Introduce actual HTTP uploads through a local disruption proxy.
4. Add retry, resumable transfer, integrity checks, and recovery metrics.
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
