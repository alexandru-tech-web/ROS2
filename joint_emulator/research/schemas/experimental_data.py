#!/usr/bin/env python3
"""Contract tipat pentru metadatele experimentale ViPRO.

Acest modul nu citeste hardware si nu modifica logging-ul existent. El defineste
contractul TASK-002. Valorile fizice necunoscute sunt reprezentate exclusiv prin
``ProvenancedValue(value=None, provenance=UNKNOWN)``.
"""

from __future__ import annotations

import dataclasses
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, Generic, Mapping, TypeVar


T = TypeVar("T")
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]*\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class ProvenanceCategory(StrEnum):
    MEASURED = "MEASURED"
    MANUAL = "MANUAL"
    CODE_CONFIG = "CODE_CONFIG"
    IDENTIFIED = "IDENTIFIED"
    DERIVED = "DERIVED"
    SIMULATED = "SIMULATED"
    UNKNOWN = "UNKNOWN"


class SessionKind(StrEnum):
    SIMULATION = "SIMULATION"
    HARDWARE = "HARDWARE"
    HYBRID = "HYBRID"
    REPLAY = "REPLAY"
    UNKNOWN = "UNKNOWN"


class SessionStatus(StrEnum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    ABORTED = "ABORTED"
    INVALID = "INVALID"


class TrialOutcome(StrEnum):
    PLANNED = "PLANNED"
    VALID = "VALID"
    INVALID = "INVALID"
    ABORTED = "ABORTED"
    UNKNOWN = "UNKNOWN"


class ClockDomain(StrEnum):
    MONOTONIC = "MONOTONIC"
    UTC = "UTC"
    ROS = "ROS"
    DEVICE = "DEVICE"
    SIMULATION = "SIMULATION"
    UNKNOWN = "UNKNOWN"


class HardwareRole(StrEnum):
    TEST_ACTUATOR_A = "TEST_ACTUATOR_A"
    LOAD_ACTUATOR_B = "LOAD_ACTUATOR_B"
    DRIVE = "DRIVE"
    ENCODER = "ENCODER"
    COUPLING = "COUPLING"
    TORQUE_SENSOR = "TORQUE_SENSOR"
    CONTROLLER = "CONTROLLER"
    COMPUTER = "COMPUTER"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class SignalValueType(StrEnum):
    FLOAT64 = "FLOAT64"
    INT64 = "INT64"
    BOOLEAN = "BOOLEAN"
    STRING = "STRING"
    JSON = "JSON"
    UNKNOWN = "UNKNOWN"


class DataTier(StrEnum):
    RAW = "RAW"
    PROCESSED = "PROCESSED"
    DERIVED = "DERIVED"


class CalibrationStatus(StrEnum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


def _require_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{label} invalid: {value!r}")


def _finite_tree(value: Any, label: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} nu poate contine NaN/Inf")
    if isinstance(value, Mapping):
        for child in value.values():
            _finite_tree(child, label)
    elif isinstance(value, (tuple, list)):
        for child in value:
            _finite_tree(child, label)


def _parse_utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} trebuie sa fie ISO 8601 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{label} trebuie sa includa fusul UTC")
    return parsed


@dataclass(frozen=True)
class EvidenceReference:
    """Locul exact din care provine o valoare sau o concluzie."""

    source: str
    locator: str | None = None
    sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("evidence.source nu poate fi gol")
        if self.sha256 is not None and not _SHA256_RE.fullmatch(self.sha256):
            raise ValueError("evidence.sha256 trebuie sa aiba 64 caractere hex")


@dataclass(frozen=True)
class UncertaintyInterval:
    """Interval explicit; nu presupune automat o distributie probabilistica."""

    lower: float
    upper: float
    unit: str
    coverage_probability: float | None = None
    method: str | None = None

    def __post_init__(self) -> None:
        _finite_tree((self.lower, self.upper), "uncertainty")
        if self.lower > self.upper:
            raise ValueError("uncertainty.lower trebuie sa fie <= upper")
        if not self.unit.strip():
            raise ValueError("uncertainty.unit nu poate fi gol")
        if (self.coverage_probability is not None and
                not 0.0 < self.coverage_probability <= 1.0):
            raise ValueError("coverage_probability trebuie sa fie in (0, 1]")


@dataclass(frozen=True)
class ProvenancedValue(Generic[T]):
    """Valoare impreuna cu provenienta si dovada sa.

    UNKNOWN este reprezentat prin ``value=None``. O valoare cunoscuta necesita
    cel putin o referinta de evidenta. IDENTIFIED si DERIVED necesita si metoda.
    """

    value: T | None
    provenance: ProvenanceCategory
    evidence: tuple[EvidenceReference, ...] = ()
    unit: str | None = None
    method: str | None = None
    uncertainty: UncertaintyInterval | None = None

    def __post_init__(self) -> None:
        if self.value is None:
            if self.provenance is not ProvenanceCategory.UNKNOWN:
                raise ValueError("value=None necesita provenance=UNKNOWN")
            if self.uncertainty is not None:
                raise ValueError("o valoare UNKNOWN nu poate avea incertitudine numerica")
            return
        if self.provenance is ProvenanceCategory.UNKNOWN:
            raise ValueError("provenance=UNKNOWN necesita value=None")
        if not self.evidence:
            raise ValueError("o valoare cunoscuta necesita evidence")
        if (self.provenance in (ProvenanceCategory.IDENTIFIED,
                               ProvenanceCategory.DERIVED) and
                not (self.method and self.method.strip())):
            raise ValueError("IDENTIFIED/DERIVED necesita method")
        if self.unit is not None and not self.unit.strip():
            raise ValueError("unit nu poate fi sir gol; foloseste '1' sau None")
        _finite_tree(self.value, "provenanced value")


def unknown(*, unit: str | None = None,
            evidence: tuple[EvidenceReference, ...] = ()) -> ProvenancedValue[Any]:
    """Constructor explicit pentru o valoare care ramane necunoscuta."""

    return ProvenancedValue(value=None, provenance=ProvenanceCategory.UNKNOWN,
                            evidence=evidence, unit=unit)


@dataclass(frozen=True)
class TimePoint:
    """Timp de esantion/trial bazat obligatoriu pe un ceas monotonic."""

    clock_id: str
    monotonic_ns: int
    sequence_index: int | None = None
    utc_iso8601: str | None = None
    device_ticks: int | None = None

    def __post_init__(self) -> None:
        _require_id(self.clock_id, "clock_id")
        if (not isinstance(self.monotonic_ns, int) or
                isinstance(self.monotonic_ns, bool) or self.monotonic_ns < 0):
            raise ValueError("monotonic_ns trebuie sa fie intreg nenegativ")
        if (self.sequence_index is not None and
                (not isinstance(self.sequence_index, int) or
                 isinstance(self.sequence_index, bool) or
                 self.sequence_index < 0)):
            raise ValueError("sequence_index trebuie sa fie nenegativ")
        if (self.device_ticks is not None and
                (not isinstance(self.device_ticks, int) or
                 isinstance(self.device_ticks, bool) or self.device_ticks < 0)):
            raise ValueError("device_ticks trebuie sa fie nenegativ")
        if self.utc_iso8601 is not None:
            _parse_utc(self.utc_iso8601, "utc_iso8601")


@dataclass(frozen=True)
class ClockMetadata:
    clock_id: str
    domain: ClockDomain
    source: ProvenancedValue[str]
    resolution_ns: ProvenancedValue[int]
    synchronized_to_clock_id: ProvenancedValue[str] = field(default_factory=unknown)

    def __post_init__(self) -> None:
        _require_id(self.clock_id, "clock_id")
        if self.resolution_ns.value is not None and self.resolution_ns.value <= 0:
            raise ValueError("resolution_ns trebuie sa fie pozitiv")


@dataclass(frozen=True)
class HardwareComponent:
    hardware_id: str
    role: ProvenancedValue[HardwareRole]
    manufacturer: ProvenancedValue[str] = field(default_factory=unknown)
    model: ProvenancedValue[str] = field(default_factory=unknown)
    serial_number: ProvenancedValue[str] = field(default_factory=unknown)
    pair_index: ProvenancedValue[int] = field(default_factory=lambda: unknown(unit="1"))
    parent_hardware_ids: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_id(self.hardware_id, "hardware_id")
        for parent in self.parent_hardware_ids:
            _require_id(parent, "parent_hardware_id")
        if self.pair_index.value is not None and self.pair_index.value < 0:
            raise ValueError("pair_index trebuie sa fie nenegativ")


@dataclass(frozen=True)
class HardwareManifest:
    manifest_id: str
    components: tuple[HardwareComponent, ...]

    def __post_init__(self) -> None:
        _require_id(self.manifest_id, "manifest_id")
        _unique((item.hardware_id for item in self.components), "hardware_id")


@dataclass(frozen=True)
class CalibrationRecord:
    calibration_id: str
    status: CalibrationStatus
    target_hardware_ids: tuple[str, ...]
    target_signal_ids: tuple[str, ...]
    method: ProvenancedValue[str]
    coefficients: Mapping[str, ProvenancedValue[int | float]] = field(default_factory=dict)
    valid_from_utc: str | None = None
    valid_until_utc: str | None = None
    artifact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_id(self.calibration_id, "calibration_id")
        if not self.target_hardware_ids and not self.target_signal_ids:
            raise ValueError("calibrarea necesita cel putin o tinta")
        for item in (*self.target_hardware_ids, *self.target_signal_ids,
                     *self.artifact_ids):
            _require_id(item, "calibration reference")
        start = (_parse_utc(self.valid_from_utc, "valid_from_utc")
                 if self.valid_from_utc else None)
        end = (_parse_utc(self.valid_until_utc, "valid_until_utc")
               if self.valid_until_utc else None)
        if start is not None and end is not None and end < start:
            raise ValueError("valid_until_utc este anterior lui valid_from_utc")


@dataclass(frozen=True)
class SignalMetadata:
    signal_id: str
    name: str
    physical_quantity: ProvenancedValue[str]
    unit: ProvenancedValue[str]
    value_type: SignalValueType
    shape: tuple[int, ...]
    source_hardware_ids: ProvenancedValue[tuple[str, ...]]
    source_interface: ProvenancedValue[str]
    nominal_rate_hz: ProvenancedValue[int | float]
    clock_id: ProvenancedValue[str]
    data_tier: DataTier
    calibration_ids: tuple[str, ...] = ()
    parent_signal_ids: tuple[str, ...] = ()
    description: str | None = None

    def __post_init__(self) -> None:
        _require_id(self.signal_id, "signal_id")
        if not self.name.strip():
            raise ValueError("signal.name nu poate fi gol")
        if any(isinstance(size, bool) or size <= 0 for size in self.shape):
            raise ValueError("signal.shape contine o dimensiune invalida")
        if (self.nominal_rate_hz.value is not None and
                self.nominal_rate_hz.value <= 0):
            raise ValueError("nominal_rate_hz trebuie sa fie pozitiv")
        for item in (*self.calibration_ids, *self.parent_signal_ids):
            _require_id(item, "signal reference")


@dataclass(frozen=True)
class DataArtifact:
    artifact_id: str
    tier: DataTier
    uri: str
    media_type: str
    immutable: bool
    sha256: ProvenancedValue[str] = field(default_factory=unknown)
    parent_artifact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_id(self.artifact_id, "artifact_id")
        if not self.uri.strip() or not self.media_type.strip():
            raise ValueError("artifact uri/media_type nu pot fi goale")
        if self.tier is DataTier.RAW and not self.immutable:
            raise ValueError("un artefact RAW trebuie declarat immutable")
        if self.sha256.value is not None and not _SHA256_RE.fullmatch(self.sha256.value):
            raise ValueError("artifact sha256 trebuie sa aiba 64 caractere hex")
        for parent in self.parent_artifact_ids:
            _require_id(parent, "parent_artifact_id")


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    study_id: str
    kind: ProvenancedValue[SessionKind]
    status: SessionStatus
    start: TimePoint
    hardware_manifest_id: str
    clock_ids: tuple[str, ...]
    software_revision: ProvenancedValue[str]
    configuration_hash: ProvenancedValue[str]
    end: TimePoint | None = None
    artifact_ids: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        for value, label in ((self.session_id, "session_id"),
                             (self.study_id, "study_id"),
                             (self.hardware_manifest_id, "hardware_manifest_id")):
            _require_id(value, label)
        for item in (*self.clock_ids, *self.artifact_ids):
            _require_id(item, "session reference")
        if self.end is not None:
            if self.end.clock_id != self.start.clock_id:
                raise ValueError("session.start/end trebuie sa foloseasca acelasi ceas")
            if self.end.monotonic_ns < self.start.monotonic_ns:
                raise ValueError("session.end este anterior lui session.start")


@dataclass(frozen=True)
class TrialRecord:
    trial_id: str
    session_id: str
    order_index: int
    mechanism_id: ProvenancedValue[str]
    excitation_id: ProvenancedValue[str]
    start: TimePoint
    outcome: TrialOutcome
    end: TimePoint | None = None
    hardware_state: Mapping[str, ProvenancedValue[Any]] = field(default_factory=dict)
    artifact_ids: tuple[str, ...] = ()
    invalid_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_id(self.trial_id, "trial_id")
        _require_id(self.session_id, "trial.session_id")
        if (not isinstance(self.order_index, int) or
                isinstance(self.order_index, bool) or self.order_index < 0):
            raise ValueError("order_index trebuie sa fie nenegativ")
        if self.end is not None:
            if self.end.clock_id != self.start.clock_id:
                raise ValueError("trial.start/end trebuie sa foloseasca acelasi ceas")
            if self.end.monotonic_ns < self.start.monotonic_ns:
                raise ValueError("trial.end este anterior lui trial.start")
        if self.outcome is TrialOutcome.INVALID and not self.invalid_reasons:
            raise ValueError("un trial INVALID necesita invalid_reasons")
        for item in self.artifact_ids:
            _require_id(item, "trial artifact_id")


def _unique(values: Any, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"{label} duplicat: {value}")
        seen.add(value)


@dataclass(frozen=True)
class ExperimentManifest:
    schema_version: str
    session: SessionRecord
    hardware: HardwareManifest
    clocks: tuple[ClockMetadata, ...]
    signals: tuple[SignalMetadata, ...]
    calibrations: tuple[CalibrationRecord, ...]
    trials: tuple[TrialRecord, ...]
    artifacts: tuple[DataArtifact, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "1.0.0":
            raise ValueError("schema_version suportat este 1.0.0")
        self.validate_references()

    def validate_references(self) -> None:
        if self.session.hardware_manifest_id != self.hardware.manifest_id:
            raise ValueError("session.hardware_manifest_id nu corespunde manifestului")

        hardware_ids = {item.hardware_id for item in self.hardware.components}
        _unique((item.clock_id for item in self.clocks), "clock_id")
        _unique((item.signal_id for item in self.signals), "signal_id")
        _unique((item.calibration_id for item in self.calibrations),
                "calibration_id")
        _unique((item.artifact_id for item in self.artifacts), "artifact_id")
        _unique((item.trial_id for item in self.trials), "trial_id")
        clock_ids = {item.clock_id for item in self.clocks}
        signal_ids = {item.signal_id for item in self.signals}
        calibration_ids = {item.calibration_id for item in self.calibrations}
        artifact_ids = {item.artifact_id for item in self.artifacts}

        self._require_subset(self.session.clock_ids, clock_ids, "session.clock_ids")
        self._require_subset(self.session.artifact_ids, artifact_ids,
                             "session.artifact_ids")
        if self.session.start.clock_id not in clock_ids:
            raise ValueError("session.start refera un clock_id inexistent")
        if self.session.end is not None and self.session.end.clock_id not in clock_ids:
            raise ValueError("session.end refera un clock_id inexistent")

        for clock in self.clocks:
            synchronized_to = clock.synchronized_to_clock_id.value
            if synchronized_to is not None and synchronized_to not in clock_ids:
                raise ValueError(
                    f"{clock.clock_id}.synchronized_to_clock_id inexistent")

        for component in self.hardware.components:
            self._require_subset(component.parent_hardware_ids, hardware_ids,
                                 f"{component.hardware_id}.parent_hardware_ids")
        for signal in self.signals:
            if signal.clock_id.value is not None and signal.clock_id.value not in clock_ids:
                raise ValueError(f"{signal.signal_id}.clock_id inexistent")
            if signal.source_hardware_ids.value is not None:
                self._require_subset(signal.source_hardware_ids.value, hardware_ids,
                                     f"{signal.signal_id}.source_hardware_ids")
            self._require_subset(signal.calibration_ids, calibration_ids,
                                 f"{signal.signal_id}.calibration_ids")
            self._require_subset(signal.parent_signal_ids, signal_ids,
                                 f"{signal.signal_id}.parent_signal_ids")
        for calibration in self.calibrations:
            self._require_subset(calibration.target_hardware_ids, hardware_ids,
                                 f"{calibration.calibration_id}.target_hardware_ids")
            self._require_subset(calibration.target_signal_ids, signal_ids,
                                 f"{calibration.calibration_id}.target_signal_ids")
            self._require_subset(calibration.artifact_ids, artifact_ids,
                                 f"{calibration.calibration_id}.artifact_ids")
        for artifact in self.artifacts:
            self._require_subset(artifact.parent_artifact_ids, artifact_ids,
                                 f"{artifact.artifact_id}.parent_artifact_ids")
        for trial in self.trials:
            if trial.session_id != self.session.session_id:
                raise ValueError(f"{trial.trial_id} refera alta sesiune")
            if trial.start.clock_id not in clock_ids:
                raise ValueError(f"{trial.trial_id}.start clock_id inexistent")
            if trial.end is not None and trial.end.clock_id not in clock_ids:
                raise ValueError(f"{trial.trial_id}.end clock_id inexistent")
            self._require_subset(trial.artifact_ids, artifact_ids,
                                 f"{trial.trial_id}.artifact_ids")

    @staticmethod
    def _require_subset(values: Any, allowed: set[str], label: str) -> None:
        missing = sorted(set(values) - allowed)
        if missing:
            raise ValueError(f"{label} contine referinte inexistente: {missing}")

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False,
                          sort_keys=True)

    def write_json(self, path: str | Path) -> None:
        """Scrie doar manifestul; nu modifica sau suprascrie date brute."""

        target = Path(path)
        if target.exists():
            raise FileExistsError(f"manifestul exista deja: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json() + "\n", encoding="utf-8")


def _plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {item.name: _plain(getattr(value, item.name))
                for item in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(child) for child in value]
    return value
