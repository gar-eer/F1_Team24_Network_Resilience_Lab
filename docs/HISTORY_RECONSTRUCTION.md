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

## Outage milestone — 10 October 2026

Assign this reconstructed milestone to Sreerag Aneesh: validate absolute phase
schedules, interrupt active connections on outage, reject offline attempts, and
accept new connections after restoration. Add the outage preset, explicit CLI
outage settings, observed phase events, and failed-transfer reports. Automatic
retry and upload resumption remain separate future milestones.

## Experiment documentation milestone — 11 October 2026

Assign this reconstructed milestone to Rini Vaishnavi: document a repeatable
baseline, low-bandwidth, and outage comparison, JSON capture commands, expected
exit codes, and an experiment report template. Distinguish observed measurements
and actual data collection dates from hypothetical timings and historical
milestone dates. No application behavior changes at this milestone.

## Upload strategies milestone — 12 October 2026

Assign this reconstructed milestone to Sreerag Aneesh: expose Basic and full-file
Retry strategies, implement capped exponential backoff and a total trial retry
budget, preserve the absolute proxy schedule across attempts, and include all
attempts and backoff in the deadline and elapsed time. Report actual attempts,
retries, and client events. Resumable transfer remains a separate milestone.

## Resumable upload milestone — 14 October 2026

Assign this reconstructed milestone to Sreerag Aneesh: commit complete contiguous
chunks at the origin, preserve prior progress across connection interruptions,
probe committed offsets through the same proxy after failures, and continue at
the confirmed offset. Keep retry budgets and deadlines global across chunks and
probes. Report confirmed bytes, request attempts, and offset probes. Hash
verification remains a separate milestone.

## Integrity and metrics milestone — 16 October 2026

Assign this reconstructed milestone to Sreerag Aneesh: require independently
computed source and origin SHA-256 hashes to match before completion; reject
missing or corrupt final hashes; measure client-submitted bytes and final origin
commitment; derive repeated/discarded body work, verified useful throughput, and
overhead percentage. Keep unavailable failure and transport metrics null and
include metric definitions in JSON results.

## Recovery and boundary milestone — 18 October 2026

Assign this reconstructed milestone to Sreerag Aneesh: record increasing client
acknowledgements and measure observed recovery from scheduled restoration;
preserve null recovery when no later progress is observed. Add a serial
bandwidth/outage grid with fresh trial services and counters, global deadlines
and retry budgets, raw results, observed-outage flags, and per-cell verified
success rates that retain failed outcomes in their denominators.

## Network cleanup milestone — 20 October 2026

Consolidate the prototype into the original trial/service architecture, with shared
pacing credit, cancellation-preserving bounded socket close, real per-request
delay, and explicit resource cleanup. Retire the earlier CLI and its obsolete
modules/tests. This makes the backend source match the original project while
frontend assets remain scheduled for later milestones.

## Networking validation milestone — 21 October 2026

Add the original networking and scheduler integration suite plus the full recovery
demo. The static root-page assertion is introduced when the frontend lands.
Measurements are collected on the actual execution date, independently of the
reconstructed Git milestone date.

## Milestone 17 — 2026-10-22

Rini documents the actual reconstruction measurements, exact metric contracts,
current scenarios/exports, and boundary interpretation. The collection date is
explicitly separate from the illustrative milestone date.

## Milestone 18 — 2026-10-23

Rini prepares the release README, architecture/development guides, contributing
instructions, issue/PR templates, and the explicitly reconstructed changelog.
