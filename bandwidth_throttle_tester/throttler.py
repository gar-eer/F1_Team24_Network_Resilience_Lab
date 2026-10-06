"""Initial delay-based simulator; this does not throttle actual network traffic."""
import math
import time


PAYLOAD_BYTES = 64 * 1024
BANDWIDTH_KBPS = 512
CHUNK_BYTES = 4096


def validate_settings(payload_bytes, bandwidth_kbps, chunk_bytes):
    """Validate common CLI settings before starting a transfer."""
    for name, value in (('payload_bytes', payload_bytes), ('chunk_bytes', chunk_bytes)):
        if type(value) is not int or value <= 0:
            raise ValueError(f'{name} must be a positive integer')
    if (isinstance(bandwidth_kbps, bool)
            or not isinstance(bandwidth_kbps, (int, float))
            or not math.isfinite(bandwidth_kbps) or bandwidth_kbps <= 0):
        raise ValueError('bandwidth_kbps must be a positive finite number')


def simulate_transfer(payload_bytes=PAYLOAD_BYTES, bandwidth_kbps=BANDWIDTH_KBPS,
                      chunk_bytes=CHUNK_BYTES):
    """Simulate chunk timing using decimal kbps and a monotonic clock."""
    validate_settings(payload_bytes, bandwidth_kbps, chunk_bytes)
    transferred = 0
    bytes_per_second = bandwidth_kbps * 1000 / 8
    started = time.perf_counter()
    while transferred < payload_bytes:
        size = min(chunk_bytes, payload_bytes - transferred)
        time.sleep(size / bytes_per_second)
        transferred += size
    return transferred, time.perf_counter() - started
