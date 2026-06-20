#!/usr/bin/env python3
"""analyze_campaign.py — din arborele results_c1/ produce TABELUL si
FIGURILE articolului A1:

  campaign_summary.csv        rand per (rmw, conditie): transport + misiune
  fig_transport.png           RTT p95 per conditie, grupat pe RMW (+pierderea
                              masurata ca etichete) — Fig. 2 din articol
  fig_mission.png             timpul de finalizare a misiunii (plafon hasurat)
                              + acoperirea finala — Fig. 3 din articol
  fig_cdf.png                 CDF-ul RTT brut la o conditie aleasa — Fig. 4

Autotestul (ruleaza AICI, fara ROS): --selftest fabrica un arbore sintetic
cu schema exacta a campaniei si trece prin tot fluxul -> valideaza analiza
inainte de a exista date reale.

  python3 analyze_campaign.py results_c1/
  python3 analyze_campaign.py --selftest
"""
import argparse
import csv
import glob
import json
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, mission_done_time, rtt_stats

COND_ORDER = [c["name"] for c in CONDITIONS]
COL = {"cyclonedds": "#2E73CC", "zenoh": "#9b59b6", "fastdds": "#2E8B57"}
MISSION_CAP = 170.0
REF_PAYLOAD = 4096                      # sarcina utila de referinta in figuri


def collect(root):
    """{(rmw, cond): {"t": [p95...], "loss": [...], "done": [t|None],
                      "cov": [...], "raw": [rtts of REF payload]}}"""
    out = {}
    for sj in glob.glob(os.path.join(root, "*", "*", "rep*",
                                     f"transport_p{REF_PAYLOAD}_summary.json")):
        parts = sj.split(os.sep)
        rmw, cond = parts[-4], parts[-3]
        d = json.load(open(sj))
        e = out.setdefault((rmw, cond), dict(t=[], loss=[], done=[],
                                             cov=[], raw=[]))
        if d.get("p95_ms") is not None:
            e["t"].append(d["p95_ms"])
        e["loss"].append(d.get("loss", 0.0))
        raw = sj.replace("_summary.json", ".csv")
        if os.path.exists(raw):
            with open(raw) as f:
                e["raw"] += [float(r["rtt_ms"]) for r in csv.DictReader(f)]
    for mm in glob.glob(os.path.join(root, "*", "*", "rep*",
                                     "mission_metrics.csv")):
        parts = mm.split(os.sep)
        rmw, cond = parts[-4], parts[-3]
        e = out.setdefault((rmw, cond), dict(t=[], loss=[], done=[],
                                             cov=[], raw=[]))
        txt = open(mm).read()
        e["done"].append(mission_done_time(txt))
        try:
            e["cov"].append(float(txt.strip().splitlines()[-1].split(",")[1]))
        except (IndexError, ValueError):
            pass
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def analyze(root, outdir):
    data = collect(root)
    rmws = sorted({k[0] for k in data})
    conds = [c for c in COND_ORDER if any(k[1] == c for k in data)]
    os.makedirs(outdir, exist_ok=True)

    with open(os.path.join(outdir, "campaign_summary.csv"), "w") as f:
        f.write("rmw,condition,rtt_p95_ms,transport_loss,mission_time_s,"
                "mission_completed,coverage_end\n")
        for (rmw, cond), e in sorted(data.items()):
            done = [d for d in e["done"] if d is not None]
            f.write(f"{rmw},{cond},"
                    f"{mean(e['t']) or '':},{mean(e['loss']) or 0:.3f},"
                    f"{mean(done) or '':},"
                    f"{len(done)}/{len(e['done']) or 0},"
                    f"{mean(e['cov']) or '':}\n")

    # Fig. 2 — transportul
    fig, ax = plt.subplots(figsize=(9, 4.2))
    w = 0.8 / max(1, len(rmws))
    for j, rmw in enumerate(rmws):
        xs, ys, ls = [], [], []
        for i, c in enumerate(conds):
            e = data.get((rmw, c), {})
            xs.append(i + j * w)
            ys.append(mean(e.get("t", [])) or 0)
            ls.append(mean(e.get("loss", [])) or 0)
        b = ax.bar(xs, ys, width=w, label=rmw, color=COL.get(rmw, "#888"))
        for r, l in zip(b, ls):
            ax.text(r.get_x() + r.get_width() / 2, r.get_height(),
                    f"{100 * l:.0f}%", ha="center", va="bottom", fontsize=8)
    ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(conds))],
                  conds, rotation=15)
    ax.set_ylabel(f"RTT p95 [ms] (payload {REF_PAYLOAD} B)")
    ax.set_title("Transport sub degradare reala (tc netem) — "
                 "etichete: pierderea masurata")
    if ax.get_legend_handles_labels()[0]:
        ax.legend(title="RMW")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig_transport.png"), dpi=140)

    # Fig. 3 — misiunea
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for j, rmw in enumerate(rmws):
        xs, ys, hatch = [], [], []
        for i, c in enumerate(conds):
            e = data.get((rmw, c), {})
            done = [d for d in e.get("done", []) if d is not None]
            xs.append(i + j * w)
            ys.append(mean(done) if done else MISSION_CAP)
            hatch.append(not done and bool(e.get("done")))
        bars = ax.bar(xs, ys, width=w, label=rmw, color=COL.get(rmw, "#888"))
        for r, h in zip(bars, hatch):
            if h:
                r.set_hatch("//")
                r.set_alpha(0.6)
    ax.axhline(MISSION_CAP, ls=":", color="#888")
    ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(conds))],
                  conds, rotation=15)
    ax.set_ylabel("timp de finalizare a misiunii [s]")
    ax.set_title("Impactul la nivel de misiune (hasurat = plafon, "
                 "misiune neterminata)")
    if ax.get_legend_handles_labels()[0]:
        ax.legend(title="RMW")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig_mission.png"), dpi=140)

    # Fig. 4 — CDF la conditia cea mai severa cu date
    pick = next((c for c in reversed(conds)
                 if any(data.get((r, c), {}).get("raw") for r in rmws)), None)
    if pick:
        fig, ax = plt.subplots(figsize=(7, 4))
        for rmw in rmws:
            raw = sorted(data.get((rmw, pick), {}).get("raw", []))
            if raw:
                ax.plot(raw, [k / len(raw) for k in range(1, len(raw) + 1)],
                        label=rmw, color=COL.get(rmw, "#888"))
        ax.set_xlabel("RTT [ms]")
        ax.set_ylabel("CDF")
        ax.set_title(f"Distributia RTT — conditia «{pick}»")
        if ax.get_legend_handles_labels()[0]:
            ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, "fig_cdf.png"), dpi=140)
    print(f"[ok] rezumat + figuri in {outdir}")


def selftest():
    """Fabrica un arbore sintetic cu schema exacta si ruleaza analiza."""
    import tempfile
    rnd = random.Random(7)
    root = os.path.join(tempfile.mkdtemp(), "results_c1")
    for rmw, bias in (("cyclonedds", 1.0), ("zenoh", 0.8)):
        for c in CONDITIONS:
            for rep in (1, 2, 3):
                d = os.path.join(root, rmw, c["name"], f"rep{rep}")
                os.makedirs(d)
                base = 2 * c["base_ms"] + 4
                rtts = [max(0.3, rnd.gauss(base * bias, 1 + c["jitter_ms"]))
                        for _ in range(300)]
                sent = 300
                recv = round(sent * (1 - c["loss"]) ** 2)
                st = rtt_stats(rtts[:recv], sent, recv)
                st["payload"] = 4096
                json.dump(st, open(os.path.join(
                    d, "transport_p4096_summary.json"), "w"))
                with open(os.path.join(d, "transport_p4096.csv"), "w") as f:
                    f.write("seq,rtt_ms\n")
                    for i, r in enumerate(rtts[:recv]):
                        f.write(f"{i},{r:.3f}\n")
                hard = c["base_ms"] >= 200 and rmw == "cyclonedds"
                tdone = None if hard and rep == 1 else \
                    rnd.uniform(100, 140) * (1 + c["loss"]) * bias
                with open(os.path.join(d, "mission_metrics.csv"), "w") as f:
                    f.write("t_s,coverage,victims_found,cohesion,"
                            "drones_in_fallback\n")
                    if tdone and tdone < MISSION_CAP:
                        f.write(f"{tdone:.1f},0.96,5,0.8,0\n")
                    f.write(f"{MISSION_CAP},0.93,4,0.8,1\n")
    analyze(root, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "selftest_out"))
    print("[ok] autotest: fluxul complet a produs rezumatul si figurile")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="results_c1")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        analyze(a.root, a.out or os.path.join(a.root, "analysis"))


if __name__ == "__main__":
    main()
