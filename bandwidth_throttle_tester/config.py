"""Named constant-rate presets for the initial transfer simulator."""
import json
import math
from pathlib import Path


# Resolve bundled examples independently of the shell's working directory.
PRESET_FILE = Path(__file__).resolve().parents[1] / 'examples' / 'scenarios.json'
SCENARIOS = {
    scenario['id']: scenario
    for scenario in json.loads(PRESET_FILE.read_text(encoding='utf-8'))['scenarios']
}


def number(value, name, low, high, integer=False):
    """Validate finite bounded experiment inputs before starting any trials."""
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value)):
        raise ValueError(f'{name} must be a finite number')
    if not low <= value <= high or integer and int(value) != value:
        raise ValueError(f'{name} must be {"an integer " if integer else ""}between {low} and {high}')
    return int(value) if integer else value


def validate_phases(phases):
    """Copy a finite, chronological schedule; zero kbps means offline."""
    if not isinstance(phases, list) or not phases:
        raise ValueError('Phase schedule must be a nonempty list')
    normalized = []
    for phase in phases:
        if not isinstance(phase, dict) or not {'at', 'kbps'} <= phase.keys():
            raise ValueError('Each phase requires at and kbps')
        for key in ('at', 'kbps'):
            value = phase[key]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ValueError('Phase times and rates must be finite and nonnegative')
        if not normalized and phase['at'] != 0:
            raise ValueError('Phase schedule must start at zero')
        if normalized and phase['at'] <= normalized[-1]['at']:
            raise ValueError('Phase times must strictly increase')
        normalized.append({'at': phase['at'], 'kbps': phase['kbps']})
    return normalized


def build_phases(bandwidth_kbps, outage_at_s=None, outage_duration_s=None):
    """Build a constant-rate schedule with an optional single outage."""
    if outage_at_s is None and outage_duration_s is None:
        return validate_phases([{'at': 0, 'kbps': bandwidth_kbps}])
    if outage_at_s is None or outage_duration_s is None:
        raise ValueError('Specify both outage start and duration')
    for value in (outage_at_s, outage_duration_s):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValueError('Outage settings must be finite and nonnegative')
    if outage_duration_s == 0:
        raise ValueError('Outage duration must be positive')
    phases = [] if outage_at_s == 0 else [{'at': 0, 'kbps': bandwidth_kbps}]
    phases.extend([
        {'at': outage_at_s, 'kbps': 0},
        {'at': outage_at_s + outage_duration_s, 'kbps': bandwidth_kbps},
    ])
    return validate_phases(phases)
