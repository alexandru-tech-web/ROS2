#!/usr/bin/env python3
"""analyze_rmw.py -- figura centrala a tezei: rmw_zenoh vs rmw_cyclonedds pe
ACELEASI metrici de misiune, sub degradare de retea.

Spre deosebire de analyze_missions.py (care agrega coverage/T90/victime),
acesta tinteste DIRECT comparatia de transport, pe metricile noi care separa
RMW-urile in conditii degradate:
  - latenta e2e a telemetriei (p50/p95): cat de veche e informatia la GCS;
  - goodput (livrate/oferite): cat ajunge prin link-ul degradat;
  - timp in fallback: cat de mult sunt dronele izolate.

Citeste arborele campaniei:
  {OUT}/{rmw}/{profil}/rep{N}/mission_metrics.csv   (serie de timp, cu e2e)
  {OUT}/{rmw}/{profil}/rep{N}/summary.json          (daca exista, SIL)

Produce in {OUT}/analysis_rmw/:
  rmw_e2e.png        latenta e2e p95: bare grupate rmw x profil (+ puncte rep)
  rmw_goodput.png    goodput: bare grupate
  rmw_summary.csv    rmw,profile,rep,e2e_p95_ms,goodput,coverage_end,...
  + verdicte in consola (propozitii de articol)

  python3 analyze_rmw.py ~/mission_results
  python3 analyze_rmw.py --selftest        # validare pe date sintetice
"""
import csv
import glob
import json
import os
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"cyclonedds": "#2E73CC", "zenoh": "#9b59b6", "fastdds": "#2E8B57"}
NICE = {"cyclonedds": "CycloneDDS", "zenoh": "Zenoh", "fastdds": "FastDDS"}


def _read_metrics(path):
    """Citeste mission_metrics.csv. Intoarce dict cu metrici finale:
    e2e_p95_ms (din coloana e2e_telemetry_ms daca exista), coverage_end,
    victims_end, msgs_delivered_end."""
    e2e, cov, vic, msgs = [], None, 0, None
    try:
        rows = list(csv.DictReader(open(path)))
    except OSError:
        return None
    for r in rows:
        try:
            cov = float(r.get("coverage") or cov or 0)
        except (ValueError, TypeError):
            pass
        try:
            vic = int(float(r.get("victims_found", vic) or vic))
        except (ValueError, TypeError):
            pass
        e = r.get("e2e_telemetry_ms")
        if e not in (None, ""):
            try:
                v = float(e)
                if v > 0:
                    e2e.append(v)
            except ValueError:
                pass
        m = r.get("msgs_delivered")
        if m not in (None, ""):
            try:
                msgs = int(float(m))
            except ValueError:
                pass
    e2e_p95 = (sorted(e2e)[int(0.95 * (len(e2e) - 1))] if e2e else None)
    return {"e2e_p95_ms": round(e2e_p95, 1) if e2e_p95 else None,
            "coverage_end": round(cov, 4) if cov is not None else None,
            "victims_end": vic, "msgs_delivered": msgs}


def _read_summary(repdir):
    """Daca exista un *_summary.json (SIL), citeste goodput + e2e direct."""
    for sp in glob.glob(os.path.join(repdir, "*summary.json")):
        try:
            s = json.load(open(sp))
            return {"goodput": s.get("goodput_gcs"),
                    "e2e_p95_ms": s.get("e2e_telemetry_p95_ms"),
                    "fallback_drone_s": s.get("fallback_drone_s"),
                    "coverage_end": s.get("coverage_final"),
                    "victims_end": s.get("victims_found")}
        except (OSError, ValueError):
            pass
    return {}


def collect(root):
    """-> dict (rmw, profil) -> list of per-rep dicts."""
    cells = {}
    pattern = os.path.join(root, "*", "*", "rep*")
    for repdir in sorted(glob.glob(pattern)):
        parts = repdir.split(os.sep)
        rmw, prof, rep = parts[-3], parts[-2], parts[-1].replace("rep", "")
        rec = {"rep": rep}
        mm = os.path.join(repdir, "mission_metrics.csv")
        if os.path.exists(mm):
            m = _read_metrics(mm)
            if m:
                rec.update(m)
        rec.update({k: v for k, v in _read_summary(repdir).items()
                    if v is not None})
        cells.setdefault((rmw, prof), []).append(rec)
    return cells


def _bars(cells, metric, title, ylab, fname, out, lower_better=True):
    profile = sorted({k[1] for k in cells})
    rmws = sorted({k[0] for k in cells})
    if not profile or not rmws:
        return
    fig, ax = plt.subplots(figsize=(1.8 + 2.4 * len(profile), 4.4))
    w = 0.8 / max(1, len(rmws))
    for j, rmw in enumerate(rmws):
        xs, ys = [], []
        for i, prof in enumerate(profile):
            vals = [r[metric] for r in cells.get((rmw, prof), [])
                    if r.get(metric) is not None]
            v = statistics.mean(vals) if vals else 0
            xs.append(i + j * w)
            ys.append(v)
            if vals:
                ax.scatter([i + j * w] * len(vals), vals, s=20, zorder=3,
                           color="#222", alpha=0.7)
        ax.bar(xs, ys, width=w, label=NICE.get(rmw, rmw),
               color=COL.get(rmw, "#888"))
    ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(profile))])
    ax.set_xticklabels(profile)
    ax.set_ylabel(ylab)
    arrow = "(mai mic = mai bine)" if lower_better else "(mai mare = mai bine)"
    ax.set_title(f"{title}  {arrow}")
    ax.legend(title="RMW")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, fname), dpi=140)
    plt.close(fig)
    print(f"[ok] {os.path.join(out, fname)}")


def analyze(root):
    cells = collect(root)
    if not cells:
        sys.exit(f"[eroare] niciun rep sub {root} "
                 f"(astept {root}/<rmw>/<profil>/rep<N>/mission_metrics.csv)")
    out = os.path.join(root, "analysis_rmw")
    os.makedirs(out, exist_ok=True)

    # sumar CSV
    with open(os.path.join(out, "rmw_summary.csv"), "w") as f:
        f.write("rmw,profile,rep,e2e_p95_ms,goodput,coverage_end,victims_end,"
                "fallback_drone_s\n")
        for (rmw, prof), runs in sorted(cells.items()):
            for r in runs:
                f.write(f"{rmw},{prof},{r.get('rep','')},"
                        f"{r.get('e2e_p95_ms','')},{r.get('goodput','')},"
                        f"{r.get('coverage_end','')},{r.get('victims_end','')},"
                        f"{r.get('fallback_drone_s','')}\n")
    print(f"[ok] {os.path.join(out, 'rmw_summary.csv')}")

    # figurile money-shot
    _bars(cells, "e2e_p95_ms",
          "Latenta e2e a telemetriei (p95): Zenoh vs DDS sub degradare",
          "latenta e2e p95 [ms]", "rmw_e2e.png", out, lower_better=True)
    _bars(cells, "goodput",
          "Goodput la GCS: fractia de telemetrie livrata",
          "goodput (livrate/oferite)", "rmw_goodput.png", out,
          lower_better=False)

    # verdicte
    print("\n== verdicte (propozitii de articol) ==")
    profile = sorted({k[1] for k in cells})
    for prof in profile:
        for metric, nice, better in (("e2e_p95_ms", "latenta e2e p95", "mic"),
                                     ("goodput", "goodput", "mare")):
            zc = [r.get(metric) for r in cells.get(("zenoh", prof), [])
                  if r.get(metric) is not None]
            cc = [r.get(metric) for r in cells.get(("cyclonedds", prof), [])
                  if r.get(metric) is not None]
            if zc and cc:
                z, c = statistics.mean(zc), statistics.mean(cc)
                if c != 0:
                    diff = 100.0 * (z - c) / abs(c)
                    cine = ("Zenoh" if (diff < 0) == (better == "mic")
                            else "CycloneDDS")
                    print(f"  [{prof}] {nice}: Zenoh={z:.1f} vs "
                          f"CycloneDDS={c:.1f} -> {cine} mai bun "
                          f"({abs(diff):.0f}% diferenta)")
    print()


def selftest():
    """Genereaza un arbore de campanie sintetic in care Zenoh are e2e mai mic
    si goodput mai mare (ipoteza), apoi ruleaza analiza."""
    import random
    import tempfile
    root = tempfile.mkdtemp()
    rng = random.Random(3)
    # zenoh: e2e mai mic, goodput mai mare; cyclone: invers
    profile_sev = {"open_field": 1.0, "urban_rubble": 1.6}
    rmw_base = {"zenoh": {"e2e": 60, "gp": 0.92},
                "cyclonedds": {"e2e": 85, "gp": 0.85}}
    for rmw, b in rmw_base.items():
        for prof, sev in profile_sev.items():
            for rep in (1, 2, 3):
                d = os.path.join(root, rmw, prof, f"rep{rep}")
                os.makedirs(d)
                e2e = b["e2e"] * sev * (1 + 0.05 * rng.random())
                gp = max(0.1, b["gp"] / sev * (1 + 0.03 * rng.random()))
                with open(os.path.join(d, "mission_metrics.csv"), "w") as f:
                    f.write("t_s,coverage,victims_found,cohesion,"
                            "drones_linked,e2e_telemetry_ms,msgs_delivered\n")
                    cov, vic = 0.0, 0
                    for t in range(0, 200, 5):
                        cov = min(0.97, cov + 0.03 / sev)
                        if vic < 5 and cov > 0.15 * (vic + 1):
                            vic += 1
                        e = e2e * (1 + 0.1 * rng.random())
                        f.write(f"{t},{cov:.4f},{vic},0.5,4,{e:.1f},"
                                f"{int(t * gp * 2)}\n")
                # summary cu goodput
                with open(os.path.join(d, "mission_summary.json"), "w") as f:
                    json.dump({"goodput_gcs": round(gp, 3),
                               "e2e_telemetry_p95_ms": round(e2e * 1.4, 1),
                               "fallback_drone_s": round(20 * (sev - 1), 1),
                               "coverage_final": round(cov, 4),
                               "victims_found": vic}, f)
    print(f"[selftest] arbore sintetic in {root}\n")
    analyze(root)
    print(f"[ok] selftest incheiat: {root}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
    else:
        analyze(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1
                                   else "~/mission_results"))
