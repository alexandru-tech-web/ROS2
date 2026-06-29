#!/usr/bin/env python3
"""sil_vs_hil_table.py -- tabel de comparatie SIL vs HIL pe transport, per (rmw, conditie), cu
VARIABILITATE rep-cu-rep (CV + interval [min,max] al p95-ului PER REPETITIE), nu medii punctuale.
Esential pentru Zenoh, imprevizibil intre rulari identice (NOTA_METODOLOGICA_C1.md: la loss_25,
p95 a variat 0.9-18.5 s intre repetitii identice -> media punctuala e inselatoare).

Nucleu PUR (statistica) testat cu _selftest; reutilizeaza campaign_stats.percentile (SURSA UNICA).
I/O subtire: parcurge arborele run_campaign root/{rmw}/{conditie}/rep*/transport_*.csv, calculeaza
p95 PER REPETITIE, apoi per (rmw, conditie): n_rep, p95 mediu, std, CV=std/medie, interval [min,max].

Folosire:
  python3 sil_vs_hil_table.py --selftest
  python3 sil_vs_hil_table.py --sil <dir_SIL> --hil <dir_HIL> [--out sil_vs_hil.csv]
  # dir = arbore results_c1 (sau arhiva ~/c1_archive/...). Eticheteaza clar care e SIL si care HIL.
"""
import argparse
import csv
import glob as globmod
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from campaign_stats import percentile, _detect_rtt_col   # SURSA UNICA a percentilei


# ---------- nucleu PUR (fara I/O) ----------
def summarize_reps(p95_list):
    """Din lista de p95-uri (unul per repetitie) -> variabilitate rep-cu-rep:
    n, mean, std (esantion), cv=std/mean (0 daca mean 0), interval [lo, hi]=[min, max]."""
    xs = [float(x) for x in p95_list]
    n = len(xs)
    if n == 0:
        return dict(n=0, mean=0.0, std=0.0, cv=0.0, lo=0.0, hi=0.0)
    mean = sum(xs) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    cv = std / mean if mean > 0 else 0.0
    return dict(n=n, mean=mean, std=std, cv=cv, lo=min(xs), hi=max(xs))


def comparison_rows(sil_groups, hil_groups):
    """sil_groups, hil_groups = {(rmw, conditie): [p95_per_rep]}. -> randuri sortate (rmw, conditie)
    cu rezumatul SIL si HIL alaturat (oricare poate lipsi -> n=0)."""
    keys = sorted(set(sil_groups) | set(hil_groups))
    return [dict(rmw=rmw, condition=cond,
                 sil=summarize_reps(sil_groups.get((rmw, cond), [])),
                 hil=summarize_reps(hil_groups.get((rmw, cond), [])))
            for (rmw, cond) in keys]


def _fmt(s):
    if s["n"] == 0:
        return "    --              "
    return "%7.0f cv%3.0f%% [%5.0f-%5.0f]" % (s["mean"], 100 * s["cv"], s["lo"], s["hi"])


def mode_label(mode):
    """Eticheta de mediu (DUPLICAT al analyze_campaign.mode_label -- tinut IDENTIC; functie pura).
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
    -> eticheta; alt input -> ValueError. DUPLICAT IDENTIC in analyze_campaign.py + campaign_stats.py."""
    if env not in ENV_LABELS:
        raise ValueError("mediu necunoscut: %r (asteptat 'sil', 'hil_wifi' sau 'hil_switch')" % (env,))
    return ENV_LABELS[env]


def format_table(rows):
    """Tabel text etichetat clar SIL vs HIL (p95 ms per repetitie, CV, interval [min-max])."""
    sil_lbl, hil_lbl = mode_label("sil"), mode_label("hil")
    out = ["Comparatie transport: %s vs %s -- p95[ms] mediu per repetitie, cv, interval [min-max]"
           % (sil_lbl, hil_lbl),
           "%-11s %-13s | %2s %-21s | %2s %-21s"
           % ("rmw", "conditie", "N", sil_lbl, "N", hil_lbl),
           "-" * 78]
    for r in rows:
        out.append("%-11s %-13s | %2d %s | %2d %s"
                   % (r["rmw"], r["condition"], r["sil"]["n"], _fmt(r["sil"]),
                      r["hil"]["n"], _fmt(r["hil"])))
    return "\n".join(out)


# ---------- I/O subtire ----------
def _read_rtt(path):
    with open(path, newline="") as f:
        rdr = csv.DictReader(f)
        col = _detect_rtt_col(rdr.fieldnames or [])
        if col is None:
            return []
        out = []
        for row in rdr:
            try:
                out.append(float(row[col]))
            except (KeyError, ValueError):
                continue
        return out


def load_rep_p95(root, glob_pat="transport_*.csv"):
    """Parcurge root/{rmw}/{conditie}/rep*/transport_*.csv, p95 PER fisier (repetitie).
    -> {(rmw, conditie): [p95_per_rep]}."""
    groups = {}
    for path in sorted(globmod.glob(os.path.join(root, "*", "*", "*", glob_pat))):
        parts = path.split(os.sep)
        rmw, cond = parts[-4], parts[-3]     # .../{rmw}/{conditie}/rep{N}/transport_*.csv
        vals = _read_rtt(path)
        if vals:
            groups.setdefault((rmw, cond), []).append(percentile(vals, 95))
    return groups


def _selftest():
    ok = 0
    def ck(name, cond):
        nonlocal ok
        assert cond, name
        ok += 1
    s = summarize_reps([100, 100, 100])
    ck("CV 0 pe constante", abs(s["cv"]) < 1e-9 and s["n"] == 3 and abs(s["mean"] - 100) < 1e-9)
    s = summarize_reps([900, 18500, 5000])               # Zenoh-style: imprevizibil (fixtura sintetica)
    ck("interval min-max", s["lo"] == 900 and s["hi"] == 18500)
    ck("CV mare la imprevizibil", s["cv"] > 0.8)
    ck("lista goala -> n=0", summarize_reps([])["n"] == 0)
    ck("o singura rep -> std 0", summarize_reps([10])["std"] == 0.0)
    sil = {("dds", "loss_15"): [1000, 1050, 980], ("zenoh", "loss_25"): [900, 18500]}
    hil = {("dds", "loss_15"): [1100], ("zenoh", "lat200_l15"): [2600, 2650]}
    rows = comparison_rows(sil, hil)
    ck("randuri = reuniunea cheilor (3), sortate", len(rows) == 3)
    dds15 = [r for r in rows if r["rmw"] == "dds" and r["condition"] == "loss_15"][0]
    ck("cheie in ambele -> SIL si HIL alaturat", dds15["sil"]["n"] == 3 and dds15["hil"]["n"] == 1)
    zen25 = [r for r in rows if r["rmw"] == "zenoh" and r["condition"] == "loss_25"][0]
    ck("doar SIL -> HIL n=0, SIL pastrat", zen25["hil"]["n"] == 0 and zen25["sil"]["n"] == 2)
    lat = [r for r in rows if r["condition"] == "lat200_l15"][0]
    ck("doar HIL -> SIL n=0, HIL pastrat", lat["sil"]["n"] == 0 and lat["hil"]["n"] == 2)
    ck("tabel are SIL si HIL in antet", "SIL" in format_table(rows) and "HIL" in format_table(rows))
    print("TOATE VERIFICARILE sil_vs_hil_table AU TRECUT: %d verificari." % ok)


def main():
    ap = argparse.ArgumentParser(description="Tabel SIL vs HIL (p95, CV, interval per rep). Vezi HIL_RUNBOOK.md.")
    ap.add_argument("--sil", help="director arbore results_c1 SIL (loopback)")
    ap.add_argument("--hil", help="director arbore results_c1 HIL (doua masini)")
    ap.add_argument("--out", default=None, help="CSV de iesire (optional)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest or (not a.sil and not a.hil):
        _selftest()
        return
    rows = comparison_rows(load_rep_p95(a.sil) if a.sil else {},
                           load_rep_p95(a.hil) if a.hil else {})
    print(format_table(rows))
    print("\nNOTA: pentru Zenoh, CV mare (zeci-sute %) inseamna ca media e inselatoare -- foloseste"
          " intervalul. Eticheteaza clar SIL (loopback) vs HIL (doua masini). Nimic etichetat HIL daca e SIL.")
    if a.out:
        with open(a.out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["rmw", "condition",
                        "sil_n", "sil_p95_mean", "sil_cv", "sil_min", "sil_max",
                        "hil_n", "hil_p95_mean", "hil_cv", "hil_min", "hil_max"])
            for r in rows:
                s, h = r["sil"], r["hil"]
                w.writerow([r["rmw"], r["condition"],
                            s["n"], "%.1f" % s["mean"], "%.4f" % s["cv"], "%.1f" % s["lo"], "%.1f" % s["hi"],
                            h["n"], "%.1f" % h["mean"], "%.4f" % h["cv"], "%.1f" % h["lo"], "%.1f" % h["hi"]])
        print("scris:", a.out)


if __name__ == "__main__":
    main()
