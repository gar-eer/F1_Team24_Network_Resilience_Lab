"""Run a localhost HTTP upload or the earlier delay-based simulator."""
import argparse
import asyncio
import json
import math

from bandwidth_throttle_tester.config import SCENARIOS, build_phases
from bandwidth_throttle_tester.throttler import (
    BANDWIDTH_KBPS, CHUNK_BYTES, PAYLOAD_BYTES, simulate_transfer, validate_settings,
)
from bandwidth_throttle_tester.transfer import run_upload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate', action='store_true',
                        help='Use the earlier delay-based simulator instead of HTTP')
    parser.add_argument('--strategy', choices=('basic', 'retry', 'resumable'), default='basic',
                        help='HTTP upload strategy (default: basic)')
    parser.add_argument('--max-retries', type=int, default=5,
                        help='Total recovery retries for Retry/Resumable (default: 5)')
    parser.add_argument('--resume-chunk-bytes', type=int, default=32768,
                        help='Resumable HTTP commit chunk size (default: 32768)')
    parser.add_argument('--scenario', choices=SCENARIOS,
                        help='Named preset; explicit settings override its values')
    parser.add_argument('--json', action='store_true',
                        help='Print one JSON result instead of the text summary')
    parser.add_argument('--size-bytes', type=int,
                        help='Positive payload size in bytes (default: 65536)')
    parser.add_argument('--bandwidth-kbps', type=float,
                        help='Positive decimal kilobits per second (default: 512)')
    parser.add_argument('--chunk-bytes', type=int, default=CHUNK_BYTES,
                        help='Positive write chunk size (default: 4096)')
    parser.add_argument('--timeout-s', type=float, default=120,
                        help='HTTP upload deadline in seconds (default: 120)')
    parser.add_argument('--outage-at-s', type=float,
                        help='Seconds after trial start to disconnect the proxy')
    parser.add_argument('--outage-duration-s', type=float,
                        help='Positive outage duration in seconds')
    args = parser.parse_args()
    preset = SCENARIOS.get(args.scenario, {})
    payload_bytes = (args.size_bytes if args.size_bytes is not None
                     else preset.get('payload_bytes', PAYLOAD_BYTES))
    bandwidth_kbps = (args.bandwidth_kbps if args.bandwidth_kbps is not None
                      else preset.get('bandwidth_kbps', BANDWIDTH_KBPS))
    try:
        validate_settings(payload_bytes, bandwidth_kbps, args.chunk_bytes)
        if args.max_retries < 0:
            raise ValueError('max_retries must be a nonnegative integer')
        if args.simulate and args.strategy != 'basic':
            raise ValueError('Retry and Resumable strategies require HTTP mode')
        if not 0 < args.resume_chunk_bytes <= 32 * 1024 * 1024:
            raise ValueError('resume_chunk_bytes must be a positive integer up to 32 MiB')
        if not math.isfinite(args.timeout_s) or args.timeout_s <= 0:
            raise ValueError('timeout_s must be a positive finite number')
        phases = build_phases(
            bandwidth_kbps,
            args.outage_at_s if args.outage_at_s is not None else preset.get('outage_at_s'),
            args.outage_duration_s if args.outage_duration_s is not None
            else preset.get('outage_duration_s'),
        )
        if args.simulate and (len(phases) > 1 or phases[0]['kbps'] == 0):
            raise ValueError('Outage schedules require HTTP mode')
        if args.simulate:
            transferred, elapsed = simulate_transfer(
                payload_bytes, bandwidth_kbps, args.chunk_bytes,
            )
        else:
            upload = asyncio.run(run_upload(
                payload_bytes, args.chunk_bytes, bandwidth_kbps, args.timeout_s, phases,
                strategy=args.strategy, max_retries=args.max_retries,
                resume_chunk_bytes=args.resume_chunk_bytes,
            ))
            transferred, elapsed = upload['transferred_bytes'], upload['elapsed_s']
    except ValueError as error:
        parser.error(str(error))
    except (OSError, TimeoutError, asyncio.IncompleteReadError) as error:
        parser.exit(1, f'Upload failed: {str(error) or "deadline exceeded"}\n')
    result = {
        'mode': 'simulation' if args.simulate else 'http',
        'bandwidth_applied': True,
        'scenario_id': args.scenario or 'custom',
        'payload_bytes': payload_bytes,
        'bandwidth_kbps': bandwidth_kbps,
        'chunk_bytes': args.chunk_bytes,
        'transferred_bytes': transferred,
        'elapsed_s': elapsed,
        'status': 'completed',
        'error': None,
    }
    if not args.simulate:
        result.update(upload, timeout_s=args.timeout_s)
    if args.json:
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        if args.simulate:
            print('Simulation only: no network traffic is generated.')
        else:
            print('Localhost HTTP upload through a bandwidth-limited proxy.')
        print(f'Scenario: {result["scenario_id"]}')
        if args.simulate:
            print(f'Transferred: {transferred} bytes at {bandwidth_kbps:g} kbps')
        else:
            print(f'Transferred: {transferred} bytes (origin acknowledged)')
            print(f'Proxy body bandwidth: {bandwidth_kbps:g} kbps')
            print(f'Strategy: {result["strategy"]}; attempts: {result["attempt_count"]}; '
                  f'retries: {result["retry_count"]}')
            print(f'SHA-256 integrity: {result["integrity"]}')
            print(f'Repeated/discarded body bytes: {result["retransmission_bytes"]}')
        print(f'Elapsed: {elapsed:.3f} s')
        print(f'Status: {result["status"]}')
        if result['error']:
            print(f'Error: {result["error"]}')
    return 0 if result['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
