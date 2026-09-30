"""Run the initial bandwidth-limited transfer simulation."""
from bandwidth_throttle_tester.throttler import BANDWIDTH_KBPS, simulate_transfer


def main():
    transferred, elapsed = simulate_transfer()
    print('Simulation only: no network traffic is generated.')
    print(f'Transferred: {transferred} bytes at {BANDWIDTH_KBPS} kbps')
    print(f'Elapsed: {elapsed:.3f} s')


if __name__ == '__main__':
    main()
