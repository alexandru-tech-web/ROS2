#!/usr/bin/env python3
"""analyze_campaign.py -- din arborele results_c1/ produce TABELUL si
FIGURILE articolului A1:

  campaign_summary.csv        rand per (rmw, conditie): transport + misiune
  fig_transport.png/.pdf      RTT p95 per conditie, grupat pe RMW (+pierderea
                              masurata ca etichete) -- Fig. 2 din articol
  fig_mission.png/.pdf        timpul de finalizare a misiunii (plafon hasurat)
                              + acoperirea finala -- Fig. 3 din articol
  fig_cdf.png/.pdf            CDF-ul RTT brut la o conditie aleasa -- Fig. 4

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


def _savefig(fig, outdir, name, caption=""):
    """Salveaza la standard academic: caption SIL sub axe, iesire .png + .pdf, DPI 200."""
    fig.subplots_adjust(left=0.10, right=0.97, top=0.91, bottom=0.27 if caption else 0.14)
    if caption:
        fig.text(0.5, 0.04, caption, ha="center", va="bottom", fontsize=8.5)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(outdir, name + "." + ext), dpi=200)


def mode_label(mode):
    """Eticheta de mediu (PASTRAT pentru compatibilitate: apelanti vechi + test_mode_label).
    Pentru cod nou prefera env_label (distinge wifi de switch).
    'sil' -> 'SIL (loopback)', 'hil' -> 'HIL (two-machine)'. Alt input -> ValueError."""
    labels = {"sil": "SIL (loopback)", "hil": "HIL (two-machine)"}
    if mode not in labels:
        raise ValueError("mod necunoscut: %r (asteptat 'sil' sau 'hil')" % (mode,))
    return labels[mode]


# Axa de MEDIU (transport fizic) a matricei 2x2 -- ortogonala fata de middleware (RMW).
ENV_LABELS = {
    "sil": "SIL (loopback)",
    "hil_wifi": "HIL (Wi-Fi)",
    "hil_switch": "HIL (Gigabit switch)",
}


def env_label(env):
    """Eticheta de MEDIU pentru subtitluri/tabele. Pura, testabila. 'sil'/'hil_wifi'/'hil_switch'
    -> eticheta; alt input -> ValueError. DUPLICAT IDENTIC in campaign_stats.py + sil_vs_hil_table.py."""
    if env not in ENV_LABELS:
        raise ValueError("mediu necunoscut: %r (asteptat 'sil', 'hil_wifi' sau 'hil_switch')" % (env,))
    return ENV_LABELS[env]


def analyze(root, outdir, env="sil"):
    data = collect(root)
    rmws = sorted({k[0] for k in data})
    conds = [c for c in COND_ORDER if any(k[1] == c for k in data)]
    label = env_label(env)
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

    nrep = max([len(e["loss"]) for e in data.values()] or [0])

    # Fig. 2 -- transportul
    fig, ax = plt.subplots(figsize=(9, 5.0))
    w = 0.8 / max(1, len(rmws))
    ymax = max([mean(data.get((r, c), {}).get("t", [])) or 0
                for r in rmws for c in conds] or [0])
    marker_h = 0.05 * (ymax or 1)          # inaltime simbolica pt marcaj de cedare totala
    for j, rmw in enumerate(rmws):
        xs, ys, ls = [], [], []
        for i, c in enumerate(conds):
            e = data.get((rmw, c), {})
            xs.append(i + j * w)
            ys.append(mean(e.get("t", [])) or 0)
            ls.append(mean(e.get("loss", [])) or 0)
        b = ax.bar(xs, ys, width=w, label=rmw, color=COL.get(rmw, "#888"),
                   edgecolor="black", linewidth=0.5)
        for r, l in zip(b, ls):
            ax.text(r.get_x() + r.get_width() / 2, r.get_height(),
                    f"{100 * l:.0f}%", ha="center", va="bottom", fontsize=8)
            if l >= 0.999 and r.get_height() == 0:
                # cedare totala (received=0): nicio bara reala -> marcaj hasurat
                # explicit, ca lipsa barei sa NU para date lipsa
                ax.bar(r.get_x() + r.get_width() / 2, marker_h, width=w,
                       color=COL.get(rmw, "#888"), hatch="xxx", alpha=0.30,
                       edgecolor="black", linewidth=0.5)
                ax.text(r.get_x() + r.get_width() / 2, marker_h,
                        "received=0\ncedare totala", ha="center", va="bottom",
                        fontsize=6.5, color="#b22222")
    ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(conds))],
                  conds, rotation=15, fontsize=10)
    ax.set_xlabel("conditie de retea (tc netem)", fontsize=11)
    ax.set_ylabel(f"RTT p95 [ms] (sarcina utila {REF_PAYLOAD} B)", fontsize=11)
    ax.set_title("Transport sub degradare (tc netem); "
                 "etichete = pierderea medie masurata", fontsize=12)
    if ax.get_legend_handles_labels()[0]:
        ax.legend(title="RMW", fontsize=10)
    ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    _savefig(fig, outdir, "fig_transport",
             "%s; N=%d repetitii; %d conditii netem; sarcina utila %d B."
             % (label, nrep, len(conds), REF_PAYLOAD))

    # Fig. 3 -- misiunea (DOAR daca stratul mission a rulat). Pe HIL transport
    # stratul mission nu se ruleaza -> toate barele ar fi la plafon (figura muta,
    # inselatoare). Detectam din date si o sarim, in loc sa inducem in eroare.
    has_mission = any(d is not None for e in data.values()
                      for d in e.get("done", []))
    if not has_mission:
        print("[skip] fig_mission: stratul mission nu a rulat (campanie doar "
              "transport) -- o sar ca sa nu induc in eroare cu o figura la plafon")
    else:
        fig, ax = plt.subplots(figsize=(9, 5.0))
        for j, rmw in enumerate(rmws):
            xs, ys, hatch = [], [], []
            for i, c in enumerate(conds):
                e = data.get((rmw, c), {})
                done = [d for d in e.get("done", []) if d is not None]
                xs.append(i + j * w)
                ys.append(mean(done) if done else MISSION_CAP)
                hatch.append(not done and bool(e.get("done")))
            bars = ax.bar(xs, ys, width=w, label=rmw, color=COL.get(rmw, "#888"),
                          edgecolor="black", linewidth=0.5)
            for r, h in zip(bars, hatch):
                if h:
                    r.set_hatch("//")
                    r.set_alpha(0.6)
        ax.axhline(MISSION_CAP, ls=":", color="#888")
        ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(conds))],
                      conds, rotation=15, fontsize=10)
        ax.set_xlabel("conditie de retea (tc netem)", fontsize=11)
        ax.set_ylabel("timp de finalizare a misiunii [s]", fontsize=11)
        ax.set_title("Impact la nivel de misiune "
                     "(hasurat = plafon, misiune neterminata)", fontsize=12)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(title="RMW", fontsize=10)
        ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
        ax.set_axisbelow(True)
        _savefig(fig, outdir, "fig_mission",
                 "%s; N=%d repetitii; %d conditii netem; plafon misiune %.0f s."
                 % (label, nrep, len(conds), MISSION_CAP))

    # Fig. 4 -- CDF la conditia cea mai severa cu date
    pick = next((c for c in reversed(conds)
                 if any(data.get((r, c), {}).get("raw") for r in rmws)), None)
    if pick:
        fig, ax = plt.subplots(figsize=(7.2, 5.0))
        for rmw in rmws:
            raw = sorted(data.get((rmw, pick), {}).get("raw", []))
            if raw:
                ax.plot(raw, [k / len(raw) for k in range(1, len(raw) + 1)],
                        label=rmw, color=COL.get(rmw, "#888"), linewidth=1.6)
        # ONESTITATE: un RMW cu received=0 la conditia aleasa nu apare in CDF;
        # il marcam EXPLICIT ca lipsa lui sa nu para 'netestat', ci cedare totala.
        missing = [r for r in rmws if not data.get((r, pick), {}).get("raw")]
        if missing:
            ax.text(0.97, 0.05,
                    "\n".join("%s: 100%% loss la '%s' (received=0, fara RTT)"
                              % (r, pick) for r in missing),
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
                    color="#b22222",
                    bbox=dict(boxstyle="round", fc="#fff0f0", ec="#b22222"))
        ax.set_xlabel("RTT [ms]", fontsize=11)
        ax.set_ylabel("probabilitate cumulata (CDF)", fontsize=11)
        ax.set_title(f"Distributia RTT -- conditia '{pick}'", fontsize=12)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(title="RMW", fontsize=10)
        ax.grid(linestyle=":", linewidth=0.5, alpha=0.6)
        ax.set_axisbelow(True)
        _savefig(fig, outdir, "fig_cdf",
                 f"{label}; conditia '{pick}'; RTT brut agregat pe repetitii.")
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
    ap.add_argument("--mode", choices=["sil", "hil_wifi", "hil_switch", "hil"], default=None,
                    help="mediul datelor: sil (loopback), hil_wifi (Wi-Fi), hil_switch (Gigabit switch). "
                         "'hil' generic e ambiguu pe matricea 2x2 -> eroare. Daca lipseste, se "
                         "presupune sil cu avertisment pe stderr.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    env = a.mode
    if env == "hil":
        sys.stderr.write("[eroare] --mode hil e ambiguu pe matricea 2x2 (wifi vs switch). "
                         "Foloseste --mode hil_wifi sau --mode hil_switch.\n")
        sys.exit(2)
    if env is None:
        sys.stderr.write("[avertisment] --mode nespecificat; presupun SIL (loopback). Pentru date "
                         "HIL ruleaza cu --mode hil_wifi sau --mode hil_switch.\n")
        env = "sil"
    analyze(a.root, a.out or os.path.join(a.root, "analysis"), env)


if __name__ == "__main__":
    main()
