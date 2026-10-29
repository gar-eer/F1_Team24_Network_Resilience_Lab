# Experiment report: [title]

Template only. Replace the bracketed instructions with observed information;
do not treat this document as evidence of an executed experiment.

## Question

[State what is being compared and which outcome would answer the question.]

## Environment and provenance

| Item | Recorded value |
| --- | --- |
| Actual collection date and timezone | [record when the commands were run] |
| Source commit | [full Git revision] |
| Python version | [version] |
| Operating system | [system and version] |
| Relevant background load | [observations] |
| Execution mode | Real localhost HTTP uploads |
| Client strategy | [Basic, Retry, or Resumable; report separately] |
| Retry budget | [config.max_retries; Basic makes no retries] |
| Resumable commit size | [config.chunk_bytes, or not applicable] |
| Planned trials per scenario | [count] |

Record when experimental data was collected, along with the source revision
and exact configuration used for the run.

## Configuration

[List the exact commands or API configuration, payload and commit chunk sizes, bandwidth limits,
deadline, and absolute phase schedules. Describe any changes from the presets.]

## Individual trials

Keep one row per finished trial and retain failures and cancellations. Record
strategy, retry_count, and confirmed_bytes from each result and link its raw JSON.
Use events to describe resumption; request-attempt and probe totals are not
exported by the final engine and must not be invented.
Record expected_sha256, actual_sha256, and integrity with each trial. A completed
row must have matching hashes and integrity true. Retain null unavailable values
for failed-trial useful throughput and overhead percentage.

| Run ID | Scenario | Outcome | Elapsed (s) | Payload (bytes) | Confirmed (bytes) | Proxy ingress (bytes) | Forwarded (bytes) | Retries | Raw JSON |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [run] | [scenario] | [completed/failed/cancelled] | [measured] | [configured] | [measured] | [measured] | [measured] | [retry_count] | [relative link] |

## Failures and observed events

[For failed trials, record the error reason and observed phase events with both
scheduled and actual timestamps. Identify scheduled phases that were never
observed because the trial ended first. List invalid or excluded runs separately
with reasons; do not silently discard them.]

## Comparison

[For boundary experiments, identify each bandwidth/outage/strategy cell and
record which trials actually experienced an outage by inspecting their event
traces; there is no separate exported outage-exposure counter. Record observed
restorations and recovery times; distinguish null recovery from an unobserved
restoration, and do not replace either with zero.]

| Scenario and strategy | Non-cancelled trials | Verified successes | Failed | Completion fraction | Completed duration range (s) | Failed duration range (s) |
| --- | --- | --- | --- | --- | --- | --- |
| [scenario / strategy] | [count] | [count] | [count] | [verified successes / non-cancelled trials] | [observed range or unavailable] | [observed range or unavailable] |

[Describe differences supported by the recorded trials. Keep failed time to
interruption separate from completed upload time. State which outcome was
expected and whether the evidence matched it.]

List cancelled trials separately and exclude them from completion-rate
denominators, matching the application's summaries.

## Limits and conclusion

[Explain what the measurements answer and what remains unmeasured. At this
milestone, TCP retransmissions and wire overhead are unavailable. Hash integrity
is checked for complete uploads. Avoid general reliability claims from a
small set of local trials.]

## Reproduction

[Link the raw records, exact commands, source revision, and any supporting notes
needed to repeat the experiment.]
