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
temporary in-memory origin. The port is assigned automatically. At this stage,
HTTP uploads are unpaced; the configured bandwidth is recorded but not applied.
Payload size is limited to 32 MiB for HTTP uploads.

Use `--simulate` for the earlier delay-based transfer runner. Its default
theoretical duration is 1.024 seconds, plus scheduling overhead.

Run the command-line smoke test with:

```powershell
python -m unittest discover -v
```

The tests check custom settings, invalid inputs, partial chunks, and minimum
durations at different rates. HTTP tests check exact received payload bytes,
partial final write chunks, endpoint rejection, and the default command's report.
The suite requires permission to open localhost sockets.

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

Select `--scenario baseline` or `--scenario low-bandwidth` to load a bundled
preset. Explicit size and bandwidth options take precedence. Add `--json` for
a structured result. The reporting tests cover preset selection, overrides,
invalid names, and execution from another working directory.

## Planned milestones

1. Implement the original bandwidth-limited transfer simulator.
2. Add configurable scenarios, timing, and result reporting.
3. Add a paced disruption proxy to the implemented HTTP upload engine.
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
