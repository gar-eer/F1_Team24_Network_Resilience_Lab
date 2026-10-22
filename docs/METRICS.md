# Metric definitions

These contracts come from the current engine's exported metadata.

| Metric | Meaning |
| --- | --- |
| `elapsed_s` | Monotonic seconds from trial start through hash verification or terminal error. |
| `bytes_sent` | Upload body bytes read at proxy ingress, including repeated and discarded bytes. Excludes HTTP headers and unread OS buffers. |
| `client_submitted_bytes` | Body bytes submitted by the client to its socket; may include buffered bytes never read by the proxy. |
| `forwarded_bytes` | Body bytes submitted by the proxy to the origin socket; excludes headers. Not a wire-level measurement. |
| `confirmed_bytes` | Server-confirmed contiguous committed payload bytes. Full uploads and resumable chunks commit atomically. |
| `retransmission_bytes` | max(0, proxy ingress bytes minus final origin committed unique bytes). Repeated/discarded application work, including failed partial bodies. |
| `overhead_percent` | 100 * retransmission_bytes / payload bytes; available for verified successes only. |
| `useful_kbps` | Verified payload bytes * 8 / elapsed seconds / 1000 on success; unavailable on failure. |
| `recovery_s` | Per restored phase: seconds from scheduled restoration to first subsequent acknowledgement that increases confirmed bytes; null when unobserved. |
| `retry_count` | Additional upload attempts begun after failure. Offset probes and successful chunks are not retries. |
| `success_rate` | Verified successes / completed trials in the same strategy/configuration cell. Cancelled trials excluded. |
| `integrity` | SHA-256 of original payload compared with SHA-256 of committed origin bytes; null unless a complete file is verified. |
| `transport_overhead` | Unavailable: TCP/IP headers, packet loss and TCP retransmissions are not measured. |

The origin commits complete full-file requests or sequential chunks in memory.
The client verifies the independently computed SHA-256 before marking completion.
Integrity is true for a match, false for a mismatch, and null when unavailable.
Useful throughput and overhead percentage are unavailable for failed or cancelled
trials. JSON uses null, CSV leaves unavailable scalar values blank, and the UI
shows an em dash. These are application-body observations, not wire measurements.

Recovery starts at the scheduled restoration time and ends at the first later
acknowledgement increasing confirmed bytes. An unchanged offset probe does not
count. An observed restoration without progress has null recovery; a restoration
after trial termination is unobserved. Backoff and per-request delay are included.

See [experiments](EXPERIMENTS.md) and [boundary comparisons](BOUNDARY_EXPERIMENTS.md).
