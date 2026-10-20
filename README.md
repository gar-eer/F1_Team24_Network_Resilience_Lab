# Network Resilience Lab

The networking engine now uses the final trial-based architecture: real localhost
HTTP uploads, a shared body-pacing scheduler, bounded socket cleanup, preserved
cancellation, hash verification, retry/resume strategies, and measured recovery.

## Run the backend

Requires Python 3.11 or newer, with no third-party packages.

```powershell
python main.py
```

The service binds to `127.0.0.1:8765`. Metadata is available at `/api/meta` and
experiments at `/api/experiments`. The browser frontend arrives in a later
milestone; the root page is not available yet.

## Validation

```powershell
python -m unittest discover -v
```

The engine regression tests check shared pacing across simultaneous connections
and cancellation of a large buffered upload.

## Development provenance

This is a reconstructed timeline, not verified historical activity. See
[history notes](docs/HISTORY_RECONSTRUCTION.md). Earlier command-line guides
describe the retired prototype, not the current service entry point.
