#!/usr/bin/env python3
"""make_figures_c2.py -- figurile analizei SIL C2 (read-only pe date, fara ROS/retea).
UN singur script, EN, paleta identica cu make_figures_c1_en (Tol). Regenerabil din date.

changelog:
  v1.0 (2026-07-19): F1 delivery vs B la L fix; F2 longest burst per conditie;
    F3 inversarea 64KB (bern/ge x payload); F4 combo in context. received=0 marcat.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_tables_c2 import delivery, bursts, ROOT4, ROOT64, ROOTCOMBO, ROOTC1
import statistics as st

COLOR_CDDS = "#4477AA"
COLOR_ZENOH = "#AA3377"
LABEL = {"cyclonedds": "rmw_cyclonedds", "zenoh": "rmw_zenoh"}
COLOR = {"cyclonedds": COLOR_CDDS, "zenoh": COLOR_ZENOH}
DPI = 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figuri_c2")


def _mean(root, rmw, cond, payload=4096):
    dv, r0, _ = delivery(root, rmw, cond, payload)
    return (st.mean(dv) if dv else float("nan"), st.pstdev(dv) if dv else 0.0, r0)


def fig1():
    Ls = [(5, ["bern_5", "ge_5_3", "ge_5_8"]), (15, ["bern_15", "ge_15_3", "ge_15_8"]),
          (30, ["bern_30", "ge_30_3", "ge_30_8"])]
    B = [1, 3, 8]
    fig, axes = plt.subplots(1, 3, figsize=(8.4, 2.8), sharey=True)
    for ax, (L, conds) in zip(axes, Ls):
        for rmw in ("cyclonedds", "zenoh"):
            ys = [_mean(ROOT4, rmw, c)[0] for c in conds]
            es = [_mean(ROOT4, rmw, c)[1] for c in conds]
            ax.errorbar(B, ys, yerr=es, marker="o", color=COLOR[rmw], label=LABEL[rmw],
                        capsize=2, linewidth=1.3)
        ax.set_title("mean loss L=%d%%" % L, fontsize=9)
        ax.set_xlabel("mean burst length B (packets)")
        ax.set_xticks(B)
        ax.grid(True, ls=":", lw=0.4, alpha=0.6)
    axes[0].set_ylabel("delivery ratio [%]")
    axes[0].legend(loc="lower left", frameon=False, fontsize=7)
    fig.suptitle("F1. Delivery vs burst length at fixed mean loss (SIL, 4 KB)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(os.path.join(OUT, "fig_c2_delivery_vs_B.png"), dpi=DPI)
    plt.close(fig)


def fig2():
    conds = ["bern_5", "ge_5_3", "ge_5_8", "bern_15", "ge_15_3", "ge_15_8",
             "bern_30", "ge_30_3", "ge_30_8"]
    fig, ax = plt.subplots(figsize=(6.6, 2.8))
    x = range(len(conds))
    w = 0.4
    for i, rmw in enumerate(("cyclonedds", "zenoh")):
        vals = [bursts(ROOT4, rmw, c)["longest_max"] for c in conds]
        ax.bar([xi + (i - 0.5) * w for xi in x], [max(1, v) for v in vals], width=w,
               color=COLOR[rmw], edgecolor="black", linewidth=0.4, label=LABEL[rmw])
    ax.set_yscale("log")
    ax.set_ylim(bottom=1)
    ax.set_ylabel("longest failure burst [packets] (log)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(conds, rotation=45, ha="right", fontsize=7)
    ax.legend(loc="upper left", frameon=False, fontsize=7)
    ax.set_title("F2. Longest consecutive failure burst per condition (SIL, 4 KB)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_c2_longest_burst.png"), dpi=DPI)
    plt.close(fig)


def fig3():
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    conds = ["bern_15", "ge_15_8"]
    for ax, rmw in zip(axes, ("cyclonedds", "zenoh")):
        x = range(len(conds))
        w = 0.38
        v4 = [_mean(ROOT4, rmw, c)[0] for c in conds]
        v64 = [_mean(ROOT64, rmw, c, 65536)[0] for c in conds]
        r0_64 = [_mean(ROOT64, rmw, c, 65536)[2] for c in conds]
        ax.bar([xi - w / 2 for xi in x], v4, width=w, color=COLOR[rmw], alpha=0.55,
               edgecolor="black", linewidth=0.4, label="4 KB")
        ax.bar([xi + w / 2 for xi in x], v64, width=w, color=COLOR[rmw],
               edgecolor="black", linewidth=0.4, label="64 KB")
        for xi, r0 in zip(x, r0_64):
            if r0:
                ax.text(xi + w / 2, 2, "recv0=%d" % r0, color="#B00000", fontsize=6,
                        rotation=90, ha="center", va="bottom")
        ax.set_title(LABEL[rmw], fontsize=9)
        ax.set_xticks(list(x))
        ax.set_xticklabels(conds, fontsize=8)
        ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
        ax.legend(loc="upper right", frameon=False, fontsize=7)
    axes[0].set_ylabel("delivery ratio [%]")
    fig.suptitle("F3. 64 KB inversion: Bernoulli vs burst x payload (SIL)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(os.path.join(OUT, "fig_c2_64k_inversion.png"), dpi=DPI)
    plt.close(fig)


def fig4():
    sets = [("combo\nlat+ge_15_8", ROOTCOMBO, "lat200_jit50_ge_15_8", 4096),
            ("ge_15_8\n(4KB)", ROOT4, "ge_15_8", 4096),
            ("bern_15\n(4KB)", ROOT4, "bern_15", 4096),
            ("lat200_jit50\nC1 SIL", ROOTC1, "lat200_jit50", 4096)]
    fig, ax = plt.subplots(figsize=(6.8, 3.0))
    x = range(len(sets))
    w = 0.4
    for i, rmw in enumerate(("cyclonedds", "zenoh")):
        ys, es = [], []
        for _, root, cond, pay in sets:
            m, s, _ = _mean(root, rmw, cond, pay)
            ys.append(m); es.append(s)
        ax.bar([xi + (i - 0.5) * w for xi in x], ys, yerr=es, width=w, color=COLOR[rmw],
               edgecolor="black", linewidth=0.4, label=LABEL[rmw], capsize=2)
    ax.set_ylabel("delivery ratio [%]")
    ax.set_xticks(list(x))
    ax.set_xticklabels([s[0] for s in sets], fontsize=7)
    ax.legend(loc="lower left", frameon=False, fontsize=7)
    ax.set_title("F4. Combo (latency + burst) in context (SIL, 4 KB)", fontsize=10)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_c2_combo_context.png"), dpi=DPI)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    fig1(); fig2(); fig3(); fig4()
    for f in ("fig_c2_delivery_vs_B", "fig_c2_longest_burst", "fig_c2_64k_inversion", "fig_c2_combo_context"):
        print("wrote figuri_c2/%s.png" % f)


if __name__ == "__main__":
    main()
