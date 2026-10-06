"""Run a localhost HTTP upload or the earlier delay-based simulator."""
import argparse
import asyncio
import json

from bandwidth_throttle_tester.config import SCENARIOS
from bandwidth_throttle_tester.throttler import (
    BANDWIDTH_KBPS, CHUNK_BYTES, PAYLOAD_BYTES, simulate_transfer, validate_settings,
)
from bandwidth_throttle_tester.transfer import run_upload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate', action='store_true',
                        help='Use the earlier delay-based simulator instead of HTTP')
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
    args = parser.parse_args()
    preset = SCENARIOS.get(args.scenario, {})
    payload_bytes = (args.size_bytes if args.size_bytes is not None
                     else preset.get('payload_bytes', PAYLOAD_BYTES))
    bandwidth_kbps = (args.bandwidth_kbps if args.bandwidth_kbps is not None
                      else preset.get('bandwidth_kbps', BANDWIDTH_KBPS))
    try:
        validate_settings(payload_bytes, bandwidth_kbps, args.chunk_bytes)
        if args.simulate:
            transferred, elapsed = simulate_transfer(
                payload_bytes, bandwidth_kbps, args.chunk_bytes,
            )
        else:
            upload = asyncio.run(run_upload(payload_bytes, args.chunk_bytes))
            transferred, elapsed = upload['transferred_bytes'], upload['elapsed_s']
    except ValueError as error:
        parser.error(str(error))
    result = {
        'mode': 'simulation' if args.simulate else 'http',
        'bandwidth_applied': args.simulate,
        'scenario_id': args.scenario or 'custom',
        'payload_bytes': payload_bytes,
        'bandwidth_kbps': bandwidth_kbps,
        'chunk_bytes': args.chunk_bytes,
        'transferred_bytes': transferred,
        'elapsed_s': elapsed,
        'status': 'completed',
        'error': None,
    }
    if args.json:
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        if args.simulate:
            print('Simulation only: no network traffic is generated.')
        else:
            print('Localhost HTTP upload: bandwidth pacing is not yet applied.')
        print(f'Scenario: {result["scenario_id"]}')
        if args.simulate:
            print(f'Transferred: {transferred} bytes at {bandwidth_kbps:g} kbps')
        else:
            print(f'Transferred: {transferred} bytes (origin acknowledged)')
            print(f'Configured bandwidth: {bandwidth_kbps:g} kbps (not applied)')
        print(f'Elapsed: {elapsed:.3f} s')
        print(f'Status: {result["status"]}')


if __name__ == '__main__':
    main()
