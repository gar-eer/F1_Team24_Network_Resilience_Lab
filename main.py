"""Network Resilience Lab: python main.py [--port 8765]."""
import argparse
import asyncio
from bandwidth_throttle_tester.app import serve

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    try:
        asyncio.run(serve(args.port))
    except KeyboardInterrupt:
        print('\nLab stopped; active transfers cleaned up.')
