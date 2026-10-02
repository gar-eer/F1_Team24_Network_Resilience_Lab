"""Run the initial bandwidth-limited transfer simulation."""
import argparse

from bandwidth_throttle_tester.throttler import (
    BANDWIDTH_KBPS, CHUNK_BYTES, PAYLOAD_BYTES, simulate_transfer,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size-bytes', type=int, default=PAYLOAD_BYTES,
                        help='Positive payload size in bytes (default: 65536)')
    parser.add_argument('--bandwidth-kbps', type=float, default=BANDWIDTH_KBPS,
                        help='Positive decimal kilobits per second (default: 512)')
    parser.add_argument('--chunk-bytes', type=int, default=CHUNK_BYTES,
                        help='Positive simulation chunk size (default: 4096)')
    args = parser.parse_args()
    try:
        transferred, elapsed = simulate_transfer(
            args.size_bytes, args.bandwidth_kbps, args.chunk_bytes,
        )
    except ValueError as error:
        parser.error(str(error))
    print('Simulation only: no network traffic is generated.')
    print(f'Transferred: {transferred} bytes at {args.bandwidth_kbps:g} kbps')
    print(f'Elapsed: {elapsed:.3f} s')


if __name__ == '__main__':
    main()
