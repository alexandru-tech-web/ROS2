# ViPRO control versus validation signals — TASK-006

## Governing rule

```text
CONTROL REFERENCE / ESTIMATOR  !=  INDEPENDENT VALIDATION MEASUREMENT
```

A useful numeric signal is not automatically an independent measurement. The
classification depends on physical origin, calibration, timing and whether the
same model/estimator participates in generating the control action.

The current repository contains only SIM signals. The classifications below
are interface requirements for future physical acquisition.

## Signal-role matrix

| Signal | What it is | Control use | Independent validation use | Current physical status |
|---|---|---:|---:|---:|
| `requested_virtual_load_torque_B` | Desired/model-derived B load request | Yes, as controller reference | No; it is one side of the comparison | SIM only |
| `tau_b` in `/joint/state` | Current gated SIM B command | SIM control/debug only | No | SIM only |
| `JointState.effort` | Copy of current SIM `tau_b` | No physical control evidence | No | SIM alias only |
| A/B encoder position | Physical kinematics if source is verified | Conditional | Yes for kinematic response; no for torque alone | `UNKNOWN` |
| A/B device timestamp | Native timing evidence | Conditional | Yes for alignment, not mechanics | `UNKNOWN` |
| Drive velocity feedback | Reported/estimated kinematics | Conditional after bandwidth/delay validation | Conditional for kinematic fidelity | `UNKNOWN` |
| Motor current | Electrical feedback with exact definition required | Conditional | Conditional torque proxy only with calibration/model/uncertainty; not independently sufficient | `UNKNOWN` |
| Drive torque estimate | Internal drive estimate | Conditional | No if shared with control; conditional only after independent calibration | `UNKNOWN` |
| Independent shaft torque | Mechanical sensor at documented port/location | Preferably not used by the primary controller during validation | Yes after calibration, timing and independence checks | existence `UNKNOWN` |
| Motor/drive temperature | Thermal state/context | Conditional for derating/abort | Context/covariate, not torque reference | `UNKNOWN` |
| Status/fault/saturation | Device operational state | Yes for inhibit/abort after decoding | Trial-validity metadata, not mechanics | `UNKNOWN` |
| Command receipt/application status | Command-path evidence | Yes for supervision | Timing validation only | `UNKNOWN` |
| Torque/current/velocity command | Command sent to hardware | Yes in a verified mode | No; command is not realization | capability `UNKNOWN` |

## Three different torque quantities

These quantities must never share one ambiguous field name:

### 1. Requested load torque

```text
tau_B_requested
```

Produced by the virtual mechanical model and safety/limit logic. It describes
what software asks B to realize. It may be used as the reference in a fidelity
error but cannot be the realized term.

Required metadata:

- model/mechanism identity;
- value before and after software limiting;
- issue monotonic timestamp, deadline and sequence;
- pair/side mapping;
- command mode and SI/device conversion version;
- backend/device receipt when available.

### 2. Drive-derived torque

```text
tau_B_drive_estimate
```

May be derived from current, flux/control state, motor parameters and drive
algorithms. It can support diagnostics and an indirect estimate, but its
independence is limited—especially if the same value or model is used by the
drive/controller.

It requires:

- exact physical reference point;
- algorithm/source documentation;
- scale, sign, gear conversion and filter/update behavior;
- calibration against an independent reference;
- uncertainty and temperature/operating-point dependence;
- explicit provenance `DERIVED` or `IDENTIFIED` as applicable.

### 3. Independent mechanical torque

```text
tau_port_sensor
```

Preferred validation quantity, measured by a separately calibrated transducer
at a documented location in the A/B load path.

It requires:

- sensor and conditioner identity;
- mounting/reference location and sign convention;
- traceable zero/span calibration and validity dates;
- bandwidth, range, cross-sensitivity and uncertainty;
- clock and alignment to request/kinematics;
- evidence that it does not reuse the control estimator.

Only after this chain is established can the direct quantity be evaluated:

```text
e_tau(t) = tau_port_sensor(t) - tau_B_requested(t)
```

The comparison must account for physically justified delay/alignment rather
than selecting a shift that merely minimizes error.

## Control eligibility rules

A physical signal is eligible for control only if all applicable conditions
are satisfied:

1. source hardware and pair/side mapping are verified;
2. unit, scaling, sign, zero and reference point are calibrated;
3. acquisition timestamp, age, rate, bandwidth and delay are characterized;
4. stale/missing/error behavior is explicit and fail-closed;
5. status/fault semantics and operating limits are documented;
6. the required signal is available in the local control timing budget;
7. use is covered by the approved safety/commissioning procedure.

`UNKNOWN` never passes an eligibility check. Missing values are not replaced
by zero, last-known data without age, or SIM output.

## Independent-validation eligibility rules

A signal is eligible as an independent validation reference only if:

1. it measures the physical quantity of interest at a documented location;
2. it has a valid calibration and quantified uncertainty;
3. its time base can be aligned with commands and kinematics;
4. its bandwidth/range are adequate for the tested operating envelope;
5. it does not derive solely from the same model/estimator being evaluated;
6. saturation, clipping, filtering and missing-data behavior are observable;
7. raw data and processing lineage are preserved.

An independent sensor may be used in safety monitoring, but using it inside
the primary control law can reduce its independence for final validation. If
that is unavoidable, validation needs another reference or a documented
analysis of dependence.

## Kinematic validation is not torque validation

Agreement such as:

```text
q_A approximately equals q_B
```

can verify coupling/kinematics after independent encoder calibration. It does
not prove:

```text
tau_physical approximately equals tau_requested
```

Equal angles can coexist with friction, inertial, compliance, drive and timing
errors in the transmitted torque.

Likewise, differentiating encoder position provides a derived velocity or
acceleration. It does not create an independent torque measurement. Any model-
based torque estimate using acceleration must preserve estimator method,
bandwidth and uncertainty.

## Minimum validation hierarchy

Use the strongest available route and label it honestly:

| Level | Available evidence | Permitted conclusion |
|---|---|---|
| V0 — software only | requested torque and SIM state | Software/pipeline verification only |
| V1 — physical kinematics | calibrated A/B encoders and timestamps | Physical motion/coupling characterization |
| V2 — drive/electrical estimate | V1 plus current or drive torque estimate with calibration/model | Estimated physical torque with quantified model dependence |
| V3 — independent metrology | V1 plus calibrated independent shaft torque and aligned timing | Direct experimental torque-fidelity evaluation within uncertainty |

Current repository status is V0. TASK-006 defines the path to V1–V3 but does
not claim any transition has occurred.

## Anti-circularity checks for every trial

Before computing a fidelity result, record:

- which signal generated/control-limited `tau_B_requested`;
- which signal is used as realized torque;
- physical source and calibration of realized torque;
- whether the realized signal shares models, parameters or filters with the
  controller;
- clock alignment method and uncertainty;
- exclusions due to fault, saturation, stale data or sensor clipping;
- raw parent artifacts and processing version.

Reject the physical-fidelity claim if the realized quantity is only:

- `tau_b` command;
- `JointState.effort` copied from that command;
- a replayed/synthetic value;
- an uncalibrated register with guessed units;
- an estimator whose dependence and uncertainty are not documented.

## Acceptance table for the future backend

| Candidate | CONTROL | INDEPENDENT VALIDATION |
|---|---|---|
| Calibrated encoder position with valid age | Conditional yes | Kinematics only |
| Derived encoder velocity | Conditional yes | Conditional kinematics; report derivation |
| Documented drive velocity | Conditional yes | Conditional kinematics |
| Calibrated current | Conditional yes/monitoring | Conditional indirect estimate, not independent alone |
| Drive torque estimate | Conditional yes | Normally no; conditional only after external calibration |
| Independent shaft torque | Optional/conditional | Preferred yes |
| Status/fault words | Required gating metadata | Trial validity only |
| Requested torque command | Yes, reference | Never realized torque |
| Command receipt | Supervision | Timing only |
| SIM `tau_b` / `JointState.effort` | SIM only | Never physical validation |

This classification must be revisited using hardware evidence before any
signal is marked usable. Until then, all physical-channel statuses remain
`UNKNOWN`.
