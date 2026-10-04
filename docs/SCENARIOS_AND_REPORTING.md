# Scenario configuration and transfer reporting

## Status

The simulator loads the bundled baseline and low-bandwidth presets and reports
actual simulator timing as text or JSON. The preset inputs remain configuration
fixtures, not measured experiment results. No real network traffic is generated.

```powershell
python main.py --scenario low-bandwidth --json
```

Explicit size and bandwidth options override preset values. Chunk size remains
a separate command-line setting. Without `--scenario`, the identifier is
`custom`. Presets are resolved relative to the application directory, so a
different shell working directory does not change their location.

## Scenario inputs

The [example scenarios](../examples/scenarios.json) describe two constant-rate
transfers using the same payload size so their timing can be compared.

| Field | Meaning |
| --- | --- |
| `id` | Unique scenario identifier |
| `description` | Human-readable purpose of the scenario |
| `payload_bytes` | Positive integer number of bytes to simulate |
| `bandwidth_kbps` | Positive, finite bandwidth in decimal kilobits per second |

A kilobit is 1,000 bits. A KiB is 1,024 bytes. The ideal duration in seconds is
`payload_bytes * 8 / (bandwidth_kbps * 1000)`.

For a 65,536-byte payload, the theoretical duration is 1.024 seconds at 512 kbps
and 2.048 seconds at 256 kbps. These values are calculations, not observed
measurements. A delay-based simulator will also include scheduling overhead.

## Result fields

| Field | Meaning |
| --- | --- |
| `mode` | `simulation`, to distinguish these results from network measurements |
| `scenario_id` | Identifier of the selected scenario |
| `payload_bytes` | Requested transfer size |
| `bandwidth_kbps` | Configured bandwidth limit |
| `chunk_bytes` | Maximum bytes accounted for in each simulation step |
| `transferred_bytes` | Bytes accounted for by the simulator |
| `elapsed_s` | Measured monotonic time from start to completion |
| `status` | `completed` for a finished simulation |
| `error` | Null for a finished simulation; reserved for future failure reporting |

Only a complete simulation should be marked completed. Simulated bytes must
not be described as verified network delivery. Integrity, outages, retries,
and server-confirmed progress require later networking milestones.

Invalid settings or unknown presets produce a command-line error with exit
status 2 and no result on standard output. They are not counted as completed
transfers. JSON output contains only the result, with no text banner.

## Implementation milestones

1. Fixed-default simulator: implemented.
2. Configurable payload and bandwidth settings with validation: implemented.
3. Named presets and transfer reports: implemented.
4. Real HTTP measurements: planned for later milestones.
