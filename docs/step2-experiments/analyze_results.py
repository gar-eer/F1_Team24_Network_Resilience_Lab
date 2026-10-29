"""Validate and summarize exported Step 2 measurements; standard library only.

Run from any directory: python docs/step2-experiments/analyze_results.py
This reads existing exports; it does not start transfers or invent measurements.
"""
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS = [('stable', 'Stable (2,048 kbps)'), ('low', 'Slow (256 kbps)'), ('outage', 'Disconnect (t=2-7s)')]
STRATEGIES = ('basic', 'retry', 'resumable')
EXPECTED_PHASES = {
    'stable': [{'at': 0, 'kbps': 2048}],
    'low': [{'at': 0, 'kbps': 256}],
    'outage': [{'at': 0, 'kbps': 2048}, {'at': 2, 'kbps': 0}, {'at': 7, 'kbps': 2048}],
}


def average(values):
    return statistics.mean(values) if values else None


def display(value, places=2):
    return 'N/A' if value is None else f'{value:.{places}f}'


def main():
    summaries, combined, hashes = [], [], set()
    metadata = []
    for scenario, label in SCENARIOS:
        job = json.loads((ROOT / 'raw' / f'{scenario}.json').read_text(encoding='utf-8-sig'))
        assert job['status'] == 'completed', (scenario, job['status'])
        assert job['mode'] == 'compare' and job['total'] == 9
        assert len(job['results']) == 9
        with (ROOT / 'raw' / f'{scenario}.csv').open(encoding='utf-8-sig', newline='') as source:
            source_rows = list(csv.DictReader(source))
        assert len(source_rows) == 9
        config = job['config']
        assert config['scenario'] == scenario and config['phases'] == EXPECTED_PHASES[scenario]
        assert config['size_bytes'] == 524288 and config['trials'] == 3
        assert config['deadline_s'] == 60 and config['max_retries'] == 12
        assert config['delay_ms'] == 20 and config['chunk_bytes'] == 32768
        assert config['strategies'] == list(STRATEGIES)
        hashes.add(job['payload_sha256'])
        metadata.append({'scenario': scenario, 'experiment_id': job['id'], 'created_at': job['created_at'], 'config': config})
        for result, source_row in zip(job['results'], source_rows):
            assert source_row['strategy'] == result['strategy'] and int(source_row['trial']) == result['trial']
            assert source_row['status'] == result['status']
            assert float(source_row['elapsed_s']) == result['elapsed_s']
            assert result['config'] == config and result['payload_bytes'] == 524288
            assert result['elapsed_s'] > 0
            assert result['expected_sha256'] == job['payload_sha256']
            assert result['retransmission_bytes'] == max(0, result['bytes_sent'] - result['confirmed_bytes'])
            if result['status'] == 'completed':
                assert result['integrity'] is True
                assert result['actual_sha256'] == result['expected_sha256']
                assert result['confirmed_bytes'] == 524288
            else:
                assert scenario == 'outage' and result['strategy'] == 'basic'
                assert result['status'] == 'failed' and result['error'] == 'Single upload interrupted'
                assert result['integrity'] is None and result['useful_kbps'] is None
            combined.append({'scenario': scenario, **result})
        for strategy in STRATEGIES:
            trials = [r for r in job['results'] if r['strategy'] == strategy]
            assert sorted(r['trial'] for r in trials) == [1, 2, 3]
            successful = [r for r in trials if r['status'] == 'completed' and r['integrity']]
            times = [r['elapsed_s'] for r in successful]
            recovery = [v['recovery_s'] for r in trials for v in r['recoveries'] if v['recovery_s'] is not None]
            summaries.append({
                'scenario': scenario, 'strategy': strategy, 'trials': 3,
                'verified_successes': len(successful), 'observed_success_percent': len(successful) / 3 * 100,
                'mean_completion_s_success_only': average(times),
                'sample_sd_completion_s_success_only': statistics.stdev(times) if len(times) > 1 else None,
                'min_completion_s_success_only': min(times) if times else None,
                'max_completion_s_success_only': max(times) if times else None,
                'mean_terminal_time_s_all_trials': average([r['elapsed_s'] for r in trials]),
                'mean_app_waste_bytes_all_trials': average([r['retransmission_bytes'] for r in trials]),
                'mean_overhead_percent_success_only': average([r['overhead_percent'] for r in successful]),
                'mean_retries_all_trials': average([r['retry_count'] for r in trials]),
                'mean_useful_kbps_success_only': average([r['useful_kbps'] for r in successful]),
                'mean_recovery_s_observed': average(recovery), 'recovery_observations': len(recovery),
            })
    assert len(hashes) == 1 and len(combined) == 27
    assert sum(r['status'] == 'completed' for r in combined) == 24
    assert sum(r['status'] == 'failed' for r in combined) == 3
    payload = bytes(range(256)) * 2048
    assert hashes == {hashlib.sha256(payload).hexdigest()}
    with (ROOT / 'summary.csv').open('w', encoding='utf-8', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    (ROOT / 'summary.json').write_text(json.dumps({'payload_sha256': next(iter(hashes)), 'experiments': metadata, 'summary': summaries}, indent=2), encoding='utf-8')
    combined_keys = ['scenario', 'strategy', 'trial', 'status', 'elapsed_s', 'bytes_sent', 'client_submitted_bytes', 'forwarded_bytes', 'confirmed_bytes', 'retransmission_bytes', 'overhead_percent', 'retry_count', 'useful_kbps', 'integrity', 'expected_sha256', 'actual_sha256', 'error', 'recoveries', 'config']
    with (ROOT / 'all-trials.csv').open('w', encoding='utf-8', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=combined_keys)
        writer.writeheader()
        for row in combined:
            writer.writerow({k: json.dumps(row.get(k)) if isinstance(row.get(k), (list, dict)) else row.get(k) for k in combined_keys})
    lines = [
        '# Step 2 — Repeated experiments and dashboard evidence', '',
        'Collected for submission preparation on 25 October 2026. These are actual localhost HTTP transfers through the project proxy, not measurements of real Wi-Fi or a mobile connection.', '',
        '## Design', '',
        '- The same deterministic **524,288-byte (0.5 MiB)** payload was used for all trials.',
        '- Three trials per strategy in each scenario: **27 total uploads**.',
        '- Strategies ran sequentially, Basic → Retry → Resumable, repeated three times within each scenario. Scenarios were collected in stable → slow → disconnected order.',
        '- Each trial received a fresh origin, proxy, scenario clock and retry budget. Strategies did not compete for bandwidth.',
        '- Settings: 60-second per-trial deadline, 20 ms per-request forwarding delay, 12 retries, 32 KiB resumable chunks.',
        '- Stable: 2,048 kbps. Slow: 256 kbps. Disconnected: 2,048 kbps, offline from t=2 to t=7 seconds, then restored to 2,048 kbps.',
        '- At 2,048 kbps, 0.5 MiB needs at least 2.048 seconds of body forwarding. The payload therefore cannot finish before the t=2s outage, even before request-delay overhead.',
        '- Inputs and measurements were exported through the actual dashboard CSV/JSON controls.', '',
        'Payload SHA-256: `' + next(iter(hashes)) + '`.', '',
        '## Observed results', '',
        '| Scenario | Strategy | Verified | Mean completion ± sample SD (s), successes only | Mean wasted application bytes, all trials | Mean retries | Mean observed recovery (s) |',
        '| --- | --- | --- | --- | ---: | ---: | ---: |',
    ]
    for summary in summaries:
        time = display(summary['mean_completion_s_success_only'])
        if summary['sample_sd_completion_s_success_only'] is not None:
            time += ' ± ' + display(summary['sample_sd_completion_s_success_only'])
        lines.append(f"| {summary['scenario']} | {summary['strategy']} | {summary['verified_successes']}/3 | {time} | {display(summary['mean_app_waste_bytes_all_trials'], 0)} | {display(summary['mean_retries_all_trials'])} | {display(summary['mean_recovery_s_observed'])} |")
    def get(scenario, strategy):
        return next(s for s in summaries if s['scenario'] == scenario and s['strategy'] == strategy)
    retry, resume = get('outage', 'retry'), get('outage', 'resumable')
    reduction = 100 * (1 - resume['mean_app_waste_bytes_all_trials'] / retry['mean_app_waste_bytes_all_trials'])
    basic_ratio = get('low', 'basic')['mean_completion_s_success_only'] / get('stable', 'basic')['mean_completion_s_success_only']
    lines += [
        '', 'N/A means unavailable, not zero. Basic did not complete any disconnected trial; its failure times must not be treated as fast completions. Failure times remain available in the raw exports and summary CSV.', '',
        '## Findings supported by these measurements', '',
        f"1. Reducing bandwidth from 2,048 to 256 kbps increased Basic's mean completion time by **{basic_ratio:.2f}×**. The nominal bandwidth ratio is 8×; request and scheduler overhead also contribute to elapsed time.",
        '2. All three strategies completed all stable and slow trials with matching SHA-256 hashes. In the disconnected scenario, Basic failed 3/3 times, while Retry and Resumable each completed 3/3 times.',
        f"3. In the disconnected scenario, Resumable's mean repeated/discarded application bytes were **{reduction:.1f}% lower** than Retry's for this payload and schedule.",
        f"4. Mean completion after a disconnected start was **{retry['mean_completion_s_success_only']:.2f}s** for Retry and **{resume['mean_completion_s_success_only']:.2f}s** for Resumable. Both include the five-second outage and backoff.",
        '5. Resumable also makes more requests. Compare its stable/slow completion times with Basic to see the cost of chunk acknowledgements and per-request delay when recovery is unnecessary.', '',
        '## Interpretation and limitations', '',
        '- Completion averages, ranges and sample standard deviations use **verified successes only**. Each group contains only three trials; these are descriptive observations, not a strong estimate of long-term reliability.',
        '- Wasted bytes mean proxy-observed repeated/discarded application body bytes: `max(0, proxy ingress bytes - final committed unique bytes)`. Failed Basic uploads have no committed file, so all observed ingress bytes are discarded work.',
        '- Recovery is the time from scheduled restoration until an acknowledgement increases confirmed progress. For full-file Retry this is normally full-file completion; for Resumable it can be a chunk acknowledgement. It is not first packet arrival.',
        '- Trial order was fixed rather than randomized, so order and machine-load effects cannot be excluded.',
        '- The backend paces upload body bytes and aborts sockets at outages. It does not emulate genuine packet loss, measure TCP retransmissions or count wire-level overhead.',
        '- These results describe only the tested local implementation, file size, phases, retry budget, deadline and request delay. They do not establish universal reliability or performance guarantees.', '',
        '## Files and reproduction', '',
        '- `raw/stable.json`, `raw/low.json`, `raw/outage.json`: untouched dashboard exports with configuration, hashes, events and throughput samples.',
        '- Matching `.csv` files: untouched per-scenario tabular exports.',
        '- `all-trials.csv`: all 27 trials in one table.',
        '- `summary.csv` and `summary.json`: derived statistics and experiment identifiers.',
        '- `screenshots/`: actual dashboard captures; see `screenshots/README.md` for captions.',
        '- `analyze_results.py`: standard-library-only validation and analysis. Run `python docs/step2-experiments/analyze_results.py` to regenerate the summaries from the saved exports.', '',
        'To collect a fresh experiment, run `python main.py`, choose Generate payload at 0.5 MiB, all three strategies, three trials, a 60-second deadline, 20 ms delay, 12 retries and 32 KiB chunks. Run the Stable connection, Low bandwidth and Temporary disconnect presets separately, waiting for 9/9 results each time. Download JSON and CSV after each scenario. New runs can have different timings and byte counts.', '',
        'Team/slot identifiers have not been supplied yet, so filenames are descriptive working names. Rename final submission artifacts to the required slot/team convention during packaging.',
    ]
    (ROOT / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Validated 27 trials: 24 verified completions and 3 expected Basic outage failures.')
    for row in summaries:
        print(row['scenario'], row['strategy'], f"{row['verified_successes']}/3", display(row['mean_completion_s_success_only']), 's', display(row['mean_app_waste_bytes_all_trials'], 0), 'wasted bytes')


if __name__ == '__main__':
    main()
