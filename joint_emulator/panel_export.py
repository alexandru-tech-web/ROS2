#!/usr/bin/env python3
"""Exporta punctele afisate de HMI, fara dependente ROS sau Matplotlib."""
import csv
import os


SIGNALS = (
    ("th", "theta_rad"),
    ("om", "omega_rad_s"),
    ("th_a", "theta_a_rad"),
    ("th_b", "theta_b_rad"),
    ("om_a", "omega_a_rad_s"),
    ("om_b", "omega_b_rad_s"),
    ("delta_th", "delta_theta_a_b_rad"),
    ("om_raw", "omega_raw_rad_s"),
    ("acc", "acc_rad_s2"),
    ("tau_a_cmd", "tau_a_cmd_nm"),
    ("tau_b", "tau_b_cmd_nm"),
    ("k_ef", "k_eff_nm_rad"),
    ("win_energy", "win_energy_j"),
)
FIELDS = ("time_s", "pair") + tuple(column for _, column in SIGNALS)


def graph_rows(buffers):
    """Aliniaza dupa timestamp; celulele lipsa raman goale, nu interpolate."""
    merged = {}
    for pair, series in enumerate(buffers):
        for signal, column in SIGNALS:
            for t, value in series.get(signal, ()):
                key = (float(t), pair)
                row = merged.setdefault(key, {"time_s": key[0], "pair": pair})
                row[column] = float(value)
    return [merged[key] for key in sorted(merged)]


def export_panel_csv(buffers, path):
    """Salveaza exact fereastra de date vizibila; nu suprascrie fisiere."""
    rows = graph_rows(buffers)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
