# Scenario configuration and reporting groundwork

## Status

This document proposes inputs and result fields for the initial transfer
simulator. It does not add a scenario loader or a reporting implementation.
The examples are design fixtures, not measured experiment results.

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

## Proposed result fields

| Field | Meaning |
| --- | --- |
| `scenario_id` | Identifier of the selected scenario |
| `payload_bytes` | Requested transfer size |
| `bandwidth_kbps` | Configured bandwidth limit |
| `transferred_bytes` | Bytes accounted for by the simulator |
| `elapsed_s` | Measured monotonic time from start to completion |
| `status` | `completed` or `failed` |
| `error` | Failure reason, or null on success |

Only a complete simulation should be marked completed. Simulated bytes must
not be described as verified network delivery. Integrity, outages, retries,
and server-confirmed progress require later networking milestones.

## Planned implementation

1. Add the initial fixed-default simulator.
2. Introduce configurable payload and bandwidth settings with validation.
3. Load named presets and report a result for the selected scenario.
4. Extend the measurements when real HTTP transfers are introduced.
