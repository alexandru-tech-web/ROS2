#!/usr/bin/env python3
"""make_figures_c2.py -- figurile analizei SIL C2 (read-only pe date, fara ROS/retea).
UN script, EN, paleta identica cu make_figures_c1_en (Tol). Regenerabil din date.

changelog:
  v1.0 (2026-07-19): F1 delivery vs B; F2 longest burst; F3 64KB inversion; F4 combo.
  v1.1 (2026-07-19): reguli de casa -- legende DEASUPRA axelor (ncol=2, frameon=False);
    dispersie peste tot cu whiskere taiate la [0,100]; conventie recv0 "n0=k/10" (rosu
    inchis, orizontal, la baza); dimensiuni fizice IEEE (F1/F2 2-col 7.16in, F3/F4 1-col
    3.4in), DPI=300. F2: zero-uri explicite + p95 suprapus + axa secundara in secunde.
    F3: hatch pe 64KB + erori. F4: ordine bern->ge->C1->combo, C1 hatch+eticheta, puncte
    individuale (bimodalitate) pe combo.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_tables_c2 import delivery, bursts, ROOT4, ROOT64, ROOTCOMBO, ROOTC1
import statistics as st

# Paleta EXACTA din make_figures_c1_en.py (Tol):
COLOR_CDDS = "#4477AA"
COLOR_ZENOH = "#AA3377"
COLOR = {"cyclonedds": COLOR_CDDS, "zenoh": COLOR_ZENOH}
LABEL = {"cyclonedds": "rmw_cyclonedds", "zenoh": "rmw_zenoh"}
RECV0 = "#7A0000"
DPI = 300
RMWS = ("cyclonedds", "zenoh")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figuri_c2")
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "legend.fontsize": 7})


def stat(root, rmw, cond, payload=4096):
    dv, r0, _ = delivery(root, rmw, cond, payload)
    m = st.mean(dv) if dv else float("nan")
    s = st.pstdev(dv) if dv else 0.0
    return m, s, r0, dv


def clip_err(m, s, lo=0.0, hi=100.0):
    """yerr asimetric taiat la [lo,hi]."""
    return [[max(0.0, m - max(lo, m - s))], [max(0.0, min(hi, m + s) - m)]]


def legend_above(ax, ncol=2):
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=ncol,
              frameon=False, fontsize=7, handletextpad=0.4, columnspacing=1.2)


def fig1():
    Ls = [(5, ["bern_5", "ge_5_3", "ge_5_8"]), (15, ["bern_15", "ge_15_3", "ge_15_8"]),
          (30, ["bern_30", "ge_30_3", "ge_30_8"])]
    B = [1, 3, 8]
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.5), sharey=True)
    for ax, (L, conds) in zip(axes, Ls):
        for rmw in RMWS:
            ms = [stat(ROOT4, rmw, c) for c in conds]
            ys = [x[0] for x in ms]
            yerr = [[max(0.0, y - max(0.0, y - x[1])) for x, y in zip(ms, ys)],
                    [max(0.0, min(100.0, y + x[1]) - y) for x, y in zip(ms, ys)]]
            ax.errorbar(B, ys, yerr=yerr, marker="o", ms=4, color=COLOR[rmw],
                        label=LABEL[rmw], capsize=2, lw=1.3)
            if L == 30:                       # recv0 pe zenoh B=3, B=8
                for bx, (m, s, r0, _) in zip(B, ms):
                    if rmw == "zenoh" and r0:
                        ax.text(bx, 1, "n0=%d/10" % r0, color=RECV0, fontsize=6,
                                ha="center", va="bottom")
        ax.set_title("mean loss L=%d%%" % L)
        ax.set_xlabel("mean burst length B [pkts]", fontsize=8)
        ax.set_xticks(B)
        ax.set_ylim(-3, 105)
        ax.grid(True, ls=":", lw=0.4, alpha=0.6)
    axes[0].set_ylabel("delivery ratio [%]")
    legend_above(axes[1], ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(os.path.join(OUT, "fig_c2_delivery_vs_B.png"), dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def fig2():
    conds = ["bern_5", "ge_5_3", "ge_5_8", "bern_15", "ge_15_3", "ge_15_8",
             "bern_30", "ge_30_3", "ge_30_8"]
    fig, ax = plt.subplots(figsize=(7.16, 2.5))
    x = list(range(len(conds)))
    w = 0.4
    for i, rmw in enumerate(RMWS):
        maxv = [bursts(ROOT4, rmw, c)["longest_max"] for c in conds]
        p95 = [bursts(ROOT4, rmw, c)["longest_p95"] for c in conds]
        xs = [xi + (i - 0.5) * w for xi in x]
        ax.bar(xs, maxv, width=w, color=COLOR[rmw], edgecolor="black", linewidth=0.4,
               label=LABEL[rmw])
        ax.scatter(xs, p95, marker="D", s=10, color="black", zorder=5,
                   label=("p95 (over N=10)" if i == 0 else None))
        for xi, v in zip(xs, maxv):
            if v == 0:                        # zero = REZULTAT, marcat explicit
                ax.text(xi, 0.15, "0", color=RECV0, fontsize=6, ha="center", va="bottom")
    ax.set_yscale("symlog", linthresh=1)
    ax.set_ylim(0, 300)
    ax.set_ylabel("longest failure burst [pkts]\n(max over N=10 repetitions)", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(conds, rotation=45, ha="right", fontsize=7)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    ax2 = ax.twinx()                          # axa secundara in SECUNDE (20 ms/pachet @50Hz)
    ax2.set_yscale("symlog", linthresh=1 * 0.02)
    ax2.set_ylim(0 * 0.02, 300 * 0.02)
    ax2.set_ylabel("duration [s] (at 50 Hz)", fontsize=7.5)
    legend_above(ax, ncol=3)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(os.path.join(OUT, "fig_c2_longest_burst.png"), dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def fig3():
    conds = ["bern_15", "ge_15_8"]
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    x = list(range(len(conds)))
    w = 0.2
    slots = [("cyclonedds", 4096, -1.5), ("cyclonedds", 65536, -0.5),
             ("zenoh", 4096, 0.5), ("zenoh", 65536, 1.5)]
    for rmw, pay, off in slots:
        ms = [stat(ROOT64 if pay == 65536 else ROOT4, rmw, c, pay) for c in conds]
        ys = [m[0] for m in ms]
        yerr = [[max(0.0, y - max(0.0, y - m[1])) for m, y in zip(ms, ys)],
                [max(0.0, min(100.0, y + m[1]) - y) for m, y in zip(ms, ys)]]
        hatch = "///" if pay == 65536 else None
        lab = "%s %s" % ("cdds" if rmw == "cyclonedds" else "zenoh", "64KB" if pay == 65536 else "4KB")
        xs = [xi + off * w for xi in x]
        ax.bar(xs, ys, width=w, color=COLOR[rmw], edgecolor="black", linewidth=0.4,
               hatch=hatch, label=lab, yerr=yerr, capsize=1.5)
        for xi, c, (m, s, r0, _) in zip(xs, conds, ms):
            if rmw == "zenoh" and pay == 65536 and c == "ge_15_8" and r0:
                ax.text(xi, 1, "n0=%d/10" % r0, color=RECV0, fontsize=6, ha="center", va="bottom")
    ax.set_ylim(-3, 105)
    ax.set_ylabel("delivery ratio [%]")
    ax.set_xticks(x)
    ax.set_xticklabels(conds, fontsize=8)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    legend_above(ax, ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(os.path.join(OUT, "fig_c2_64k_inversion.png"), dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def fig4():
    # ordine: blocurile (bern, ge, C1 latenta) apoi combinatia
    sets = [("bern_15", ROOT4, "bern_15", 4096, None, ""),
            ("ge_15_8", ROOT4, "ge_15_8", 4096, None, ""),
            ("lat200_jit50\n(C1 SIL, 2026-07-01)", ROOTC1, "lat200_jit50", 4096, "xx", ""),
            ("combo\nlat+ge_15_8", ROOTCOMBO, "lat200_jit50_ge_15_8", 4096, None, "pts")]
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    x = list(range(len(sets)))
    w = 0.4
    rng = [0.11, 0.19, 0.29, 0.13, 0.23, 0.07, 0.17, 0.27, 0.05, 0.15]  # jitter determinist
    for i, rmw in enumerate(RMWS):
        ys, yerr, allpts = [], [[], []], []
        for _, root, cond, pay, hatch, over in sets:
            m, s, r0, dv = stat(root, rmw, cond, pay)
            ys.append(m)
            yerr[0].append(max(0.0, m - max(0.0, m - s)))
            yerr[1].append(max(0.0, min(100.0, m + s) - m))
            allpts.append(dv if over == "pts" else None)
        xs = [xi + (i - 0.5) * w for xi in x]
        hatches = [sset[4] for sset in sets]
        bars = ax.bar(xs, ys, width=w, color=COLOR[rmw], edgecolor="black", linewidth=0.4,
                      label=LABEL[rmw], yerr=yerr, capsize=1.5)
        for b, h in zip(bars, hatches):
            if h:
                b.set_hatch(h)
        for xi, dv in zip(xs, allpts):         # puncte individuale pe combo (bimodalitate)
            if dv:
                jx = [xi - 0.14 + rng[k % len(rng)] * 0.28 for k in range(len(dv))]
                ax.scatter(jx, dv, s=6, color="black", alpha=0.7, zorder=6)
    ax.set_ylim(-3, 105)
    ax.set_ylabel("delivery ratio [%]")
    ax.set_xticks(x)
    ax.set_xticklabels([sset[0] for sset in sets], fontsize=6.5)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    legend_above(ax, ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(os.path.join(OUT, "fig_c2_combo_context.png"), dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    fig1(); fig2(); fig3(); fig4()
    for f in ("fig_c2_delivery_vs_B", "fig_c2_longest_burst", "fig_c2_64k_inversion", "fig_c2_combo_context"):
        print("wrote figuri_c2/%s.png" % f)


if __name__ == "__main__":
    main()
