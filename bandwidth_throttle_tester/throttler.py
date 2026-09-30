"""Initial delay-based simulator; this does not throttle actual network traffic."""
import time


PAYLOAD_BYTES = 64 * 1024
BANDWIDTH_KBPS = 512
CHUNK_BYTES = 4096


def simulate_transfer():
    """Account for fixed-size chunks after sleeping for their transfer time.

    Bandwidth uses decimal kilobits per second. The elapsed time includes
    scheduler delays and Python overhead, so it may exceed the ideal duration.
    """
    transferred = 0
    bytes_per_second = BANDWIDTH_KBPS * 1000 / 8
    started = time.perf_counter()
    while transferred < PAYLOAD_BYTES:
        size = min(CHUNK_BYTES, PAYLOAD_BYTES - transferred)
        time.sleep(size / bytes_per_second)
        transferred += size
    return transferred, time.perf_counter() - started
