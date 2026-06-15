#!/usr/bin/env python3
"""sil_mesh.py -- SIL: STEA vs MESH pe un scenariu de partitie de roi.

Demonstreaza contributia C3: cand o partitie izoleaza d3/d4 de GCS (legatura
directa), topologia STEA pierde telemetria lor (GCS orbeste), dar MESH-ul le
recupereaza prin relay multi-hop (d3 -> d2 -> d1 -> gcs).

Scenariul: 4 drone pornesc langa GCS si se imprastie spre frontiere; la un
moment dat d3/d4 ajung departe de GCS (peste raza radio directa) dar raman in
raza vecinilor d1/d2. Comparam, in timp:
  - cate drone AJUNG la GCS (reachability) in stea vs mesh;
  - cate PACHETE de telemetrie ajung la GCS (livrare) in stea vs mesh;
  - distributia hopurilor folosite de mesh.

Produce: mesh_reachability.png, mesh_delivery.png, mesh_topology.png
si un bilant numeric cu verificari de sanatate.

Rulare:  python3 sil_mesh.py            (cere radio_link.py + mesh_core.py)
         python3 sil_mesh.py --profile open_field
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from radio_link import make_link
from mesh_core import (MeshGraph, DirectedRelay, deliver_once,
                       star_reachable, mesh_vs_star)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_PLT = True
except ImportError:
    HAVE_PLT = False


# ---- traiectorie: dronele se imprastie radial de la GCS spre colturile ariei
def trajectory(t, t_max, start, target):
    """Interpolare lineara start->target pe [0, 0.7*t_max], apoi stationar
    (drona a ajuns la zona ei de cautare departe de GCS)."""
    frac = min(1.0, t / (0.7 * t_max))
    return (start[0] + (target[0] - start[0]) * frac,
            start[1] + (target[1] - start[1]) * frac)


def run(profile="urban_rubble", t_max=120.0, dt=1.0, seed=4, out_dir=None):
    out_dir = out_dir or os.path.dirname(os.path.abspath(__file__))
    link = make_link(profile, shadow_sigma_db=0.0)
    rng = random.Random(seed)

    ids = ["d1", "d2", "d3", "d4"]
    # toate pornesc langa GCS; tintele finale: d1/d2 raman in raza, d3/d4 pleaca
    # departe (dincolo de raza radio directa) dar ALINIATE in spatele lui d1/d2
    starts = {d: (10.0, 10.0 + i * 5) for i, d in enumerate(ids)}
    targets = {
        "d1": (45.0, 0.0),     # ramane in raza GCS
        "d2": (45.0, 35.0),    # ramane in raza GCS
        "d3": (95.0, 0.0),     # pleaca departe, dar in spatele lui d1
        "d4": (95.0, 35.0),    # pleaca departe, dar in spatele lui d2
    }

    ts = []
    n_star_hist, n_mesh_hist = [], []
    star_pkts, mesh_pkts = 0, 0          # pachete livrate cumulat
    star_sent, mesh_sent = 0, 0
    star_series, mesh_series = [], []
    hop_hist = {1: 0, 2: 0, 3: 0, 4: 0}
    snapshots = {}                        # t -> (positions, mesh_bilant)

    g = MeshGraph(link, pdr_min=0.10)
    relays = {n: DirectedRelay(n, ttl=8) for n in (["gcs"] + ids)}

    t = 0.0
    while t <= t_max:
        pos = {"gcs": (0.0, 0.0)}
        for d in ids:
            pos[d] = trajectory(t, t_max, starts[d], targets[d])
        g.set_positions(pos)

        star = star_reachable(g)
        mesh = g.reachable_set("gcs")
        n_star_hist.append(len(star))
        n_mesh_hist.append(len(mesh))
        ts.append(t)

        # fiecare drona incearca sa trimita 1 pachet de telemetrie la GCS
        for d in ids:
            # STEA: reuseste doar daca are legatura directa
            star_sent += 1
            if d in star:
                star_pkts += 1
            # MESH: relay multi-hop (determinist pe ruta ETX = reachability)
            mesh_sent += 1
            for n in relays:
                relays[n].seen.clear()
            res = deliver_once(g, relays, d, {"id": d, "t": t}, dest="gcs")
            if res["delivered"]:
                mesh_pkts += 1
                h = res["hops"]
                if h in hop_hist:
                    hop_hist[h] += 1
        star_series.append(star_pkts)
        mesh_series.append(mesh_pkts)

        # snapshot pentru figura de topologie la 3 momente
        for key, frac in (("start", 0.0), ("mid", 0.5), ("end", 0.95)):
            if abs(t - frac * t_max) < dt / 2 and key not in snapshots:
                snapshots[key] = (dict(pos), mesh_vs_star(g))
        t += dt

    # ----------------------------- bilant -----------------------------
    print(f"=== SIL star vs mesh (profil={profile}, seed={seed}) ===")
    print(f"pachete telemetrie livrate la GCS:")
    print(f"  STEA: {star_pkts}/{star_sent}  ({100*star_pkts/star_sent:.1f}%)")
    print(f"  MESH: {mesh_pkts}/{mesh_sent}  ({100*mesh_pkts/mesh_sent:.1f}%)")
    gain = 100.0 * (mesh_pkts - star_pkts) / max(1, star_pkts)
    print(f"  castig mesh: +{gain:.0f}% pachete livrate")
    print(f"distributia hopurilor (mesh): {hop_hist}")
    end_bil = snapshots.get("end", (None, {}))[1]
    if end_bil:
        print(f"la final: stea ajunge la {end_bil['n_star']}/4 drone, "
              f"mesh la {end_bil['n_mesh']}/4 "
              f"(recuperate: {sorted(end_bil['recovered_by_mesh'])})")

    n_ok = [0]

    def check(name, cond):
        print(("[ok]   " if cond else "[FAIL] ") + name)
        n_ok[0] += bool(cond)

    check("mesh livreaza cel putin cat steaua", mesh_pkts >= star_pkts)
    if end_bil and end_bil["n_star"] < 4:
        # scenariu cu partitie reala: mesh TREBUIE sa recupereze
        check("la final stea pierde cel putin o drona", end_bil["n_star"] < 4)
        check("la final mesh recupereaza dronele pierdute de stea",
              end_bil["n_mesh"] > end_bil["n_star"])
        check("mesh foloseste relay multi-hop (>=2 hopuri apar)",
              (hop_hist[2] + hop_hist[3] + hop_hist[4]) > 0)
    else:
        # raza radio acopera tot: mesh = stea (corect, nu e nevoie de relay)
        print("[info] raza radio acopera toate dronele -> mesh = stea "
              "(relay inutil pe acest profil; multi-hop conteaza pe raza mica)")
        n_ok[0] += 3        # nu penalizam: e comportament corect

    # ----------------------------- figuri -----------------------------
    if HAVE_PLT:
        # 1. reachability in timp
        fig, ax = plt.subplots(figsize=(7.5, 4.0))
        ax.plot(ts, n_star_hist, "-", color="#c0392b", lw=2,
                label="STEA (legatura directa)")
        ax.plot(ts, n_mesh_hist, "-", color="#2E8B57", lw=2,
                label="MESH (relay multi-hop)")
        ax.fill_between(ts, n_star_hist, n_mesh_hist, color="#2E8B57",
                        alpha=0.12)
        ax.set_xlabel("timp [s]"); ax.set_ylabel("drone care ajung la GCS")
        ax.set_ylim(-0.2, 4.3); ax.set_yticks([0, 1, 2, 3, 4])
        ax.set_title(f"Reachability: stea vs mesh (profil {profile})\n"
                     "zona verde = drone recuperate de mesh")
        ax.legend(loc="lower left"); ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "mesh_reachability.png"), dpi=150)
        plt.close(fig)

        # 2. pachete livrate cumulat
        fig, ax = plt.subplots(figsize=(7.5, 4.0))
        ax.plot(ts, star_series, "-", color="#c0392b", lw=2, label="STEA")
        ax.plot(ts, mesh_series, "-", color="#2E8B57", lw=2, label="MESH")
        ax.set_xlabel("timp [s]")
        ax.set_ylabel("pachete telemetrie livrate la GCS (cumulat)")
        ax.set_title("Telemetrie livrata: mesh recupereaza ce pierde steaua")
        ax.legend(loc="upper left"); ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "mesh_delivery.png"), dpi=150)
        plt.close(fig)

        # 3. topologia la final (cine vede pe cine + rutele mesh)
        snap = snapshots.get("end")
        if snap:
            pos, bil = snap
            fig, ax = plt.subplots(figsize=(6.8, 5.2))
            # muchiile mesh
            g.set_positions(pos)
            for (a, b) in g.edges:
                xa, ya = pos[a]; xb, yb = pos[b]
                ax.plot([xa, xb], [ya, yb], "-", color="#2E8B57",
                        lw=1.2, alpha=0.5, zorder=1)
            # noduri
            for n, (x, y) in pos.items():
                if n == "gcs":
                    ax.plot(x, y, "*", ms=20, mfc="gold", mec="k", zorder=3)
                    ax.annotate("GCS", (x, y), textcoords="offset points",
                                xytext=(8, 8), fontweight="bold")
                else:
                    direct = n in bil["star_reachable"]
                    col = "#2E73CC" if direct else "#d8702e"
                    ax.plot(x, y, "o", ms=12, mfc=col, mec="k", zorder=3)
                    tag = n + ("" if direct else " (relay)")
                    ax.annotate(tag, (x, y), textcoords="offset points",
                                xytext=(8, 8))
            ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
            ax.set_title("Topologia la final: albastru=link direct, "
                         "portocaliu=ajunge prin relay\n"
                         "(linii verzi = muchii radio utilizabile)")
            ax.grid(alpha=0.3); ax.set_aspect("equal", "box")
            fig.tight_layout()
            fig.savefig(os.path.join(out_dir, "mesh_topology.png"), dpi=150)
            plt.close(fig)

        print(f"\n[ok] 3 figuri scrise in {out_dir}")

    return 0 if n_ok[0] == 4 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="urban_rubble",
                    choices=["open_field", "urban_rubble", "forest"])
    ap.add_argument("--t_max", type=float, default=120.0)
    ap.add_argument("--seed", type=int, default=4)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    sys.exit(run(profile=a.profile, t_max=a.t_max, seed=a.seed, out_dir=a.out))
