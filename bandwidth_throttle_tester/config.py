"""Named constant-rate presets for the initial transfer simulator."""
import json
from pathlib import Path


# Resolve bundled examples independently of the shell's working directory.
PRESET_FILE = Path(__file__).resolve().parents[1] / 'examples' / 'scenarios.json'
SCENARIOS = {
    scenario['id']: scenario
    for scenario in json.loads(PRESET_FILE.read_text(encoding='utf-8'))['scenarios']
}
