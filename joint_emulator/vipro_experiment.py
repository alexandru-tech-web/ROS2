#!/usr/bin/env python3
"""Protocol SIL repetabil pe o pereche si analiza jurnalelor ViPRO.

Nu comunica niciodata cu drive-uri sau cu topicuri ROS. Comanda `reference`
foloseste acelasi SimBackend si aceeasi lege de impedanta ca emulatorul,
intr-un ceas determinist. Comanda `analyze` citeste o sesiune ROS existenta.
Toate rezultatele sunt SIL, nu masuratori ale bancului ABB.
"""
import argparse
import csv
import json
import math
import os
import statistics
from datetime import datetime, timezone

from drive_iface import SimBackend
from encoder_core import (EncoderLogger, MotorEncoderBank,
                          MotorEncoderLogger)
from joint_core import EnergyMonitor, ImpedanceLaw
from session_export import (SessionEventLogger, SessionStateLogger,
                            checked_session_id, export_session_xlsx,
                            session_path, utc_now, write_config)
from teleimpedance import DegradedMeasure


def _number(row, key):
    value = row.get(key, "")
    return float(value) if value not in ("", None) else None


def _mean(values):
    return sum(values) / len(values) if values else None


def _first_crossing(rows, baseline, target, fraction):
    threshold = fraction * abs(target - baseline)
    direction = 1.0 if target >= baseline else -1.0
    for row in rows:
        if direction * (_number(row, "theta_axis_rad") - baseline) >= threshold:
            return _number(row, "time_s")
    return None


def analyze_session(data_dir, session_id, pair=0, event_index=-1):
    """Calculeaza indicatori pentru o treapta A, fara interpolare de date."""
    data_dir = os.path.expanduser(str(data_dir))
    session_id = checked_session_id(session_id)
    paths = {
        "state": session_path(data_dir, session_id, "states"),
        "events": session_path(data_dir, session_id, "events"),
        "motor": os.path.join(data_dir, f"motor_encoders_{session_id}.csv"),
    }
    with open(paths["state"], newline="", encoding="utf-8") as stream:
        states = list(csv.DictReader(stream))
    with open(paths["events"], newline="", encoding="utf-8") as stream:
        events = list(csv.DictReader(stream))
    if not states:
        raise ValueError("jurnalul de stare este gol")
    pair = int(pair)
    candidates = [e for e in events if e["event"] == "cmd_a" and
                  e["pair"] == str(pair) and
                  abs(float(e["tau_a_cmd_nm"] or 0.0)) > 1e-12]
    if not candidates:
        raise ValueError(f"nu exista o comanda A nenula pe perechea {pair}")
    event = candidates[event_index]
    onset = float(event["time_s"])
    later_events = [float(e["time_s"]) for e in events
                    if float(e["time_s"]) > onset + 1e-9 and
                    (e["event"] == "estop" or
                     (e["event"] == "cmd_a" and e["pair"] == str(pair)))]
    last_time = max(float(r["time_s"]) for r in states)
    end = min(later_events) if later_events else last_time + 1e-6
    if end - onset < 0.3:
        raise ValueError("treapta are sub 0.3 s; nu se poate evalua stabilizarea")
    selected = [r for r in states if int(r["pair"]) == pair]
    selected.sort(key=lambda r: float(r["time_s"]))
    before = [r for r in selected if onset - 0.3 <= float(r["time_s"]) < onset]
    hold = [r for r in selected if onset <= float(r["time_s"]) < end]
    if not before or len(hold) < 3:
        raise ValueError("lipsesc esantioane inainte sau dupa comanda")
    tail_start = max(onset, end - 0.3)
    tail = [r for r in hold if float(r["time_s"]) >= tail_start]
    baseline = _mean([float(r["theta_axis_rad"]) for r in before])
    steady = _mean([float(r["theta_axis_rad"]) for r in tail])
    amplitude = steady - baseline
    direction = 1.0 if amplitude >= 0 else -1.0
    peak = max(direction * (float(r["theta_axis_rad"]) - baseline)
               for r in hold)
    overshoot_pct = (max(0.0, peak - abs(amplitude)) / abs(amplitude) * 100.0
                     if abs(amplitude) > 1e-9 else None)
    t10 = _first_crossing(hold, baseline, steady, 0.1)
    t90 = _first_crossing(hold, baseline, steady, 0.9)
    tolerance = max(0.02 * abs(amplitude), 1e-5)
    # Prima mostra dupa ultima iesire din banda; O(n), inclusiv pe CSV mari.
    last_outside = max((i for i, row in enumerate(hold)
                        if abs(float(row["theta_axis_rad"]) - steady) > tolerance),
                       default=-1)
    settle = (float(hold[last_outside + 1]["time_s"]) - onset
              if last_outside + 1 < len(hold) else None)
    k_effective = _mean([float(r["k_eff_nm_rad"]) for r in tail])
    theta0 = _mean([float(r["theta0_rad"]) for r in tail])
    mode = tail[-1]["reaction_mode"]
    command = float(event["tau_a_cmd_nm"])
    expected = (theta0 + command / k_effective
                if mode == "impedance" and k_effective and k_effective > 0
                else None)
    inactive = [r for r in states if int(r["pair"]) != pair and
                onset <= float(r["time_s"]) < end]
    other_tau_max = max(
        (abs(float(r["tau_a_cmd_nm"])) for r in inactive), default=0.0)
    true_by_time = {round(float(r["time_s"]), 4): r for r in hold}
    motor_a, motor_b = {}, {}
    with open(paths["motor"], newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if int(row["pair"]) != pair:
                continue
            t = round(float(row["t_s"]), 4)
            if onset <= t < end:
                (motor_a if row["side"] == "A" else motor_b)[t] = row
    shared = motor_a.keys() & motor_b.keys()
    matching = motor_a.keys() & true_by_time.keys()
    encoder_mismatch = (max(abs(float(motor_a[t]["th_raw"]) -
                                float(motor_b[t]["th_raw"])) for t in shared)
                        if shared else None)
    encoder_error = (max(abs(float(motor_a[t]["th_raw"]) -
                             float(true_by_time[t]["theta_axis_rad"]))
                         for t in matching) if matching else None)
    velocity_rmse = (math.sqrt(_mean([
        (float(motor_a[t]["om"]) -
         float(true_by_time[t]["omega_axis_rad_s"])) ** 2
        for t in matching])) if matching else None)
    filter_displacement = (max(abs(float(r["th"]) - float(r["th_raw"]))
                               for r in motor_a.values()) if motor_a else None)
    sampling = [float(b["time_s"]) - float(a["time_s"])
                for a, b in zip(hold, hold[1:])]
    result = {
        "session_id": session_id, "source": "SIM (nu ABB)",
        "analyzed_at_utc": utc_now(), "pair": pair,
        "event_time_s": onset, "window_end_s": end,
        "command_a_nm": command,
        "samples_state": len(hold), "samples_encoder_a": len(motor_a),
        "state_sample_period_median_s": statistics.median(sampling)
        if sampling else None,
        "baseline_theta_rad": baseline, "steady_theta_rad": steady,
        "expected_theta_rad": expected,
        "steady_error_rad": steady - expected if expected is not None else None,
        "apparent_k_from_command_nm_rad": (
            command / (steady - theta0)
            if theta0 is not None and abs(steady - theta0) > 1e-9 else None),
        "rise_time_10_90_s": t90 - t10 if t10 is not None and t90 is not None
        else None,
        "settling_time_2pct_s": settle,
        "overshoot_pct": overshoot_pct,
        "peak_abs_omega_true_rad_s": max(abs(float(r["omega_axis_rad_s"]))
                                          for r in hold),
        "steady_tau_b_cmd_nm": _mean([float(r["tau_b_cmd_nm"]) for r in tail]),
        "steady_torque_balance_cmd_nm": (
            command + _mean([float(r["tau_b_cmd_nm"]) for r in tail])),
        "max_abs_theta_other_pairs_rad": max(
            (abs(float(r["theta_axis_rad"])) for r in inactive), default=0.0),
        "samples_other_pairs": len(inactive),
        "max_abs_tau_a_other_pairs_nm": other_tau_max,
        "isolation_test_valid": bool(inactive) and other_tau_max < 1e-9,
        "max_abs_encoder_delta_a_b_rad": encoder_mismatch,
        "max_abs_encoder_vs_sim_rad": encoder_error,
        "velocity_est_rmse_vs_sim_rad_s": velocity_rmse,
        "max_abs_filtered_minus_raw_rad": filter_displacement,
        "max_window_energy_j": max(float(r["win_energy_j"]) for r in hold),
        "steady_speed_abs_max_rad_s": max(
            abs(float(r["omega_axis_rad_s"])) for r in tail),
        "note": ("Cuplurile si rigiditatea aparenta provin din COMENZI SIM, "
                 "nu din senzori de cuplu. Viteza de varf intre esantioane "
                 "poate lipsi din jurnal. Pentru validare ABB trebuie citit "
                 "cuplul/curentul real si calibrate encoderele."),
    }
    return result


def plot_session(data_dir, session_id, pair=0):
    """Salveaza o figura de diagnostic din CSV-urile complete, fara GUI."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data_dir = os.path.expanduser(str(data_dir))
    session_id = checked_session_id(session_id)
    pair = int(pair)
    state_path = session_path(data_dir, session_id, "states")
    motor_path = os.path.join(data_dir, f"motor_encoders_{session_id}.csv")
    with open(state_path, newline="", encoding="utf-8") as stream:
        states = [r for r in csv.DictReader(stream) if int(r["pair"]) == pair]
    with open(motor_path, newline="", encoding="utf-8") as stream:
        motors = [r for r in csv.DictReader(stream)
                  if int(r["pair"]) == pair and r["side"] == "A"]
    if not states or not motors:
        raise ValueError("jurnalele nu contin perechea solicitata")
    t = [float(r["time_s"]) for r in states]
    te = [float(r["t_s"]) for r in motors]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(t, [float(r["tau_a_cmd_nm"]) for r in states],
                 label="A comandat", color="tab:blue")
    axes[0].plot(t, [float(r["tau_b_cmd_nm"]) for r in states],
                 label="B comandat", color="tab:orange")
    axes[0].set_ylabel("cuplu [Nm]")
    axes[1].plot(t, [float(r["theta_axis_rad"]) for r in states],
                 label="ax SIM", color="tab:blue")
    axes[1].plot(te, [float(r["th_raw"]) for r in motors],
                 label="encoder A cuantizat", color="tab:green", alpha=0.7)
    axes[1].set_ylabel("unghi [rad]")
    axes[2].plot(t, [float(r["omega_axis_rad_s"]) for r in states],
                 label="ax SIM (esantionat)", color="tab:blue")
    axes[2].plot(te, [float(r["om"]) for r in motors],
                 label="viteza estimata A", color="tab:green", alpha=0.8)
    axes[2].set_ylabel("viteza [rad/s]")
    axes[2].set_xlabel("timp simulare [s]")
    for ax in axes:
        ax.grid(alpha=0.3)
        ax.legend(loc="best")
    fig.suptitle(f"ViPRO SIL - sesiunea {session_id}, perechea {pair}\n"
                 "Cupluri comandate si encodere simulate; NU masuratori ABB")
    fig.tight_layout()
    target = session_path(data_dir, session_id, f"pair{pair}_plot", "png")
    if os.path.exists(target):
        raise FileExistsError(f"figura exista deja: {target}")
    fig.savefig(target, dpi=150)
    plt.close(fig)
    return target


def _write_report(path, report):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=True)
        stream.write("\n")


def run_reference(data_dir, tau=0.24, k_gain=20.0, b_gain=0.8,
                  onset=1.0, release=3.0, duration=4.0,
                  sample_hz=100, counts_per_rev=4096, session_id=None):
    """Ruleaza exact o treapta A0 pe trei perechi SIM independente."""
    tau, k_gain, b_gain = float(tau), float(k_gain), float(b_gain)
    onset, release, duration = float(onset), float(release), float(duration)
    sample_hz, counts_per_rev = int(sample_hz), int(counts_per_rev)
    if (not all(math.isfinite(x) for x in
                (tau, k_gain, b_gain, onset, release, duration)) or
            not 0 < tau <= 2.0 or not 0 < k_gain <= 40.0 or
            not 0 <= b_gain <= 2.0 or
            not 0 < onset < release < duration or
            sample_hz not in (20, 50, 100, 200) or counts_per_rev <= 0):
        raise ValueError("protocol invalid: tau/K/B/timpi/rata/CPR in afara domeniului SIM")
    inner_dt = 0.0005
    stride = round(1.0 / (sample_hz * inner_dt))
    n_steps = round(duration / inner_dt)
    on_step = round(onset / inner_dt)
    off_step = round(release / inner_dt)
    session_id = checked_session_id(
        session_id or datetime.now(timezone.utc).strftime("ref_%Y%m%dT%H%M%S%fZ"))
    data_dir = os.path.expanduser(str(data_dir))
    os.makedirs(data_dir, exist_ok=True)
    hw = SimBackend(n_pairs=3, dt=inner_dt)
    laws = [ImpedanceLaw(k_nm_rad=k_gain, b_nms_rad=b_gain,
                         tau_max=2.0) for _ in range(3)]
    links = [DegradedMeasure() for _ in range(3)]
    energy = [EnergyMonitor(window_s=1.0, estop_energy=1e9)
              for _ in range(3)]
    bank = MotorEncoderBank(n_pairs=3, counts_per_rev=counts_per_rev,
                            estimator_kind="sampled")
    for motor_id in range(6):
        hw.enable(motor_id)
    write_config(session_path(data_dir, session_id, "sim_config"), {
        "backend": "reference_sim", "pair_excited": 0,
        "input": "single_positive_torque_step_then_zero",
        "tau_a_nm": tau, "onset_s": onset, "release_s": release,
        "duration_s": duration, "initial_k_nm_rad": k_gain,
        "initial_b_nms_rad": b_gain, "sample_hz": sample_hz,
        "physics_inner_dt_s": inner_dt, "n_pairs": 3,
        "adaptive": False, "reaction_mode": "impedance",
    })
    write_config(session_path(data_dir, session_id, "encoder_config"), {
        "estimator_kind": "sampled", "counts_per_rev": counts_per_rev,
        "velocity_tau_s": 0.1, "acceleration_tau_s": 0.15,
    })
    state_log = SessionStateLogger(session_path(data_dir, session_id, "states"))
    event_log = SessionEventLogger(session_path(data_dir, session_id, "events"))
    axis_log = EncoderLogger(os.path.join(data_dir,
                                          f"encoders_{session_id}.csv"))
    motor_log = MotorEncoderLogger(os.path.join(data_dir,
                                                f"motor_encoders_{session_id}.csv"))
    event_log.row(0.0, "start", status="reference_sim")

    def capture():
        stamp = utc_now()
        for pair in range(3):
            t, theta, omega = hw.read(2 * pair)
            state = {
                "t": round(t, 4), "th": round(theta, 6),
                "om": round(omega, 6),
                "motors": {side: {"th": theta, "om": omega,
                                  "source": "reference_sim"}
                           for side in ("A", "B")},
                "tau_a_cmd": tau if pair == 0 and onset <= t < release else 0.0,
                "tau_b": hw.tau[pair][1], "k_ef": k_gain,
                "win_energy": energy[pair].win_energy,
                "reaction_mode": "impedance", "contact_angle_deg": 0.0,
                "estopped": False, "reset_status": "",
            }
            state_log.row(pair, state, laws[pair], links[pair], time_utc=stamp)
            for side, index in (("A", 0), ("B", 1)):
                sample = bank.sample(2 * pair + index, t, theta)
                motor_log.row(pair, side, sample, time_utc=stamp,
                              source="reference_sim")
                if side == "A":
                    axis_log.row(t, pair, sample["th_raw"], sample["th"],
                                 sample["om"], sample["acc"], time_utc=stamp)

    try:
        capture()  # starea t=0 exista si in jurnale, nu doar in configuratie
        for step in range(n_steps):
            if step == on_step:
                event_log.row(step * inner_dt, "cmd_a", pair=0,
                              tau_a_cmd_nm=tau)
            if step == off_step:
                event_log.row(step * inner_dt, "cmd_a", pair=0,
                              tau_a_cmd_nm=0.0)
            hw.set_torque(0, tau if on_step <= step < off_step else 0.0)
            hw.step(inner_dt)
            for pair in range(3):
                t, theta, omega = hw.read(2 * pair + 1)
                reaction = laws[pair].torque(theta, omega)
                hw.set_torque(2 * pair + 1, reaction)
                energy[pair].step(reaction, omega, inner_dt)
            if (step + 1) % stride == 0:
                capture()
    finally:
        state_log.close(); event_log.close()
        axis_log.close(); motor_log.close()
    report = analyze_session(data_dir, session_id, pair=0)
    report["protocol"] = "reference_fixed_impedance_single_pair"
    report["source"] = "DETERMINISTIC_SIL (nu ABB)"
    report_path = session_path(data_dir, session_id, "analysis", "json")
    _write_report(report_path, report)
    book_path = export_session_xlsx(data_dir, session_id)
    figure_path = plot_session(data_dir, session_id, pair=0)
    return report_path, book_path, figure_path, report


def plot_suite(data_dir, session_id):
    """Figura compacta A/B si pozitie pentru toate cele trei perechi SIM."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = session_path(data_dir, session_id, "states")
    with open(path, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    fig, axes = plt.subplots(3, 2, figsize=(13, 9), sharex=True)
    for pair in range(3):
        rr = [r for r in rows if int(r["pair"]) == pair]
        times = [float(r["time_s"]) for r in rr]
        axes[pair][0].plot(times, [float(r["tau_a_cmd_nm"]) for r in rr],
                           label="A comandat", color="tab:blue")
        axes[pair][0].plot(times, [float(r["tau_b_cmd_nm"]) for r in rr],
                           label="B comandat", color="tab:orange")
        axes[pair][1].plot(times, [float(r["theta_axis_rad"]) for r in rr],
                           color="tab:green", label="ax SIM")
        axes[pair][0].set_ylabel(f"perechea {pair}\ncuplu [Nm]")
        axes[pair][1].set_ylabel("unghi [rad]")
        for ax in axes[pair]:
            ax.grid(alpha=0.3)
            ax.legend(loc="upper right", fontsize=8)
    axes[2][0].set_xlabel("timp simulare [s]")
    axes[2][1].set_xlabel("timp simulare [s]")
    fig.suptitle(f"ViPRO - suita automata SIL {session_id}\n"
                 "Cupluri comandate, NU masuratori ABB")
    fig.tight_layout()
    target = session_path(data_dir, session_id, "suite_plot", "png")
    if os.path.exists(target):
        raise FileExistsError(f"figura exista deja: {target}")
    fig.savefig(target, dpi=150)
    plt.close(fig)
    return target


def suite_checks(metrics, expected_theta, hold_s, counts_per_rev,
                 rest_angle, rest_speed):
    """Criterii de regresie ale modelului SIM; nu praguri de siguranta ABB."""
    mismatch = metrics["max_abs_encoder_delta_a_b_rad"]
    settling = metrics["settling_time_2pct_s"]
    return {
        "theta_expected": abs(metrics["steady_theta_rad"] - expected_theta) <=
            max(0.001, 0.03 * abs(expected_theta)),
        "torque_opposition": abs(metrics["steady_torque_balance_cmd_nm"]) <= 0.02,
        "pairs_isolated": (metrics["isolation_test_valid"] and
                           metrics["max_abs_theta_other_pairs_rad"] <= 0.001),
        "encoder_rigid": (mismatch is not None and
                          mismatch <= 2.0 * math.pi / counts_per_rev),
        "settled_in_hold": settling is not None and settling <= hold_s,
        "returned_to_zero": (rest_angle is not None and rest_speed is not None
                             and rest_angle <= 0.002 and rest_speed <= 0.02),
    }


def build_suite_plan(levels=(0.25, 0.5), hold_s=1.0, rest_s=0.6):
    """Plan pur, comun suitei offline si redarii vizuale in Gazebo."""
    levels = tuple(float(x) for x in levels)
    hold_s, rest_s = float(hold_s), float(rest_s)
    if (not levels or len(levels) > 4 or
            not all(math.isfinite(x) and 0 < x <= 2.0 for x in levels) or
            not math.isfinite(hold_s) or not 0.6 <= hold_s <= 5.0 or
            not math.isfinite(rest_s) or not 0.4 <= rest_s <= 5.0):
        raise ValueError("parametrii planului sunt in afara domeniului SIM")
    plan = []
    cursor = 0.5
    for pair in range(3):
        for magnitude in levels:
            for sign in (1, -1):
                start = round(cursor, 4)
                end = round(cursor + hold_s, 4)
                plan.append({"case_id": len(plan) + 1, "pair": pair,
                             "tau_a_nm": sign * magnitude,
                             "onset_s": start, "release_s": end})
                cursor = end + rest_s
    duration = round(cursor, 4)
    return plan, duration


def run_suite(data_dir, k_gain=20.0, b_gain=0.8, levels=(0.25, 0.5),
              hold_s=1.0, rest_s=0.6, sample_hz=100,
              counts_per_rev=4096, session_id=None):
    """12 trepte SIM izolate: 3 perechi x 2 amplitudini x 2 sensuri."""
    k_gain, b_gain = float(k_gain), float(b_gain)
    hold_s, rest_s = float(hold_s), float(rest_s)
    sample_hz, counts_per_rev = int(sample_hz), int(counts_per_rev)
    plan, duration = build_suite_plan(levels, hold_s, rest_s)
    if (not all(math.isfinite(x) for x in
                (k_gain, b_gain)) or
            not 0 < k_gain <= 40.0 or not 0 <= b_gain <= 2.0 or
            sample_hz not in (20, 50, 100, 200) or counts_per_rev <= 0):
        raise ValueError("parametrii suitei sunt in afara domeniului SIM")
    inner_dt = 0.0005
    stride = round(1.0 / (sample_hz * inner_dt))
    if any(abs(round(x / inner_dt) * inner_dt - x) > 1e-8
           for x in [duration] + [t for case in plan
                                  for t in (case["onset_s"], case["release_s"])]):
        raise ValueError("timpii suitei trebuie sa fie multipli de 0.5 ms")
    session_id = checked_session_id(
        session_id or datetime.now(timezone.utc).strftime("suite_%Y%m%dT%H%M%S%fZ"))
    data_dir = os.path.expanduser(str(data_dir))
    os.makedirs(data_dir, exist_ok=True)
    hw = SimBackend(n_pairs=3, dt=inner_dt)
    laws = [ImpedanceLaw(k_nm_rad=k_gain, b_nms_rad=b_gain,
                         tau_max=2.0) for _ in range(3)]
    links = [DegradedMeasure() for _ in range(3)]
    energy = [EnergyMonitor(window_s=1.0, estop_energy=1e9)
              for _ in range(3)]
    bank = MotorEncoderBank(n_pairs=3, counts_per_rev=counts_per_rev,
                            estimator_kind="sampled")
    commands = [0.0] * 3
    transitions = {}
    event_time_utc = {}
    for case in plan:
        on_step = round(case["onset_s"] / inner_dt)
        off_step = round(case["release_s"] / inner_dt)
        transitions.setdefault(on_step, []).append((case["pair"], case["tau_a_nm"]))
        transitions.setdefault(off_step, []).append((case["pair"], 0.0))
    for motor_id in range(6):
        hw.enable(motor_id)
    write_config(session_path(data_dir, session_id, "sim_config"), {
        "backend": "suite_sim", "protocol": "sequential_signed_torque_steps",
        "cases_json": json.dumps(plan, separators=(",", ":")),
        "duration_s": duration, "hold_s": hold_s, "rest_s": rest_s,
        "initial_k_nm_rad": k_gain, "initial_b_nms_rad": b_gain,
        "sample_hz": sample_hz, "physics_inner_dt_s": inner_dt,
        "n_pairs": 3, "adaptive": False, "reaction_mode": "impedance",
    })
    write_config(session_path(data_dir, session_id, "encoder_config"), {
        "estimator_kind": "sampled", "counts_per_rev": counts_per_rev,
        "velocity_tau_s": 0.1, "acceleration_tau_s": 0.15,
    })
    state_log = SessionStateLogger(session_path(data_dir, session_id, "states"))
    event_log = SessionEventLogger(session_path(data_dir, session_id, "events"))
    axis_log = EncoderLogger(os.path.join(data_dir, f"encoders_{session_id}.csv"))
    motor_log = MotorEncoderLogger(os.path.join(data_dir,
                                                f"motor_encoders_{session_id}.csv"))
    event_log.row(0.0, "start", status="suite_sim")

    def capture():
        stamp = utc_now()
        for pair in range(3):
            t, theta, omega = hw.read(2 * pair)
            state = {
                "t": round(t, 4), "th": round(theta, 6),
                "om": round(omega, 6),
                "motors": {side: {"th": theta, "om": omega,
                                  "source": "suite_sim"}
                           for side in ("A", "B")},
                "tau_a_cmd": commands[pair], "tau_b": hw.tau[pair][1],
                "k_ef": k_gain, "win_energy": energy[pair].win_energy,
                "reaction_mode": "impedance", "contact_angle_deg": 0.0,
                "estopped": False, "reset_status": "",
            }
            state_log.row(pair, state, laws[pair], links[pair], time_utc=stamp)
            for side, index in (("A", 0), ("B", 1)):
                sample = bank.sample(2 * pair + index, t, theta)
                motor_log.row(pair, side, sample, time_utc=stamp,
                              source="suite_sim")
                if side == "A":
                    axis_log.row(t, pair, sample["th_raw"], sample["th"],
                                 sample["om"], sample["acc"], time_utc=stamp)

    try:
        capture()
        for step in range(round(duration / inner_dt)):
            for pair, tau in transitions.get(step, ()):
                commands[pair] = tau
                hw.set_torque(2 * pair, tau)
                stamp = utc_now()
                event_log.row(step * inner_dt, "cmd_a", pair=pair,
                              tau_a_cmd_nm=tau, time_utc=stamp)
                if tau != 0.0:
                    event_time_utc[(pair, round(step * inner_dt, 4))] = stamp
            hw.step(inner_dt)
            for pair in range(3):
                t, theta, omega = hw.read(2 * pair + 1)
                reaction = laws[pair].torque(theta, omega)
                hw.set_torque(2 * pair + 1, reaction)
                energy[pair].step(reaction, omega, inner_dt)
            if (step + 1) % stride == 0:
                capture()
    finally:
        state_log.close(); event_log.close()
        axis_log.close(); motor_log.close()

    with open(session_path(data_dir, session_id, "states"),
              newline="", encoding="utf-8") as stream:
        all_states = list(csv.DictReader(stream))
    cases = []
    indices = [0, 0, 0]
    for case in plan:
        pair = case["pair"]
        metrics = analyze_session(data_dir, session_id, pair=pair,
                                  event_index=indices[pair])
        indices[pair] += 1
        release = case["release_s"]
        rest_tail = [r for r in all_states if int(r["pair"]) == pair and
                     release + rest_s - 0.1 <= float(r["time_s"]) < release + rest_s]
        rest_angle = max((abs(float(r["theta_axis_rad"])) for r in rest_tail),
                         default=None)
        rest_speed = max((abs(float(r["omega_axis_rad_s"])) for r in rest_tail),
                         default=None)
        expected = case["tau_a_nm"] / k_gain
        checks = suite_checks(metrics, expected, hold_s, counts_per_rev,
                              rest_angle, rest_speed)
        cases.append({**case, "metrics": metrics,
                      "recovery_theta_max_rad": rest_angle,
                      "recovery_omega_max_rad_s": rest_speed,
                      "checks": checks, "passed": all(checks.values())})
    passed = sum(case["passed"] for case in cases)
    summary = {
        "session_id": session_id, "source": "DETERMINISTIC_SIL (nu ABB)",
        "protocol": "signed steps, one pair at a time",
        "analyzed_at_utc": utc_now(), "k_nm_rad": k_gain,
        "b_nms_rad": b_gain, "sample_hz": sample_hz,
        "n_cases": len(cases), "passed": passed,
        "failed": len(cases) - passed, "cases": cases,
        "note": "Pragurile sunt verificari de regresie SIM, nu limite certificate pentru ABB.",
    }
    summary_path = session_path(data_dir, session_id, "suite_analysis", "json")
    _write_report(summary_path, summary)
    summary_csv = session_path(data_dir, session_id, "suite_summary")
    fields = ("time_utc", "case_id", "pair", "tau_a_nm", "onset_s",
              "steady_theta_rad", "expected_theta_rad", "steady_tau_b_cmd_nm",
              "settling_time_2pct_s", "overshoot_pct", "recovery_theta_max_rad",
              "max_abs_theta_other_pairs_rad", "passed", "failed_checks")
    with open(summary_csv, "x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            metrics = case["metrics"]
            writer.writerow({
                "time_utc": event_time_utc[(case["pair"], case["onset_s"])],
                "case_id": case["case_id"], "pair": case["pair"],
                "tau_a_nm": case["tau_a_nm"], "onset_s": case["onset_s"],
                "steady_theta_rad": metrics["steady_theta_rad"],
                "expected_theta_rad": metrics["expected_theta_rad"],
                "steady_tau_b_cmd_nm": metrics["steady_tau_b_cmd_nm"],
                "settling_time_2pct_s": metrics["settling_time_2pct_s"],
                "overshoot_pct": metrics["overshoot_pct"],
                "recovery_theta_max_rad": case["recovery_theta_max_rad"],
                "max_abs_theta_other_pairs_rad":
                    metrics["max_abs_theta_other_pairs_rad"],
                "passed": int(case["passed"]),
                "failed_checks": ";".join(k for k, ok in case["checks"].items()
                                          if not ok),
            })
    book_path = export_session_xlsx(data_dir, session_id)
    figure_path = plot_suite(data_dir, session_id)
    return summary_path, summary_csv, book_path, figure_path, summary


def main():
    parser = argparse.ArgumentParser(description="Protocol si analiza ViPRO SIL")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("reference", help="treapta determinista pe A0")
    run.add_argument("--data-dir", required=True)
    run.add_argument("--tau", type=float, default=0.24)
    run.add_argument("--k", type=float, default=20.0)
    run.add_argument("--b", type=float, default=0.8)
    run.add_argument("--onset", type=float, default=1.0)
    run.add_argument("--release", type=float, default=3.0)
    run.add_argument("--duration", type=float, default=4.0)
    run.add_argument("--sample-hz", type=int, default=100)
    run.add_argument("--cpr", type=int, default=4096)
    run.add_argument("--session-id", default=None)
    suite = sub.add_parser("suite", help="trepte +/- pe A0, A1, A2 (doar SIL)")
    suite.add_argument("--data-dir", required=True)
    suite.add_argument("--k", type=float, default=20.0)
    suite.add_argument("--b", type=float, default=0.8)
    suite.add_argument("--levels", type=float, nargs="+", default=[0.25, 0.5])
    suite.add_argument("--hold-s", type=float, default=1.0)
    suite.add_argument("--rest-s", type=float, default=0.6)
    suite.add_argument("--sample-hz", type=int, default=100)
    suite.add_argument("--cpr", type=int, default=4096)
    suite.add_argument("--session-id", default=None)
    inspect = sub.add_parser("analyze", help="analizeaza o sesiune ROS existenta")
    inspect.add_argument("session_id")
    inspect.add_argument("--data-dir", default="/home/ubuntu/Analiza_Teza/ViPRO/DATE")
    inspect.add_argument("--pair", type=int, default=0)
    inspect.add_argument("--event-index", type=int, default=-1)
    inspect.add_argument("--output", help="cale JSON noua; implicit doar consola")
    plot = sub.add_parser("plot", help="figura PNG din CSV-uri existente")
    plot.add_argument("session_id")
    plot.add_argument("--data-dir", default="/home/ubuntu/Analiza_Teza/ViPRO/DATE")
    plot.add_argument("--pair", type=int, default=0)
    args = parser.parse_args()
    if args.command == "reference":
        report_path, book_path, figure_path, report = run_reference(
            args.data_dir, tau=args.tau, k_gain=args.k, b_gain=args.b,
            onset=args.onset, release=args.release, duration=args.duration,
            sample_hz=args.sample_hz, counts_per_rev=args.cpr,
            session_id=args.session_id)
        print(f"Raport: {report_path}\nExcel: {book_path}\nFigura: {figure_path}")
    elif args.command == "suite":
        summary_path, csv_path, book_path, figure_path, summary = run_suite(
            args.data_dir, k_gain=args.k, b_gain=args.b,
            levels=args.levels, hold_s=args.hold_s, rest_s=args.rest_s,
            sample_hz=args.sample_hz, counts_per_rev=args.cpr,
            session_id=args.session_id)
        print(f"Teste: {summary['passed']}/{summary['n_cases']} trecute")
        print(f"Raport: {summary_path}\nTabel: {csv_path}\n"
              f"Excel: {book_path}\nFigura: {figure_path}")
        if summary["failed"]:
            raise SystemExit(1)
    elif args.command == "plot":
        print(f"Figura: {plot_session(args.data_dir, args.session_id, args.pair)}")
    else:
        report = analyze_session(args.data_dir, args.session_id,
                                 pair=args.pair, event_index=args.event_index)
        if args.output:
            _write_report(args.output, report)
            print(f"Raport: {args.output}")
        else:
            print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
