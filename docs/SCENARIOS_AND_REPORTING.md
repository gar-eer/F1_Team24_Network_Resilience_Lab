# Scenario configuration and transfer reporting

## Status

The command loads bundled presets and reports transfer results as text or JSON.
Its default mode now sends real localhost HTTP uploads. The preset inputs are
configuration fixtures, not measured experiment results. Use `--simulate` to
run the earlier delay-based simulator.

HTTP uploads now pass through a body-paced proxy. Preset bandwidth limits are
applied to real forwarding, and `bandwidth_applied` is true in both modes.
Scheduled rate changes and outages belong to later milestones.

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
| `payload_bytes` | Positive integer transfer size; HTTP uploads are limited to 32 MiB |
| `bandwidth_kbps` | Positive, finite bandwidth in decimal kilobits per second |

A kilobit is 1,000 bits. A KiB is 1,024 bytes. The ideal duration in seconds is
`payload_bytes * 8 / (bandwidth_kbps * 1000)`.

For a 65,536-byte payload, the theoretical duration is 1.024 seconds at 512 kbps
and 2.048 seconds at 256 kbps. These values are calculations, not observed
measurements. A delay-based simulator also includes scheduling overhead.
Paced HTTP uploads also include connection and acknowledgement overhead.

## Result fields

| Field | Meaning |
| --- | --- |
| `mode` | `http` for real uploads, or `simulation` for delay-based accounting |
| `bandwidth_applied` | True: real proxy pacing in HTTP mode, simulated timing otherwise |
| `scenario_id` | Identifier of the selected scenario |
| `payload_bytes` | Requested transfer size |
| `bandwidth_kbps` | Configured bandwidth limit |
| `chunk_bytes` | Maximum application body write size, or simulation step size |
| `transferred_bytes` | Origin-acknowledged bytes in HTTP mode; simulated bytes otherwise |
| `proxy_ingress_bytes` | HTTP-only body bytes read by the proxy, excluding headers |
| `forwarded_bytes` | HTTP-only body bytes submitted by the proxy to the origin socket |
| `timeout_s` | HTTP-only upload deadline, excluding service setup and cleanup |
| `elapsed_s` | Measured monotonic time from start to completion |
| `status` | `completed` after a full transfer acknowledgement or finished simulation |
| `error` | Null for a finished transfer; reserved for future failure reporting |

HTTP acknowledgement confirms receipt of the full body by the local origin.
It does not establish hash integrity, durable disk storage, or wire overhead.
Simulation counts do not establish network delivery. Integrity checks, outages,
retries, and resumable progress belong to later milestones.

Invalid settings or unknown presets produce a command-line error with exit
status 2 and no result on standard output. They are not counted as completed
transfers. JSON output contains only the result, with no text banner.
HTTP deadlines or connection failures exit with status 1 and no completed JSON
result. The current runner does not yet record failed-trial reports.

## Implementation milestones

1. Fixed-default simulator: implemented.
2. Configurable payload and bandwidth settings with validation: implemented.
3. Named presets and transfer reports: implemented.
4. Real HTTP body delivery and acknowledgement timing: implemented.
5. Shared proxy body pacing, byte counters, and upload deadlines: implemented.
