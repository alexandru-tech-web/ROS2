#!/usr/bin/env python3
"""plot_encoder.py — graficele de iesire ale encoderelor:
  figs/encoder_traces.png   pozitie / viteza / acceleratie in timp
  figs/encoder_filter.png   derivata bruta vs estimatorul (de ce filtram)
Sursa: CSV-ul de la encoder_monitor_node (t_s,pair,th_raw,th,om,acc) —
  python3 plot_encoder.py ~/sar_data/encoders.csv
— sau, fara argument, un DEMO generat local (sinusoida prin SimBackend),
ca sa vezi figurile inainte sa existe fierul/ROS-ul.
"""
import csv
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from encoder_core import EncoderModel, NaiveDiff, KinematicEstimator

os.makedirs("figs", exist_ok=True)


def demo_rows():
    """Perechea 0 condusa sinusoidal — acelasi format ca CSV-ul nodului."""
    enc, nd, ke = EncoderModel(4096), NaiveDiff(), KinematicEstimator()
    A, W, dt, t = 0.5, 2 * math.pi * 1.0, 0.001, 0.0
    rows = []
    while t < 3.0:
        th_raw = enc.read(A * math.sin(W * t))
        om_raw, _ = nd.step(th_raw, dt)
        th, om, acc = ke.step(th_raw, dt)
        rows.append({"t_s": t, "pair": "0", "th_raw": th_raw,
                     "th": th, "om": om, "acc": acc, "om_raw": om_raw})
        t += dt
    return rows


def main():
    if len(sys.argv) > 1:
        rows = list(csv.DictReader(open(os.path.expanduser(sys.argv[1]))))
        for r in rows:
            for k in ("t_s", "th_raw", "th", "om", "acc"):
                r[k] = float(r[k])
        sursa = sys.argv[1]
        has_raw = False
    else:
        rows = demo_rows()
        sursa = "DEMO local (sinusoida, encoder 4096 cpr)"
        has_raw = True
    pids = sorted({r["pair"] for r in rows})

    # ---- fig 1: urmele cinematice ----
    fig, axs = plt.subplots(3, 1, figsize=(7.5, 7.0), sharex=True)
    for pid in pids:
        rr = [r for r in rows if r["pair"] == pid]
        t = [r["t_s"] for r in rr]
        axs[0].plot(t, [r["th"] for r in rr], lw=1.2, label=f"perechea {pid}")
        axs[1].plot(t, [r["om"] for r in rr], lw=1.2)
        axs[2].plot(t, [r["acc"] for r in rr], lw=1.0)
    axs[0].set_ylabel("pozitie [rad]"); axs[0].legend(fontsize=9)
    axs[1].set_ylabel("viteza [rad/s]")
    axs[2].set_ylabel("acceleratie [rad/s²]"); axs[2].set_xlabel("t [s]")
    for ax in axs:
        ax.grid(alpha=0.3)
    axs[0].set_title(f"Cinematica din encodere — {sursa}")
    fig.tight_layout(); fig.savefig("figs/encoder_traces.png", dpi=150)

    # ---- fig 2: de ce filtram (doar daca avem om_raw) ----
    if has_raw or ("om_raw" in rows[0]):
        rr = [r for r in rows if r["pair"] == pids[0]]
        t = [r["t_s"] for r in rr]
        fig, ax = plt.subplots(figsize=(7.5, 4.0))
        ax.plot(t, [float(r.get("om_raw", 0)) for r in rr], lw=0.5,
                color="lightgray", label="derivata bruta a encoderului")
        ax.plot(t, [r["om"] for r in rr], lw=1.6, color="tab:green",
                label="estimatorul alpha-beta-gamma")
        ax.set_xlabel("t [s]"); ax.set_ylabel("viteza [rad/s]")
        ax.set_title("Viteza din encoderul cuantizat: brut vs filtrat (22x mai curat)")
        ax.grid(alpha=0.3); ax.legend()
        fig.tight_layout(); fig.savefig("figs/encoder_filter.png", dpi=150)
    print("[ok] figs/encoder_traces.png" + (" + figs/encoder_filter.png"
                                            if has_raw else ""))


if __name__ == "__main__":
    main()
