#!/usr/bin/env python3
"""
session_report.py — Raport de sesiune din CSV-urile inregistrate de sensor_recorder.

Nu este nod ROS: e un instrument offline care transforma datele brute din
~/rehab_data/ in metrici standard din literatura de recuperare + un raport PDF
cu grafice — exact materialul pentru figurile de articol si pentru comisie.

Metrici calculate per articulatie / per sesiune:
  * ROM        amplitudinea de miscare atinsa (max - min), in grade;
  * Simetrie   indice stanga/dreapta pe ROM:  SI = 2(L-R)/(L+R) * 100 [%];
  * SPARC      netezimea miscarii (spectral arc length, Balasubramanian 2015);
               valori mai apropiate de 0 = miscare mai lina;
  * Repetari   numarul de cicluri detectate pe profilul de pozitie;
  * Cuplu      |effort| mediu si maxim (daca CSV-ul contine coloane de effort);
  * Urmarire   RMS(q_cmd - q) daca exista si coloane de comanda (sufix _cmd).

Utilizare:
    python3 session_report.py ~/rehab_data/sesiune.csv
    python3 session_report.py sesiune.csv --out ~/rehab_data/rapoarte
    python3 session_report.py sesiune.csv --inspect      # doar listeaza coloanele

Parserul este tolerant la denumiri: pentru fiecare articulatie cauta coloane de
forma <joint>_pos / <joint>_position / <joint>, respectiv _vel/_velocity si
_eff/_effort/_torque; coloana de timp poate fi t / time / stamp / timestamp /
sec (altfel se foloseste prima coloana). Daca formatul vostru difera, rulati
--inspect si redenumiti antetul sau adaugati alias-urile in JOINT_SUFFIXES.
"""

import argparse
import csv as csvmod
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

LEG_JOINTS = [
    "left_hip_joint", "left_knee_joint", "left_ankle_joint",
    "right_hip_joint", "right_knee_joint", "right_ankle_joint",
]
PAIRS = [("left_hip_joint", "right_hip_joint"),
         ("left_knee_joint", "right_knee_joint"),
         ("left_ankle_joint", "right_ankle_joint")]
TIME_CANDIDATES = ["t", "time", "stamp", "timestamp", "sec", "t_unix", "t_s"]
JOINT_SUFFIXES = {
    "pos": ["_pos", "_position", ""],
    "vel": ["_vel", "_velocity"],
    "eff": ["_eff", "_effort", "_torque"],
    "cmd": ["_cmd", "_pos_cmd", "_position_cmd"],
}


# --------------------------------------------------------------------- citire
def read_csv(path):
    with open(path, "r", newline="") as f:
        reader = csvmod.reader(f)
        header = [h.strip() for h in next(reader)]
        rows = [r for r in reader if r and len(r) == len(header)]
    if not rows:
        sys.exit(f"CSV gol sau cu randuri inconsistente: {path}")
    data = {}
    cols = list(zip(*rows))
    for name, col in zip(header, cols):
        try:
            data[name] = np.array([float(x) for x in col])
        except ValueError:
            pass  # coloane non-numerice (etichete) — ignorate la analiza
    return header, data


def find_col(data, joint, kind):
    for suf in JOINT_SUFFIXES[kind]:
        name = joint + suf
        if name in data:
            return name
    return None


def find_time(header, data):
    for c in TIME_CANDIDATES:
        if c in data:
            return c
    for c in header:  # prima coloana numerica drept timp
        if c in data:
            return c
    sys.exit("nu gasesc nicio coloana numerica de timp")


# -------------------------------------------------------------------- metrici
def sparc(speed, fs, fc=20.0, amp_th=0.05):
    """Spectral Arc Length (Balasubramanian et al., 2015), pe profilul de viteza."""
    speed = np.asarray(speed, dtype=float)
    if len(speed) < 8 or fs <= 0 or not np.any(np.abs(speed) > 1e-9):
        return float("nan")
    n = int(2 ** math.ceil(math.log2(len(speed)) + 2))  # zero-padding x4
    f = np.fft.rfftfreq(n, d=1.0 / fs)
    mag = np.abs(np.fft.rfft(np.abs(speed), n))
    mag = mag / mag.max()
    sel = f <= fc
    f, mag = f[sel], mag[sel]
    above = np.where(mag >= amp_th)[0]
    if len(above) > 1:
        f, mag = f[: above[-1] + 1], mag[: above[-1] + 1]
    if len(f) < 2 or f[-1] == f[0]:
        return float("nan")
    df = np.diff(f) / (f[-1] - f[0])
    return float(-np.sum(np.sqrt(df ** 2 + np.diff(mag) ** 2)))


def count_reps(q, min_amp_rad=0.05):
    """Numara ciclurile: treceri sus/jos in jurul medianei, cu histerezis."""
    q = np.asarray(q, dtype=float)
    if q.max() - q.min() < 2 * min_amp_rad:
        return 0
    mid = np.median(q)
    hi, lo = mid + min_amp_rad / 2, mid - min_amp_rad / 2
    state, reps = 0, 0  # 0 = sub prag, 1 = peste prag
    for v in q:
        if state == 0 and v > hi:
            state, reps = 1, reps + 1
        elif state == 1 and v < lo:
            state = 0
    return reps


def analyze(path, out_dir):
    header, data = read_csv(path)
    tcol = find_time(header, data)
    t = data[tcol]
    t = t - t[0]
    if np.nanmax(t) > 1e7:      # timp in nanosecunde -> secunde
        t = t / 1e9
    dt = np.median(np.diff(t)) if len(t) > 1 else 0.01
    fs = 1.0 / dt if dt > 0 else 100.0

    rows, series = [], {}
    for j in LEG_JOINTS:
        cp = find_col(data, j, "pos")
        if cp is None:
            continue
        q = data[cp]
        cv = find_col(data, j, "vel")
        qd = data[cv] if cv else np.gradient(q, t)
        ce = find_col(data, j, "eff")
        eff = data[ce] if ce else None
        cc = find_col(data, j, "cmd")
        rms = (float(np.sqrt(np.mean((data[cc] - q) ** 2))) if cc else float("nan"))

        rom_deg = math.degrees(float(q.max() - q.min()))
        rows.append({
            "joint": j,
            "rom_deg": rom_deg,
            "sparc": sparc(qd, fs),
            "reps": count_reps(q),
            "eff_mean": float(np.mean(np.abs(eff))) if eff is not None else float("nan"),
            "eff_max": float(np.max(np.abs(eff))) if eff is not None else float("nan"),
            "rms_track": rms,
        })
        series[j] = (q, qd, eff)

    if not rows:
        sys.exit("nu am gasit nicio coloana de pozitie pentru articulatiile "
                 f"{LEG_JOINTS}; ruleaza cu --inspect ca sa vezi antetul")

    sym = []
    rom = {r["joint"]: r["rom_deg"] for r in rows}
    for l, r in PAIRS:
        if l in rom and r in rom and (rom[l] + rom[r]) > 1e-6:
            si = 200.0 * (rom[l] - rom[r]) / (rom[l] + rom[r])
            sym.append((l.replace("left_", "").replace("_joint", ""), si))

    write_report(path, out_dir, t, series, rows, sym, fs)
    return rows, sym


# --------------------------------------------------------------------- raport
def write_report(path, out_dir, t, series, rows, sym, fs):
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    pdf_path = os.path.join(out_dir, f"raport_{base}.pdf")

    with PdfPages(pdf_path) as pdf:
        # Pagina 1: pozitii (grade), stanga vs dreapta pe acelasi grafic per pereche
        fig, axes = plt.subplots(3, 1, figsize=(8.27, 11.0), sharex=True)
        for ax, (l, r) in zip(axes, PAIRS):
            for j, style in ((l, "-"), (r, "--")):
                if j in series:
                    ax.plot(t, np.degrees(series[j][0]), style, label=j)
            ax.set_ylabel("unghi [°]")
            ax.legend(loc="upper right", fontsize=8)
            ax.grid(alpha=0.3)
        axes[-1].set_xlabel("timp [s]")
        fig.suptitle(f"Sesiune {base} — pozitii articulare ({fs:.0f} Hz)")
        pdf.savefig(fig); plt.close(fig)

        # Pagina 2: cupluri (daca exista)
        if any(series[j][2] is not None for j in series):
            fig, ax = plt.subplots(figsize=(8.27, 5.5))
            for j in series:
                if series[j][2] is not None:
                    ax.plot(t, series[j][2], label=j, linewidth=0.9)
            ax.set_xlabel("timp [s]"); ax.set_ylabel("cuplu [Nm]")
            ax.legend(fontsize=8); ax.grid(alpha=0.3)
            ax.set_title("Cupluri masurate (effort)")
            pdf.savefig(fig); plt.close(fig)

        # Pagina 3: tabelul de metrici
        fig, ax = plt.subplots(figsize=(8.27, 5.5)); ax.axis("off")
        cols = ["Articulatie", "ROM [°]", "SPARC", "Repetari",
                "|τ| mediu [Nm]", "|τ| max [Nm]", "RMS urmarire [rad]"]
        cells = [[r["joint"], f"{r['rom_deg']:.1f}", f"{r['sparc']:.2f}",
                  str(r["reps"]), f"{r['eff_mean']:.1f}", f"{r['eff_max']:.1f}",
                  f"{r['rms_track']:.3f}"] for r in rows]
        tab = ax.table(cellText=cells, colLabels=cols, loc="center")
        tab.auto_set_font_size(False); tab.set_fontsize(8); tab.scale(1.0, 1.5)
        sym_txt = "  ".join(f"{n}: {v:+.1f}%" for n, v in sym) or "n/a"
        ax.set_title(f"Metrici de sesiune — indice de simetrie (L vs R): {sym_txt}",
                     fontsize=10, pad=20)
        pdf.savefig(fig); plt.close(fig)

    print(f"raport scris: {pdf_path}")
    for r in rows:
        print(f"  {r['joint']:<18} ROM {r['rom_deg']:6.1f}°  SPARC {r['sparc']:6.2f}  "
              f"rep {r['reps']:2d}  |τ|max {r['eff_max']:5.1f} Nm")
    for n, v in sym:
        print(f"  simetrie {n:<8} {v:+.1f}%")


def main():
    ap = argparse.ArgumentParser(description="Raport de sesiune rehab_exo din CSV")
    ap.add_argument("csv", help="fisierul CSV inregistrat de sensor_recorder")
    ap.add_argument("--out", default=os.path.expanduser("~/rehab_data/rapoarte"),
                    help="directorul pentru raportul PDF")
    ap.add_argument("--inspect", action="store_true",
                    help="doar listeaza coloanele detectate si iese")
    args = ap.parse_args()

    if args.inspect:
        header, data = read_csv(args.csv)
        print("coloane in antet:", header)
        print("coloane numerice:", sorted(data.keys()))
        return
    analyze(args.csv, args.out)


if __name__ == "__main__":
    main()
