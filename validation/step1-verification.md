# Step 1 — Application verification

Date: 25 October 2026 (Asia/Calcutta).
Environment: Windows, Python 3.13.13, Node.js for JavaScript syntax checks; real localhost TCP sockets. Temporary dashboard services used ports 8766 and 8767; no external network or OS traffic-shaping changes were made.

## Final result

**Passed after fixing one cancellation bug.** The application is ready for the next step: collecting repeated experimental results and submission screenshots. This verification is not a claim of remote-network reliability or complete production hardening.

## Automated checks

Command: `python -m unittest discover -v`

Final result: **18 tests passed in 26.106 seconds**, with no failures or errors. Full output: [step1-tests.txt](step1-tests.txt).

The suite exercises real proxy transfers, independent SHA-256 verification, bandwidth-duration differences, shared limits across concurrent connections, Basic interruption failure, Retry restart overhead, Resumable progress preservation, repeated outages, changing bandwidth, request delay, retry exhaustion, origin errors, corrupted hashes, deadlines, serial sweeps, file selection, exports, input validation and cancellation.

Separate checks also passed with exit code 0:

- `node --check bandwidth_throttle_tester/static/app.js`
- `node --check bandwidth_throttle_tester/static/theme.js`
- `python -m compileall -q main.py bandwidth_throttle_tester tests`

## Bug discovered and corrected

The initial 17-test suite passed, but browser testing exposed a problem when cancelling a large, slow upload with unsent socket buffers. A timeout while closing the client socket replaced an already-propagating cancellation exception. The trial was incorrectly recorded as a failure, allowing the scheduler to continue with the next strategy while the Cancel request waited.

The focused regression `test_cancel_large_buffered_upload_preserves_cancellation` failed before the fix (`CancelledError not raised`). Socket cleanup now handles cancellation separately from ordinary close errors, aborting buffered writes without replacing the original cancellation. The regression passed after the fix, followed by the full 18-test suite.

Browser verification after restarting the corrected backend confirmed:

- Cancelling a 2 MiB upload under the 256 kbps preset changes the experiment to Cancelled.
- Exactly one cancelled trial is recorded; the two queued strategy trials do not run.
- Start becomes enabled again, and a subsequent experiment runs successfully.

Changed source: `bandwidth_throttle_tester/throttler.py`.
Regression: `tests/test_network.py`.

## Dashboard checks

| Control or behavior | Observed result |
| --- | --- |
| Initial page and API connection | Dashboard loads and reports Connected. |
| Light/dark mode | Both themes switch; the selected theme survives reload. |
| No strategy selected | Start displays a clear validation message and does not create a job. |
| Generated payload and stable comparison | All three strategies completed a 131,072-byte payload with matching SHA-256 hashes. |
| Result-row inspection | Shows equal original/origin hashes, byte counters and the actual trial configuration. |
| CSV and JSON export | Both links downloaded real files. Parsed exports each contained three verified stable trials. |
| Local-file picker | Selected README.md (15,428 bytes); all three strategies completed successfully. Original and origin SHA-256 both matched `4e7ca7e80cc90c012783460c1c70592c8068ce5bb2f59cb981c9f233eee36e5f`. |
| Cancellation | Large slow upload cancels and queued trials stay unstarted after the fix. |
| Custom phase editing and advanced settings | Three edited phases, zero request delay, eight retries and 16 KiB chunks were reflected in the inspected result configuration. |
| Custom outage recovery | Basic failed at interruption. Retry and Resumable finished with matching hashes. |
| Failure-boundary controls | A six-trial sweep finished, with correct per-strategy success rates. |
| Browser error/warning log | No entries after the final sweep. |

### Custom scenario checked in the browser

Payload: 131,072 bytes. Phases: 512 kbps at t=0; offline at t=0.3s; restored to 512 kbps at t=0.8s. Deadline: 15 seconds. Request delay: 0 ms. Retry budget: 8. Resumable chunk size: 16,384 bytes.

| Strategy | Outcome | Duration | Extra application bytes | Retries | Recovery |
| --- | --- | ---: | ---: | ---: | ---: |
| Basic | Expected failure on interruption | 0.30 s | 20 KiB | 0 | Unavailable |
| Retry | SHA-256 verified | 3.16 s | 20 KiB | 2 | 2.36 s |
| Resumable | SHA-256 verified | 2.94 s | 4 KiB | 2 | 0.57 s |

These are single-run functional checks, not the repeated evaluation planned for Step 2.

### Boundary sweep checked in the browser

Generated size: 0.064 MiB (67,109 bytes); bandwidth: 256 kbps; outage durations: 0 and 0.5 seconds; outage starts at t=1s; deadline: 5 seconds; one trial per strategy; request delay: 0 ms; retry budget: 8; chunk size: 16 KiB.

| Outage duration | Basic | Retry | Resumable |
| --- | --- | --- | --- |
| 0 s | 1/1 verified | 1/1 verified | 1/1 verified |
| 0.5 s | 0/1 (interrupted) | 1/1 verified | 1/1 verified |

Downloaded JSON and CSV were parsed and verified to contain six trials, five verified successes and the one expected Basic failure. This confirms the table represents measured outcomes; an expected strategy failure is not an application failure.

## Saved evidence

- [Automated test output](step1-tests.txt)
- [Stable comparison JSON downloaded through the UI](step1-browser-results.json)
- [Stable comparison CSV downloaded through the UI](step1-browser-results.csv)
- [Boundary sweep JSON downloaded through the UI](step1-boundary-results.json)
- [Boundary sweep CSV downloaded through the UI](step1-boundary-results.csv)

The pre-existing full-duration demonstration evidence remains in `demo-results.json`; it was not regenerated during this step. Formal repeated experiments, report screenshots, PDF/PPTX creation and GitHub publication remain separate tasks.

## Limits

Verification used local connections through the controllable proxy. It did not test two physical computers, Wi-Fi/hotspot interruptions, genuine packet loss, wire-level transport overhead or server crash recovery. A broader security, accessibility and cross-browser audit was not performed.
