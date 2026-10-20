"""Metric contracts shared by exports and documentation."""
METRICS = {
    'elapsed_s': 'Monotonic seconds from trial start through hash verification or terminal error.',
    'bytes_sent': 'Upload body bytes read at proxy ingress, including repeated and discarded bytes. Excludes HTTP headers and unread OS buffers.',
    'client_submitted_bytes': 'Body bytes submitted by the client to its socket; may include buffered bytes never read by the proxy.',
    'forwarded_bytes': 'Body bytes submitted by the proxy to the origin socket; excludes headers. Not a wire-level measurement.',
    'confirmed_bytes': 'Server-confirmed contiguous committed payload bytes. Full uploads and resumable chunks commit atomically.',
    'retransmission_bytes': 'max(0, proxy ingress bytes minus final origin committed unique bytes). Repeated/discarded application work, including failed partial bodies.',
    'overhead_percent': '100 * retransmission_bytes / payload bytes; available for verified successes only.',
    'useful_kbps': 'Verified payload bytes * 8 / elapsed seconds / 1000 on success; unavailable on failure.',
    'recovery_s': 'Per restored phase: seconds from scheduled restoration to first subsequent acknowledgement that increases confirmed bytes; null when unobserved.',
    'retry_count': 'Additional upload attempts begun after failure. Offset probes and successful chunks are not retries.',
    'success_rate': 'Verified successes / completed trials in the same strategy/configuration cell. Cancelled trials excluded.',
    'integrity': 'SHA-256 of original payload compared with SHA-256 of committed origin bytes; null unless a complete file is verified.',
    'transport_overhead': 'Unavailable: TCP/IP headers, packet loss and TCP retransmissions are not measured.',
}
