# Failure-boundary comparisons

Use the application's **Failure boundaries** controls once the frontend lands,
or the `Lab.start` example in [EXPERIMENTS.md](EXPERIMENTS.md). The earlier
prototype `--boundary` CLI has been retired.

Each bandwidth/outage pair receives phases starting at its selected rate,
disconnecting at 1 second for the selected positive duration, then restoring
that rate. Zero duration means no outage. All selected strategies and repeats
run serially with the same payload/settings and fresh trial services/state.

The API supports 1-6 bandwidths (8-100,000 kbps), 1-6 outage durations (0-120 s),
1-10 repeats, and at most 300 total trials. General trial bounds include a
1 KiB-32 MiB payload, 0.1-3,600 second deadline, 0-30 retries, 0-2,000 ms
per-request delay, and 1-256 KiB commit chunks. Worst-case trial time is the
number of trials times the deadline, plus cleanup.

Cells show hash-verified successes divided by completed non-cancelled trials.
Failed trials stay in the denominator; cancelled and unrun trials do not become
successes or failures. A job is completed after planned trials finish even when
some trials fail. The JSON's raw configuration and events explain failures.

Small payloads may finish before 1 second and never experience the outage.
Inspect observed events rather than inferring exposure from the schedule.
Success rates describe only tested configurations and sample sizes, not general
reliability guarantees or statistically certain thresholds. Repeat trials and
preserve error reasons, including deadline and retry exhaustion.

[Metric definitions](METRICS.md) explain the observed recovery intervals and
unavailable values. Use the [report template](EXPERIMENT_REPORT_TEMPLATE.md).
