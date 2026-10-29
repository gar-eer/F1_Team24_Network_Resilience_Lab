# Step 2 — Repeated experiments and dashboard evidence

Collected for submission preparation on 25 October 2026. These are actual localhost HTTP transfers through the project proxy, not measurements of real Wi-Fi or a mobile connection.

## Design

- The same deterministic **524,288-byte (0.5 MiB)** payload was used for all trials.
- Three trials per strategy in each scenario: **27 total uploads**.
- Strategies ran sequentially, Basic → Retry → Resumable, repeated three times within each scenario. Scenarios were collected in stable → slow → disconnected order.
- Each trial received a fresh origin, proxy, scenario clock and retry budget. Strategies did not compete for bandwidth.
- Settings: 60-second per-trial deadline, 20 ms per-request forwarding delay, 12 retries, 32 KiB resumable chunks.
- Stable: 2,048 kbps. Slow: 256 kbps. Disconnected: 2,048 kbps, offline from t=2 to t=7 seconds, then restored to 2,048 kbps.
- At 2,048 kbps, 0.5 MiB needs at least 2.048 seconds of body forwarding. The payload therefore cannot finish before the t=2s outage, even before request-delay overhead.
- Inputs and measurements were exported through the actual dashboard CSV/JSON controls.

Payload SHA-256: `33bc8aab40703678c3ebe94d2dd8f2afff285dd901f9234e841e4679f8204fd5`.

## Observed results

| Scenario | Strategy | Verified | Mean completion ± sample SD (s), successes only | Mean wasted application bytes, all trials | Mean retries | Mean observed recovery (s) |
| --- | --- | --- | --- | ---: | ---: | ---: |
| stable | basic | 3/3 | 2.12 ± 0.01 | 0 | 0.00 | N/A |
| stable | retry | 3/3 | 2.12 ± 0.00 | 0 | 0.00 | N/A |
| stable | resumable | 3/3 | 2.61 ± 0.01 | 0 | 0.00 | N/A |
| low | basic | 3/3 | 16.46 ± 0.01 | 0 | 0.00 | N/A |
| low | retry | 3/3 | 16.46 ± 0.00 | 0 | 0.00 | N/A |
| low | resumable | 3/3 | 16.95 ± 0.00 | 0 | 0.00 | N/A |
| outage | basic | 0/3 | N/A | 496981 | 0.00 | N/A |
| outage | retry | 3/3 | 9.95 ± 0.01 | 498347 | 5.00 | 2.95 |
| outage | resumable | 3/3 | 8.50 ± 0.01 | 4096 | 5.00 | 1.01 |

N/A means unavailable, not zero. Basic did not complete any disconnected trial; its failure times must not be treated as fast completions. Failure times remain available in the raw exports and summary CSV.

## Findings supported by these measurements

1. Reducing bandwidth from 2,048 to 256 kbps increased Basic's mean completion time by **7.75×**. The nominal bandwidth ratio is 8×; request and scheduler overhead also contribute to elapsed time.
2. All three strategies completed all stable and slow trials with matching SHA-256 hashes. In the disconnected scenario, Basic failed 3/3 times, while Retry and Resumable each completed 3/3 times.
3. In the disconnected scenario, Resumable's mean repeated/discarded application bytes were **99.2% lower** than Retry's for this payload and schedule.
4. Mean completion after a disconnected start was **9.95s** for Retry and **8.50s** for Resumable. Both include the five-second outage and backoff.
5. Resumable also makes more requests. Compare its stable/slow completion times with Basic to see the cost of chunk acknowledgements and per-request delay when recovery is unnecessary.

## Interpretation and limitations

- Completion averages, ranges and sample standard deviations use **verified successes only**. Each group contains only three trials; these are descriptive observations, not a strong estimate of long-term reliability.
- Wasted bytes mean proxy-observed repeated/discarded application body bytes: `max(0, proxy ingress bytes - final committed unique bytes)`. Failed Basic uploads have no committed file, so all observed ingress bytes are discarded work.
- Recovery is the time from scheduled restoration until an acknowledgement increases confirmed progress. For full-file Retry this is normally full-file completion; for Resumable it can be a chunk acknowledgement. It is not first packet arrival.
- Trial order was fixed rather than randomized, so order and machine-load effects cannot be excluded.
- The backend paces upload body bytes and aborts sockets at outages. It does not emulate genuine packet loss, measure TCP retransmissions or count wire-level overhead.
- These results describe only the tested local implementation, file size, phases, retry budget, deadline and request delay. They do not establish universal reliability or performance guarantees.

## Files and reproduction

- `raw/stable.json`, `raw/low.json`, `raw/outage.json`: untouched dashboard exports with configuration, hashes, events and throughput samples.
- Matching `.csv` files: untouched per-scenario tabular exports.
- `all-trials.csv`: all 27 trials in one table.
- `summary.csv` and `summary.json`: derived statistics and experiment identifiers.
- `screenshots/`: actual dashboard captures; see `screenshots/README.md` for captions.
- `analyze_results.py`: standard-library-only validation and analysis. Run `python docs/step2-experiments/analyze_results.py` to regenerate the summaries from the saved exports.

To collect a fresh experiment, run `python main.py`, choose Generate payload at 0.5 MiB, all three strategies, three trials, a 60-second deadline, 20 ms delay, 12 retries and 32 KiB chunks. Run the Stable connection, Low bandwidth and Temporary disconnect presets separately, waiting for 9/9 results each time. Download JSON and CSV after each scenario. New runs can have different timings and byte counts.

Team/slot identifiers have not been supplied yet, so filenames are descriptive working names. Rename final submission artifacts to the required slot/team convention during packaging.
