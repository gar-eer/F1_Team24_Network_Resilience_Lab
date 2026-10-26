"""Validated, exportable experiment configuration. Rates use decimal kbps."""
import math

STRATEGIES = ('basic', 'retry', 'resumable')
SCENARIOS = {
    'stable': [{'at': 0, 'kbps': 2048}],
    'low': [{'at': 0, 'kbps': 256}],
    'drop': [{'at': 0, 'kbps': 2048}, {'at': 2, 'kbps': 256}],
    'outage': [{'at': 0, 'kbps': 2048}, {'at': 2, 'kbps': 0}, {'at': 7, 'kbps': 2048}],
    'intermittent': [{'at': 0, 'kbps': 2048}, {'at': 2, 'kbps': 0},
                     {'at': 4, 'kbps': 2048}, {'at': 6, 'kbps': 0}, {'at': 8, 'kbps': 2048}],
    'demo': [{'at': 0, 'kbps': 2000}, {'at': 3, 'kbps': 256},
             {'at': 7, 'kbps': 0}, {'at': 12, 'kbps': 2000}],
}

def number(value, name, low, high, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if not low <= value <= high or (integer and int(value) != value):
        raise ValueError(f'{name} must be {"an integer " if integer else ""}between {low} and {high}')
    return int(value) if integer else value

def validate(raw):
    if not isinstance(raw, dict):
        raise ValueError('Configuration must be an object')
    scenario = raw.get('scenario', 'demo')
    if scenario not in SCENARIOS and scenario != 'custom':
        raise ValueError('Unknown scenario')
    strategies = raw.get('strategies', list(STRATEGIES))
    if not isinstance(strategies, list) or not strategies or any(s not in STRATEGIES for s in strategies) or len(set(strategies)) != len(strategies):
        raise ValueError('Select unique upload strategies')
    phases = raw.get('phases', SCENARIOS.get(scenario))
    if not isinstance(phases, list) or not 1 <= len(phases) <= 20:
        raise ValueError('Provide 1-20 network phases')
    clean = []
    for phase in phases:
        if not isinstance(phase, dict):
            raise ValueError('Each phase must be an object')
        at = number(phase.get('at'), 'Phase time', 0, 3600)
        kbps = number(phase.get('kbps'), 'Bandwidth', 0, 100000)
        if (not clean and at != 0) or (clean and at <= clean[-1]['at']):
            raise ValueError('Phases must start at zero and increase strictly')
        clean.append({'at': at, 'kbps': kbps})
    return {
        'scenario': scenario, 'strategies': strategies, 'phases': clean,
        'size_bytes': number(raw.get('size_bytes', 2 * 1024**2), 'Payload bytes', 1024, 32 * 1024**2, True),
        'trials': number(raw.get('trials', 1), 'Trials', 1, 10, True),
        'delay_ms': number(raw.get('delay_ms', 20), 'Delay', 0, 2000),
        'deadline_s': number(raw.get('deadline_s', 120), 'Deadline', .1, 3600),
        'max_retries': number(raw.get('max_retries', 12), 'Retries', 0, 30, True),
        'chunk_bytes': number(raw.get('chunk_bytes', 32768), 'Chunk bytes', 1024, 262144, True),
    }
