# F1 Team24 submission guide

Course: BCSE308P Computer Networks Lab. Submission slot: F1. Team: 24.

## Deliverables

| VTOP assignment | Deliverable | Status |
| --- | --- | --- |
| 8 | [F1_Team24_Report.pdf](F1_Team24_Report.pdf) | Included |
| 9 | F1_Team24_PPT.pptx | Pending presentation from the team |
| 10 | Accessible GitHub repository URL | Publish and verify before submission |

Source is available directly in the repository and in
[F1_Team24_SourceCode.zip](F1_Team24_SourceCode.zip). Screenshots are available in
[F1_Team24_Screenshots.zip](F1_Team24_Screenshots.zip) and the original experiment
directory. [Test output](F1_Team24_TestResults.txt) and the
[experiment index](../docs/EXPERIMENTS.md) support verification.

The report PDF is exported from the supplied Word report. Its text, tables,
figures, and references are retained; the editable original is included under
the submission filename. Submission uses F1; the report also identifies the
theory and practical teaching slots in its author block.

## Local execution and demonstration

1. Install Python 3.11 or newer. No third-party packages are needed.
2. Run `python main.py` from the repository root.
3. Open http://127.0.0.1:8765 in a browser.
4. Use a generated 2 MiB payload, Recovery demo, all three strategies, one
   trial, and a 120-second deadline. Start the experiment.
5. Show the throughput trace, outage, retry events, and server-confirmed progress.
   Basic is expected to fail on interruption; Retry and Resumable should finish
   with matching SHA-256 hashes. Timings vary by machine and load.
6. Inspect completed results, compare redundant bytes and recovery, export CSV
   and JSON, and demonstrate the light/dark theme control.
7. Run `python -m unittest discover -v` to exercise the integration suite.

The report uses a separate 0.5 MiB, 27-upload evaluation. Exact settings, raw
results, statistics, screenshots, and checksums are under
`docs/step2-experiments/`. The 2 MiB demonstration is not the report dataset.

The project uses real loopback HTTP/TCP sockets with a user-space disruption
proxy. It does not use Packet Tracer, routers, a database, or packet-loss
emulation. Its architecture and scenario schedules are documented in
[architecture](../docs/ARCHITECTURE.md) and [scenarios](../docs/SCENARIOS_AND_REPORTING.md).

## Naming and organization

The repository folder and submission deliverables use `F1_Team24`. Runtime
source filenames, package paths, and original experiment evidence remain intact
to preserve imports, execution commands, references, and evidence checksums.
The source ZIP excludes Git metadata and submission archives. Full history is
retained by the Git repository, with inherited branch tips listed in
[F1_Team24_History.json](F1_Team24_History.json).

## Publishing after local review

Create an empty GitHub repository, preferably named `F1_Team24`, without adding
an initial README, license, or gitignore. From this folder, run:

```powershell
git remote add origin https://github.com/gar-eer/F1_Team24.git
git push -u origin main
git push origin --all
```

The `source-history` remote points to the local source repository; `origin`
above is the new submission repository. Existing commits and branches are
preserved. Git pushes do not create GitHub pull-request or review records.

For public access, open the final URL in a signed-out browser and check the
report, source, screenshots, test results, README, and commit history. For a
private repository, grant faculty access. Submit the final URL in Assignment 10.
Upload the report PDF separately to Assignment 8. Add the final presentation
and upload it separately to Assignment 9 when available.

## Submission verification on 31 October 2026

- Fresh integration run: 18 tests passed in 27.770 seconds.
- All 14 application and test files retain the source repository's exact bytes.
- All 28 original evidence files and four supplemental raw records retain their hashes.
- Saved-data analysis validates all 27 report trials in a separate working copy;
  see [analysis output](F1_Team24_AnalysisResults.txt).
- The 12-page report PDF was rendered and visually checked on every page.
- Existing history: 48 commits and 24 branch tips preserved before packaging.
- [Package hashes](F1_Team24_SHA256SUMS.txt) support integrity checks.
- Presentation and GitHub/VTOP publication remain pending.
