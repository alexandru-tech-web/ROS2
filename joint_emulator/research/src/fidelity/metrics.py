"""Offline, hardware-independent torque-fidelity metrics.

The module accepts explicit arrays only.  It has no ROS, simulator, logger,
fieldbus or hardware dependency.  Primary error metrics are intentionally
computed without time shifting; delay estimation and delay-aligned RMSE are
reported separately as diagnostics.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence

import numpy as np


METRIC_VERSION = "vipro-fidelity-metrics/1.1.0"


class TorqueObservationKind(StrEnum):
    """Origin of the signal used as observed torque."""

    SIMULATED = "SIMULATED"
    DERIVED = "DERIVED"
    IDENTIFIED = "IDENTIFIED"
    MEASURED = "MEASURED"


class AnalysisLabel(StrEnum):
    """Permitted interpretation of an analysis result."""

    OFFLINE_SIGNAL_COMPARISON = "OFFLINE_SIGNAL_COMPARISON"
    PHYSICAL_FIDELITY = "PHYSICAL_FIDELITY"


class TrialStatus(StrEnum):
    """Methodological status of the complete trial."""

    VALID = "VALID"
    DEGRADED = "DEGRADED"
    FAULTED = "FAULTED"
    INVALID_MEASUREMENT = "INVALID_MEASUREMENT"


@dataclass(frozen=True)
class FidelityConfig:
    """Numerical and preprocessing policy for one analysis.

    ``excitation_threshold_nm`` is a numerical guard, not an experimentally
    justified ViPRO acceptance threshold.  A study-specific threshold should
    be supplied when the metrology noise floor is known.
    """

    epsilon: float = 1.0e-12
    excitation_threshold_nm: float = 1.0e-9
    sampling_uniformity_rtol: float = 1.0e-3
    missing_gap_factor: float = 1.5
    minimum_delay_samples: int = 16
    max_delay_s: float | None = None
    estimate_delay: bool = True

    def __post_init__(self) -> None:
        if not math.isfinite(self.epsilon) or self.epsilon <= 0.0:
            raise ValueError("epsilon must be finite and > 0")
        if (not math.isfinite(self.excitation_threshold_nm) or
                self.excitation_threshold_nm < 0.0):
            raise ValueError("excitation_threshold_nm must be finite and >= 0")
        if (not math.isfinite(self.sampling_uniformity_rtol) or
                self.sampling_uniformity_rtol < 0.0):
            raise ValueError("sampling_uniformity_rtol must be finite and >= 0")
        if (not math.isfinite(self.missing_gap_factor) or
                self.missing_gap_factor <= 1.0):
            raise ValueError("missing_gap_factor must be finite and > 1")
        if self.minimum_delay_samples < 3:
            raise ValueError("minimum_delay_samples must be >= 3")
        if self.max_delay_s is not None and (
                not math.isfinite(self.max_delay_s) or self.max_delay_s <= 0.0):
            raise ValueError("max_delay_s must be finite and > 0 when supplied")


@dataclass(frozen=True)
class FidelityTrial:
    """Explicit arrays and metadata for one offline comparison."""

    trial_id: str
    timestamps_s: Sequence[float]
    tau_requested_nm: Sequence[float]
    tau_observed_nm: Sequence[float]
    requested_signal_source: str
    observed_signal_source: str
    observed_torque_kind: TorqueObservationKind
    dq_rad_s: Sequence[float] | None = None
    saturation_mask: Sequence[bool] | None = None
    # ``fault_mask`` means a hardware/system fault during execution.  These
    # samples are deliberately retained in primary metrics when measurable.
    fault_mask: Sequence[bool] | None = None
    measurement_invalid_mask: Sequence[bool] | None = None
    measurement_invalid_reasons: Sequence[str] = ()
    stale_mask: Sequence[bool] | None = None
    expected_sample_period_s: float | None = None
    observed_independent: bool = False

    def __post_init__(self) -> None:
        if not self.trial_id.strip():
            raise ValueError("trial_id cannot be empty")
        if not self.requested_signal_source.strip():
            raise ValueError("requested_signal_source cannot be empty")
        if not self.observed_signal_source.strip():
            raise ValueError("observed_signal_source cannot be empty")
        object.__setattr__(self, "observed_torque_kind",
                           TorqueObservationKind(self.observed_torque_kind))
        if self.expected_sample_period_s is not None and (
                not math.isfinite(self.expected_sample_period_s) or
                self.expected_sample_period_s <= 0.0):
            raise ValueError(
                "expected_sample_period_s must be finite and > 0 when supplied")
        reasons = tuple(str(reason).strip()
                        for reason in self.measurement_invalid_reasons)
        if any(not reason for reason in reasons):
            raise ValueError("measurement_invalid_reasons cannot contain blanks")
        object.__setattr__(self, "measurement_invalid_reasons", reasons)


@dataclass(frozen=True)
class SampleGap:
    after_index: int
    before_index: int
    duration_s: float
    estimated_missing_samples: int


@dataclass(frozen=True)
class MaskInterval:
    start_index: int
    end_index: int
    start_time_s: float | None
    end_time_s: float | None


@dataclass(frozen=True)
class MaskSummary:
    active_samples: int
    fraction: float
    intervals: tuple[MaskInterval, ...]


@dataclass(frozen=True)
class SignalQuality:
    sample_count: int
    timestamps_strictly_increasing: bool
    duplicate_timestamp_indices: tuple[int, ...]
    backward_timestamp_indices: tuple[int, ...]
    nonfinite_indices: Mapping[str, tuple[int, ...]]
    expected_sample_period_s: float | None
    expected_period_source: str
    uniform_sampling: bool | None
    missing_sample_gaps: tuple[SampleGap, ...]
    estimated_missing_samples: int | None
    requested_rms_nm: float | None
    requested_centered_rms_nm: float | None
    insufficient_excitation: bool
    near_zero_requested_denominator: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MetricProvenance:
    source_trial: str
    requested_signal_source: str
    observed_signal_source: str
    metric_version: str
    preprocessing_applied: tuple[str, ...]
    observed_torque_kind: TorqueObservationKind
    analysis_label: AnalysisLabel
    observed_independent: bool


@dataclass(frozen=True)
class MetricResult:
    name: str
    value: float | None
    unit: str
    valid: bool
    reason: str | None
    provenance: MetricProvenance


@dataclass(frozen=True)
class FidelityReport:
    trial_id: str
    analysis_label: AnalysisLabel
    is_physical_fidelity: bool
    trial_status: TrialStatus
    eligible_for_later_certification: bool
    certification_ineligibility_reasons: tuple[str, ...]
    provenance: MetricProvenance
    quality: SignalQuality
    saturation: MaskSummary
    system_fault: MaskSummary
    measurement_invalid: MaskSummary
    stale: MaskSummary
    fault_occurrence: bool
    excluded_measurement_fraction: float
    evaluation_sample_count: int
    torque_error_nm: tuple[float | None, ...]
    metrics: Mapping[str, MetricResult]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        def convert(value: Any) -> Any:
            if isinstance(value, StrEnum):
                return str(value)
            if dataclasses.is_dataclass(value):
                return {field.name: convert(getattr(value, field.name))
                        for field in dataclasses.fields(value)}
            if isinstance(value, Mapping):
                return {str(key): convert(item) for key, item in value.items()}
            if isinstance(value, tuple):
                return [convert(item) for item in value]
            return value

        return convert(self)


def _as_float_array(values: Sequence[float], name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a one-dimensional array")
    return array


def _as_bool_mask(values: Sequence[bool] | None, size: int,
                  name: str) -> np.ndarray:
    if values is None:
        return np.zeros(size, dtype=bool)
    array = np.asarray(values)
    if array.ndim != 1 or array.size != size:
        raise ValueError(f"{name} must be one-dimensional with {size} samples")
    if array.dtype.kind != "b":
        if not all(isinstance(value, (bool, np.bool_)) for value in values):
            raise ValueError(f"{name} must contain only boolean values")
    return array.astype(bool, copy=False)


def _finite_indices(array: np.ndarray) -> tuple[int, ...]:
    return tuple(int(index) for index in np.flatnonzero(~np.isfinite(array)))


def _rms(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(values))))


def _mask_intervals(mask: np.ndarray, timestamps: np.ndarray) -> MaskSummary:
    indices = np.flatnonzero(mask)
    intervals: list[MaskInterval] = []
    if indices.size:
        start = int(indices[0])
        previous = start
        for raw_index in indices[1:]:
            index = int(raw_index)
            if index != previous + 1:
                intervals.append(_make_interval(start, previous, timestamps))
                start = index
            previous = index
        intervals.append(_make_interval(start, previous, timestamps))
    fraction = float(indices.size / mask.size) if mask.size else 0.0
    return MaskSummary(int(indices.size), fraction, tuple(intervals))


def _make_interval(start: int, end: int,
                   timestamps: np.ndarray) -> MaskInterval:
    start_time = float(timestamps[start]) if np.isfinite(timestamps[start]) else None
    end_time = float(timestamps[end]) if np.isfinite(timestamps[end]) else None
    return MaskInterval(start, end, start_time, end_time)


def _quality_report(timestamps: np.ndarray, requested: np.ndarray,
                    observed: np.ndarray, dq: np.ndarray | None,
                    trial: FidelityTrial,
                    config: FidelityConfig) -> SignalQuality:
    dt = np.diff(timestamps)
    duplicate = tuple(int(index + 1) for index in np.flatnonzero(dt == 0.0))
    backward = tuple(int(index + 1) for index in np.flatnonzero(dt < 0.0))
    nonfinite = {
        "timestamps_s": _finite_indices(timestamps),
        "tau_requested_nm": _finite_indices(requested),
        "tau_observed_nm": _finite_indices(observed),
    }
    if dq is not None:
        nonfinite["dq_rad_s"] = _finite_indices(dq)

    finite_time = not nonfinite["timestamps_s"]
    strictly_increasing = bool(
        timestamps.size >= 2 and finite_time and np.all(dt > 0.0))

    expected = trial.expected_sample_period_s
    expected_source = "EXPLICIT" if expected is not None else "UNKNOWN"
    if expected is None and strictly_increasing and dt.size:
        expected = float(np.median(dt))
        expected_source = "INFERRED_MEDIAN"

    uniform: bool | None = None
    gaps: list[SampleGap] = []
    estimated_missing: int | None = None
    if expected is not None and strictly_increasing:
        tolerance = max(config.epsilon,
                        config.sampling_uniformity_rtol * expected)
        uniform = bool(np.all(np.abs(dt - expected) <= tolerance))
        estimated_missing = 0
        for index, duration in enumerate(dt):
            if duration > config.missing_gap_factor * expected:
                count = max(1, int(round(float(duration) / expected)) - 1)
                gaps.append(SampleGap(index, index + 1, float(duration), count))
                estimated_missing += count

    usable_requested = requested[np.isfinite(requested)]
    requested_rms = _rms(usable_requested) if usable_requested.size else None
    centered_rms = (_rms(usable_requested - np.mean(usable_requested))
                    if usable_requested.size else None)
    insufficient = bool(
        usable_requested.size < 2 or centered_rms is None or
        centered_rms <= config.excitation_threshold_nm)
    near_zero = bool(
        requested_rms is None or requested_rms <= config.epsilon)

    warnings: list[str] = []
    if timestamps.size < 2:
        warnings.append("fewer than two samples")
    if duplicate:
        warnings.append("duplicate timestamps present")
    if backward:
        warnings.append("timestamps move backward")
    for signal_name, indices in nonfinite.items():
        if indices:
            warnings.append(f"{signal_name} contains NaN/Inf")
    if gaps:
        warnings.append("missing samples estimated from timestamp gaps")
    if insufficient:
        warnings.append("insufficient dynamic excitation for delay identification")
    if near_zero:
        warnings.append("requested RMS is near zero; normalized metrics protected")

    return SignalQuality(
        sample_count=int(timestamps.size),
        timestamps_strictly_increasing=strictly_increasing,
        duplicate_timestamp_indices=duplicate,
        backward_timestamp_indices=backward,
        nonfinite_indices=nonfinite,
        expected_sample_period_s=expected,
        expected_period_source=expected_source,
        uniform_sampling=uniform,
        missing_sample_gaps=tuple(gaps),
        estimated_missing_samples=estimated_missing,
        requested_rms_nm=requested_rms,
        requested_centered_rms_nm=centered_rms,
        insufficient_excitation=insufficient,
        near_zero_requested_denominator=near_zero,
        warnings=tuple(warnings),
    )


def _metric(name: str, value: float | None, unit: str,
            provenance: MetricProvenance,
            reason: str | None = None) -> MetricResult:
    valid = value is not None and math.isfinite(value)
    return MetricResult(name, float(value) if valid else None, unit, valid,
                        None if valid else (reason or "metric unavailable"),
                        provenance)


def _invalid_metric(name: str, unit: str, reason: str,
                    provenance: MetricProvenance) -> MetricResult:
    return MetricResult(name, None, unit, False, reason, provenance)


def _estimate_delay(requested: np.ndarray, observed: np.ndarray,
                    dt_s: float, config: FidelityConfig
                    ) -> tuple[int, float, np.ndarray, np.ndarray] | None:
    size = requested.size
    if size < config.minimum_delay_samples:
        return None
    if config.max_delay_s is None:
        max_lag = max(1, size // 4)
    else:
        max_lag = int(math.floor(config.max_delay_s / dt_s))
    max_lag = min(max_lag, size - config.minimum_delay_samples)
    if max_lag < 0:
        return None

    candidates: list[tuple[float, int, np.ndarray, np.ndarray]] = []
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            req_segment = requested[:size - lag] if lag else requested
            obs_segment = observed[lag:]
        else:
            req_segment = requested[-lag:]
            obs_segment = observed[:size + lag]
        if req_segment.size < config.minimum_delay_samples:
            continue
        req_centered = req_segment - np.mean(req_segment)
        obs_centered = obs_segment - np.mean(obs_segment)
        denominator = float(np.linalg.norm(req_centered) *
                            np.linalg.norm(obs_centered))
        if denominator <= config.epsilon:
            continue
        correlation = float(np.dot(req_centered, obs_centered) / denominator)
        candidates.append((correlation, lag, req_segment, obs_segment))

    if not candidates:
        return None
    # Prefer the smallest absolute shift when correlations are numerically tied.
    candidates.sort(key=lambda item: (item[0], -abs(item[1])), reverse=True)
    correlation, lag, req_segment, obs_segment = candidates[0]
    return lag, correlation, req_segment, obs_segment


def _integrate_contiguous(power: np.ndarray, timestamps: np.ndarray,
                          valid_mask: np.ndarray) -> float | None:
    indices = np.flatnonzero(valid_mask)
    if indices.size < 2:
        return None
    total = 0.0
    integrated = False
    start = 0
    for cursor in range(1, indices.size + 1):
        boundary = (cursor == indices.size or
                    indices[cursor] != indices[cursor - 1] + 1)
        if not boundary:
            continue
        segment = indices[start:cursor]
        if segment.size >= 2:
            total += float(np.trapz(power[segment], timestamps[segment]))
            integrated = True
        start = cursor
    return total if integrated else None


def analyze_trial(
    trial: FidelityTrial,
    *,
    config: FidelityConfig | None = None,
    analysis_label: AnalysisLabel = AnalysisLabel.OFFLINE_SIGNAL_COMPARISON,
) -> FidelityReport:
    """Analyze one explicit trial without accessing runtime or hardware.

    A ``PHYSICAL_FIDELITY`` label is accepted only for an explicitly
    independent ``MEASURED`` observation.  The function does not establish
    calibration, bandwidth or uncertainty; those remain trial-data obligations.
    """

    config = config or FidelityConfig()
    label = AnalysisLabel(analysis_label)
    if label is AnalysisLabel.PHYSICAL_FIDELITY:
        if trial.observed_torque_kind is not TorqueObservationKind.MEASURED:
            raise ValueError(
                "PHYSICAL_FIDELITY requires observed_torque_kind=MEASURED; "
                "SIMULATED/DERIVED/IDENTIFIED observations are offline comparisons")
        if not trial.observed_independent:
            raise ValueError(
                "PHYSICAL_FIDELITY requires an explicitly independent observation")

    timestamps = _as_float_array(trial.timestamps_s, "timestamps_s")
    requested = _as_float_array(trial.tau_requested_nm, "tau_requested_nm")
    observed = _as_float_array(trial.tau_observed_nm, "tau_observed_nm")
    size = timestamps.size
    if requested.size != size or observed.size != size:
        raise ValueError("timestamps and torque arrays must have equal length")
    dq = (_as_float_array(trial.dq_rad_s, "dq_rad_s")
          if trial.dq_rad_s is not None else None)
    if dq is not None and dq.size != size:
        raise ValueError("dq_rad_s must have the same length as timestamps")
    saturation = _as_bool_mask(trial.saturation_mask, size, "saturation_mask")
    fault = _as_bool_mask(trial.fault_mask, size, "fault_mask")
    measurement_invalid = _as_bool_mask(
        trial.measurement_invalid_mask, size, "measurement_invalid_mask")
    stale = _as_bool_mask(trial.stale_mask, size, "stale_mask")

    if np.any(measurement_invalid) and not trial.measurement_invalid_reasons:
        raise ValueError(
            "measurement_invalid_mask requires at least one explicit reason")
    if trial.measurement_invalid_reasons and not np.any(measurement_invalid):
        raise ValueError(
            "measurement_invalid_reasons require an active measurement_invalid_mask")

    finite_for_torque = (
        np.isfinite(timestamps) & np.isfinite(requested) & np.isfinite(observed))
    finite_for_all_supplied = finite_for_torque.copy()
    if dq is not None:
        finite_for_all_supplied &= np.isfinite(dq)
    unclassified_nonfinite = (~finite_for_all_supplied) & ~measurement_invalid
    if np.any(unclassified_nonfinite):
        indices = tuple(int(index) for index in np.flatnonzero(unclassified_nonfinite))
        raise ValueError(
            "NaN/Inf samples may be excluded only by an explicit "
            f"measurement_invalid_mask and reason; unclassified indices={indices}")

    quality = _quality_report(timestamps, requested, observed, dq, trial, config)
    preprocessing = [
        "pointwise comparison on original timestamps",
        "no time alignment applied to primary metrics",
        "system-fault samples retained when measurement-valid",
        "saturation samples retained",
        "explicit measurement-invalid samples excluded",
        "explicit stale samples excluded",
    ]
    if trial.measurement_invalid_reasons:
        preprocessing.append(
            "measurement-invalid reasons: " +
            "; ".join(trial.measurement_invalid_reasons))

    provenance = MetricProvenance(
        source_trial=trial.trial_id,
        requested_signal_source=trial.requested_signal_source,
        observed_signal_source=trial.observed_signal_source,
        metric_version=METRIC_VERSION,
        preprocessing_applied=tuple(preprocessing),
        observed_torque_kind=trial.observed_torque_kind,
        analysis_label=label,
        observed_independent=trial.observed_independent,
    )

    # A system fault or saturation is evidence about realizability and remains
    # part of the primary error.  Only explicitly invalid/stale measurements
    # are removed from metric evaluation.
    valid = finite_for_torque & ~measurement_invalid & ~stale

    error_output: list[float | None] = [None] * size
    error = observed[valid] - requested[valid]
    for index, value in zip(np.flatnonzero(valid), error, strict=True):
        error_output[int(index)] = float(value)

    metrics: dict[str, MetricResult] = {}
    if error.size:
        rmse = _rms(error)
        mae = float(np.mean(np.abs(error)))
        peak = float(np.max(np.abs(error)))
        requested_valid = requested[valid]
        observed_valid = observed[valid]
        req_rms = _rms(requested_valid)
        obs_rms = _rms(observed_valid)
        metrics["rmse_nm"] = _metric("rmse_nm", rmse, "N.m", provenance)
        metrics["mae_nm"] = _metric("mae_nm", mae, "N.m", provenance)
        metrics["peak_absolute_error_nm"] = _metric(
            "peak_absolute_error_nm", peak, "N.m", provenance)
        metrics["requested_rms_nm"] = _metric(
            "requested_rms_nm", req_rms, "N.m", provenance)
        metrics["observed_rms_nm"] = _metric(
            "observed_rms_nm", obs_rms, "N.m", provenance)
        if req_rms > config.epsilon:
            metrics["torque_nrmse"] = _metric(
                "torque_nrmse", rmse / (req_rms + config.epsilon), "1", provenance)
            metrics["gain_ratio"] = _metric(
                "gain_ratio", obs_rms / (req_rms + config.epsilon), "1", provenance)
            metrics["normalized_amplitude_error"] = _metric(
                "normalized_amplitude_error",
                (obs_rms - req_rms) / (req_rms + config.epsilon),
                "1", provenance)
        else:
            reason = "requested RMS is too close to zero for normalization"
            for name in ("torque_nrmse", "gain_ratio",
                         "normalized_amplitude_error"):
                metrics[name] = _invalid_metric(name, "1", reason, provenance)
    else:
        reason = "no measurement-valid, non-stale sample pairs"
        for name, unit in (
            ("rmse_nm", "N.m"), ("mae_nm", "N.m"),
            ("peak_absolute_error_nm", "N.m"),
            ("requested_rms_nm", "N.m"), ("observed_rms_nm", "N.m"),
            ("torque_nrmse", "1"), ("gain_ratio", "1"),
            ("normalized_amplitude_error", "1"),
        ):
            metrics[name] = _invalid_metric(name, unit, reason, provenance)

    delay_reason: str | None = None
    delay_result: tuple[int, float, np.ndarray, np.ndarray] | None = None
    if not config.estimate_delay:
        delay_reason = "delay estimation disabled by configuration"
    elif not quality.timestamps_strictly_increasing:
        delay_reason = "delay estimation requires finite, strictly increasing timestamps"
    elif quality.uniform_sampling is not True:
        delay_reason = "delay estimation requires uniform sampling"
    elif quality.missing_sample_gaps:
        delay_reason = "delay estimation requires no detected missing samples"
    elif not np.all(valid):
        delay_reason = "delay estimation requires a complete unmasked finite record"
    elif quality.insufficient_excitation:
        delay_reason = "requested signal lacks dynamic excitation"
    elif _rms(observed - np.mean(observed)) <= config.excitation_threshold_nm:
        delay_reason = "observed signal lacks dynamic excitation"
    else:
        assert quality.expected_sample_period_s is not None
        delay_result = _estimate_delay(requested, observed,
                                       quality.expected_sample_period_s, config)
        if delay_result is None:
            delay_reason = "no mathematically valid correlation estimate"

    if delay_result is None:
        metrics["estimated_delay_s"] = _invalid_metric(
            "estimated_delay_s", "s", delay_reason or "delay unavailable", provenance)
        metrics["delay_correlation"] = _invalid_metric(
            "delay_correlation", "1", delay_reason or "delay unavailable", provenance)
        metrics["delay_aligned_rmse_nm"] = _invalid_metric(
            "delay_aligned_rmse_nm", "N.m",
            delay_reason or "delay unavailable", provenance)
    else:
        lag, correlation, req_segment, obs_segment = delay_result
        delay_s = lag * quality.expected_sample_period_s
        aligned_rmse = _rms(obs_segment - req_segment)
        metrics["estimated_delay_s"] = _metric(
            "estimated_delay_s", delay_s, "s", provenance)
        metrics["delay_correlation"] = _metric(
            "delay_correlation", correlation, "1", provenance)
        metrics["delay_aligned_rmse_nm"] = _metric(
            "delay_aligned_rmse_nm", aligned_rmse, "N.m", provenance)

    work_reason: str | None = None
    requested_work: float | None = None
    observed_work: float | None = None
    if dq is None:
        work_reason = "dq_rad_s was not supplied"
    elif not quality.timestamps_strictly_increasing:
        work_reason = "work integration requires strictly increasing timestamps"
    else:
        work_valid = valid & np.isfinite(dq)
        requested_work = _integrate_contiguous(
            requested * dq, timestamps, work_valid)
        observed_work = _integrate_contiguous(
            observed * dq, timestamps, work_valid)
        if requested_work is None or observed_work is None:
            work_reason = (
                "fewer than two contiguous measurement-valid, non-stale power samples")

    if work_reason is not None:
        for name, unit in (
            ("requested_work_j", "J"), ("observed_work_j", "J"),
            ("work_error_j", "J"), ("normalized_work_error", "1"),
        ):
            metrics[name] = _invalid_metric(name, unit, work_reason, provenance)
    else:
        assert requested_work is not None and observed_work is not None
        work_error = observed_work - requested_work
        metrics["requested_work_j"] = _metric(
            "requested_work_j", requested_work, "J", provenance)
        metrics["observed_work_j"] = _metric(
            "observed_work_j", observed_work, "J", provenance)
        metrics["work_error_j"] = _metric(
            "work_error_j", work_error, "J", provenance)
        if abs(requested_work) > config.epsilon:
            metrics["normalized_work_error"] = _metric(
                "normalized_work_error",
                abs(work_error) / (abs(requested_work) + config.epsilon),
                "1", provenance)
        else:
            metrics["normalized_work_error"] = _invalid_metric(
                "normalized_work_error", "1",
                "requested work is too close to zero for normalization",
                provenance)

    status_reasons: list[str] = []
    fault_occurrence = bool(np.any(fault))
    invalid_measurement_occurrence = bool(
        np.any(measurement_invalid) or
        quality.duplicate_timestamp_indices or
        quality.backward_timestamp_indices or
        not quality.timestamps_strictly_increasing)
    degraded_occurrence = bool(
        np.any(saturation) or np.any(stale) or
        quality.missing_sample_gaps or
        quality.insufficient_excitation or
        quality.near_zero_requested_denominator)

    if fault_occurrence:
        trial_status = TrialStatus.FAULTED
        status_reasons.append("hardware/system fault occurred during the trial")
    elif invalid_measurement_occurrence:
        trial_status = TrialStatus.INVALID_MEASUREMENT
        status_reasons.append("measurement record contains explicitly invalid data")
    elif degraded_occurrence:
        trial_status = TrialStatus.DEGRADED
    else:
        trial_status = TrialStatus.VALID

    if np.any(measurement_invalid):
        status_reasons.append("measurement-invalid samples were excluded")
    if not quality.timestamps_strictly_increasing:
        status_reasons.append("timestamps are not finite and strictly increasing")
    if np.any(saturation):
        status_reasons.append("saturation occurred")
    if np.any(stale):
        status_reasons.append("stale samples occurred")
    if quality.missing_sample_gaps:
        status_reasons.append("timestamp gaps indicate missing samples")
    if quality.insufficient_excitation:
        status_reasons.append("dynamic excitation is insufficient")
    if quality.near_zero_requested_denominator:
        status_reasons.append("requested torque denominator is near zero")
    if not error.size:
        status_reasons.append("no samples remain for primary metrics")

    if label is not AnalysisLabel.PHYSICAL_FIDELITY:
        status_reasons.append(
            "analysis is not an independent MEASURED physical-fidelity trial")
    eligible = bool(
        trial_status is TrialStatus.VALID and error.size and
        label is AnalysisLabel.PHYSICAL_FIDELITY)

    return FidelityReport(
        trial_id=trial.trial_id,
        analysis_label=label,
        is_physical_fidelity=label is AnalysisLabel.PHYSICAL_FIDELITY,
        trial_status=trial_status,
        eligible_for_later_certification=eligible,
        certification_ineligibility_reasons=(
            () if eligible else tuple(dict.fromkeys(status_reasons))),
        provenance=provenance,
        quality=quality,
        saturation=_mask_intervals(saturation, timestamps),
        system_fault=_mask_intervals(fault, timestamps),
        measurement_invalid=_mask_intervals(measurement_invalid, timestamps),
        stale=_mask_intervals(stale, timestamps),
        fault_occurrence=fault_occurrence,
        excluded_measurement_fraction=(
            float(np.count_nonzero(measurement_invalid | stale) / size)
            if size else 0.0),
        evaluation_sample_count=int(np.count_nonzero(valid)),
        torque_error_nm=tuple(error_output),
        metrics=metrics,
    )
