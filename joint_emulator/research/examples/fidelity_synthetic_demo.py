#!/usr/bin/env python3
"""Run deterministic TASK-010 comparisons without ROS or hardware."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


RESEARCH_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(RESEARCH_SRC))

from fidelity import (  # noqa: E402
    FidelityConfig,
    FidelityTrial,
    TorqueObservationKind,
    analyze_trial,
)
from fidelity.synthetic import (  # noqa: E402
    deterministic_request,
    inject_delay,
    inject_gain,
    inject_noise,
    inject_rate_limit,
    inject_saturation,
)


def main() -> None:
    sample_rate_hz = 250.0
    timestamps_s = np.arange(0.0, 5.0, 1.0 / sample_rate_hz)
    requested_nm = deterministic_request(timestamps_s)
    saturated_nm, saturation_mask = inject_saturation(requested_nm, 0.30)
    cases = {
        "clean": (requested_nm, None),
        "gain_0p75": (inject_gain(requested_nm, 0.75), None),
        "delay_60ms": (inject_delay(requested_nm, 15), None),
        "noise_0p04Nm": (inject_noise(requested_nm, 0.04, seed=7), None),
        "saturation_0p30Nm": (saturated_nm, saturation_mask),
        "rate_limit_0p60Nm_s": (
            inject_rate_limit(requested_nm, timestamps_s, 0.60), None),
    }
    config = FidelityConfig(max_delay_s=0.20)
    output: dict[str, object] = {}
    print("case                       NRMSE       gain      delay [s]   status")
    print("-------------------------  ----------  --------  ----------  ----------")
    for name, (observed_nm, mask) in cases.items():
        trial = FidelityTrial(
            trial_id=f"synthetic-{name}",
            timestamps_s=timestamps_s,
            tau_requested_nm=requested_nm,
            tau_observed_nm=observed_nm,
            requested_signal_source="synthetic.request",
            observed_signal_source=f"synthetic.{name}",
            observed_torque_kind=TorqueObservationKind.SIMULATED,
            saturation_mask=mask,
        )
        report = analyze_trial(trial, config=config)
        nrmse = report.metrics["torque_nrmse"].value
        gain = report.metrics["gain_ratio"].value
        delay = report.metrics["estimated_delay_s"].value
        print(f"{name:25s}  {nrmse:10.6f}  {gain:8.5f}  "
              f"{delay:10.6f}  {report.trial_status}")
        output[name] = {
            "trial_id": report.trial_id,
            "analysis_label": str(report.analysis_label),
            "observed_torque_kind": str(report.provenance.observed_torque_kind),
            "trial_status": str(report.trial_status),
            "eligible_for_later_certification": (
                report.eligible_for_later_certification),
            "quality_warnings": list(report.quality.warnings),
            "saturation_fraction": report.saturation.fraction,
            "excluded_measurement_fraction": (
                report.excluded_measurement_fraction),
            "metrics": {
                metric_name: {
                    "value": result.value,
                    "unit": result.unit,
                    "valid": result.valid,
                    "reason": result.reason,
                }
                for metric_name, result in report.metrics.items()
            },
        }

    print("\nAll observations are SIMULATED and therefore labelled only as "
          "OFFLINE_SIGNAL_COMPARISON.")
    print("Compact JSON result (clean case):")
    print(json.dumps(output["clean"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
