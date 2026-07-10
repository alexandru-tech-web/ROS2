#!/usr/bin/env python3
# make_figures_c1_en.py
# English, publication-style figures for the C1 paper
# (rmw_zenoh vs rmw_cyclonedds under controlled tc/netem degradation).
#
# HONESTY / PROVENANCE
# --------------------
# The EMBEDDED values below are transcribed from the draft's own tables
# (Table II / Table III, "Source: campaign summaries, 2026-07-01",
# SIL N=10, HIL Wi-Fi N=5) and, for the payload figure only, from the
# value labels printed on the campaign chart fig_payload.png. Entries
# marked "displayed" are integers read from chart labels; refresh them
# with exact decimals from the canonical CSV in ~/DATE_CAMPANIE/ before
# submission (see --summary-csv mode below).
#
# ENVIRONMENT
# -----------
# Pure Python + matplotlib. No ROS 2, no network access needed. Verified
# in the delivery container (which has no ROS 2 and no internet); run it
# anywhere, ideally on the machine that holds the canonical campaign CSV.
#
# USAGE
# -----
#   python3 make_figures_c1_en.py
#       -> writes fig_divergence_en.png, fig_loss_sil_hil_en.png,
#          fig_payload_en.png next to the script (embedded values).
#
#   python3 make_figures_c1_en.py --summary-csv campaign_summary.csv
#       -> same figures PLUS fig_rtt_p95_en.png, all from the canonical
#          per-condition summary. Expected columns (one row per
#          env,condition,rmw):
#            env          : SIL | HIL
#            condition    : ideal, loss_5, ... lat200_jit50, lat200_l15
#            rmw          : cyclonedds | zenoh
#            loss_pct     : float, aggregated sample loss in percent
#            rtt_p95_ms   : float, aggregated p95 RTT in ms
#          Adapt COLMAP below if your canonical column names differ.
#
#   python3 make_figures_c1_en.py --rtt-csv rtt_samples.csv --cdf-cond lat200_jit50
#       -> additionally writes fig_cdf_<cond>_en.png from raw samples.
#          Expected columns: env, condition, rmw, rtt_ms (HIL rows used).
#
# ASCII-clean by project convention.
#
# v2 (2026-07-07):
#   - load_summary tolerates an empty rtt_p95_ms cell (received=0 case,
#     e.g. HIL zenoh lat200_l15) instead of crashing on float('');
#     honesty guard: empty p95 is accepted ONLY where loss_pct == 100.
#   - fig_rtt_p95 marks received=0 cells in red instead of plotting a bar.
#   - PAYLOAD_LOSS updated to canonical decimals (audit Pas 2d, 2026-07,
#     recomputed via the campaign pipeline on canonical data).
#
# v2.1 (2026-07-08):
#   - Legends moved ABOVE the axes (outside the plot area) on all
#     figures: fixes legend/panel-tag/value-label collisions that
#     appear with different font metrics across environments (R17).
#     No data changes.
#
# v2.2 (2026-07-08):
#   - Value labels of the two series are offset laterally (+/-2.5 pt)
#     so labels of similar-height adjacent bars no longer touch.
#   - Log-scale figure gets multiplicative headroom (top = max*2.2)
#     so the tallest label stays inside the axes; linear panels get
#     ylim 112. No data changes.
#
# v2.3 (2026-07-09):
#   - Three architecture diagrams (Fig. 1 RMW abstraction, Fig. 2 SIL,
#     Fig. 3 HIL) redrawn in English, technical tone, same visual
#     style as the data figures. Pure matplotlib boxes/arrows; no
#     campaign data involved.

import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# Style (academic: no in-figure titles, captions live in the paper)
# ----------------------------------------------------------------------
COLOR_CDDS = "#4477AA"   # Tol bright blue  - rmw_cyclonedds
COLOR_ZENOH = "#AA3377"  # Tol bright purple - rmw_zenoh
LABEL_CDDS = "rmw_cyclonedds"
LABEL_ZENOH = "rmw_zenoh"
DPI = 300

plt.rcParams.update({
    "font.size": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.grid": True,
    "grid.linestyle": ":",
    "grid.linewidth": 0.5,
    "grid.alpha": 0.6,
    "axes.axisbelow": True,
})

CONDITIONS = ["ideal", "loss_5", "loss_15", "loss_20",
              "loss_25", "loss_30", "lat200_jit50", "lat200_l15"]

# ----------------------------------------------------------------------
# EMBEDDED DATA (transcribed; see provenance note in the header)
# ----------------------------------------------------------------------
# Sample loss [%], 4 KB payload. Source: draft Table II (2026-07-01).
LOSS = {
    ("SIL", "cdds"):  [0.0, 0.0,  1.4,  7.7, 26.5, 41.0,  1.8,  36.0],
    ("SIL", "zenoh"): [0.0, 0.0,  8.5, 16.9, 34.1, 57.8,  1.3,  20.8],
    ("HIL", "cdds"):  [0.0, 0.0, 20.8, 53.5, 70.4, 80.5, 14.7,  72.4],
    ("HIL", "zenoh"): [0.0, 0.0, 61.6, 93.7, 98.8, 99.2, 96.3, 100.0],
}

# Payload sensitivity, sample loss [%]. 4 KB values from Table II;
# 64 B / 64 KB values are "displayed" chart labels -> refresh decimals
# from the canonical CSV before submission.
PAYLOADS = ["64 B", "4 KB", "64 KB"]
PAYLOAD_LOSS = {
    ("ideal",   "cdds"):  [0.0,  0.0,  0.0],
    ("ideal",   "zenoh"): [0.0,  0.0, 57.8],   # canonical decimals:
    ("loss_15", "cdds"):  [0.8, 20.8, 99.2],   # audit Pas 2d (2026-07),
    ("loss_15", "zenoh"): [39.5, 61.6, 98.3],  # recomputed via pipeline
}


def _bar_pair(ax, xlabels, vals_cdds, vals_zenoh, ylim=(0, 112),
              value_fmt="{:.1f}"):
    n = len(xlabels)
    x = range(n)
    w = 0.38
    plot_c = [0 if v is None else v for v in vals_cdds]
    plot_z = [0 if v is None else v for v in vals_zenoh]
    b1 = ax.bar([i - w / 2 for i in x], plot_c, width=w,
                color=COLOR_CDDS, edgecolor="black", linewidth=0.4,
                label=LABEL_CDDS)
    b2 = ax.bar([i + w / 2 for i in x], plot_z, width=w,
                color=COLOR_ZENOH, edgecolor="black", linewidth=0.4,
                label=LABEL_ZENOH)
    for bars, vals, dx in ((b1, vals_cdds, -2.5), (b2, vals_zenoh, 2.5)):
        for rect, v in zip(bars, vals):
            if v is None:
                continue  # received=0: no bar label; caller marks it
            ax.annotate(value_fmt.format(v),
                        xy=(rect.get_x() + rect.get_width() / 2, v),
                        xytext=(dx, 2.0), textcoords="offset points",
                        ha="center", va="bottom", fontsize=6)
    ax.set_xticks(list(x))
    ax.set_xticklabels(xlabels, rotation=30, ha="right")
    ax.set_ylim(*ylim)
    return b1, b2


def _legend_top(fig, ax, top):
    """Legend above the axes, outside the plot area (collision-proof)."""
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, top))


def fig_divergence(outdir):
    """Grouped bars: sample loss at lat200_jit50, SIL vs HIL."""
    i = CONDITIONS.index("lat200_jit50")
    sil = [LOSS[("SIL", "cdds")][i], LOSS[("SIL", "zenoh")][i]]
    hil = [LOSS[("HIL", "cdds")][i], LOSS[("HIL", "zenoh")][i]]
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    _bar_pair(ax, ["SIL (loopback)", "HIL (real Wi-Fi)"],
              [sil[0], hil[0]], [sil[1], hil[1]])
    ax.set_ylabel("Sample loss [%]")
    _legend_top(fig, ax, top=0.90)
    path = os.path.join(outdir, "fig_divergence_en.png")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def fig_loss_sil_hil(outdir, loss=None):
    """Two stacked panels (SIL top, HIL bottom), all conditions."""
    loss = loss or LOSS
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 4.8), sharex=True)
    for ax, env in zip(axes, ("SIL", "HIL")):
        _bar_pair(ax, CONDITIONS,
                  loss[(env, "cdds")], loss[(env, "zenoh")],
                  value_fmt="{:.0f}")
        ax.set_ylabel("Sample loss [%]")
        ax.text(0.02, 0.90,
                "SIL (loopback)" if env == "SIL" else "HIL (real Wi-Fi)",
                transform=ax.transAxes, fontsize=8, fontweight="bold")
    axes[1].set_xlabel("Network condition (tc netem)")
    _legend_top(fig, axes[0], top=0.95)
    path = os.path.join(outdir, "fig_loss_sil_hil_en.png")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def fig_payload(outdir):
    """Two stacked panels: payload effect under ideal and loss_15 (HIL)."""
    fig, axes = plt.subplots(2, 1, figsize=(3.4, 4.2), sharex=True)
    for ax, cond, tag in zip(axes, ("ideal", "loss_15"),
                             ("ideal", "15% injected loss")):
        _bar_pair(ax, PAYLOADS,
                  PAYLOAD_LOSS[(cond, "cdds")],
                  PAYLOAD_LOSS[(cond, "zenoh")],
                  value_fmt="{:.0f}")
        ax.set_ylabel("Sample loss [%]")
        ax.text(0.02, 0.90, tag, transform=ax.transAxes,
                fontsize=8, fontweight="bold")
    axes[1].set_xlabel("Payload size")
    _legend_top(fig, axes[0], top=0.94)
    path = os.path.join(outdir, "fig_payload_en.png")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


# ----------------------------------------------------------------------
# Architecture diagrams (Fig. 1-3) -- English, technical tone
# ----------------------------------------------------------------------
import matplotlib.patches as mpatches

BOX_APP = "#E8E8F8"   # lavender: application-side layers
BOX_RMW = "#FBEEDB"   # sand: rmw layer
BOX_NET = "#EDEDED"   # grey: network interface layer
BOX_CD  = "#DFF0DF"   # green tint: cyclonedds leaf
BOX_ZN  = "#F4E3EC"   # purple tint: zenoh leaf
EDGE = "#333333"


def _box(ax, cx, cy, w, h, lines, fc, fs=7, mono=False):
    r = mpatches.FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.015",
                                linewidth=0.8, edgecolor=EDGE, facecolor=fc)
    ax.add_patch(r)
    fam = "monospace" if mono else None
    ax.text(cx, cy, "\n".join(lines), ha="center", va="center",
            fontsize=fs, family=fam)
    return r


def _arrow(ax, x0, y0, x1, y1, style="-|>", lw=0.9):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, lw=lw, color=EDGE,
                                shrinkA=1, shrinkB=1))


def fig_rmw_stack(outdir):
    """Fig. 1: the RMW abstraction stack with the two rmw leaves."""
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ys = [0.92, 0.74, 0.56, 0.38]
    labels = [
        ("Application code (ROS 2 node)", BOX_APP, False),
        ("rclcpp / rclpy (client library)", BOX_APP, False),
        ("rcl (language-agnostic client interface)", BOX_APP, False),
        ("rmw (selected via RMW_IMPLEMENTATION)", BOX_RMW, False),
    ]
    for y, (txt, fc, mono) in zip(ys, labels):
        _box(ax, 0.5, y, 0.78, 0.115, [txt], fc, fs=7, mono=mono)
    for ya, yb in zip(ys[:-1], ys[1:]):
        _arrow(ax, 0.5, ya - 0.058, 0.5, yb + 0.058)
    _box(ax, 0.24, 0.16, 0.42, 0.115, ["rmw_cyclonedds_cpp"], BOX_CD,
         fs=7, mono=True)
    _box(ax, 0.76, 0.16, 0.42, 0.115, ["rmw_zenoh_cpp"], BOX_ZN,
         fs=7, mono=True)
    _arrow(ax, 0.40, ys[3] - 0.058, 0.24, 0.16 + 0.058)
    _arrow(ax, 0.60, ys[3] - 0.058, 0.76, 0.16 + 0.058)
    ax.text(0.24, 0.045, "DDS/RTPS: peer-to-peer UDP,\nmulticast discovery",
            ha="center", va="center", fontsize=5.8)
    ax.text(0.76, 0.045, "Zenoh: brokered TCP,\nrouter + gossip scouting",
            ha="center", va="center", fontsize=5.8)
    fig.tight_layout(pad=0.2)
    path = os.path.join(outdir, "fig_rmw_stack_en.png")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def fig_sil_arch(outdir):
    """Fig. 2: SIL architecture -- single host, loopback, netem on lo."""
    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    host = mpatches.FancyBboxPatch((0.03, 0.05), 0.94, 0.80,
                                   boxstyle="round,pad=0.008",
                                   linewidth=0.8, edgecolor=EDGE,
                                   facecolor="none", linestyle="--")
    ax.add_patch(host)
    ax.text(0.5, 0.93, "SIL -- single host (loopback)", ha="center",
            va="center", fontsize=8, fontweight="bold")
    _box(ax, 0.27, 0.72, 0.40, 0.155,
         ["Client", "bench_client.py"], BOX_APP, fs=6.5, mono=False)
    _box(ax, 0.73, 0.72, 0.40, 0.155,
         ["Echo server", "bench_echo_server.py"], BOX_APP, fs=6.5)
    _box(ax, 0.5, 0.45, 0.80, 0.13,
         ["RMW: rmw_cyclonedds_cpp | rmw_zenoh_cpp (+ router)"],
         BOX_RMW, fs=6.5)
    _box(ax, 0.5, 0.18, 0.86, 0.13,
         ["loopback interface (lo)  +  tc netem (delay / jitter / loss)"],
         BOX_NET, fs=6.5)
    _arrow(ax, 0.27, 0.72 - 0.078, 0.40, 0.45 + 0.065)
    _arrow(ax, 0.73, 0.72 - 0.078, 0.60, 0.45 + 0.065)
    _arrow(ax, 0.5, 0.45 - 0.065, 0.5, 0.18 + 0.065, style="<|-|>")
    fig.tight_layout(pad=0.2)
    path = os.path.join(outdir, "fig_sil_arch_en.png")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def fig_hil_arch(outdir):
    """Fig. 3: HIL architecture -- two hosts over real Wi-Fi."""
    fig, ax = plt.subplots(figsize=(3.5, 1.85))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.5, 0.95,
            "HIL -- two hosts, real Wi-Fi (symmetric netem on both interfaces)",
            ha="center", va="center", fontsize=6.8, fontweight="bold")
    for x0, tag in ((0.03, "M1 (laptop)"), (0.53, "M2 (Raspberry Pi 4)")):
        r = mpatches.FancyBboxPatch((x0, 0.06), 0.44, 0.76,
                                    boxstyle="round,pad=0.006",
                                    linewidth=0.8, edgecolor=EDGE,
                                    facecolor="none", linestyle="--")
        ax.add_patch(r)
        ax.text(x0 + 0.22, 0.87, tag, ha="center", va="center",
                fontsize=6.5, fontweight="bold")
    _box(ax, 0.25, 0.70, 0.36, 0.16, ["Client", "bench_client.py"],
         BOX_APP, fs=6)
    _box(ax, 0.75, 0.70, 0.36, 0.16, ["Echo server", "bench_echo_server.py"],
         BOX_CD, fs=6)
    _box(ax, 0.25, 0.44, 0.40, 0.13, ["RMW: CDDS | Zenoh (+ router)"],
         BOX_RMW, fs=6)
    _box(ax, 0.75, 0.44, 0.40, 0.13, ["RMW: CDDS | Zenoh (+ router)"],
         BOX_RMW, fs=6)
    _box(ax, 0.25, 0.18, 0.34, 0.13, ["wlp4s0 + tc netem"], BOX_NET, fs=6)
    _box(ax, 0.75, 0.18, 0.34, 0.13, ["wlan0 + tc netem"], BOX_NET, fs=6)
    for x in (0.25, 0.75):
        _arrow(ax, x, 0.70 - 0.08, x, 0.44 + 0.065)
        _arrow(ax, x, 0.44 - 0.065, x, 0.18 + 0.065)
    _arrow(ax, 0.25 + 0.17, 0.18, 0.75 - 0.17, 0.18, style="<|-|>")
    ax.text(0.5, 0.085,
            "real Wi-Fi (consumer AP) -- explicit unicast connect between routers",
            ha="center", va="center", fontsize=5.6)
    fig.tight_layout(pad=0.2)
    path = os.path.join(outdir, "fig_hil_arch_en.png")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


# ----------------------------------------------------------------------
# Canonical-CSV modes (run locally on the machine with DATE_CAMPANIE)
# ----------------------------------------------------------------------
COLMAP = {"env": "env", "condition": "condition", "rmw": "rmw",
          "loss_pct": "loss_pct", "rtt_p95_ms": "rtt_p95_ms",
          "rtt_ms": "rtt_ms"}
RMW_KEY = {"cyclonedds": "cdds", "rmw_cyclonedds": "cdds",
           "rmw_cyclonedds_cpp": "cdds", "cdds": "cdds",
           "zenoh": "zenoh", "rmw_zenoh": "zenoh",
           "rmw_zenoh_cpp": "zenoh"}


def _opt_float(raw):
    """Empty / NA cells -> None (legitimate only for received=0)."""
    v = (raw or "").strip()
    if v.lower() in ("", "na", "nan", "none", "null", "-"):
        return None
    return float(v)


def load_summary(path):
    loss, p95 = {}, {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            env = row[COLMAP["env"]].strip().upper()
            cond = row[COLMAP["condition"]].strip()
            rmw = RMW_KEY[row[COLMAP["rmw"]].strip().lower()]
            if cond not in CONDITIONS:
                continue
            i = CONDITIONS.index(cond)
            loss.setdefault((env, rmw), [None] * len(CONDITIONS))
            p95.setdefault((env, rmw), [None] * len(CONDITIONS))
            loss[(env, rmw)][i] = float(row[COLMAP["loss_pct"]])
            p95[(env, rmw)][i] = _opt_float(row[COLMAP["rtt_p95_ms"]])
    for key, vals in loss.items():
        missing = [CONDITIONS[i] for i, v in enumerate(vals) if v is None]
        if missing:
            sys.exit("summary CSV incomplete for %s: missing %s"
                     % (key, ", ".join(missing)))
    # honesty guard: a missing p95 is only legitimate when nothing was
    # received (loss == 100%); otherwise the CSV is inconsistent.
    for key, vals in p95.items():
        for i, v in enumerate(vals):
            if v is None and loss[key][i] < 100.0:
                sys.exit("p95 missing but loss=%.1f%% (<100) for %s @ %s"
                         % (loss[key][i], key, CONDITIONS[i]))
    return loss, p95


def fig_rtt_p95(outdir, p95):
    """HIL p95 RTT per condition, log scale (canonical data required).
    Cells with p95=None (received=0) get a red marker instead of a bar."""
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    vc, vz = p95[("HIL", "cdds")], p95[("HIL", "zenoh")]
    _bar_pair(ax, CONDITIONS, vc, vz, ylim=(1, None), value_fmt="{:.0f}")
    ax.set_yscale("log")
    vmax = max(v for vals in (vc, vz) for v in vals if v is not None)
    ax.set_ylim(1, vmax * 2.2)
    for vals, dx in ((vc, -0.19), (vz, +0.19)):
        for i, v in enumerate(vals):
            if v is None:
                ax.text(i + dx, 1.4, "received=0", color="#B00000",
                        fontsize=5.5, rotation=90, ha="center",
                        va="bottom")
    ax.set_ylabel("RTT p95 [ms] (log scale)")
    ax.set_xlabel("Network condition (tc netem)")
    _legend_top(fig, ax, top=0.90)
    path = os.path.join(outdir, "fig_rtt_p95_en.png")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def fig_cdf(outdir, rtt_csv, cond):
    """Empirical RTT CDF for one condition (HIL), from raw samples."""
    samples = {"cdds": [], "zenoh": []}
    with open(rtt_csv, newline="") as f:
        for row in csv.DictReader(f):
            if row[COLMAP["condition"]].strip() != cond:
                continue
            if row[COLMAP["env"]].strip().upper() != "HIL":
                continue
            rmw = RMW_KEY[row[COLMAP["rmw"]].strip().lower()]
            samples[rmw].append(float(row[COLMAP["rtt_ms"]]))
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    for key, color, label in (("cdds", COLOR_CDDS, LABEL_CDDS),
                              ("zenoh", COLOR_ZENOH, LABEL_ZENOH)):
        vals = sorted(samples[key])
        if not vals:
            ax.text(0.55, 0.15, "%s: no samples received" % label,
                    transform=ax.transAxes, fontsize=7, color=color)
            continue
        n = len(vals)
        ax.plot(vals, [(i + 1) / n for i in range(n)],
                color=color, label=label, linewidth=1.2)
    ax.set_xlabel("RTT [ms]")
    ax.set_ylabel("Empirical CDF")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    path = os.path.join(outdir, "fig_cdf_%s_en.png" % cond)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--summary-csv", default=None,
                    help="canonical per-condition summary (see header)")
    ap.add_argument("--rtt-csv", default=None,
                    help="raw RTT samples CSV for the CDF figure")
    ap.add_argument("--cdf-cond", default="lat200_jit50")
    ap.add_argument("--arch", action="store_true",
                    help="also draw the three architecture diagrams")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    made = []
    if args.summary_csv:
        loss, p95 = load_summary(args.summary_csv)
        made.append(fig_loss_sil_hil(args.outdir, loss=loss))
        made.append(fig_rtt_p95(args.outdir, p95))
        # divergence + payload still use embedded values unless you
        # extend load_summary; loss panel above already uses canonical.
        made.append(fig_divergence(args.outdir))
        made.append(fig_payload(args.outdir))
    else:
        made.append(fig_divergence(args.outdir))
        made.append(fig_loss_sil_hil(args.outdir))
        made.append(fig_payload(args.outdir))

    if args.arch:
        made.append(fig_rmw_stack(args.outdir))
        made.append(fig_sil_arch(args.outdir))
        made.append(fig_hil_arch(args.outdir))

    if args.rtt_csv:
        made.append(fig_cdf(args.outdir, args.rtt_csv, args.cdf_cond))

    for p in made:
        print("wrote", p)


if __name__ == "__main__":
    main()
