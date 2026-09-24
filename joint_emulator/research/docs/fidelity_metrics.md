# TASK-010/010R — offline torque-fidelity metrics

## Scope

The module answers one hardware-independent question: given explicit,
time-indexed requested and observed torque arrays for one trial, how different
are they, and is the record suitable for each metric? It does not read ROS or
files, communicate with hardware, infer ABB semantics, certify a mechanism or
implement machine learning.

Implementation:

```text
research/src/fidelity/metrics.py
research/src/fidelity/synthetic.py
```

NumPy is the only non-standard dependency; SciPy is not required.

## Input contract

A `FidelityTrial` contains:

- trial ID and equal-length one-dimensional arrays;
- timestamps, requested torque and observed torque;
- exact requested and observed signal-source identifiers;
- observed origin: `SIMULATED`, `DERIVED`, `IDENTIFIED` or `MEASURED`;
- optional angular velocity and expected sample period;
- optional saturation, hardware/system-fault, measurement-invalid and stale
  masks;
- at least one explicit reason whenever `measurement_invalid_mask` is active;
- an explicit independence flag for the observed torque.

NaN/Inf is accepted only when every affected sample is covered by an explicit
measurement-invalid mask and reason. Otherwise analysis fails instead of
silently discarding data.

## Primary torque metrics

For measurement-valid, non-stale samples at their original indices:

\[
e_\tau[k]=\tau_{observed}[k]-\tau_{requested}[k].
\]

\[
RMSE=\sqrt{\frac{1}{N}\sum_k e_\tau[k]^2},\quad
MAE=\frac{1}{N}\sum_k |e_\tau[k]|,\quad
e_{peak}=\max_k |e_\tau[k]|.
\]

\[
E_{\tau,NRMSE}=\frac{RMSE}{RMS(\tau_{requested})+\epsilon}.
\]

The module also reports requested/observed RMS, RMS gain ratio and signed
normalized amplitude error. When requested RMS is at or below epsilon, all
normalized torque metrics are invalid; epsilon is not treated as excitation.
These are amplitude diagnostics, not transfer-function identification.

## Delay

Delay is estimated from normalized cross-correlation of centered signals. A
positive result means observed torque lags requested torque. The primary error
is never time-shifted. `delay_aligned_rmse_nm` is only a diagnostic.

Delay is invalid if timestamps are nonfinite/non-monotonic/nonuniform, gaps or
excluded samples are present, either signal lacks dynamic excitation, or the
record is too short.

## Work and energy

With angular velocity supplied:

\[
W_r=\int\tau_r(t)\dot q(t)dt,\qquad
W_o=\int\tau_o(t)\dot q(t)dt,\qquad e_W=W_o-W_r.
\]

Trapezoidal integration is performed independently on contiguous valid
segments; it never bridges excluded data. Normalized work error is invalid
when requested signed work is near zero.

## TASK-010R status and event semantics

`trial_status` is one of:

- `VALID`: no detected system fault, saturation, stale/missing data,
  measurement invalidity or excitation defect;
- `DEGRADED`: usable measurements exist, but saturation, stale/missing data,
  insufficient excitation or near-zero normalization occurred;
- `FAULTED`: a hardware/system fault occurred during the request;
- `INVALID_MEASUREMENT`: the record has explicitly invalid measurements or
  invalid timestamp ordering and no system fault has higher precedence.

Precedence is `FAULTED` → `INVALID_MEASUREMENT` → `DEGRADED` → `VALID`. Thus a
real fault cannot disappear behind a logging defect.

The mask policy is fixed:

- hardware/system-fault samples remain in primary metrics when measurable;
- saturation samples remain in primary metrics;
- measurement-invalid samples are excluded only with explicit mask and reason;
- stale samples are excluded and reported separately;
- absent samples remain absent and are reported as timestamp gaps.

Fault and saturation are evidence about realizability. Removing them could
make a failed request appear accurate. A stale value is excluded because it is
not a new measurement at the nominal timestamp.

The report contains metrics on valid measurement samples, evaluation sample
count, excluded measurement fraction, saturation fraction, fault occurrence,
all mask intervals, status, and certification-ineligibility reasons. Only a
`VALID` trial analyzed as `PHYSICAL_FIDELITY` from an independent `MEASURED`
signal is marked `eligible_for_later_certification`. SIM/offline trials remain
ineligible even when their data status is `VALID`. This flag is not an
`ACCEPT` verdict and defines no acceptance threshold. Under metric version
`vipro-fidelity-metrics/1.1.0`, a `FAULTED` trial is always ineligible for a
future `ACCEPT`.

## Signal-quality checks

The report records finite/nonfinite indices, timestamp monotonicity, duplicate
and backward timestamps, sampling uniformity, estimated missing samples,
requested RMS/centered RMS, insufficient excitation and near-zero denominator.
Missing-sample detection uses an explicit expected period when available;
otherwise a valid record's median period is labelled `INFERRED_MEDIAN`, not
claimed as device-rate evidence.

The default excitation threshold is only a numerical guard. A physical study
must derive it from the metrology noise floor.

## Provenance and physical-fidelity guard

Every metric carries trial ID, source identifiers, metric version, exact
preprocessing, observation kind, analysis label and independence flag. The
default label is `OFFLINE_SIGNAL_COMPARISON`.

`PHYSICAL_FIDELITY` is rejected unless the observation is both `MEASURED` and
explicitly independent. SIM, drive/model-derived and identified signals cannot
be promoted to physical ground truth. Even a permitted label still requires
calibration, uncertainty, reference point, bandwidth and timing evidence.

## Synthetic validation

Deterministic tests inject gain error, delay, seeded noise, saturation and rate
limiting. They also verify that a system fault remains in RMSE and yields
`FAULTED`; invalid measurements need both mask and reason; stale/missing and
saturated data are explicit; and prohibited observation types cannot be called
physical fidelity.

Run:

```bash
cd /home/ubuntu/ros2_ws/src/joint_emulator
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s research/tests -v
/usr/bin/python3 research/examples/fidelity_synthetic_demo.py
```

The demonstration uses only `SIMULATED` observations and
`OFFLINE_SIGNAL_COMPARISON`.

## Minimum physical data needed later

Physical use requires requested B torque before/after limiting; calibrated and
preferably independent port torque; aligned acquisition/device timestamps and
sequence IDs; calibrated angular velocity; explicit saturation, warning,
fault, stale and invalid-measurement masks; calibration IDs, uncertainty,
bandwidth and filter metadata; pair/session/hardware/configuration identities;
and operating-state/temperature context. Drive current or estimated torque may
be analyzed as `DERIVED` or `IDENTIFIED`, never silently as ground truth.
