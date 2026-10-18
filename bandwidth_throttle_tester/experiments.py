"""Serial failure-boundary sweeps with fresh services and measured outcomes."""
from .config import build_phases, number
from .transfer import MAX_PAYLOAD_BYTES, run_upload


STRATEGIES = ('basic', 'retry', 'resumable')


def axis(values, name, low, high):
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= 6:
        raise ValueError(f'{name} requires 1-6 values')
    return sorted(set(number(value, name, low, high) for value in values))


async def run_boundary(payload_bytes=65536, *, bandwidths=None, outages=None,
                       strategies=None, trials=1, timeout_s=120, outage_at_s=1,
                       chunk_bytes=4096, resume_chunk_bytes=32768, max_retries=5):
    """Return raw trials and per-cell success rates, including failed outcomes."""
    bands = axis(bandwidths if bandwidths is not None else [256, 512],
                 'Bandwidths', 8, 100000)
    durations = axis(outages if outages is not None else [0, 0.5], 'Outages', 0, 120)
    selected = list(STRATEGIES) if strategies is None else strategies
    if (not isinstance(selected, (list, tuple)) or not selected
            or any(strategy not in STRATEGIES for strategy in selected)
            or len(set(selected)) != len(selected)):
        raise ValueError('Select unique Basic, Retry, or Resumable strategies')
    selected = list(selected)
    config = {
        'payload_bytes': number(payload_bytes, 'Payload bytes', 1, MAX_PAYLOAD_BYTES, True),
        'bandwidths': bands, 'outages': durations, 'strategies': list(selected),
        'trials': number(trials, 'Trials', 1, 10, True),
        'timeout_s': number(timeout_s, 'Deadline', 0.1, 3600),
        'outage_at_s': number(outage_at_s, 'Outage start', 0, 3600),
        'chunk_bytes': number(chunk_bytes, 'Write chunk bytes', 1, MAX_PAYLOAD_BYTES, True),
        'resume_chunk_bytes': number(resume_chunk_bytes, 'Commit chunk bytes', 1, MAX_PAYLOAD_BYTES, True),
        'max_retries': number(max_retries, 'Retries', 0, 30, True),
    }
    total = len(bands) * len(durations) * len(selected) * config['trials']
    if total > 300:
        raise ValueError('Limit a boundary experiment to 300 trials')
    results = []
    for band in bands:
        for duration in durations:
            phases = (build_phases(band, config['outage_at_s'], duration) if duration
                      else build_phases(band))
            for trial in range(1, config['trials'] + 1):
                for strategy in selected:
                    # run_upload creates a new origin, proxy, clock, counters,
                    # and retry budget while regenerating the identical payload.
                    result = await run_upload(
                        config['payload_bytes'], config['chunk_bytes'], band,
                        config['timeout_s'], phases, strategy, config['max_retries'],
                        config['resume_chunk_bytes'],
                    )
                    result.update(
                        mode='http', bandwidth_applied=True, trial=trial,
                        payload_bytes=config['payload_bytes'], bandwidth_kbps=band,
                        outage_s=duration, outage_at_s=config['outage_at_s'],
                        timeout_s=config['timeout_s'], chunk_bytes=config['chunk_bytes'],
                        outage_observed=any(event['kind'] == 'outage' for event in result['events']),
                    )
                    results.append(result)
    summaries = []
    for band in bands:
        for duration in durations:
            for strategy in selected:
                rows = [row for row in results if row['bandwidth_kbps'] == band
                        and row['outage_s'] == duration and row['strategy'] == strategy]
                successes = sum(row['status'] == 'completed' and row['integrity'] is True
                                for row in rows)
                summaries.append({
                    'bandwidth_kbps': band, 'outage_s': duration, 'strategy': strategy,
                    'finished_trials': len(rows), 'verified_successes': successes,
                    'failed_trials': len(rows) - successes,
                    'success_rate': successes / len(rows),
                    'observed_outage_trials': sum(row['outage_observed'] for row in rows),
                })
    return {'mode': 'boundary', 'status': 'completed', 'config': config,
            'total_trials': total, 'results': results, 'summaries': summaries}
