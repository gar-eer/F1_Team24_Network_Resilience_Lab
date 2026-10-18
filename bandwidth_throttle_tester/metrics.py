"""Definitions and derived application-level transfer measurements."""
METRICS = {
    'elapsed_s': 'Monotonic seconds through hash verification or terminal failure; excludes service setup and cleanup.',
    'bytes_sent': 'Upload body bytes read at proxy ingress, including repeated/discarded bodies; HTTP headers excluded.',
    'client_submitted_bytes': 'Body bytes submitted to the client socket; buffered bytes may never reach the proxy.',
    'forwarded_bytes': 'Body bytes submitted by the proxy to the origin socket; not actual wire traffic.',
    'confirmed_bytes': 'Final contiguous bytes committed in origin memory, inspected after connection cleanup.',
    'retransmission_bytes': 'max(0, proxy ingress bytes minus final committed bytes): application repeated/discarded work.',
    'overhead_percent': '100 * retransmission_bytes / payload bytes, on hash-verified success only.',
    'useful_kbps': 'Payload bytes * 8 / elapsed seconds / 1000, on hash-verified success only.',
    'integrity': 'True for matching SHA-256, false for a mismatching returned hash, null when unavailable.',
    'transport_overhead': 'Unavailable: TCP/IP headers, TCP retransmissions and actual wire overhead are not measured.',
    'recovery_s': 'Seconds from scheduled restoration to the first subsequent acknowledgement increasing confirmed progress; null if unobserved.',
    'success_rate': 'Hash-verified successes divided by finished trials in one strategy, bandwidth, and outage cell.',
}


def recovery_observations(events):
    """Measure only observed restoration and increasing client acknowledgements."""
    observations = []
    confirmed = 0
    for event in events:
        if event['kind'] == 'restored':
            observations.append({'restored_at': event['scheduled_at'], 'recovery_s': None})
        elif event['kind'] == 'progress' and event['confirmed_bytes'] > confirmed:
            confirmed = event['confirmed_bytes']
            for observation in observations:
                if observation['recovery_s'] is None:
                    observation['recovery_s'] = event['at'] - observation['restored_at']
    return observations


def derive_metrics(result, payload_bytes, committed_bytes):
    """Preserve missing success measurements as null instead of fabricated zero."""
    repeated = max(0, result['proxy_ingress_bytes'] - committed_bytes)
    verified = result['status'] == 'completed' and result['integrity'] is True
    return {
        'bytes_sent': result['proxy_ingress_bytes'],
        'confirmed_bytes': committed_bytes,
        'retransmission_bytes': repeated,
        'overhead_percent': 100 * repeated / payload_bytes if verified else None,
        'useful_kbps': payload_bytes * 8 / result['elapsed_s'] / 1000 if verified else None,
        'transport_overhead': None,
        'recoveries': recovery_observations(result['events']),
        'metric_definitions': dict(METRICS),
    }
