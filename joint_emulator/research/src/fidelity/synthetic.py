"""Deterministic synthetic faults for TASK-010 validation and regression."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def deterministic_request(timestamps_s: Sequence[float]) -> np.ndarray:
    """Return a broadband-enough deterministic torque request in N.m."""

    time = np.asarray(timestamps_s, dtype=np.float64)
    if time.ndim != 1:
        raise ValueError("timestamps_s must be one-dimensional")
    return (0.70 * np.sin(2.0 * math.pi * 0.73 * time) +
            0.25 * np.sin(2.0 * math.pi * 1.91 * time + 0.31) +
            0.10 * np.cos(2.0 * math.pi * 3.17 * time))


def inject_gain(signal: Sequence[float], gain: float) -> np.ndarray:
    if not math.isfinite(gain):
        raise ValueError("gain must be finite")
    return np.asarray(signal, dtype=np.float64) * gain


def inject_delay(signal: Sequence[float], delay_samples: int,
                 *, fill_value: float = 0.0) -> np.ndarray:
    """Delay a signal by a nonnegative integer number of samples."""

    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("signal must be one-dimensional")
    if delay_samples < 0:
        raise ValueError("delay_samples must be >= 0")
    if not math.isfinite(fill_value):
        raise ValueError("fill_value must be finite")
    if delay_samples == 0:
        return values.copy()
    result = np.full(values.shape, fill_value, dtype=np.float64)
    if delay_samples < values.size:
        result[delay_samples:] = values[:-delay_samples]
    return result


def inject_noise(signal: Sequence[float], standard_deviation: float,
                 *, seed: int) -> np.ndarray:
    """Add reproducible zero-mean Gaussian noise."""

    if not math.isfinite(standard_deviation) or standard_deviation < 0.0:
        raise ValueError("standard_deviation must be finite and >= 0")
    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("signal must be one-dimensional")
    rng = np.random.default_rng(seed)
    return values + rng.normal(0.0, standard_deviation, size=values.shape)


def inject_saturation(signal: Sequence[float], limit_abs: float
                      ) -> tuple[np.ndarray, np.ndarray]:
    """Clip symmetrically and return both the output and active mask."""

    if not math.isfinite(limit_abs) or limit_abs <= 0.0:
        raise ValueError("limit_abs must be finite and > 0")
    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("signal must be one-dimensional")
    mask = np.abs(values) > limit_abs
    return np.clip(values, -limit_abs, limit_abs), mask


def inject_rate_limit(signal: Sequence[float], timestamps_s: Sequence[float],
                      maximum_rate_nm_s: float) -> np.ndarray:
    """Apply a symmetric discrete slew-rate limit in N.m/s."""

    if not math.isfinite(maximum_rate_nm_s) or maximum_rate_nm_s <= 0.0:
        raise ValueError("maximum_rate_nm_s must be finite and > 0")
    values = np.asarray(signal, dtype=np.float64)
    time = np.asarray(timestamps_s, dtype=np.float64)
    if values.ndim != 1 or time.ndim != 1 or values.size != time.size:
        raise ValueError("signal and timestamps_s must be equal-length 1D arrays")
    if values.size == 0:
        return values.copy()
    dt = np.diff(time)
    if not np.all(np.isfinite(time)) or not np.all(dt > 0.0):
        raise ValueError("timestamps_s must be finite and strictly increasing")
    result = np.empty_like(values)
    result[0] = values[0]
    for index in range(1, values.size):
        maximum_delta = maximum_rate_nm_s * dt[index - 1]
        delta = float(np.clip(values[index] - result[index - 1],
                              -maximum_delta, maximum_delta))
        result[index] = result[index - 1] + delta
    return result
