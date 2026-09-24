# TASK-007 — ViPRO RTU / physical-bus discovery plan

Date: 2026-09-23  
Status: tool and dry-run procedure available; physical protocol remains
`UNKNOWN`

## Objective and boundary

This task prepares a Raspberry Pi as a diagnostic instrument for a possible
Modbus RTU / RS-485 ViPRO bus. It does not establish that the bench uses
Modbus, does not implement an ABB backend and does not authorize motor control.

The supplied tool can:

- enumerate candidate Linux serial devices without opening them;
- validate and report an explicit serial configuration;
- produce a zero-transmission dry-run plan;
- when separately and explicitly authorized, send only Modbus RTU function
  codes `0x03` (Read Holding Registers) and `0x04` (Read Input Registers);
- address only explicitly listed slave IDs and register ranges;
- timestamp each transaction with `CLOCK_MONOTONIC`;
- retain raw request/response frames and unsigned 16-bit register words;
- report responding IDs, Modbus exceptions, communication errors, round-trip
  latency and an explicitly derived wire-occupancy estimate.

It cannot:

- detect the actual protocol from the historical prototype;
- infer register semantics, units, signedness, word order or scaling;
- enable, disable, reset or command a drive;
- guarantee that a nominally readable vendor register has no device-specific
  read side effect;
- safely coexist with an existing Modbus RTU master;
- replace an independent shaft-torque reference.

## Repository evidence

### Confirmed only as source-code facts

| Item | Evidence | Interpretation |
|---|---|---|
| Historical backend calls itself an ABB "series 300" Modbus RTU/TCP skeleton | `joint_emulator/modbus_backend.py:2-6` | A past implementation direction, not a hardware identification |
| Example serial values are RTU, `/dev/ttyUSB0`, 19200 baud, even parity, one stop bit | `modbus_backend.py:21-26` | Explicit placeholders; must not be copied into an active lab configuration |
| Example unit IDs are 1–6 | `modbus_backend.py:26` | Placeholder logical mapping, not observed slave addresses |
| All register addresses and scaling values are `None` | `modbus_backend.py:27-34` | Register map and engineering units are unavailable |
| Historical backend exits while required fields are missing | `modbus_backend.py:42-48` | Deliberate fail-closed behavior |
| Historical backend contains register-write methods | `modbus_backend.py:66-95` | This file must not be used for discovery; TASK-007 does not import it |
| Project documentation says the physical interface may be CAN/CANopen, EtherCAT, Modbus or something else | `joint_emulator/README_JOINT.md:79-88` | Actual physical protocol remains `UNKNOWN` |
| Runtime accepts only `SimBackend` | `nodes/emulator_node.py:47-67` | No current ROS-to-ABB path exists |
| `pymodbus` is an optional project dependency | `requirements.txt:3-5` | Dependency declaration does not prove a Modbus bench |

### Physical values remaining `UNKNOWN`

- exact motor, drive, controller and communication-module models;
- whether the physical layer is RS-485;
- whether Modbus RTU is enabled and which device is master;
- port pinout, signal labels/polarity, shielding, reference conductor and
  galvanic isolation;
- baud, parity, stop bits and data bits;
- slave IDs;
- register ranges that are safe and meaningful to read;
- data types, signedness, byte/word order, scaling and units;
- update mechanism, device sampling time and response latency;
- current, position, torque, temperature and status mappings;
- termination and biasing arrangement.

No `UNKNOWN` value is replaced by the examples in `modbus_backend.py`.

## Safety model implemented by the tool

The canonical configuration
`research/configs/rtu_probe.yaml` is disabled. All unknown serial values are
`null`, both active-transmission switches are false and both lists are empty.

An active request is possible only when all of these conditions hold:

1. the operator supplies `--transmit-read-only` on the command line;
2. configuration `mode` is `ACTIVE_READ_ONLY`;
3. `safety.allow_active_transmit` is `true`;
4. absence of another master is explicitly confirmed;
5. use of an isolated RS-485 adapter is explicitly confirmed;
6. wiring and topology have been reviewed and approved;
7. the serial port and every serial parameter are explicit;
8. `probe.active_scan_enabled` is `true`;
9. slave IDs and register ranges are explicit and nonempty;
10. the output directory and inter-request delay are explicit.

Slave ID zero is rejected, so the Modbus broadcast address cannot be used. The
only constructible protocol requests are FC03 and FC04. The utility contains no
Modbus functions for writing coils/registers, enabling drives, setting torque
or resetting faults.

The flag authorizes read traffic only for that invocation. It does not certify
the configured ranges as safe; that evidence must come from the matching
official manual and the approved laboratory procedure.

## Laboratory procedure

### Phase 0 — documentation and non-energized inventory

Before connecting the Raspberry Pi, obtain:

1. clear nameplate photographs for every drive, motor, controller and
   communication module;
2. the official manuals matching the complete type codes and firmware;
3. cabinet wiring drawings and controller/PLC project export;
4. drive parameter backups, including communication option configuration;
5. the documented existing master and bus topology;
6. connector/pinout, cable, isolation, termination and biasing information;
7. the vendor register map and explicit identification of registers approved
   for diagnostic reads;
8. laboratory safety approval and a recovery procedure.

Inspect labels such as `A/B`, `D+/D-`, `RS-485` or `Modbus`, but do not infer
polarity or pinout from generic naming. Follow the exact hardware manual.

### Phase 1 — determine whether active probing is permissible

Active probing is **NO-GO** if any of the following is true:

- another master may already be connected;
- the physical protocol or connector is uncertain;
- the adapter is not galvanically isolated;
- wiring, termination or reference conductors are not verified;
- no manual-backed, read-only register range is known;
- the installation owner has not approved the connection.

If another master exists, use an approved passive capture method or retrieve
data through the existing controller. A normal USB–RS-485 adapter plus this
tool is not presented as a passive sniffer.

### Phase 2 — enumerate Raspberry Pi ports without opening them

```bash
/usr/bin/python3 \
  research/tools/rtu_probe.py \
  --config research/configs/rtu_probe.yaml \
  --list-ports
```

This searches `/dev/ttyUSB*`, `/dev/ttyACM*`, `/dev/ttyAMA*` and `/dev/ttyS*`
and reads available sysfs identity strings. It does not open a serial port and
does not transmit.

Device enumeration does not prove which port reaches the ViPRO bus. Preserve
the adapter serial number and stable `/dev/serial/by-id/...` path when
available.

### Phase 3 — create an evidence-backed lab configuration

Copy the disabled template to a session-specific configuration. Do not alter
the canonical unknown template to make its placeholders look confirmed.

Fill only values supported by the inspected manual/configuration:

```yaml
mode: ACTIVE_READ_ONLY
serial:
  port: "/dev/serial/by-id/<verified-adapter>"
  baud: <manual/config evidence>
  parity: <N, E or O>
  stop_bits: <1, 1.5 or 2>
  data_bits: <5, 6, 7 or 8>
  timeout_s: <approved finite value>
safety:
  allow_active_transmit: true
  existing_master_confirmed_absent: true
  isolated_rs485_adapter_confirmed: true
  wiring_and_topology_approved: true
probe:
  active_scan_enabled: true
  slave_ids: [<explicit IDs only>]
  register_ranges:
    - name: "<manual reference>"
      function: "holding_registers"  # or input_registers
      start_address: <documented address>
      count: <documented count, 1..125>
  inter_request_delay_s: <approved value>
output:
  directory: "<new session directory>"
```

Address notation is a frequent source of error: a vendor label such as
`40001` is not automatically the zero-based protocol address `0`. Resolve the
manual's addressing convention explicitly before entering `start_address`.

### Phase 4 — mandatory dry run

Run the session configuration without the active flag:

```bash
/usr/bin/python3 research/tools/rtu_probe.py \
  --config /path/to/session_rtu_probe.yaml
```

Expected properties:

```text
mode: DRY_RUN
serial_port_opened: false
frames_transmitted: 0
```

Review the exact slave/range Cartesian product and planned transaction count.
The tool never expands the scan to IDs 1–247 and never invents a register
range.

### Phase 5 — approved active read-only probe

Only after Phases 0–4 and laboratory approval:

```bash
/usr/bin/python3 research/tools/rtu_probe.py \
  --config /path/to/session_rtu_probe.yaml \
  --transmit-read-only
```

Begin with one documented slave ID, one documented register and a conservative
request cadence justified for that bus. Expand only after reviewing the raw
result. Do not run the historical `modbus_backend.py`.

Stop if there are unexpected drive/controller state changes, bus errors,
timeouts inconsistent with the manual, or evidence of another master.

## Output contract

The tool creates new timestamped files and never overwrites an existing probe
file:

```text
rtu_probe_<UTC>_<pid>_transactions.jsonl
rtu_probe_<UTC>_<pid>_summary.json
```

Each transaction record contains:

- transaction index;
- `monotonic_start_ns`, `monotonic_end_ns` and `rtt_ns` from
  `CLOCK_MONOTONIC`;
- log-write UTC for traceability, not duration calculation;
- slave ID, FC03/FC04, explicit range name, address and count;
- complete raw request and response frames in hexadecimal;
- raw unsigned 16-bit register words;
- Modbus exception or communication error details.

The summary contains:

- responding slave IDs;
- counts of successful requests, exceptions and communication errors;
- minimum, mean, P50, P95 and maximum round-trip time;
- observed raw wire bytes;
- estimated wire time and probe bus-occupancy fraction.

The occupancy value is a derived diagnostic from configured serial framing and
observed byte counts. It excludes unknown traffic, bus-silent intervals,
adapter turnaround and drive processing and must not be treated as a calibrated
bus measurement.

Raw register words are intentionally not converted to position, current,
torque or temperature. Interpretation requires the exact register manual,
signedness/word-order evidence and calibration.

## Interpretation rules

A valid response demonstrates only that, under the exact tested serial
configuration, a device at that address answered an FC03/FC04 request. It does
not by itself demonstrate:

- that the device is an ABB drive;
- that every ViPRO drive uses the same protocol/configuration;
- that an address is position, current or torque;
- that a raw count has SI units;
- that drive-estimated torque equals shaft/port torque;
- that the signal is independent from the controller model;
- that the bus timing is suitable for closed-loop load emulation.

Candidate signal mappings must remain `suspected` until correlated against a
manual-backed controlled change and then calibrated. Results from a drive
estimate still require an independent mechanical reference for fidelity
validation whenever feasible.

## GO / NO-GO after discovery

Proceed to a future read-only ABB acquisition backend only if:

1. protocol, physical layer and every used serial parameter are confirmed;
2. the bus master/topology is understood;
3. slave-to-physical-drive mapping is documented;
4. read ranges, data representation, scaling and units are manual-backed;
5. update rate, latency and error behavior are measured;
6. raw results, configuration and evidence are archived;
7. no motor command/enable path is needed for acquisition.

Do not proceed to a command backend until the separate physical-interface,
safety, scaling, operating-envelope and controlled commissioning requirements
are satisfied. TASK-007 is discovery, not motor control.

## Dependencies and tests

Dry run and port enumeration require Python 3 and PyYAML. Active serial access
also requires `pyserial`; it is imported only after all active configuration
gates pass. The tool does not depend on or import the historical
`modbus_backend.py`.

Run all research tests from the workspace root:

```bash
/usr/bin/python3 -m unittest discover \
  -s src/joint_emulator/research/tests -v
```

The tests use a fake transport. They do not open serial hardware or transmit on
the physical bus.
