"""Initial delay-based simulator; this does not throttle actual network traffic."""
import math
import time


PAYLOAD_BYTES = 64 * 1024
BANDWIDTH_KBPS = 512
CHUNK_BYTES = 4096


def simulate_transfer(payload_bytes=PAYLOAD_BYTES, bandwidth_kbps=BANDWIDTH_KBPS,
                      chunk_bytes=CHUNK_BYTES):
    """Account for chunks after sleeping for their configured transfer time.

    Bandwidth uses decimal kilobits per second. The elapsed time includes
    scheduler delays and Python overhead, so it may exceed the ideal duration.
    """
    for name, value in (('payload_bytes', payload_bytes), ('chunk_bytes', chunk_bytes)):
        if type(value) is not int or value <= 0:
            raise ValueError(f'{name} must be a positive integer')
    if (isinstance(bandwidth_kbps, bool)
            or not isinstance(bandwidth_kbps, (int, float))
            or not math.isfinite(bandwidth_kbps) or bandwidth_kbps <= 0):
        raise ValueError('bandwidth_kbps must be a positive finite number')
    transferred = 0
    bytes_per_second = bandwidth_kbps * 1000 / 8
    started = time.perf_counter()
    while transferred < payload_bytes:
        size = min(chunk_bytes, payload_bytes - transferred)
        time.sleep(size / bytes_per_second)
        transferred += size
    return transferred, time.perf_counter() - started
