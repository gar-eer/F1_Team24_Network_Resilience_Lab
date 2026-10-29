# Report evaluation and supporting evidence

The report **Comparative Evaluation of File-Upload Recovery Strategies under
Controlled Network Disruption** uses the original 27-upload evaluation collected
on 25 October 2026. Its raw exports, analysis, statistics, screenshots, and
checksum manifest are restored unchanged in [step2-experiments](step2-experiments/README.md).
They are distinct from the additional 29 October validation checks.

## Evaluation settings

- One deterministic 524,288-byte (0.5 MiB) payload.
- Basic, Retry, and Resumable; three repetitions under each of three scenarios.
- A 60-second deadline, 20 ms request delay, 12 retries, and 32 KiB commit chunks.
- Stable: 2,048 kbps. Slow (`low`): 256 kbps. Outage: 2,048 kbps, offline from
  2 to 7 seconds, then restored to 2,048 kbps.

Each trial has fresh services, committed data, counters, clock, and retry budget.
The fixed strategy/scenario order and three repeats limit generalization.

## Results supporting the report

| Scenario | Strategy | Verified | Mean completion (s), successes only | Mean repeated/discarded bytes |
| --- | --- | --- | ---: | ---: |
| stable | basic | 3/3 | 2.12 | 0 |
| stable | retry | 3/3 | 2.12 | 0 |
| stable | resumable | 3/3 | 2.61 | 0 |
| low | basic | 3/3 | 16.46 | 0 |
| low | retry | 3/3 | 16.46 | 0 |
| low | resumable | 3/3 | 16.95 | 0 |
| outage | basic | 0/3 | N/A | 496,981 |
| outage | retry | 3/3 | 9.95 | 498,347 |
| outage | resumable | 3/3 | 8.50 | 4,096 |

The outage comparison is 9.95 seconds for Retry versus 8.50 seconds for Resumable,
with 498,347 versus 4,096 mean redundant body bytes: 99.2% less for this tested
configuration. All 18 stable/slow uploads verified; outage Basic failed 3/3,
and Retry/Resumable each verified 3/3. Full precision and sample standard
deviations are retained in [summary.csv](step2-experiments/summary.csv).

## Evidence and reproduction

- [Raw JSON/CSV exports](step2-experiments/raw/), [combined trials](step2-experiments/all-trials.csv),
  and [summary JSON](step2-experiments/summary.json).
- [Original screenshots and captions](step2-experiments/screenshots/README.md).
- [Evidence checksum manifest](step2-experiments/SHA256SUMS.txt).
- [Original Step 1 validation](../validation/step1-verification.md).

```powershell
python main.py
python -m unittest discover -v
python docs/step2-experiments/analyze_results.py
```

The analysis command validates saved exports and regenerates derived summaries;
it does not rerun network uploads. To collect another evaluation, use the settings
above and export each scenario separately. New measurements may differ; preserve
them separately rather than replacing the original report evidence.

## Additional validation

Additional validation includes a separate 2 MiB demonstration with three uploads,
a different phase schedule, and a 120-second deadline. Its timings are not the
report's 27-trial results. See [additional validation](SUPPLEMENTAL_VALIDATION.md)
and [saved validation records](../validation/additional-2026-10-29/verification.md).
