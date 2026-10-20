> Historical prototype guide through 18 October. The current backend uses the trial/service API; this guide will be updated with the release documentation.

# Transfer metrics and integrity

These definitions apply to real HTTP trials. The delay-based simulator is a
separate mode and does not verify network delivery or origin integrity.
JSON results include machine-readable `metric_definitions` from `metrics.py`.

## Verified completion

The client hashes the original deterministic payload independently of the origin.
The origin returns SHA-256 only after its committed body has the complete expected
size. Full-file acknowledgements, final chunk acknowledgements, and complete-file
offset probes can carry the hash. Completion requires the returned hash to match
the source hash. A mismatch is terminal for every strategy and is not retried.

| Field | Meaning |
| --- | --- |
| `expected_sha256` | SHA-256 of the original source payload |
| `actual_sha256` | Origin-returned hash of the complete committed body; null if unavailable |
| `integrity` | True for matching hashes, false for a returned mismatch, null if no final hash is available |
| `status` | Completed only after hash verification; failed on interruption, deadline, budget exhaustion, missing hash, or mismatch |

A hash mismatch can occur after the entire body has been committed. Nonzero
or complete byte counts alone must not be interpreted as verified success.

## Body counters and derived values

| Field | Definition |
| --- | --- |
| `client_submitted_bytes` | Body bytes passed to the client's socket writes, including retries; excludes headers |
| `bytes_sent` | Body bytes actually read at proxy ingress, including partial and repeated requests |
| `proxy_ingress_bytes` | Compatibility name for the same observation as `bytes_sent` |
| `forwarded_bytes` | Body bytes submitted by the proxy to its origin socket |
| `confirmed_bytes` | Final contiguous committed origin bytes, inspected after active connections are cleaned up |
| `transferred_bytes` | Last contiguous byte count acknowledged or probed by the client; may lag final origin state after a lost acknowledgement |
| `retransmission_bytes` | `max(0, bytes_sent - confirmed_bytes)`; application-level repeated or discarded work |
| `overhead_percent` | `100 * retransmission_bytes / payload_bytes`, available only on verified success |
| `useful_kbps` | `payload_bytes * 8 / elapsed_s / 1000`, available only on verified success |
| `elapsed_s` | Monotonic time through verification or terminal error, including failures, probes, and backoff; excludes service setup and cleanup |
| `transport_overhead` | Null: TCP/IP headers, TCP retransmissions, and wire overhead are not measured |

The client can submit buffered bytes that never reach the proxy. Forwarding to a
socket does not by itself establish origin commitment. The origin commits full
requests or contiguous complete chunks atomically in memory; this is not durable
disk storage. All counters above exclude HTTP headers.

Failed uploads retain their measured counters. Failed or unverified trials have
null useful throughput and overhead percentage rather than misleading zeroes.
Repeated/discarded bytes can still be measured on failure. That value does not
measure TCP retransmissions, packet loss, or transport overhead.

## Recovery and success rates

`recoveries[].restored_at` is an observed restoration's scheduled time.
`recoveries[].recovery_s` is the time from there to the first subsequent
acknowledgement that increases confirmed bytes. The `progress` event trace
records those client acknowledgements. An unchanged probe does not qualify.
Backoff and request overhead are included. Null means an observed restoration
had no later progress; no entry means restoration was not observed at all.

Boundary `success_rate` is verified successes divided by finished trials in the
same strategy/rate/outage cell. Failed trials stay in the denominator. A fraction
of 1 describes only that tested cell and sample, not a general reliability
guarantee. Check observed-outage counts to identify uploads that finished before
the disruption. See [boundary experiments](BOUNDARY_EXPERIMENTS.md).

## Comparison

Compare useful throughput and overhead only among verified successes with their
configuration and strategy recorded. Keep failure counts and time to failure
separate. Use the [experiment guide](EXPERIMENTS.md) for collection commands and
[scenario definitions](SCENARIOS_AND_REPORTING.md) for retry and progress fields.
