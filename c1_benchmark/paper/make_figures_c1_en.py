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
    ("ideal",   "zenoh"): [0.0,  0.0, 58.0],   # 58: displayed + stated in Sec. 4.1
    ("loss_15", "cdds"):  [1.0, 20.8, 99.0],   # 1, 99: displayed
    ("loss_15", "zenoh"): [39.0, 61.6, 98.0],  # 39, 98: displayed
}


def _bar_pair(ax, xlabels, vals_cdds, vals_zenoh, ylim=(0, 108),
              value_fmt="{:.1f}"):
    n = len(xlabels)
    x = range(n)
    w = 0.38
    b1 = ax.bar([i - w / 2 for i in x], vals_cdds, width=w,
                color=COLOR_CDDS, edgecolor="black", linewidth=0.4,
                label=LABEL_CDDS)
    b2 = ax.bar([i + w / 2 for i in x], vals_zenoh, width=w,
                color=COLOR_ZENOH, edgecolor="black", linewidth=0.4,
                label=LABEL_ZENOH)
    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            ax.annotate(value_fmt.format(h),
                        xy=(rect.get_x() + rect.get_width() / 2, h),
                        xytext=(0, 1.5), textcoords="offset points",
                        ha="center", va="bottom", fontsize=6)
    ax.set_xticks(list(x))
    ax.set_xticklabels(xlabels, rotation=30, ha="right")
    ax.set_ylim(*ylim)
    return b1, b2


def fig_divergence(outdir):
    """Grouped bars: sample loss at lat200_jit50, SIL vs HIL."""
    i = CONDITIONS.index("lat200_jit50")
    sil = [LOSS[("SIL", "cdds")][i], LOSS[("SIL", "zenoh")][i]]
    hil = [LOSS[("HIL", "cdds")][i], LOSS[("HIL", "zenoh")][i]]
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    _bar_pair(ax, ["SIL (loopback)", "HIL (real Wi-Fi)"],
              [sil[0], hil[0]], [sil[1], hil[1]])
    ax.set_ylabel("Sample loss [%]")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
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
    axes[0].legend(loc="upper center", frameon=False, ncol=2)
    axes[1].set_xlabel("Network condition (tc netem)")
    fig.tight_layout()
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
    axes[0].legend(loc="upper center", frameon=False, ncol=2)
    axes[1].set_xlabel("Payload size")
    fig.tight_layout()
    path = os.path.join(outdir, "fig_payload_en.png")
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
            p95[(env, rmw)][i] = float(row[COLMAP["rtt_p95_ms"]])
    for key, vals in loss.items():
        missing = [CONDITIONS[i] for i, v in enumerate(vals) if v is None]
        if missing:
            sys.exit("summary CSV incomplete for %s: missing %s"
                     % (key, ", ".join(missing)))
    return loss, p95


def fig_rtt_p95(outdir, p95):
    """HIL p95 RTT per condition, log scale (canonical data required)."""
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    _bar_pair(ax, CONDITIONS, p95[("HIL", "cdds")], p95[("HIL", "zenoh")],
              ylim=(1, None), value_fmt="{:.0f}")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1)
    ax.set_ylabel("RTT p95 [ms] (log scale)")
    ax.set_xlabel("Network condition (tc netem)")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
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

    if args.rtt_csv:
        made.append(fig_cdf(args.outdir, args.rtt_csv, args.cdf_cond))

    for p in made:
        print("wrote", p)


if __name__ == "__main__":
    main()
