# Scenarios and exports

The current `config.py` supplies stable, low, drop, outage, intermittent, demo,
and custom scenarios. Rates are decimal kbps; zero means offline. Phase times
are absolute, start at zero, and strictly increase. The default demo uses a
2 MiB deterministic payload to ensure the early slowdown and outage are reached.

Basic sends once. Retry restarts from byte zero with capped exponential backoff.
Resumable sends complete chunks, probes committed offsets through the same proxy
after failure, and continues from confirmed progress. Successful chunks/probes
do not reset or consume the total retry budget. Failed probes consume it.

The dashboard API exports CSV at `/api/experiments/<id>/csv` and full JSON at
`/api/experiments/<id>?download`. JSON includes configuration, raw events,
throughput samples, summaries, hashes, and metric definitions. CSV records one
finished trial per row with scalar metrics and JSON configuration/recovery data.
Exports during execution are snapshots. Results and chosen payloads are held in
memory; restart loses session history. Files are persisted only by explicit export.

See [metric definitions](METRICS.md), [experiment evidence](EXPERIMENTS.md), and
[boundary comparisons](BOUNDARY_EXPERIMENTS.md).
