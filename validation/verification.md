# Validation record

Actual collection: 29 October 2026. Git milestone dates are reconstructed.
Environment: Python 3.13.13 on Windows.

- Networking/scheduler integration suite: 18 tests passed before frontend integration.
- Full `python -m tests.run_demo`: passed all recovery and integrity assertions.
- Raw measurements: [demo-results.json](demo-results.json).
- Interpreted observations: [experiment report](../docs/EXPERIMENTS.md).

The root-page assertion is restored when the frontend is introduced. Final
source parity and UI/API integration are verified in the later release stages.

## Dashboard integration milestone

The complete 18-test suite passed with its root-page assertion restored.
Fifteen additional live-service checks passed for static assets, metadata,
configuration errors, origin guards, comparison completion, hashes, and CSV/JSON
exports. Browser checks confirmed three verified strategy rows, measured SVG
chart data, inspection details, and no console warnings/errors. See
[raw integration checks](dashboard-integration.json).

Source line endings are preserved with `.gitattributes` so matching the original
means matching bytes, not only equivalent normalized text. Layout and theme
remain the final two staged frontend changes.

## Final release checks

The release suite passed all 18 tests; see [full output](network-tests.txt).
Browser checks verified light-mode persistence after reload, measured charts,
row inspection, a completed boundary map, and a 390-pixel responsive layout.
No console warnings or errors were observed. All 14 original application and
test files match byte-for-byte; see [source hashes](exact-source-match.json).
