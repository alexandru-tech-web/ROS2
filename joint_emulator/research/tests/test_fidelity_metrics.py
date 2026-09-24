#!/usr/bin/env python3
"""Deterministic validation for the TASK-010 fidelity pipeline."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np


RESEARCH_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(RESEARCH_SRC))

from fidelity import (  # noqa: E402
    AnalysisLabel,
    FidelityConfig,
    FidelityTrial,
    TorqueObservationKind,
    TrialStatus,
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


def metric(report, name):
    return report.metrics[name].value


class FidelityMetricTest(unittest.TestCase):
    def setUp(self):
        self.sample_rate_hz = 200.0
        self.time = np.arange(0.0, 4.0, 1.0 / self.sample_rate_hz)
        self.requested = deterministic_request(self.time)
        self.config = FidelityConfig(max_delay_s=0.25)

    def trial(self, observed=None, **kwargs):
        return FidelityTrial(
            trial_id=kwargs.pop("trial_id", "synthetic-trial"),
            timestamps_s=kwargs.pop("timestamps_s", self.time),
            tau_requested_nm=kwargs.pop("tau_requested_nm", self.requested),
            tau_observed_nm=(self.requested if observed is None else observed),
            requested_signal_source="synthetic.request",
            observed_signal_source="synthetic.observed",
            observed_torque_kind=kwargs.pop(
                "observed_torque_kind", TorqueObservationKind.SIMULATED),
            **kwargs,
        )

    def test_exact_signal_has_zero_primary_error(self):
        report = analyze_trial(self.trial(), config=self.config)
        self.assertAlmostEqual(metric(report, "rmse_nm"), 0.0)
        self.assertAlmostEqual(metric(report, "mae_nm"), 0.0)
        self.assertAlmostEqual(metric(report, "torque_nrmse"), 0.0)
        self.assertAlmostEqual(metric(report, "normalized_amplitude_error"), 0.0)
        self.assertAlmostEqual(metric(report, "estimated_delay_s"), 0.0)
        self.assertEqual(report.trial_status, TrialStatus.VALID)
        self.assertFalse(report.eligible_for_later_certification)
        self.assertTrue(report.certification_ineligibility_reasons)

    def test_gain_error_is_recovered(self):
        report = analyze_trial(
            self.trial(inject_gain(self.requested, 0.8)), config=self.config)
        self.assertAlmostEqual(metric(report, "gain_ratio"), 0.8, places=9)
        self.assertAlmostEqual(
            metric(report, "normalized_amplitude_error"), -0.2, places=9)
        self.assertGreater(metric(report, "rmse_nm"), 0.0)

    def test_positive_delay_is_recovered(self):
        delay_samples = 12
        observed = inject_delay(self.requested, delay_samples)
        report = analyze_trial(self.trial(observed), config=self.config)
        self.assertAlmostEqual(
            metric(report, "estimated_delay_s"),
            delay_samples / self.sample_rate_hz,
            places=12,
        )
        self.assertLess(metric(report, "delay_aligned_rmse_nm"),
                        metric(report, "rmse_nm"))

    def test_noise_increases_error_deterministically(self):
        clean = analyze_trial(self.trial(), config=self.config)
        noisy_values = inject_noise(self.requested, 0.05, seed=20260923)
        noisy = analyze_trial(self.trial(noisy_values), config=self.config)
        repeated = inject_noise(self.requested, 0.05, seed=20260923)
        np.testing.assert_array_equal(noisy_values, repeated)
        self.assertGreater(metric(noisy, "rmse_nm"), metric(clean, "rmse_nm"))

    def test_saturation_is_reported_and_retained_by_default(self):
        observed, mask = inject_saturation(self.requested, 0.35)
        report = analyze_trial(
            self.trial(observed, saturation_mask=mask), config=self.config)
        self.assertGreater(report.saturation.active_samples, 0)
        self.assertGreater(len(report.saturation.intervals), 0)
        self.assertEqual(report.evaluation_sample_count, self.time.size)
        self.assertGreater(metric(report, "rmse_nm"), 0.0)
        self.assertEqual(report.trial_status, TrialStatus.DEGRADED)
        self.assertFalse(report.eligible_for_later_certification)
        self.assertIn("saturation samples retained",
                      report.provenance.preprocessing_applied)

    def test_rate_limit_increases_error(self):
        limited = inject_rate_limit(self.requested, self.time, 0.8)
        report = analyze_trial(self.trial(limited), config=self.config)
        self.assertGreater(metric(report, "rmse_nm"), 0.0)
        self.assertGreater(metric(report, "peak_absolute_error_nm"), 0.0)

    def test_system_fault_is_retained_and_makes_trial_ineligible(self):
        observed = self.requested.copy()
        fault = np.zeros(self.time.size, dtype=bool)
        fault[100:120] = True
        observed[fault] = 1000.0
        report = analyze_trial(
            self.trial(observed, fault_mask=fault), config=self.config)
        self.assertGreater(metric(report, "rmse_nm"), 100.0)
        self.assertEqual(report.system_fault.active_samples, 20)
        self.assertEqual(report.system_fault.intervals[0].start_index, 100)
        self.assertEqual(report.system_fault.intervals[0].end_index, 119)
        self.assertIsNotNone(report.torque_error_nm[100])
        self.assertTrue(report.fault_occurrence)
        self.assertEqual(report.trial_status, TrialStatus.FAULTED)
        self.assertFalse(report.eligible_for_later_certification)

    def test_duplicate_and_backward_timestamps_are_reported(self):
        time = self.time.copy()
        time[30] = time[29]
        time[60] = time[59] - 0.01
        report = analyze_trial(
            self.trial(timestamps_s=time), config=self.config)
        self.assertFalse(report.quality.timestamps_strictly_increasing)
        self.assertIn(30, report.quality.duplicate_timestamp_indices)
        self.assertIn(60, report.quality.backward_timestamp_indices)
        self.assertFalse(report.metrics["estimated_delay_s"].valid)
        self.assertEqual(report.trial_status, TrialStatus.INVALID_MEASUREMENT)

    def test_missing_samples_are_estimated_from_explicit_period(self):
        keep = np.ones(self.time.size, dtype=bool)
        keep[100:103] = False
        trial = self.trial(
            timestamps_s=self.time[keep],
            tau_requested_nm=self.requested[keep],
            observed=self.requested[keep],
            expected_sample_period_s=1.0 / self.sample_rate_hz,
        )
        report = analyze_trial(trial, config=self.config)
        self.assertEqual(report.quality.estimated_missing_samples, 3)
        self.assertEqual(len(report.quality.missing_sample_gaps), 1)
        self.assertFalse(report.metrics["estimated_delay_s"].valid)
        self.assertEqual(report.trial_status, TrialStatus.DEGRADED)

    def test_nan_and_inf_require_explicit_invalid_mask_and_reason(self):
        observed = self.requested.copy()
        observed[10] = np.nan
        observed[20] = np.inf
        invalid = np.zeros(self.time.size, dtype=bool)
        invalid[[10, 20]] = True
        report = analyze_trial(self.trial(
            observed,
            measurement_invalid_mask=invalid,
            measurement_invalid_reasons=("logger decode failure",),
        ), config=self.config)
        self.assertEqual(report.quality.nonfinite_indices["tau_observed_nm"],
                         (10, 20))
        self.assertEqual(report.evaluation_sample_count, self.time.size - 2)
        self.assertAlmostEqual(report.excluded_measurement_fraction,
                               2 / self.time.size)
        self.assertEqual(report.measurement_invalid.active_samples, 2)
        self.assertEqual(report.trial_status, TrialStatus.INVALID_MEASUREMENT)
        self.assertFalse(report.eligible_for_later_certification)
        self.assertFalse(report.metrics["estimated_delay_s"].valid)

    def test_unclassified_nonfinite_values_are_rejected(self):
        observed = self.requested.copy()
        observed[10] = np.nan
        with self.assertRaisesRegex(ValueError, "explicit"):
            analyze_trial(self.trial(observed), config=self.config)

    def test_invalid_mask_requires_reason(self):
        invalid = np.zeros(self.time.size, dtype=bool)
        invalid[10] = True
        with self.assertRaisesRegex(ValueError, "reason"):
            analyze_trial(self.trial(
                measurement_invalid_mask=invalid), config=self.config)

    def test_stale_samples_are_excluded_and_reported_as_degraded(self):
        stale = np.zeros(self.time.size, dtype=bool)
        stale[30:40] = True
        observed = self.requested.copy()
        observed[stale] = 1000.0
        report = analyze_trial(
            self.trial(observed, stale_mask=stale), config=self.config)
        self.assertAlmostEqual(metric(report, "rmse_nm"), 0.0)
        self.assertEqual(report.stale.active_samples, 10)
        self.assertEqual(report.evaluation_sample_count, self.time.size - 10)
        self.assertEqual(report.trial_status, TrialStatus.DEGRADED)
        self.assertFalse(report.eligible_for_later_certification)

    def test_zero_request_protects_normalized_metrics(self):
        zeros = np.zeros_like(self.time)
        report = analyze_trial(
            self.trial(zeros, tau_requested_nm=zeros), config=self.config)
        self.assertTrue(report.quality.near_zero_requested_denominator)
        self.assertFalse(report.metrics["torque_nrmse"].valid)
        self.assertFalse(report.metrics["gain_ratio"].valid)
        self.assertFalse(report.metrics["normalized_amplitude_error"].valid)

    def test_constant_request_is_insufficient_for_delay(self):
        constant = np.ones_like(self.time)
        report = analyze_trial(
            self.trial(constant, tau_requested_nm=constant), config=self.config)
        self.assertTrue(report.quality.insufficient_excitation)
        self.assertFalse(report.metrics["estimated_delay_s"].valid)
        self.assertTrue(report.metrics["torque_nrmse"].valid)

    def test_work_metrics_use_tau_times_dq(self):
        time = np.linspace(0.0, 1.0, 101)
        requested = np.full(time.shape, 2.0)
        observed = np.full(time.shape, 3.0)
        dq = np.full(time.shape, 4.0)
        report = analyze_trial(FidelityTrial(
            trial_id="work-case",
            timestamps_s=time,
            tau_requested_nm=requested,
            tau_observed_nm=observed,
            requested_signal_source="fixture.request",
            observed_signal_source="fixture.observed",
            observed_torque_kind=TorqueObservationKind.SIMULATED,
            dq_rad_s=dq,
        ))
        self.assertAlmostEqual(metric(report, "requested_work_j"), 8.0)
        self.assertAlmostEqual(metric(report, "observed_work_j"), 12.0)
        self.assertAlmostEqual(metric(report, "work_error_j"), 4.0)
        self.assertAlmostEqual(metric(report, "normalized_work_error"), 0.5)

    def test_work_metrics_require_velocity(self):
        report = analyze_trial(self.trial(), config=self.config)
        self.assertFalse(report.metrics["requested_work_j"].valid)
        self.assertIn("dq_rad_s", report.metrics["requested_work_j"].reason)

    def test_model_based_observations_cannot_be_physical_fidelity(self):
        forbidden = (
            TorqueObservationKind.SIMULATED,
            TorqueObservationKind.DERIVED,
            TorqueObservationKind.IDENTIFIED,
        )
        for kind in forbidden:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                analyze_trial(
                    self.trial(observed_torque_kind=kind,
                               observed_independent=True),
                    analysis_label=AnalysisLabel.PHYSICAL_FIDELITY,
                )

    def test_measured_but_dependent_observation_cannot_claim_physical(self):
        with self.assertRaises(ValueError):
            analyze_trial(
                self.trial(observed_torque_kind=TorqueObservationKind.MEASURED,
                           observed_independent=False),
                analysis_label=AnalysisLabel.PHYSICAL_FIDELITY,
            )

    def test_independent_measured_observation_can_request_physical_label(self):
        report = analyze_trial(
            self.trial(observed_torque_kind=TorqueObservationKind.MEASURED,
                       observed_independent=True),
            analysis_label=AnalysisLabel.PHYSICAL_FIDELITY,
            config=self.config,
        )
        self.assertTrue(report.is_physical_fidelity)
        self.assertEqual(report.analysis_label, AnalysisLabel.PHYSICAL_FIDELITY)
        self.assertEqual(report.trial_status, TrialStatus.VALID)
        self.assertTrue(report.eligible_for_later_certification)

    def test_every_metric_carries_complete_provenance(self):
        report = analyze_trial(self.trial(), config=self.config)
        for result in report.metrics.values():
            with self.subTest(metric=result.name):
                self.assertEqual(result.provenance.source_trial,
                                 "synthetic-trial")
                self.assertEqual(result.provenance.requested_signal_source,
                                 "synthetic.request")
                self.assertEqual(result.provenance.observed_signal_source,
                                 "synthetic.observed")
                self.assertEqual(result.provenance.metric_version,
                                 "vipro-fidelity-metrics/1.1.0")
                self.assertTrue(result.provenance.preprocessing_applied)
                self.assertEqual(result.provenance.observed_torque_kind,
                                 TorqueObservationKind.SIMULATED)

    def test_report_is_json_serializable(self):
        report = analyze_trial(self.trial(), config=self.config)
        payload = json.loads(json.dumps(report.to_dict()))
        self.assertEqual(payload["trial_id"], "synthetic-trial")
        self.assertEqual(payload["provenance"]["observed_torque_kind"],
                         "SIMULATED")
        self.assertFalse(payload["is_physical_fidelity"])
        self.assertEqual(payload["trial_status"], "VALID")

    def test_array_lengths_must_match(self):
        with self.assertRaises(ValueError):
            analyze_trial(self.trial(timestamps_s=self.time[:-1]))


class SyntheticFaultDirectionTest(unittest.TestCase):
    def test_all_required_faults_change_expected_metric_direction(self):
        sample_rate_hz = 250.0
        time = np.arange(0.0, 5.0, 1.0 / sample_rate_hz)
        requested = deterministic_request(time)
        config = FidelityConfig(max_delay_s=0.2)

        def report(name, observed, saturation_mask=None):
            return analyze_trial(FidelityTrial(
                trial_id=name,
                timestamps_s=time,
                tau_requested_nm=requested,
                tau_observed_nm=observed,
                requested_signal_source="synthetic.request",
                observed_signal_source=f"synthetic.{name}",
                observed_torque_kind=TorqueObservationKind.SIMULATED,
                saturation_mask=saturation_mask,
            ), config=config)

        baseline = report("baseline", requested)
        gain = report("gain", inject_gain(requested, 0.75))
        delay = report("delay", inject_delay(requested, 15))
        noise = report("noise", inject_noise(requested, 0.04, seed=7))
        saturated_values, saturated_mask = inject_saturation(requested, 0.30)
        saturation = report("saturation", saturated_values, saturated_mask)
        rate = report("rate", inject_rate_limit(requested, time, 0.6))

        baseline_rmse = metric(baseline, "rmse_nm")
        for faulted in (gain, delay, noise, saturation, rate):
            self.assertGreater(metric(faulted, "rmse_nm"), baseline_rmse)
        self.assertLess(metric(gain, "gain_ratio"), 1.0)
        self.assertAlmostEqual(metric(delay, "estimated_delay_s"),
                               15.0 / sample_rate_hz, places=12)
        self.assertGreater(saturation.saturation.fraction, 0.0)


if __name__ == "__main__":
    unittest.main()
