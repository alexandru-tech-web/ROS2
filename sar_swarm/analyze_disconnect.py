#!/usr/bin/env python3
"""analyze_disconnect.py — CE SE INTAMPLA cand o drona pierde legatura cu GCS?

Citeste jurnalul per-drona (scris local de drona, deci complet inclusiv in
timpul deconectarii — exact perioada in care GCS-ul NU o mai vede) si
produce o figura-cronologie cu 3 panouri + un rezumat in consola:

  1. starea de avarie in timp (LINKED / LOCAL_EXPLORE / RETURN_TO_LINK /
     LOITER / comenzi operator), cu intervalele de legatura cazuta hasurate;
  2. restanta de date: tamponul store-and-forward si celulele de harta
     neconfirmate (cresc cat e cazuta legatura, se golesc la reconectare);
  3. distanta fata de ultimul punct cu legatura (urca in explorarea locala,
     coboara la intoarcere, ~3 m constant in loiter).

Surse (acelasi format, acelasi analizor):
  SIL:  results/{scenariu}_drone_{id}.csv      (scrise de sil_run.py)
  ROS:  ~/sar_data/drone_{id}_log.csv          (scrise de drone_node.py)

Rulare:
  python3 analyze_disconnect.py results/drone_isolation_drone_d2.csv
  python3 analyze_disconnect.py ~/sar_data/drone_d2_log.csv
  optional: --down 25:60 (hasureaza manual intervalul, ex. pentru SIL)
            --out figura.png
"""
import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORDER = ["LINKED", "LOCAL_EXPLORE", "RETURN_TO_LINK", "LOITER",
         "GOTO", "HOLD", "RTH"]
COLOR = {"LINKED": "#2E8B57", "LOCAL_EXPLORE": "#e0a500",
         "RETURN_TO_LINK": "#d8702e", "LOITER": "#c0392b",
         "GOTO": "#2E73CC", "HOLD": "#7f8c8d", "RTH": "#9b59b6"}


def load(path):
    rows = list(csv.DictReader(open(path)))
    if not rows:
        sys.exit(f"jurnal gol: {path}")
    t = [float(r["t_s"]) for r in rows]
    st = [r["state"] for r in rows]
    def col(name):
        return [float(r[name]) if r.get(name) not in (None, "", "None")
                else None for r in rows]
    return t, st, col("gcs_up"), col("saf_buffered"), \
        col("cells_pending"), col("dist_link")


def segments(t, st):
    """[(stare, t_start, t_sfarsit), ...] pe portiuni contigue."""
    segs, s0, t0 = [], st[0], t[0]
    for i in range(1, len(t)):
        if st[i] != s0:
            segs.append((s0, t0, t[i]))
            s0, t0 = st[i], t[i]
    segs.append((s0, t0, t[-1]))
    return segs


def down_spans(t, gcs_up, manual):
    if manual:
        return manual
    spans, start = [], None
    for ti, up in zip(t, gcs_up):
        if up is None:
            return []
        if up < 0.5 and start is None:
            start = ti
        if up >= 0.5 and start is not None:
            spans.append((start, ti))
            start = None
    if start is not None:
        spans.append((start, t[-1]))
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--down", action="append", default=[],
                    help="interval a:b de hasurat (ex. 25:60)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    t, st, up, saf, pend, dist = load(a.csv_path)
    manual = [tuple(map(float, s.split(":"))) for s in a.down]
    spans = down_spans(t, up, manual)
    segs = segments(t, st)
    states = [s for s in ORDER if any(x == s for x in st)] or sorted(set(st))
    yi = {s: i for i, s in enumerate(states)}

    fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    name = os.path.basename(a.csv_path)
    fig.suptitle(f"Pierderea legaturii cu GCS — cronologia dronei ({name})",
                 fontweight="bold")
    for s, t0, t1 in segs:
        ax[0].barh(yi.get(s, len(states)), t1 - t0, left=t0, height=0.6,
                   color=COLOR.get(s, "#555"))
    ax[0].set_yticks(range(len(states)), states)
    ax[0].set_ylabel("starea dronei")
    ax[0].invert_yaxis()

    if any(v is not None for v in saf):
        ax[1].plot(t, [v or 0 for v in saf], label="tampon S&F [mesaje]",
                   color="#2E73CC")
    ax[1].plot(t, [v or 0 for v in pend], label="celule harta neconfirmate",
               color="#d8702e", ls="--")
    ax[1].set_ylabel("restanta de date")
    ax[1].legend(loc="upper left")

    ax[2].plot(t, [v or 0 for v in dist], color="#2E8B57")
    ax[2].set_ylabel("dist. fata de ultimul\npunct cu legatura [m]")
    ax[2].set_xlabel("timp [s]")
    for axx in ax:
        for (s0, s1) in spans:
            axx.axvspan(s0, s1, color="red", alpha=0.10)
        axx.grid(alpha=0.25)
    out = a.out or os.path.splitext(a.csv_path)[0] + "_timeline.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)

    print(f"[ok] figura: {out}")
    print("intervale cu legatura cazuta:",
          ", ".join(f"{s0:.0f}-{s1:.0f}s" for s0, s1 in spans) or "—")
    print("tranzitiile starii:")
    for s, t0, t1 in segs:
        print(f"  {t0:7.1f}s -> {s:<16} ({t1 - t0:5.1f}s)")
    mp = max((v or 0) for v in pend)
    print(f"varf restanta harta: {mp:.0f} celule"
          + (f"; varf S&F: {max((v or 0) for v in saf):.0f} mesaje"
             if any(v is not None for v in saf) else ""))


if __name__ == "__main__":
    main()
