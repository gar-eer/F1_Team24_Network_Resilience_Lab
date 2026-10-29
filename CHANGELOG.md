# Changelog

## Documentation cleanup

- Simplify the README, development guide, and changelog.
- Organize supplemental validation records and update their links.

## Report evidence

- Include the original 27-trial evaluation, raw exports, summaries, screenshots,
  analysis script, and checksum manifest.
- Preserve supplemental validation runs separately from the report dataset.

## Dashboard and themes

- Add experiment controls, live results, throughput charts, and trial inspection.
- Support CSV/JSON downloads and responsive layouts.
- Add light and dark modes with saved and system theme preferences.

## Upload recovery engine

- Replace the initial bandwidth tester with real localhost HTTP uploads.
- Add shared bandwidth pacing, scheduled outages, and connection cleanup.
- Implement Basic, full-file Retry, and Resumable upload strategies.
- Verify uploads with SHA-256 and measure recovery, retries, and redundant data.
- Add failure-boundary experiments and networking integration tests.
