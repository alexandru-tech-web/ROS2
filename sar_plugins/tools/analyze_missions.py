#!/usr/bin/env python3
"""analyze_missions.py — agregarea campaniei de misiune.

Citeste arborele produs de mission_experiment.sh:
  {OUT}/{rmw}/{profil}/rep{N}/mission_metrics.csv (+ op_commands.csv,
  victims.csv, battery.csv daca exista)
si produce in {OUT}/analysis/:
  mission_summary.csv   rmw,profile,rep,t90_s,mission_time_s,completed,
                        coverage_end,victims_found,rtl_events
  mission_coverage.png  curbele de acoperire (subplot per profil)
  mission_t90.png       T90 pe celula (bare + punctele repetitiilor)
  mission_victims.png   victimele gasite la final
  mission_rtl.png       evenimentele RTL (failsafe baterie)

Definitii: T90 = primul t cu coverage >= 0.90; misiune completa =
coverage >= 0.95 si victims_found >= VICTIMS_TOTAL (5, lumea sar_swarm);
mission_time = primul t al completarii, altfel plafonul rularii.

  python3 analyze_missions.py ~/mission_results
  python3 analyze_missions.py --selftest
"""
import csv
import glob
import io
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

VICTIMS_TOTAL = 5
COV_GOAL, COV_T90 = 0.95, 0.90
COL = {"cyclonedds": "#2E73CC", "zenoh": "#9b59b6", "fastdds": "#2E8B57"}


def citeste_misiune(cale):
    """-> (curba [(t,cov)], t90, t_done, cov_end, victims_end)"""
    curba, t90, t_done, cov_end, vic = [], None, None, None, 0
    try:
        rows = list(csv.DictReader(open(cale)))
    except OSError:
        return curba, t90, t_done, cov_end, vic
    for r in rows:
        try:
            t = float(r.get("t_s") or r.get("t") or "nan")
            cov = float(r.get("coverage") or r.get("cov") or "nan")
        except ValueError:
            continue
        if t != t or cov != cov:
            continue
        curba.append((t, cov))
        cov_end = cov
        try:
            vic = int(float(r.get("victims_found", vic) or vic))
        except ValueError:
            pass
        if t90 is None and cov >= COV_T90:
            t90 = t
        if t_done is None and cov >= COV_GOAL and vic >= VICTIMS_TOTAL:
            t_done = t
    return curba, t90, t_done, cov_end, vic


def numara_rtl(repdir):
    """rth-urile din op_commands.csv; alternativ tranzitiile RTL din battery.csv."""
    oc = os.path.join(repdir, "op_commands.csv")
    if os.path.exists(oc):
        txt = open(oc, errors="replace").read().lower()
        n = txt.count("rth")
        if n:
            return n
    bc = os.path.join(repdir, "battery.csv")
    if os.path.exists(bc):
        n, vazut = 0, set()
        for ln in open(bc, errors="replace"):
            low = ln.lower()
            if "rtl" in low:
                cheie = low.split(",")[0:2]
                cheie = tuple(cheie)
                if cheie not in vazut:
                    vazut.add(cheie)
                    n += 1
        return n
    return 0


def analizeaza(root):
    out = os.path.join(root, "analysis")
    os.makedirs(out, exist_ok=True)
    celule = {}          # (rmw, prof) -> list of dict(rep ...)
    for mm in sorted(glob.glob(os.path.join(root, "*", "*", "rep*",
                                            "mission_metrics.csv"))):
        repdir = os.path.dirname(mm)
        parti = repdir.split(os.sep)
        rmw, prof, rep = parti[-3], parti[-2], parti[-1].replace("rep", "")
        curba, t90, t_done, cov_end, vic = citeste_misiune(mm)
        plafon = curba[-1][0] if curba else 0.0
        celule.setdefault((rmw, prof), []).append(dict(
            rep=rep, curba=curba, t90=t90,
            mission_time=t_done if t_done is not None else plafon,
            completed=1 if t_done is not None else 0,
            coverage_end=cov_end, victims=vic, rtl=numara_rtl(repdir)))
    if not celule:
        sys.exit(f"[eroare] niciun mission_metrics.csv sub {root}")

    # ---------------- sumarul CSV ----------------
    cale_sum = os.path.join(out, "mission_summary.csv")
    with open(cale_sum, "w") as f:
        f.write("rmw,profile,rep,t90_s,mission_time_s,completed,"
                "coverage_end,victims_found,rtl_events\n")
        for (rmw, prof), runs in sorted(celule.items()):
            for r in runs:
                f.write(f"{rmw},{prof},{r['rep']},"
                        f"{'' if r['t90'] is None else round(r['t90'],1)},"
                        f"{round(r['mission_time'],1)},{r['completed']},"
                        f"{'' if r['coverage_end'] is None else round(r['coverage_end'],4)},"
                        f"{r['victims']},{r['rtl']}\n")

    profile = sorted({k[1] for k in celule})
    rmws = sorted({k[0] for k in celule})

    # ---------------- curbele de acoperire ----------------
    fig, axs = plt.subplots(1, len(profile), figsize=(6 * len(profile), 4.2),
                            sharey=True, squeeze=False)
    for j, prof in enumerate(profile):
        ax = axs[0][j]
        for rmw in rmws:
            for k, r in enumerate(celule.get((rmw, prof), [])):
                if not r["curba"]:
                    continue
                ts, cs = zip(*r["curba"])
                ax.plot(ts, cs, color=COL.get(rmw, "#888"),
                        alpha=0.45, lw=1.2,
                        label=rmw if k == 0 else None)
        ax.axhline(COV_T90, ls=":", color="#888", lw=1)
        ax.set_title(f"profil: {prof}")
        ax.set_xlabel("t [s]")
        ax.grid(alpha=0.3)
        ax.legend(title="RMW")
    axs[0][0].set_ylabel("acoperire [0..1]")
    fig.suptitle("Dinamica acoperirii — canal dependent de distanta")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "mission_coverage.png"), dpi=140)

    # ---------------- barele pe metrice ----------------
    def bare(metr, titlu, ylab, fis, none_la=None):
        fig, ax = plt.subplots(figsize=(8.5, 4.2))
        w = 0.8 / max(1, len(rmws))
        for j, rmw in enumerate(rmws):
            xs, ys = [], []
            for i, prof in enumerate(profile):
                runs = celule.get((rmw, prof), [])
                vals = [r[metr] for r in runs if r[metr] is not None]
                v = sum(vals) / len(vals) if vals else (none_la or 0)
                xs.append(i + j * w)
                ys.append(v)
                ax.scatter([i + j * w] * len(vals), vals, s=18, zorder=3,
                           color="#222")
            ax.bar(xs, ys, width=w, label=rmw, color=COL.get(rmw, "#888"))
        ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(profile))],
                      profile)
        ax.set_ylabel(ylab)
        ax.set_title(titlu)
        ax.legend(title="RMW")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(out, fis), dpi=140)

    bare("t90", "Timpul pana la 90% acoperire", "T90 [s]",
         "mission_t90.png")
    bare("victims", "Victime gasite la final (lumea roiului, total 5)",
         "victime", "mission_victims.png")
    bare("rtl", "Evenimente RTL (failsafe baterie)", "numar RTL",
         "mission_rtl.png")

    print(f"[ok] {sum(len(v) for v in celule.values())} rulari agregate")
    print(f"[ok] {cale_sum}")
    for f in ("mission_coverage.png", "mission_t90.png",
              "mission_victims.png", "mission_rtl.png"):
        print(f"[ok] {os.path.join(out, f)}")


def selftest():
    import random
    import tempfile
    root = tempfile.mkdtemp()
    rng = random.Random(7)
    for rmw, baza in (("cyclonedds", 1.00), ("zenoh", 0.93)):
        for prof, greu in (("open_field", 1.0), ("urban_rubble", 1.45)):
            for rep in (1, 2):
                d = os.path.join(root, rmw, prof, f"rep{rep}")
                os.makedirs(d)
                with open(os.path.join(d, "mission_metrics.csv"), "w") as f:
                    f.write("t_s,coverage,victims_found,cohesion,links_up\n")
                    cov, vic = 0.0, 0
                    for t in range(0, 300, 2):
                        cov = min(0.99, cov + 0.014 / (baza * greu)
                                  * (1 + 0.1 * rng.random()))
                        if vic < 5 and cov > 0.15 * (vic + 1):
                            vic += 1
                        f.write(f"{t},{cov:.4f},{vic},0.5,4\n")
                with open(os.path.join(d, "op_commands.csv"), "w") as f:
                    f.write("t,cmd\n")
                    for k in range(rng.randint(1, 2)):
                        f.write(f'{100+40*k},"{{""action"":""rth""}}"\n')
    analizeaza(root)
    print("[ok] selftest incheiat:", root)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
    else:
        analizeaza(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1
                                      else "~/mission_results"))
