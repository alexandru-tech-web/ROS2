# TASK-006 — ViPRO physical integration requirements

Date: 2026-09-23  
Status: requirements only; no physical communication or command implementation

## Result

The minimum physical-integration boundary can be defined without knowing the
ABB protocol. The research layer must consume and produce typed SI-domain
records; a backend owns device transport, raw representation, mapping,
calibration and clock conversion.

```text
                         RESEARCH LOGIC
          virtual model / trials / fidelity / certification
                                  │
                   normalized backend contract
                  samples │ commands │ receipts
                    ┌─────┴──────────┐
                    │                │
          SimBackend adapter   ABBPhysicalBackend
             SIMULATED             ABSENT
                    │                │
                 PairSim     device-specific I/O
                                     │
                                  ABB bench
```

The repository currently ends on the left branch. The right branch is a
requirement, not implemented evidence.

## Confirmed baseline

The contract uses only these confirmed or canonically declared facts:

- the research topology contains logical pairs `(A0,B0)`, `(A1,B1)`,
  `(A2,B2)`;
- A is the physical actuator under test and B is the physical load actuator;
- A/B are declared locally coupled through a rigid common shaft/coupling;
- the current executable backend is `SimBackend` only;
- there is no physical acquisition/control node in the current ROS graph;
- current `tau_b` is a requested/model-derived SIM command;
- current `JointState.effort` is a visualization alias of `tau_b`;
- neither is a physical torque measurement.

The physical pair mapping, protocol, device models, sample rates, control modes,
scaling and safety limits remain `UNKNOWN`.

## Separation of responsibilities

### Research logic owns

- virtual mechanical model and requested load torque;
- experiment/session/trial identity;
- fidelity metrics and uncertainty analysis;
- ACCEPT/REJECT or later adaptation logic;
- requirements on normalized signals, quality and timing;
- immutable association of samples, commands and configuration.

Research logic must never contain ABB register addresses, slave IDs, fieldbus
object indices, raw scaling constants or vendor status-word bit masks.

### Backend owns

- transport and physical-device discovery;
- physical-to-logical A/B mapping;
- raw I/O and preservation of raw values/frames;
- device data type, signedness and byte/word order;
- calibration-backed conversion to SI;
- acquisition timestamps, device timestamps and clock identifiers;
- status/fault decoding with firmware/manual applicability;
- command-mode capability and command receipts;
- enforcement of evidence-backed local limits and stale-command behavior.

### Independent metrology owns

When available, an independent torque acquisition path should remain logically
separate from the controller estimator. Its sensor identity, calibration,
clock, mounting point and uncertainty must be preserved. A backend may package
the value into a common snapshot, but must not erase its independent origin.

## Conceptual backend API

This task does not modify `drive_iface.py`. The following is a specification
for a future versioned adapter/boundary.

```text
open_read_only(config_evidence) -> BackendCapabilities
get_capabilities()              -> BackendCapabilities
read_snapshot()                 -> BackendSample
close()                         -> None

# Available only in a separately permitted COMMAND_CAPABLE profile:
prepare_command_session(permit, limits, initial_state) -> CommandReceipt
request_enable_state(command)                         -> CommandReceipt
apply_command(command)                                -> CommandReceipt
request_fault_reset(command)                          -> CommandReceipt
request_safe_state(reason)                            -> CommandReceipt
```

`open_read_only()` must expose no route to enable, reset or command a device.
Command methods are not optional shortcuts inside the read-only object; they
belong to a separately gated profile.

### `BackendCapabilities`

Must state, with evidence:

- backend identity and profile;
- physical pair/side mapping;
- available measurements and commands;
- clock domains;
- calibration identifiers;
- documented limits;
- status/fault semantics;
- unavailable/unknown capabilities.

Capability absence is represented as unavailable/null, not as a zero-valued
signal.

### `BackendSample`

Each coherent physical sample needs at least:

```text
pair_id
side
sequence_index
acquisition_monotonic_ns
device_timestamp_raw          # null only if device supplies none
device_clock_id               # null with UNKNOWN provenance if absent
normalized_signals            # SI values only after validated conversion
raw_signals                   # immutable raw values
quality_flags
fault_status
provenance
calibration_ids
```

The backend must not generate plausible physical values for unavailable
channels. An absent current/torque/temperature channel remains absent.

### `BackendCommand` and `CommandReceipt`

A command needs a unique ID, pair/side, documented mode, SI value, monotonic
issue time, deadline, sequence and external permit ID. A receipt needs to state
whether the backend/device accepted or rejected it and, if available, when it
was acknowledged/applied.

Requested, accepted and physically realized quantities are distinct:

```text
requested command
      != command receipt
      != drive torque estimate
      != independent shaft torque
```

## Physical input contract

The complete machine-readable definitions are in
`research/configs/physical_interface_contract.yaml`.

| Input | SI boundary unit | Source/status now | Control use | Independent validation use |
|---|---|---|---|---|
| A/B encoder position | rad | source `UNKNOWN` | Conditional after calibration/timing | Kinematic validation only; not torque fidelity |
| A/B device timestamp | s plus preserved raw ticks | `UNKNOWN` | Conditional | Temporal alignment only |
| A/B velocity feedback | rad/s | `UNKNOWN` | Conditional after filter/bandwidth characterization | Conditional for kinematics |
| A/B motor current | A | `UNKNOWN` | Conditional for monitoring/documented loop | Not independently sufficient for port torque |
| A/B drive torque estimate | N·m at documented point | `UNKNOWN` | Conditional | No if shared with control; conditional after independent calibration |
| A/B motor temperature | K | `UNKNOWN` | Conditional for derating/abort | Experimental context, not torque reference |
| A/B drive temperature | K | `UNKNOWN` | Conditional for derating/abort | Experimental context, not torque reference |
| A/B status/fault words | 1 | `UNKNOWN` | Required for inhibit/abort after decoding | Trial-validity metadata only |
| Independent shaft torque | N·m at documented location | existence `UNKNOWN` | Preferably reserved for validation | Yes after calibration/timing/independence checks |
| Command receipt/status | 1 | `UNKNOWN` | Command supervision | Timing only, not mechanical validation |

The status of every physical source is currently `UNKNOWN`. Table units are
requirements at the normalized boundary, not claims about device-native units.

## Physical output contract

| Output | SI unit | Current capability | Control use | Validation use |
|---|---|---|---|---|
| Command-mode request | 1 / closed enum | `UNKNOWN` | Conditional | No |
| Torque command | N·m at documented point | `UNKNOWN` | Conditional if supported | Reference/request only |
| Current command | A with documented meaning | `UNKNOWN` | Conditional if supported | No |
| Velocity command | rad/s | `UNKNOWN` | Conditional if supported | No |
| Enable/disable request | 1 / documented state enum | `UNKNOWN` | Conditional after safety approval | No |
| Fault-reset request | event | `UNKNOWN`; unavailable by default | Conditional, documented capability only | No |

The contract lists mutually possible command types; it does not state that any
one is supported by the ABB hardware. A future backend advertises only modes
confirmed by exact manuals/configuration and validated during commissioning.

No position command is assumed. In particular, this contract does not endorse
independent position control of two rigidly coupled actuators.

## Timestamp requirements

Every acquired sample must carry:

1. `acquisition_monotonic_ns` from a named `CLOCK_MONOTONIC` domain;
2. a monotonically increasing sequence index;
3. device-native timestamp/ticks if exposed;
4. the device clock identity and wrap behavior;
5. UTC only as supplementary session correlation, never for durations.

Every command must carry issue time and deadline. Receipts should preserve
backend receive time and device acknowledgment/application time if available.

The following rates/timing values remain `UNKNOWN` until measured:

- physical acquisition rate;
- drive internal update rate;
- command update rate;
- sample age;
- request/response delay;
- command-to-physical-torque delay;
- jitter and dropped/reordered samples.

No numerical minimum rate is imposed without bandwidth and fidelity evidence.

## Calibration and provenance requirements

### Position/velocity

Require source identity, raw representation, sign, zero, counts-to-angle scale,
gear ratio, mounting mapping, update/filter behavior and uncertainty. A velocity
reported by a drive may be measured or internally derived; its provenance must
state which.

### Current and torque

Motor current requires current definition (phase, RMS, DC-link, torque-producing
component, etc.), scale, offset, bandwidth and calibration. Conversion to torque
also requires torque constant, gear ratio/reference point, efficiency/loss
model, sign and uncertainty.

A drive torque estimate is `DERIVED` or `IDENTIFIED`; the fact that the drive
reports a numeric value does not make it an independent mechanical measurement.

An independent shaft transducer requires sensor/conditioner identity,
mounting/reference location, traceable zero/span/sign, range, bandwidth,
cross-sensitivity, calibration validity and uncertainty.

### Status and commands

Raw status words are `MEASURED`; bit decoding is `MANUAL`/`CODE_CONFIG` and
must match model/firmware. Command scaling and state transitions require manual
and configuration evidence plus commissioning logs.

## Safety boundary

The backend software cannot replace the physical safety chain. Before command
support exists, the project needs:

- independent physical E-stop and documented safe torque removal/disable path;
- risk assessment and approved operating envelope;
- verified continuous/peak torque, current, torque-rate, speed, position,
  power and thermal limits;
- documented enable/disable/fault state machine;
- local watchdog and stale-command timeout;
- command deadline and sequence enforcement;
- fail-closed behavior on missing/stale feedback, communication loss, backend
  exception and clock invalidity;
- no restoration of a previous nonzero command after reconnect/reset;
- staged low-energy commissioning with authorized supervision.

`request_safe_state()` is only a software request. It must never be documented
or tested as if it were the independent physical E-stop.

## A. Minimum laboratory evidence required

1. Nameplate photographs and exact type codes for six motors, all drives,
   controller and communication modules.
2. Official manuals matching the exact type codes and firmware.
3. Cabinet wiring/I/O drawings and a verified A0/B0–A2/B2 mapping.
4. Drive/controller parameter backup and project export.
5. Confirmed physical protocol, topology, existing master and device addresses.
6. Encoder, gearbox and coupling datasheets; signs, zeros, ratios and mounting.
7. Current/torque/status/temperature channel definitions and raw scaling.
8. Independent torque-sensor model, location, conditioner and calibration, if
   present.
9. Physical safety circuit, E-stop/STO behavior, risk assessment and approved
   operating limits.
10. Clock/timestamp capabilities and expected update mechanisms.

## B. Minimum signals for first read-only physical acquisition

The first acquisition milestone can remain non-commanding. Minimum set:

- verified physical component and pair/side identity;
- A and B position feedback, or an explicit documented statement that a side
  has no independently accessible encoder;
- acquisition monotonic timestamp and sequence index for every record;
- device timestamp/ticks when available;
- raw drive status/fault words;
- immutable raw values plus configuration, software revision and mapping;
- quality flags for timeout, stale data, decoding error and clock validity.

Current, drive torque, temperature and velocity should be acquired at this
stage when documented and available, but their absence does not prevent the
first connectivity/acquisition record. It does prevent stronger conclusions.

## C. Minimum additional signals for fidelity research

To compare requested and physically realized load, add:

- timestamped requested B load torque;
- calibrated physical torque at a documented mechanical point, ideally from an
  independent shaft transducer;
- if torque is estimated indirectly: motor current, motor constant, gear ratio,
  efficiency/loss model and quantified uncertainty;
- aligned A/B position and velocity;
- command receipt/application timing if available;
- saturation, warning and fault status;
- motor/drive temperature and session-state metadata;
- measured rates, latency, jitter, missing samples and clock alignment.

Without a calibrated physical torque route, the first read-only acquisition is
useful for architecture and timing but does not validate torque fidelity.

## D. Blockers before any motor command is permitted

1. Exact protocol, hardware, firmware, mapping and control mode are unknown.
2. Command addresses/objects, data types, scaling and sign are unknown.
3. Hardware limits and safe operating envelope are unknown.
4. Physical E-stop/STO and drive state transitions are undocumented here.
5. Command watchdog, deadline, stale-feedback and reconnect behavior are not
   commissioned.
6. Command acknowledgment/application observability is unknown.
7. Rigid-coupling hazards and low-energy commissioning procedure are not
   approved.
8. No explicit authorized command permit exists.

Consequently, no future hardware backend may expose a command-capable profile
until all applicable blockers are resolved by evidence and safety review.

## E. Blockers before ViPRO-00B is experimentally valid

1. Existence and specification of an independent shaft/port torque sensor are
   unknown.
2. No calibrated current-to-torque or drive-estimate uncertainty route exists.
3. Physical encoder acquisition/calibration is absent.
4. Device/acquisition/command/torque timing cannot yet be aligned.
5. Signal update rates, filtering, bandwidth, latency and jitter are unknown.
6. Validation independence from the control estimator is not established.
7. Mechanical reference location, gear/coupling losses and sign conventions are
   unknown.
8. Repeatability, drift and temperature context have not been measured.

Until these are addressed, `tau_physical - tau_requested` remains unavailable.
The schema and this interface contract are ready for the evidence, but they are
not themselves physical validation.
