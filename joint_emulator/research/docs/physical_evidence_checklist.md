# TASK-008 — ViPRO physical evidence checklist

Date prepared: 2026-09-23  
Purpose: non-commanding, evidence-driven inspection of the physical bench

## Hard boundary

During TASK-008:

- do not command, enable, reset or jog a motor;
- do not transmit Modbus/RTU, CAN, EtherCAT or other fieldbus traffic;
- do not run `rtu_probe.py --transmit-read-only`;
- do not disconnect, rewire, remove covers or energize equipment without the
  responsible laboratory person and the approved procedure;
- do not infer protocol, polarity, register meaning or safety behavior from a
  generic label;
- do not replace an unreadable/absent datum with a plausible ABB value.

The outcome is a set of traceable observations, photographs and documents—not
a hardware backend.

## Status vocabulary

Every checklist item and manifest entry uses exactly one status:

| Status | Meaning | Minimum evidence |
|---|---|---|
| `CONFIRMED` | The requested fact was directly observed or established by an applicable authoritative record. | Original photo/document/export/measurement, exact locator, UTC capture metadata and hash |
| `UNKNOWN` | Evidence is absent, unreadable, inaccessible, ambiguous or conflicting. | Record why it remains unknown; never insert a guessed value |
| `NOT_PRESENT` | Inspection establishes that the component/capability is absent from the inspected scope. | Scope-complete photographs/drawing/authorized statement; absence must not be inferred from one missing label |
| `NOT_APPLICABLE` | The item genuinely does not apply to the verified architecture. | Written justification plus the evidence establishing the architecture |

`NOT_PRESENT` and `NOT_APPLICABLE` are evidence-bearing conclusions, not
synonyms for `UNKNOWN`.

Repository claims remain prior leads until physically reconciled. For example,
the project describes six ABB servomotors and a possible Modbus prototype, but
neither claim confirms a physical model, protocol or address.

## Evidence-record requirements

For every captured item record:

```text
item_id
status
observed value, exactly as written
manufacturer/model/part number/serial/firmware, where applicable
physical location
logical A/B/pair mapping, if established
evidence filename(s)
document page/section or image region
capture UTC and person
capture method
SHA-256 of original file
ambiguity/conflict notes
```

Preserve original images, exports and documents unchanged. Generate hashes
before annotation or compression. Any cropped/enhanced image is a derived file
and must retain a link to the original.

Recommended filename form:

```text
<inspection_id>_<category>_<logical-or-location-id>_<view>_<sequence>.<ext>
```

Example structure only:

```text
VIPRO-INSPECT-YYYYMMDD_motor_A0_nameplate_001.jpg
VIPRO-INSPECT-YYYYMMDD_drive_cabinet_slot03_nameplate_001.jpg
VIPRO-INSPECT-YYYYMMDD_comm_module_connectors_001.jpg
```

Do not assign `A0`, `B0`, etc. to a physical component until cabling/drawing or
another valid mapping source supports it. Use location IDs first if uncertain.

## Before entering the laboratory

- [ ] Obtain authorization for photography and document/export collection.
- [ ] Identify the responsible person for the bench and electrical safety.
- [ ] Prepare a new inspection ID and an empty copy of
      `physical_evidence_manifest.yaml`.
- [ ] Prepare asset labels that do not imply an unverified A/B mapping.
- [ ] Bring a camera with sufficient macro focus and lighting.
- [ ] Bring a notebook for cable endpoints and cabinet locations.
- [ ] Do not bring/connect the RPi adapter as part of the initial inspection.
- [ ] Agree which equipment state permits safe visual inspection.

## 1. Component identity

Capture one context photograph and one readable nameplate photograph per
component. Include connector/module option labels without exposing personnel
or unrelated confidential material.

### Motors — six expected logical slots, physical mapping unverified

| Logical slot | Location label | Manufacturer | Exact model/type | Part/order no. | Serial no. | Rating plate | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| A0 |  |  |  |  |  |  | `UNKNOWN` |  |
| B0 |  |  |  |  |  |  | `UNKNOWN` |  |
| A1 |  |  |  |  |  |  | `UNKNOWN` |  |
| B1 |  |  |  |  |  |  | `UNKNOWN` |  |
| A2 |  |  |  |  |  |  | `UNKNOWN` |  |
| B2 |  |  |  |  |  |  | `UNKNOWN` |  |

Record rated voltage/current/power/speed/torque only as nameplate fields with
units; do not reinterpret them as approved experimental limits.

### Drives — six requested inventory slots, count/mapping to verify

| Logical slot | Cabinet/location | Manufacturer | Exact model/type | Option modules | Firmware | Serial no. | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| drive-A0 |  |  |  |  |  |  | `UNKNOWN` |  |
| drive-B0 |  |  |  |  |  |  | `UNKNOWN` |  |
| drive-A1 |  |  |  |  |  |  | `UNKNOWN` |  |
| drive-B1 |  |  |  |  |  |  | `UNKNOWN` |  |
| drive-A2 |  |  |  |  |  |  | `UNKNOWN` |  |
| drive-B2 |  |  |  |  |  |  | `UNKNOWN` |  |

- [ ] Photograph each drive front/nameplate.
- [ ] Photograph fitted communication/feedback option modules.
- [ ] Record display-reported model/firmware only through an approved,
      non-state-changing procedure.
- [ ] Record physical location before assigning logical A/B identity.

### Controller and communication equipment

| Component | Location | Manufacturer | Exact model/type | Firmware/OS | Serial | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Controller/PLC/industrial PC |  |  |  |  |  | `UNKNOWN` |  |
| Suspected RTU/fieldbus module |  |  |  |  |  | `UNKNOWN` |  |
| Network switch/gateway |  |  |  |  |  | `UNKNOWN` |  |
| USB/serial converter |  |  |  |  |  | `UNKNOWN` |  |

The label “RTU” is not proof of Modbus RTU. Capture the entire module label,
part number, ports and relationship to the controller.

### Encoders, reducers, couplings and torque sensors

| Item | Pair/side or location | Exact model/type | Ratio/range | Mounting/reference point | Status | Evidence |
|---|---|---|---|---|---|---|
| Encoder A0/B0 |  |  |  |  | `UNKNOWN` |  |
| Encoder A1/B1 |  |  |  |  | `UNKNOWN` |  |
| Encoder A2/B2 |  |  |  |  | `UNKNOWN` |  |
| Reducer pair 0 |  |  |  |  | `UNKNOWN` |  |
| Reducer pair 1 |  |  |  |  | `UNKNOWN` |  |
| Reducer pair 2 |  |  |  |  | `UNKNOWN` |  |
| Coupling pair 0 |  |  |  |  | `UNKNOWN` |  |
| Coupling pair 1 |  |  |  |  | `UNKNOWN` |  |
| Coupling pair 2 |  |  |  |  | `UNKNOWN` |  |
| Torque transducer pair 0 |  |  |  |  | `UNKNOWN` |  |
| Torque transducer pair 1 |  |  |  |  | `UNKNOWN` |  |
| Torque transducer pair 2 |  |  |  |  | `UNKNOWN` |  |

For a possible torque sensor, also capture the signal conditioner/amplifier,
connector, cable and calibration label. A coupling flange is not itself a
torque transducer.

## 2. Communication topology

Use `bench_topology_template.md` to record endpoint-to-endpoint connections.

- [ ] Photograph every controller/module/drive communication connector.
- [ ] Record exact printed labels: for example `A`, `B`, `D+`, `D-`, `GND`,
      `RS-485`, `CAN`, `EtherCAT`, `PROFINET`, `Modbus`—without translating one
      label into another protocol.
- [ ] Record connector type and pin numbering from the exact manual.
- [ ] Trace controller-to-drive cabling visually where authorized.
- [ ] Record daisy-chain, star, ring or point-to-point topology only when
      traceable.
- [ ] Identify termination and bias components from drawing/manual/inspection.
- [ ] Identify galvanic-isolation boundaries.
- [ ] Identify shields, reference conductors and protective earth connections
      only from approved drawings/inspection.
- [ ] Determine whether a controller/PLC/PC is already the bus master.
- [ ] Record any service port that is electrically/logically separate.
- [ ] Record USB/serial converters and stable device serial numbers.
- [ ] Record whether communication remains available with power stage disabled.

Do not probe continuity or resistance on energized equipment. Do not attach a
second active master to an occupied bus.

## 3. Safety evidence

This is documentary/visual inspection, not a functional safety test.

| Safety item | What to capture | Status | Evidence |
|---|---|---|---|
| Emergency-stop chain | schematic, devices, reset path, affected contactors/drives | `UNKNOWN` |  |
| Drive-enable chain | source, interlocks, state feedback | `UNKNOWN` |  |
| Safe Torque Off (STO) | terminals, channels, logic, manual reference | `UNKNOWN` |  |
| Approved operating limits | controlled document and responsible approval | `UNKNOWN` |  |
| Communication with drives disabled | documented/approved behavior | `UNKNOWN` |  |
| Mechanical guarding | guards, exclusion zone, access restrictions | `UNKNOWN` |  |
| Energy isolation | approved lockout/isolation procedure | `UNKNOWN` |  |

Do not mark safety capability `CONFIRMED` from a label alone. Match the exact
wiring and device configuration. Nameplate ratings are not automatically the
safe experimental envelope.

## 4. Documentation and exports

Collect original exports read-only through the responsible engineer. Record
tool/version and export procedure.

| Evidence | Exact equipment/version applicability | Status | File/hash |
|---|---|---|---|
| Drive parameter backups |  | `UNKNOWN` |  |
| ABB engineering project/export |  | `UNKNOWN` |  |
| PLC/controller project/export |  | `UNKNOWN` |  |
| Electrical schematics |  | `UNKNOWN` |  |
| Communication option manual |  | `UNKNOWN` |  |
| Motor/drive manuals |  | `UNKNOWN` |  |
| Register/object/fieldbus map |  | `UNKNOWN` |  |
| Encoder/reducer/coupling datasheets |  | `UNKNOWN` |  |
| Torque/current/sensor calibration certificates |  | `UNKNOWN` |  |
| Safety/risk-assessment records |  | `UNKNOWN` |  |

For each manual record document number, revision, publication date and exact
model/firmware applicability. Generic ABB documentation is not sufficient.

## 5. Available measurements

For each candidate measurement, identify where the value originates—not only
where it is displayed.

| Quantity | A/B/pair availability | Physical source | Interface/object | Native unit/type | Timestamp/update evidence | Calibration | Status |
|---|---|---|---|---|---|---|---|
| Position |  |  |  |  |  |  | `UNKNOWN` |
| Velocity |  |  |  |  |  |  | `UNKNOWN` |
| Motor current |  |  |  |  |  |  | `UNKNOWN` |
| Drive torque estimate |  |  |  |  |  |  | `UNKNOWN` |
| Independent shaft torque |  |  |  |  |  |  | `UNKNOWN` |
| Motor temperature |  |  |  |  |  |  | `UNKNOWN` |
| Drive temperature |  |  |  |  |  |  | `UNKNOWN` |
| Fault/status |  |  |  |  |  |  | `UNKNOWN` |
| Device timestamp/ticks |  |  |  |  |  |  | `UNKNOWN` |

For torque/current-related values record:

- command, measured, or internally estimated;
- motor-side, gearbox output, coupling or other reference point;
- signedness, word order, scale and unit;
- filtering/update behavior and latency;
- whether the same estimate participates in control;
- calibration and uncertainty.

## 6. Minimum photographic set

Capture at least:

1. full bench from multiple sides;
2. all six motor nameplates and their physical locations;
3. all drives and their cabinet/slot positions;
4. controller/PLC/industrial PC nameplates;
5. suspected RTU/fieldbus module label and ports;
6. communication connectors and cable routes;
7. A/B mechanical coupling for each pair;
8. encoder/reducer labels and mounting where accessible;
9. torque transducers and conditioners, or scope-complete evidence supporting
   `NOT_PRESENT`;
10. E-stop, enable/STO terminals and guarding, subject to authorization;
11. cabinet overview matching electrical drawings;
12. any existing service/USB/serial adapters.

Use an overview image to establish location and a close-up for legibility. Do
not crop the original evidence set.

## 7. Reconciliation after the visit

1. Copy originals into a new immutable raw-evidence directory.
2. Compute SHA-256 for every file.
3. Complete `physical_evidence_manifest.yaml` item by item.
4. Use `CONFIRMED` only when value, source, locator and evidence agree.
5. If two sources conflict, retain both and keep the item `UNKNOWN` until the
   conflict is resolved.
6. Update TASK-001 inventory only in a separate reviewed reconciliation task.
7. Populate `vipro_manifest_current.yaml` only for an actual session; do not
   retroactively turn the planned SIM manifest into a physical session.
8. Review TASK-006 capabilities against the observed hardware.
9. Evaluate `RTU_READ_GO` only after protocol/master/topology/manual evidence is
   complete.

## Inspection completion criteria

TASK-008 is complete when every manifest item has been reviewed and assigned
one of the four statuses, all `CONFIRMED`/`NOT_PRESENT` conclusions have linked
evidence, and remaining `UNKNOWN` values have a precise next action.

Completion of TASK-008 does not permit motor command. It may permit planning a
first read-only acquisition only after the applicable safety and communication
gates are independently approved.
