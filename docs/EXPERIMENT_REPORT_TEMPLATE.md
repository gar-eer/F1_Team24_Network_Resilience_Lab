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
| Execution mode | [HTTP or simulation; report separately] |
| Client strategy | [single attempt at this milestone] |
| Planned trials per scenario | [count] |

Historical milestone dates in the reconstructed Git history are not evidence
of when experimental data was collected. Record the actual collection date.

## Configuration

[List the exact commands, payload and write chunk sizes, bandwidth limits,
deadline, and absolute phase schedules. Describe any changes from the presets.]

## Individual trials

Keep one row per valid finished trial. Use the exact JSON field definitions.
Add rows as needed and retain failures. Link the raw JSON for each row.

| Run ID | Scenario | Outcome | Elapsed (s) | Payload (bytes) | Acknowledged (bytes) | Proxy ingress (bytes) | Forwarded (bytes) | Exit code | Raw JSON |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [run] | [scenario] | [completed/failed] | [measured] | [configured] | [measured] | [measured] | [measured] | [recorded] | [relative link] |

## Failures and observed events

[For failed trials, record the error reason and observed phase events with both
scheduled and actual timestamps. Identify scheduled phases that were never
observed because the trial ended first. List invalid or excluded runs separately
with reasons; do not silently discard them.]

## Comparison

| Scenario | Valid trials | Completed | Failed | Completion fraction | Completed duration range (s) | Failed duration range (s) |
| --- | --- | --- | --- | --- | --- | --- |
| [scenario] | [count] | [count] | [count] | [completed / valid trials] | [observed range or unavailable] | [observed range or unavailable] |

[Describe differences supported by the recorded trials. Keep failed time to
interruption separate from completed upload time. State which outcome was
expected and whether the evidence matched it.]

## Limits and conclusion

[Explain what the measurements answer and what remains unmeasured. At this
milestone, hash integrity, TCP retransmissions, wire overhead, automatic retry,
and resumable recovery are unavailable. Avoid general reliability claims from a
small set of local trials.]

## Reproduction

[Link the raw records, exact commands, source revision, and any supporting notes
needed to repeat the experiment.]
