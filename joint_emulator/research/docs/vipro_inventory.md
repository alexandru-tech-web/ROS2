# ViPRO inventory — TASK-001

Audit date: 2026-09-23  
Repository revision inspected: `main@0d7d864ba85805090d97edcf639586ff27f457c8`

## Scope and evidence policy

This is a static, evidence-based audit of `/home/ubuntu/ros2_ws/src`, with
focused inspection of `joint_emulator`, its launch/configuration, existing
documentation, and generated session configurations. It does not claim that
the physical bench has been inspected.

Before creating these outputs, the whole workspace and all Git refs were
searched for both `vipro_inventory.*` and `vipo_inventory.*`, plus
`ros_graph.*` and `signals.*`. No pre-existing TASK-001 artifact was found.
The only match was the mention of the expected names in TASK-002 documentation.

The provenance vocabulary in this artifact is restricted to:

- `CODE_CONFIG`: directly encoded in source/configuration;
- `MANUAL_REFERENCE`: stated by the canonical context or project
  documentation, but not demonstrated by runtime code;
- `DERIVED`: a transparent consequence of cited evidence;
- `UNKNOWN`: no sufficient evidence.

`confidence` describes confidence that the cited source says or implements the
recorded value. It is not confidence that an undocumented physical value is
correct.

## Executive finding

The repository contains a functional **simulation architecture**, not a
connected ViPRO/ABB hardware architecture. The runtime node rejects every
backend other than `sim` and instantiates `SimBackend`
(`joint_emulator/nodes/emulator_node.py:47-67`). The only physical-backend file
is an intentionally nonfunctional Modbus skeleton whose register addresses and
scales are `None` (`joint_emulator/modbus_backend.py:21-48`). It is not imported
by the runtime node.

Therefore:

```text
CONFIRMED IN CODE
operator/suite -> ROS command -> simulated A/B dynamics -> simulated state
               -> synthetic encoder channels -> logs/HMI/Gazebo mirror

DECLARED, NOT PHYSICALLY VERIFIED
A_i test actuator ║ rigid coupling/common shaft ║ B_i load actuator

NOT PRESENT
ROS/ABB gateway -> physical drive command -> physical encoder/current/torque
```

The current workspace cannot determine the physical load experienced by A.
It can only report requested/calculated SIM torques.

## Physical topology declared by the research context

| Item | Value | Unit | Provenance | Evidence | Confidence / ambiguity |
|---|---:|---|---|---|---|
| Local pairs | 3: A0/B0, A1/B1, A2/B2 | 1 | MANUAL_REFERENCE | `/home/ubuntu/Downloads/RESEARCH_CONTEXT.md:126-136` | Medium; no drawing or wiring inventory in repo |
| Actuators per pair | 2 | 1 | MANUAL_REFERENCE | `RESEARCH_CONTEXT.md:55-62` | Medium |
| Total actuator count | 6 | 1 | DERIVED | `RESEARCH_CONTEXT.md:55-62,126-136`; `joint_emulator/README_JOINT.md:1-7` | Medium; 3×2 and a project-document claim |
| A role | actuator under test / active actuator | — | MANUAL_REFERENCE | `RESEARCH_CONTEXT.md:57-62` | Medium; role is not mapped to cabinet terminals |
| B role | physical load actuator | — | MANUAL_REFERENCE | `RESEARCH_CONTEXT.md:57-62,99-124` | Medium; drive realization absent |
| Within-pair coupling | rigid common shaft/coupling | — | MANUAL_REFERENCE | `RESEARCH_CONTEXT.md:57-75` | Medium; stiffness/backlash/geometry UNKNOWN |
| Between-pair physical coupling | UNKNOWN | — | UNKNOWN | `RESEARCH_CONTEXT.md:126-138` | Context explicitly makes independence conditional on real inventory |
| Pair-to-body-joint mapping | UNKNOWN | — | UNKNOWN | no evidence | No verified wrist/elbow/shoulder assignment |

The three-pair mechanical arrangement is the canonical working interpretation,
not a result of this audit. The code independently implements three **SIM**
pairs, but simulation agreement does not verify the physical topology.

## Hardware inventory

| Item | Value | Unit | Provenance | Evidence | Confidence / ambiguity |
|---|---|---|---|---|---|
| Motor manufacturer claim | ABB | — | MANUAL_REFERENCE | `joint_emulator/README_JOINT.md:1-7` | Low; no nameplate/manual/part number |
| Motor models and serials | UNKNOWN | — | UNKNOWN | no evidence | Blocking |
| Drive manufacturer claim | ABB | — | MANUAL_REFERENCE | `joint_emulator/modbus_backend.py:2-6` | Low; same file says it is a skeleton |
| Drive model/firmware/parameter set | UNKNOWN | — | UNKNOWN | `joint_emulator/drive_iface.py:2-6` | Explicitly deferred |
| Real drive protocol | UNKNOWN | — | UNKNOWN | `joint_emulator/README_JOINT.md:79-88` | EtherCAT/analog/CAN/Modbus/vendor remain unconfirmed alternatives |
| Actual A control mode | UNKNOWN | — | UNKNOWN | no hardware configuration | Code SIM command is torque, not physical evidence |
| Actual B control mode | UNKNOWN | — | UNKNOWN | no hardware configuration | Torque mode is a requirement/proposal, not confirmed state |
| Encoder type/resolution/interface | UNKNOWN | — | UNKNOWN | no hardware documentation | `4096 count/rev` in code is synthetic quantization |
| Encoder sign/zero calibration | UNKNOWN | — | UNKNOWN | `joint_emulator/encoder_core.py:127-150` | Mechanism exists in code; physical coefficients absent |
| Gear ratio | UNKNOWN | 1 | UNKNOWN | no evidence | Blocking torque/position interpretation |
| External torque transducer | UNKNOWN | — | UNKNOWN | no component, topic or calibration found | Critical blocker |
| Motor-current feedback | UNKNOWN | A | UNKNOWN | no acquisition path found | Critical blocker |
| Drive torque estimate | UNKNOWN | N·m | UNKNOWN | no acquisition path found | Critical blocker |
| Temperature/state feedback | UNKNOWN | °C | UNKNOWN | no acquisition path found | Relevant to drift/repeatability |
| Physical limits | UNKNOWN | mixed SI | UNKNOWN | no manual/parameter dump | Torque, torque-rate, current, speed, position, power and thermal limits all unknown |
| Physical E-stop chain | UNKNOWN | — | UNKNOWN | no electrical/safety documentation | Software SIM ESTOP is not evidence of it |

### Why the Modbus file is not hardware evidence

`modbus_backend.py:21-35` contains example values (`rtu`, `/dev/ttyUSB0`,
19200 baud, addresses 1…6), but the same block labels its register map as a
placeholder. Torque, position, velocity, enable registers and all scales are
`None`; construction exits when they are missing (`modbus_backend.py:42-48`).
Those values are recorded in the YAML only as **placeholder code**, never as
ViPRO hardware configuration.

## Implemented SIM topology and control

| Item | Value | Unit | Provenance | Evidence | Confidence / ambiguity |
|---|---:|---|---|---|---|
| Runtime backend | `SimBackend` only | — | CODE_CONFIG | `nodes/emulator_node.py:47-67` | High; non-SIM exits |
| SIM pairs | 3 | 1 | CODE_CONFIG | `nodes/emulator_node.py:48-67` | High |
| Logical IDs | A_i=`2i`, B_i=`2i+1` | — | DERIVED | `nodes/emulator_node.py:103-105,172-176,280-307` | High; not physical addresses |
| Pair mechanical state | one common `th, om` | rad, rad/s | CODE_CONFIG | `drive_iface.py:53-60`; `joint_core.py:171-192` | High |
| SIM plant | `J q̈ = τ_A + τ_B − b q̇ − τ_c sign(q̇)` | SI | CODE_CONFIG | `joint_core.py:171-192` | High; generic, not identified |
| SIM J default | 0.004 | kg·m² | CODE_CONFIG | `joint_core.py:175-180` | High for SIM; physical value UNKNOWN |
| SIM viscous friction default | 0.01 | N·m·s/rad | CODE_CONFIG | `joint_core.py:175-180` | High for SIM only |
| SIM Coulomb friction default | 0 | N·m | CODE_CONFIG | `joint_core.py:175-180` | High for SIM only |
| A input | clipped torque command | N·m | CODE_CONFIG | `nodes/emulator_node.py:159-176` | High; not measured torque |
| B default law | `−K(q−q0)−B q̇`, saturated | N·m | CODE_CONFIG | `joint_core.py:25-46` | High |
| Default K | 20 | N·m/rad | CODE_CONFIG | `nodes/emulator_node.py:48-53` | SIM only |
| Default B | 0.8 | N·m·s/rad | CODE_CONFIG | `nodes/emulator_node.py:48-53` | SIM only |
| Default torque clamp | ±2 | N·m | CODE_CONFIG | `nodes/emulator_node.py:48-53,172-176` | SIM only; not a safe hardware limit |
| Watchdog timeout | 0.1 | s | CODE_CONFIG | `nodes/emulator_node.py:90-100` | SIM measurement-time gate |
| Full-launch ROS timer | 200 | Hz | CODE_CONFIG | `launch/full_sim.launch.py:42-63,112-114` | Nominal, not measured |
| Numerical inner step | 0.0005 | s | CODE_CONFIG | `joint_core.py:195-204` | Numerical substep, not a measured 2 kHz real-time loop |
| Full-launch state rate | 100 | Hz | CODE_CONFIG | `launch/full_sim.launch.py:112-115` | Overrides node default 50 Hz |
| Encoder kinematics publication | 50 | Hz | CODE_CONFIG | `nodes/encoder_monitor_node.py:45-64,109-114` | CSV ingestion follows `/joint/state`, not this timer |
| SIM encoder quantization | 4096 | count/rev | CODE_CONFIG | `nodes/encoder_monitor_node.py:58-69` | Synthetic only |
| Velocity filter τ | 0.1 | s | CODE_CONFIG | `nodes/encoder_monitor_node.py:59-73` | Estimator, not sensor bandwidth |
| Acceleration filter τ | 0.15 | s | CODE_CONFIG | `nodes/encoder_monitor_node.py:59-73` | Derived acceleration |

The HMI commands each A separately, but sends the same K/B update to all three
B laws (`nodes/operator_panel_node.py:123-134`). Link degradation is also
applied to all three simulated links (`nodes/emulator_node.py:209-216`).

## A/B command and observation chain

### Confirmed implemented chain

```text
operator_panel or suite_player
    │  /joint/cmd_a  std_msgs/String {pair, tau}
    ▼
joint_emulator
    ├─ clip τ_A to SIM tau_max
    ├─ read common PairSim state as A and B
    ├─ compute τ_B_requested from impedance/contact law
    ├─ SafetyGate + SIM ESTOP
    └─ PairSim: Jq̈ = τ_A + τ_B - simulated friction
             │
             └─ /joint/state (SIM state + command values)
                    ├─ encoder_monitor -> synthetic encoder/kinematics + CSV
                    ├─ operator_panel -> plots
                    ├─ gz_mirror -> Gazebo position mirror
                    └─ state_to_jointstate -> /joint_states
```

Sources: `nodes/operator_panel_node.py:65-73,123-140`,
`nodes/emulator_node.py:107-153,159-176,276-345`,
`joint_core.py:171-192`, and `nodes/encoder_monitor_node.py:109-164`.

### Required physical chain and current evidence

```text
q_A / q_B hardware acquisition        UNKNOWN
          ↓
physical state acquisition node       ABSENT
          ↓
virtual-load computation              exists only inside SIM node
          ↓
requested τ_B                         exists only as SIM command
          ↓
ROS-to-ABB/drive interface            ABSENT
          ↓
drive B / motor B                     model, mode, mapping UNKNOWN
          ║
rigid coupling                        declared; properties UNKNOWN
          ║
motor A physical load                 not observed
```

No ROS service or action associated with ViPRO was found. All implemented
control/state interfaces use topics; most use JSON inside `std_msgs/String`.

## Existing data paths and clocks

| Item | Value | Provenance | Evidence | Ambiguity |
|---|---|---|---|---|
| Default data directory | `/home/ubuntu/Analiza_Teza/ViPRO/DATE` | CODE_CONFIG | `launch/full_sim.launch.py:119-125` | Runtime configurable |
| State CSV | `session_<id>_states.csv` | CODE_CONFIG | `session_export.py:44-68`; `nodes/emulator_node.py:114-134` | Current source is SIM |
| Event CSV | `session_<id>_events.csv` | CODE_CONFIG | `nodes/emulator_node.py:114-134` | Event time uses SIM state plus log-time UTC |
| Six-channel encoder CSV | `motor_encoders_<id>.csv` | CODE_CONFIG | `nodes/encoder_monitor_node.py:50-57,103-108` | Synthetic/requantized channels |
| Common-axis encoder CSV | `encoders_<id>.csv` | CODE_CONFIG | same | Derived from `/joint/state` |
| Config CSVs | `session_<id>_{sim,encoder}_config.csv` | CODE_CONFIG | `nodes/emulator_node.py:114-129`; `nodes/encoder_monitor_node.py:90-102` | Do not include software commit/config hash |
| XLSX | timestamped snapshot of CSVs | CODE_CONFIG | `session_export.py:174-263` | Export, not primary data |
| Write policy | exclusive create (`x`) | CODE_CONFIG | `session_export.py:50-63`; `encoder_core.py:188-230` | Prevents implicit overwrite |
| `time_s` / `t_s` | accumulated `PairSim.t` | CODE_CONFIG | `joint_core.py:175-192`; `session_export.py:70-100` | Simulation time, not OS monotonic |
| `time_utc` | UTC wall clock at callback/write | CODE_CONFIG | `session_export.py:33-35,70-110`; `encoder_monitor_node.py:116-134` | Not device acquisition time |
| `/joint_states.header.stamp` | ROS node clock at translation | CODE_CONFIG | `nodes/state_to_jointstate_node.py:22-31` | Original state timestamp not preserved |
| Logged monotonic OS timestamp | UNKNOWN | UNKNOWN | no field found | Blocking timing audit |
| Physical device timestamp | UNKNOWN | UNKNOWN | no device interface | Blocking timing audit |

Existing generated `*_sim_config.csv` files under the default data directory
identify their backend as `sim`, `reference_sim`, or `suite_sim`; none is
evidence of an ABB session.

## What is currently observed

| Desired quantity | Current status | Physical meaning | Independent validation? |
|---|---|---|---|
| `tau_A_command` | available | clipped SIM command | No |
| `tau_B_requested` | available | computed/gated SIM command | No |
| `q_A`, `q_B` | available as two synthetic channels | both originate from the same latent SIM angle | No physical observation |
| `q_A-q_B` | available | diagnostic of synthetic channels | No; exactly zero in ideal SIM |
| `motor_current_B` | UNKNOWN / absent | no signal path | No |
| `drive_torque_B` | UNKNOWN / absent | no signal path | No |
| `tau_port_sensor` | UNKNOWN / absent | no signal path/calibration | No |
| physical load experienced by A | UNKNOWN | cannot be inferred from command alone | No |
| temperature | UNKNOWN / absent | no signal path | No |

`sensor_msgs/JointState.effort` is filled with `tau_b` by the visualization
bridge (`nodes/state_to_jointstate_node.py:22-31`). It is therefore another
alias of the SIM command, not a measured effort.

## A. Confirmed A/B signal and control chain

1. Physical role declaration: A is the tested actuator, B the load actuator,
   with a declared rigid common shaft (`RESEARCH_CONTEXT.md:55-124`).
2. Implemented command producer: HMI and SIM suite publish A commands on
   `/joint/cmd_a` (`operator_panel_node.py:65-70,123-140`;
   `suite_player_node.py:35-36,107-119`).
3. Implemented controller/plant: `joint_emulator` accepts only `SimBackend`,
   computes B torque from simulated state, and steps `PairSim`
   (`emulator_node.py:47-100,159-176,276-330`).
4. Implemented observation path: `/joint/state` feeds the encoder estimator,
   HMI, Gazebo mirror and optional JointState bridge.
5. Physical acquisition, ROS-to-drive command and drive feedback are not
   implemented. Consequently, the code-confirmed chain stops at simulation.

## B. Unresolved `UNKNOWN` items

- exact motor, drive and controller models, firmware and serial numbers;
- actual mapping A0/B0…A2/B2 to drives, terminals and anatomical roles;
- drive protocol, command mode, units/scales, update mechanism and diagnostics;
- encoder technology, resolution, sign, zero, mounting, timestamp and rate;
- gear ratios, coupling dimensions/stiffness/backlash and bearing/friction data;
- physical torque/current/drive-estimate signals and their calibration;
- presence and specification of an independent torque transducer;
- physical sampling rates, command rates, latency and jitter;
- all certified continuous/peak limits and the physical E-stop chain;
- temperature and regenerative-energy observations;
- whether the three physical pairs are mechanically independent.

## C. Code/configuration/documentation inconsistencies

1. `README_JOINT.md:1` names six ABB servomotors, but no model/nameplate/manual
   exists and runtime code is SIM-only.
2. `modbus_backend.py:2-6` calls itself an ABB “series 300” Modbus skeleton,
   while `README_JOINT.md:83-88` explicitly says Modbus is unconfirmed. The
   latter interpretation is used: actual protocol/model remain `UNKNOWN`.
3. Documentation phrases B as reading an encoder, but current B control reads
   the same latent `PairSim` state used for both sides; the six encoder channels
   are generated later for observation (`emulator_node.py:280-323` versus
   `encoder_monitor_node.py:116-158`). Control does not consume those synthetic
   quantized encoder outputs.
4. `emulator_node` defaults state publication to 50 Hz
   (`emulator_node.py:48-53`), while `full_sim.launch.py:112-115` overrides it
   to 100 Hz. Both are valid configuration layers and must be recorded per run.
5. Encoder monitor `rate_hz=50` controls publication, while CSV rows are added
   in the state subscription callback. “Encoder rate” is therefore ambiguous
   unless acquisition, processing, publication and logging rates are separated.
6. The 0.5 ms inner step is executed as ten numerical substeps inside a 200 Hz
   ROS timer callback; documentation must not call this a measured 2 kHz
   real-time hardware loop.
7. Gazebo uses a position controller to mirror the emulator and has one joint
   per pair, not independently simulated A/B motors (`gz_mirror_node.py:1-28`;
   `gz/joint_bench_world.sdf:145-150`). It cannot validate physical torque.
8. Current CSVs have SIM time and log-time UTC but no OS monotonic acquisition
   timestamp, sequence number, device time, software commit or configuration
   hash required by the research constitution.

## D. Blockers for ViPRO-00B metrology

1. No independent physical port-torque measurement is known.
2. No motor current or drive-internal torque estimate is acquired.
3. No torque constant, gear ratio, efficiency/loss model or calibration makes
   current-to-port-torque conversion possible.
4. No physical encoder acquisition/calibration is implemented.
5. No acquisition and actuation timestamps permit temporal alignment of
   requested and realized load.
6. No hardware limits or risk-approved operating envelope exists in the repo.
7. The same SIM model currently generates commands and all available
   “observations”; it cannot serve as independent fidelity validation.

Until at least one calibrated physical torque route is available, the error
`tau_physical - tau_requested` cannot be evaluated rigorously.

## E. Exact files/evidence to inspect manually next

### Repository files

1. `joint_emulator/modbus_backend.py:21-95` — replace placeholders only after
   protocol/manual evidence exists; do not arm it as-is.
2. `joint_emulator/drive_iface.py:2-77` — decide whether the physical contract
   needs device timestamps, status/faults, current and measured/estimated torque.
3. `joint_emulator/nodes/emulator_node.py:47-153,276-345` — map the SIM-only
   boundary before adding any future hardware node.
4. `joint_emulator/nodes/encoder_monitor_node.py:42-164` — identify where real
   encoder samples, device timestamps and calibration would enter.
5. `joint_emulator/session_export.py:18-123` — input to later TASK-003 only;
   current fields expose timing and provenance gaps.
6. `joint_emulator/launch/full_sim.launch.py:42-135` — explicitly SIM launch;
   it must not be confused with a future hardware launch.

### Missing laboratory files/records to acquire

1. clear nameplate photographs for all motors, drives and controller modules;
2. official motor/drive/controller manuals matching exact type codes;
3. electrical wiring and cabinet I/O drawings;
4. ABB controller/PLC project export and drive parameter backup;
5. fieldbus/network configuration files (for example ESI/EDS/GSDML only if
   actually applicable after identification);
6. encoder/reducer/coupling datasheets and physical A/B mapping sheet;
7. torque/current scaling and calibration certificates;
8. external sensor model, mounting drawing, signal conditioner and calibration,
   if one exists;
9. safety circuit/risk-assessment documentation and approved operating limits;
10. one non-energized bench walk-down record linking physical labels to
    software/drive identifiers.

No runtime, control, logging, or TASK-002 schema file was modified by TASK-001.
