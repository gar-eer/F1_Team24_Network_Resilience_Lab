# Dashboard screenshot index

All images are actual browser captures from the Step 2 experiments on 25 October 2026. No dashboard values, outcomes, graphs or events were drawn or substituted. Full-page captures include the real configuration and results. Image 06 is a viewport capture positioned on the comparison table.

| File | Suggested report/presentation caption |
| --- | --- |
| [01-stable-dashboard.jpg](01-stable-dashboard.jpg) | Stable 2,048 kbps connection: three trials per strategy, all nine uploads verified by SHA-256. Configuration, throughput trace and individual results are visible. |
| [02-low-bandwidth-running.jpg](02-low-bandwidth-running.jpg) | Live upload at a 256 kbps limit. Captured while the final Resumable trial was still running; this is an intermediate state, not the final success count. |
| [03-low-bandwidth-completed.jpg](03-low-bandwidth-completed.jpg) | Completed low-bandwidth experiment: all nine uploads verified, with longer completion times than the stable baseline. |
| [04-outage-in-progress.jpg](04-outage-in-progress.jpg) | Resumable trial during the scheduled outage: network limit and measured throughput are zero while 384 KiB of server-confirmed progress remains intact. Backoff events show recovery attempts. |
| [05-outage-completed-dashboard.jpg](05-outage-completed-dashboard.jpg) | Completed temporary-disconnection experiment: the real throughput trace falls to zero, then resumes after restoration. Basic fails three times, while Retry and Resumable each verify three uploads. |
| [06-outage-results-comparison.jpg](06-outage-results-comparison.jpg) | Nine individual outage trials: compare failure/success, elapsed time, useful throughput, extra application bytes, retries and recovery. This is the most useful comparison image for a slide. |
| [07-file-integrity-inspection.jpg](07-file-integrity-inspection.jpg) | Inspecting the final Resumable result exposes matching original/origin SHA-256 hashes, application-byte counters and the exact experiment configuration. |

Recommended selection for a short presentation: **01, 04, 06 and 07**. Use raw/summary data rather than estimating precise values from a graph. Stable/slow traces show one selected trial at a time; the result table and raw exports contain all trials.

Names are working filenames. Apply the required slot/team naming convention when the final submission package is prepared.
