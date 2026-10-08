# History reconstruction

This repository reconstructs an approximate development sequence for an existing
project. Its milestone dates represent an assumed development window of
27 September through 26 October 2026, not verified historical activity.

The planned work allocation is approximately 60% core networking and backend
development (Contributor A), and 40% frontend, reporting, and documentation
(Contributor B). This allocation describes a simulated workflow, not evidence
of actual contributions or reviews.

Contributor identities were supplied for Sreerag Aneesh (`gar-eer`) and Rini
Vaishnavi (`rini-7`). Assigned commits use the corresponding supplied identity.
These assignments describe this reconstruction rather than verified past work.
Branch and merge history can be reconstructed locally;
GitHub pull requests and reviews retain their actual creation timestamps.

## Initial milestone — 27 September 2026

Create the Python package, entry point placeholder, dependency declaration,
ignore rules, and introductory documentation. No transfer functionality exists
at this milestone.

## Original simulator milestone — 30 September 2026

Introduce a delay-based simulator with a fixed 64 KiB payload, 512 kbps limit,
4 KiB chunks, command-line reporting, and a timing smoke test. This is an
approximate recreation of the original concept, not recovered original source.

## Configurable simulation milestone — 2 October 2026

Add command-line payload size, bandwidth, and chunk size settings. Validate
positive inputs and finite rates, retain monotonic transfer timing, and check
custom rates and partial final chunks with automated tests.

## Scenario reporting milestone — 4 October 2026

Assign this reconstructed milestone to Rini Vaishnavi: load named constant-rate
presets, allow explicit setting overrides, and report simulation results as
text or JSON. Cover preset selection and reporting with command-line tests.

## HTTP upload milestone — 6 October 2026

Assign this reconstructed milestone to Sreerag Aneesh: make real localhost HTTP
uploads the default, acknowledge complete bodies at an in-memory origin, and
measure actual upload timing. Retain explicit simulation mode for the earlier
behavior. Report unpaced HTTP bandwidth honestly; proxy pacing follows later.

## Bandwidth proxy milestone — 8 October 2026

Assign this reconstructed milestone to Sreerag Aneesh: route uploads through a
body-paced proxy, share the allowance across connections, report proxy body
counters, and enforce an upload deadline with connection cleanup. Scheduled
outages and restoration follow in the next development milestone.

Completed feature branches are integrated into `main` using local milestone
merge commits. These merge commits are additional to the numbered development
commits. They do not represent GitHub PRs, approvals, or reviews.
