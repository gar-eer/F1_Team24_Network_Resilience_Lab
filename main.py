"""Run the initial bandwidth-limited transfer simulation."""
import argparse
import json

from bandwidth_throttle_tester.config import SCENARIOS
from bandwidth_throttle_tester.throttler import (
    BANDWIDTH_KBPS, CHUNK_BYTES, PAYLOAD_BYTES, simulate_transfer,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=SCENARIOS,
                        help='Named preset; explicit settings override its values')
    parser.add_argument('--json', action='store_true',
                        help='Print one JSON result instead of the text summary')
    parser.add_argument('--size-bytes', type=int,
                        help='Positive payload size in bytes (default: 65536)')
    parser.add_argument('--bandwidth-kbps', type=float,
                        help='Positive decimal kilobits per second (default: 512)')
    parser.add_argument('--chunk-bytes', type=int, default=CHUNK_BYTES,
                        help='Positive simulation chunk size (default: 4096)')
    args = parser.parse_args()
    preset = SCENARIOS.get(args.scenario, {})
    payload_bytes = (args.size_bytes if args.size_bytes is not None
                     else preset.get('payload_bytes', PAYLOAD_BYTES))
    bandwidth_kbps = (args.bandwidth_kbps if args.bandwidth_kbps is not None
                      else preset.get('bandwidth_kbps', BANDWIDTH_KBPS))
    try:
        transferred, elapsed = simulate_transfer(
            payload_bytes, bandwidth_kbps, args.chunk_bytes,
        )
    except ValueError as error:
        parser.error(str(error))
    result = {
        'mode': 'simulation',
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
        print('Simulation only: no network traffic is generated.')
        print(f'Scenario: {result["scenario_id"]}')
        print(f'Transferred: {transferred} bytes at {bandwidth_kbps:g} kbps')
        print(f'Elapsed: {elapsed:.3f} s')
        print(f'Status: {result["status"]}')


if __name__ == '__main__':
    main()
