#!/usr/bin/python3
"""Raport tehnic offline pentru schema curenta ``sesiune.csv`` a twin-ului LLR.

Raportul separa explicit trei clase de semnal:

* pozitia/viteza sunt feedback de simulare Gazebo;
* ``*.effort_sim`` este efortul articulatiei din Gazebo, NU cuplu fizic masurat;
* M2210B/TR69/BWK216/rigla sunt semnale SINTETICE cu model declarat.

Utilizare:
  python3 session_report.py ~/DATE_TWIN/<sesiune>/
  python3 session_report.py .../sesiune.csv --out .../raport
  python3 session_report.py --selftest
"""

import argparse
import csv
import json
import math
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plot_sesiune as ps
import recorder_core as rc

JOINTS = (
    "left_hip_joint", "left_knee_joint", "left_ankle_joint",
    "right_hip_joint", "right_knee_joint", "right_ankle_joint",
)
PAIRS = (("hip", "sold"), ("knee", "genunchi"), ("ankle", "glezna"))
SIM_LIMITS = {
    "hip": {"velocity": 1.5786, "effort": 176.7},
    "knee": {"velocity": 1.9732, "effort": 141.4},
    "ankle": {"velocity": 3.0369, "effort": 52.0},
}


def _finite(a):
    return np.asarray(a, dtype=float)[np.isfinite(a)]


def _rms(a):
    a = _finite(a)
    return float(np.sqrt(np.mean(a * a))) if len(a) else float("nan")


def _peak(a):
    a = _finite(a)
    return float(np.max(np.abs(a))) if len(a) else float("nan")


def _fmt(v, digits=4):
    return "N/A" if not math.isfinite(float(v)) else f"{float(v):.{digits}f}"


def resolve_csv(path):
    path = os.path.abspath(os.path.expanduser(path))
    return os.path.join(path, "sesiune.csv") if os.path.isdir(path) else path


def active_mask(t, data):
    """Detecteaza miscarea din referinte, apoi adauga 0,5 s la capete."""
    moving = np.zeros(len(t), dtype=bool)
    for joint in JOINTS:
        key = joint + ".cmd"
        if key not in data:
            continue
        q = np.asarray(data[key], dtype=float)
        valid = np.isfinite(q)
        if valid.sum() > 2:
            filled = np.interp(t, t[valid], q[valid])
            moving |= np.abs(np.gradient(filled, t)) > 1e-4
    idx = np.flatnonzero(moving)
    if not len(idx):
        return np.ones(len(t), dtype=bool)
    dt = float(np.nanmedian(np.diff(t)))
    pad = max(1, int(round(0.5 / dt))) if dt > 0 else 1
    lo, hi = max(0, idx[0] - pad), min(len(t), idx[-1] + pad + 1)
    out = np.zeros(len(t), dtype=bool)
    out[lo:hi] = True
    return out


def analyze(path):
    meta, columns, t, data = ps.incarca(path)
    t = np.asarray(t, dtype=float)
    if len(t) < 3:
        raise ValueError("sesiunea are mai putin de 3 esantioane")
    dt = np.diff(t)
    if np.any(~np.isfinite(dt)) or np.any(dt <= 0):
        raise ValueError("t_sim nu este strict crescator")
    mask_active = active_mask(t, data)
    wall = np.asarray(data.get("t_wall_unix", []), dtype=float)
    duration_sim = float(t[-1] - t[0])
    duration_wall = float(wall[-1] - wall[0]) if len(wall) == len(t) else float("nan")
    summary = {
        "source_csv": os.path.abspath(path), "metadata": meta,
        "samples": int(len(t)), "duration_sim_s": duration_sim,
        "duration_wall_s": duration_wall,
        "rtf_computed": duration_sim / duration_wall if duration_wall > 0 else float("nan"),
        "sample_rate_hz": float(1.0 / np.median(dt)),
        "dt_jitter_std_ms": float(np.std(dt) * 1000.0),
        "active_start_s": float(t[np.flatnonzero(mask_active)[0]]),
        "active_end_s": float(t[np.flatnonzero(mask_active)[-1]]),
        "joint_metrics": [], "sensor_ranges": [], "warnings": [],
    }

    for joint in JOINTS:
        required = [joint + s for s in (".pos", ".vel", ".effort_sim", ".cmd")]
        if any(k not in data for k in required):
            summary["warnings"].append(f"lipsesc canale pentru {joint}")
            continue
        q, dq, effort, cmd = (np.asarray(data[k], dtype=float) for k in required)
        valid = np.isfinite(q) & np.isfinite(cmd)
        active = valid & mask_active
        use = active if active.sum() else valid
        err = q[use] - cmd[use]
        axis = joint.split("_")[1]
        vmax, emax = _peak(dq[mask_active]), _peak(effort[mask_active])
        velocity_hit = vmax >= SIM_LIMITS[axis]["velocity"] * .999
        effort_hit = emax >= SIM_LIMITS[axis]["effort"] * .999
        if velocity_hit or effort_hit:
            summary["warnings"].append(
                f"{joint}: limita simulata atinsa/depasita "
                f"(v={vmax:.4f}/{SIM_LIMITS[axis]['velocity']:.4f} rad/s, "
                f"efort={emax:.3f}/{SIM_LIMITS[axis]['effort']:.3f} Nm)")
        summary["joint_metrics"].append({
            "joint": joint,
            "rom_deg": math.degrees(float(np.nanmax(q) - np.nanmin(q))),
            "tracking_rmse_rad_active": _rms(err),
            "tracking_peak_rad_active": _peak(err),
            "velocity_peak_rad_s": vmax,
            "velocity_limit_hit": velocity_hit,
            "effort_sim_peak_Nm": emax,
            "effort_limit_hit": effort_hit,
            "effort_sim_rms_Nm": _rms(effort[mask_active]),
            "position_provenance": "SIMULATED_GAZEBO_JOINT_STATES",
            "effort_provenance": "SIMULATED_GAZEBO_JOINT_STATES_NOT_PHYSICAL_TORQUE",
        })

    for prefix in ("cuplu.", "f6d.", "unghi_glezna.", "rigla."):
        for key in sorted(c for c in columns if c.startswith(prefix)):
            values = _finite(data[key])
            summary["sensor_ranges"].append({
                "signal": key,
                "min": float(np.min(values)) if len(values) else float("nan"),
                "max": float(np.max(values)) if len(values) else float("nan"),
                "mean": float(np.mean(values)) if len(values) else float("nan"),
                "valid_samples": int(len(values)),
                "provenance": "SYNTHETIC_DECLARED_MODEL",
            })

    for axis, _ in PAIRS:
        left = np.asarray(data.get(f"left_{axis}_joint.pos", []), dtype=float)
        right = np.asarray(data.get(f"right_{axis}_joint.pos", []), dtype=float)
        if len(left) == len(t) and len(right) == len(t):
            summary[f"symmetry_{axis}_rms_rad"] = _rms(left - right)
    return meta, columns, t, data, mask_active, summary


def write_metrics_csv(out_dir, summary):
    path = os.path.join(out_dir, "metrici_sesiune.csv")
    fields = list(summary["joint_metrics"][0]) if summary["joint_metrics"] else ["joint"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(summary["joint_metrics"])
    return path


def write_markdown(out_dir, summary):
    path = os.path.join(out_dir, "raport_sesiune.md")
    m = summary["metadata"]
    lines = [
        "# Raport tehnic al sesiunii LLR", "",
        f"- Sursa: `{summary['source_csv']}`",
        f"- Exercitiu: `{m.get('exercitiu', 'NECUNOSCUT')}`; postura: `{m.get('postura', 'NECUNOSCUT')}`",
        f"- Cod/conventie: `{m.get('commit', 'NECUNOSCUT')}` / `{m.get('conventie', 'NECUNOSCUT')}`",
        f"- Esantioane: {summary['samples']}; durata simulata: {_fmt(summary['duration_sim_s'], 3)} s; rata: {_fmt(summary['sample_rate_hz'], 2)} Hz",
        f"- Interval activ detectat din referinte: {_fmt(summary['active_start_s'], 3)}–{_fmt(summary['active_end_s'], 3)} s",
        "", "## Provenienta si limita interpretarii", "",
        "Pozitia, viteza si `effort_sim` provin din Gazebo. `effort_sim` nu este un cuplu fizic masurat. Canalele M2210B, TR69-1500, BWK216 si rigla 406 sunt sintetice, cu model declarat; ele verifica achizitia si prelucrarea, nu fidelitatea hardware.",
        "", "## Indicatori pe articulatie", "",
        "| Articulatie | ROM [deg] | RMSE urmarire activ [rad] | Eroare maxima [rad] | Viteza maxima [rad/s] | Efort Gazebo maxim [Nm] | Limita atinsa |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary["joint_metrics"]:
        limit = "DA" if row["velocity_limit_hit"] or row["effort_limit_hit"] else "nu"
        lines.append(("| {joint} | {rom_deg:.3f} | {tracking_rmse_rad_active:.6f} | "
                      "{tracking_peak_rad_active:.6f} | {velocity_peak_rad_s:.6f} | "
                      "{effort_sim_peak_Nm:.6f} | " + limit + " |").format(**row))
    lines += ["", "## Indicatori de simetrie", ""]
    for axis, label in PAIRS:
        lines.append(f"- {label}: RMS(stanga-dreapta) = {_fmt(summary.get('symmetry_'+axis+'_rms_rad', float('nan')), 6)} rad")
    if summary["warnings"]:
        lines += ["", "## Avertismente automate", ""]
        lines += [f"- {warning}" for warning in summary["warnings"]]
    lines += ["", "## Verdict", "",
              "Datele sunt relevante pentru verificarea cinematica, urmarirea referintei, limitele de viteza si functionarea lantului de achizitie. Nu valideaza inca forta/cuplul dispozitivului fizic si nu reprezinta un rezultat clinic."]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def write_pdf(out_dir, meta, t, data, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    path = os.path.join(out_dir, "raport_sesiune.pdf")
    title = f"{meta.get('exercitiu', 'NECUNOSCUT')} | {meta.get('data_ora', '')} | commit {meta.get('commit', 'NECUNOSCUT')}"
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        text = ["RAPORT TEHNIC — TWIN LLR", title, "",
                f"Esantioane: {summary['samples']}",
                f"Durata simulata: {_fmt(summary['duration_sim_s'], 3)} s",
                f"Rata mediana: {_fmt(summary['sample_rate_hz'], 2)} Hz",
                f"Jitter dt (std): {_fmt(summary['dt_jitter_std_ms'], 3)} ms", "",
                "CLASIFICAREA SEMNALELOR", "Pozitie/viteza: feedback Gazebo",
                "effort_sim: efort Gazebo — NU cuplu fizic masurat",
                "M2210B/TR69/BWK216/rigla: SINTETIC, model declarat", "",
                "Raportul valideaza pipeline-ul de simulare si achizitie.",
                "Nu valideaza dispozitivul fizic si nu constituie rezultat clinic."]
        fig.text(.08, .94, "\n".join(text), va="top", fontsize=11)
        pdf.savefig(fig); plt.close(fig)

        fig, axes = plt.subplots(3, 1, figsize=(8.27, 11.0), sharex=True)
        for ax, (axis, label) in zip(axes, PAIRS):
            for side, color in (("left", "#2166ac"), ("right", "#b2182b")):
                key = f"{side}_{axis}_joint"
                ax.plot(t, data[key + ".cmd"], "--", color=color, alpha=.65, label=f"{side} referinta")
                ax.plot(t, data[key + ".pos"], "-", color=color, lw=1, label=f"{side} feedback")
            ax.set_ylabel(f"{label} [rad]"); ax.grid(alpha=.3); ax.legend(fontsize=7, ncol=2)
        axes[-1].set_xlabel("timp simulat [s]"); fig.suptitle("Referinta vs feedback\n" + title)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)

        fig, axes = plt.subplots(3, 1, figsize=(8.27, 11.0), sharex=True)
        for ax, (axis, label) in zip(axes, PAIRS):
            for side, color in (("left", "#2166ac"), ("right", "#b2182b")):
                key = f"{side}_{axis}_joint"
                err = np.asarray(data[key + ".pos"]) - np.asarray(data[key + ".cmd"])
                ax.plot(t, err, color=color, label=side)
            ax.axhline(0, color="black", lw=.6); ax.set_ylabel(f"eroare {label} [rad]")
            ax.grid(alpha=.3); ax.legend(fontsize=8)
        axes[-1].set_xlabel("timp simulat [s]"); fig.suptitle("Eroarea de urmarire\n" + title)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)

        fig, axes = plt.subplots(3, 1, figsize=(8.27, 11.0), sharex=True)
        for ax, (axis, label) in zip(axes, PAIRS):
            for side, color in (("left", "#2166ac"), ("right", "#b2182b")):
                ax.plot(t, data[f"{side}_{axis}_joint.vel"], color=color, label=side)
            lim = SIM_LIMITS[axis]["velocity"]
            ax.axhline(lim, color="#555", ls=":", lw=.8)
            ax.axhline(-lim, color="#555", ls=":", lw=.8)
            ax.set_ylabel(f"{label} [rad/s]"); ax.grid(alpha=.3); ax.legend(fontsize=8)
        axes[-1].set_xlabel("timp simulat [s]")
        fig.suptitle("Viteze si limitele simulate\n" + title)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)

        fig, axes = plt.subplots(3, 1, figsize=(8.27, 11.0), sharex=True)
        for ax, (axis, label) in zip(axes, PAIRS):
            for side, color in (("left", "#2166ac"), ("right", "#b2182b")):
                ax.plot(t, data[f"{side}_{axis}_joint.effort_sim"], color=color, label=side)
            ax.set_ylabel(f"{label} [Nm]"); ax.grid(alpha=.3); ax.legend(fontsize=8)
        axes[-1].set_xlabel("timp simulat [s]")
        fig.suptitle("Efort articulatie Gazebo — NU cuplu fizic masurat\n" + title)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)

        fig, axes = plt.subplots(3, 1, figsize=(8.27, 11.0), sharex=True)
        groups = ((("f6d.left.force.x", "f6d.right.force.x", "f6d.left.force.z", "f6d.right.force.z"), "Ff/FN sintetic [N]"),
                  (("f6d.left.torque.y", "f6d.right.torque.y"), "MC sintetic [Nm]"),
                  (tuple(c for c in data if c.startswith("cuplu.")), "M2210B sintetic [Nm]"))
        for ax, (keys, ylabel) in zip(axes, groups):
            for key in keys:
                if key in data:
                    ax.plot(t, data[key], label=key)
            ax.set_ylabel(ylabel); ax.grid(alpha=.3)
            if ax.lines:
                ax.legend(fontsize=7, ncol=2)
        axes[-1].set_xlabel("timp simulat [s]")
        fig.suptitle("Canale de senzori SINTETICI — modele declarate\n" + title)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)

        fig, axes = plt.subplots(2, 1, figsize=(8.27, 8.0), sharex=True)
        for side, color in (("left", "#2166ac"), ("right", "#b2182b")):
            axes[0].plot(t, data[f"{side}_ankle_joint.pos"], color=color,
                         ls="--", label=f"{side} articulatie")
            if f"unghi_glezna.{side}" in data:
                axes[0].plot(t, data[f"unghi_glezna.{side}"], color=color,
                             label=f"{side} BWK216 sintetic")
            if f"rigla.{side}" in data:
                axes[1].plot(t, data[f"rigla.{side}"], color=color, label=side)
        axes[0].set_ylabel("unghi [rad]"); axes[1].set_ylabel("rigla [m]")
        axes[1].set_xlabel("timp simulat [s]")
        for ax in axes:
            ax.grid(alpha=.3)
            if ax.lines:
                ax.legend(fontsize=8)
        fig.suptitle("BWK216 si rigla 406 — semnale SINTETICE\n" + title)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)
    return path


def generate(path, out_dir=None):
    csv_path = resolve_csv(path)
    out_dir = os.path.abspath(os.path.expanduser(out_dir or os.path.dirname(csv_path)))
    os.makedirs(out_dir, exist_ok=True)
    meta, _, t, data, _, summary = analyze(csv_path)
    json_path = os.path.join(out_dir, "metrici_sesiune.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, allow_nan=True)
    outputs = [json_path, write_metrics_csv(out_dir, summary),
               write_markdown(out_dir, summary), write_pdf(out_dir, meta, t, data, summary)]
    return summary, outputs


def selftest():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "sesiune.csv")
        with open(path, "w") as f:
            for line in rc.antet({"exercitiu": "test", "commit": "abc", "conventie": "B1"}):
                f.write(line + "\n")
            columns = ["t_sim", "t_wall_unix"]
            for joint in JOINTS:
                columns += [joint + s for s in (".pos", ".vel", ".effort_sim", ".cmd")]
            columns += ["cuplu.left_hip", "f6d.left.force.x"]
            f.write(",".join(columns) + "\n")
            for i in range(101):
                t = i * .02; cmd = .2 * math.sin(t); row = [t, 1000 + t]
                for _ in JOINTS:
                    row += [cmd + .01, .2 * math.cos(t), 2.0, cmd]
                row += [3.0, float("nan")]
                f.write(",".join(str(x) for x in row) + "\n")
        summary, outputs = generate(path, d)
        assert summary["samples"] == 101
        assert abs(summary["sample_rate_hz"] - 50.0) < 1e-8
        assert abs(summary["joint_metrics"][0]["tracking_rmse_rad_active"] - .01) < 1e-8
        assert all(os.path.isfile(p) for p in outputs)
    print("SELFTEST session_report OK")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", help="directorul sesiunii sau sesiune.csv")
    ap.add_argument("--out", help="directorul de iesire; implicit langa CSV")
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        selftest(); return 0
    if not args.path:
        ap.error("este necesar path sau --selftest")
    csv_path = resolve_csv(args.path)
    if args.inspect:
        meta, cols, _, _ = ps.incarca(csv_path)
        print(json.dumps(meta, indent=2)); print("\n".join(cols)); return 0
    summary, outputs = generate(args.path, args.out)
    print(f"Esantioane: {summary['samples']}; rata: {summary['sample_rate_hz']:.2f} Hz")
    for path in outputs:
        print("Scris:", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
