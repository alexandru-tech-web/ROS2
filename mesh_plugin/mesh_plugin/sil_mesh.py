#!/usr/bin/env python3
"""sil_mesh.py - demonstratie Software-in-the-Loop: stea vs mesh multi-hop.

Fara ROS. Simuleaza 4 drone in pattern lawnmower pe o arie SAR, fiecare
indepartandu-se de GCS, si masoara la fiecare pas cate noduri ajung la GCS:
  - STEA: doar cele cu legatura DIRECTA;
  - MESH: cele care ajung prin orice releu multi-hop (mesh_core).

Arata exact castigul releului: pe masura ce roiul se imprastie, steaua pierde
noduri, iar mesh-ul le tine conectate prin vecini. Produce, daca matplotlib e
disponibil, sil_mesh_reachability.png si sil_mesh_snapshot.png.

  python3 sil_mesh.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_core import MeshTopology, reachability   # noqa: E402

HALF = 60.0          # semi-latura ariei [m]
N = 4
T_MAX = 120.0
DT = 1.0
V = 1.6              # viteza [m/s] - lantul se intinde lent


def lawnmower_targets():
    """Tinta finala: dronele se aranjeaza intr-un LANT radial care pleaca de
    la GCS spre marginea ariei. Pasul intre drone (~18 m) ramane sub raza
    utila (~22 m), deci lantul tine chiar daca varful iese din raza DIRECTA
    a GCS -> exact cazul in care releul multi-hop salveaza nodurile."""
    step = 18.0
    return {f"d{i+1}": ((i + 1) * step, 0.0) for i in range(N)}


def run():
    gcs = (0.0, 0.0)
    targets = lawnmower_targets()
    # pornesc toate gramada langa GCS; se intind treptat in lant
    pos = {f"d{i+1}": (3.0 + i * 0.5, 0.0) for i in range(N)}
    radio = {}                                    # implicit (raza ~22 m)

    ts, star, mesh = [], [], []
    snapshots = {}
    t = 0.0
    while t <= T_MAX:
        # avans spre tinta
        for d, (tx, ty) in targets.items():
            x, y = pos[d]
            dx, dy = tx - x, ty - y
            dist = math.hypot(dx, dy)
            if dist > 1e-6:
                step = min(V * DT, dist)
                pos[d] = (x + step * dx / dist, y + step * dy / dist)
        nodes = {"GCS": gcs, **pos}
        topo = MeshTopology(nodes, gcs="GCS", radio=radio)
        rr = reachability(topo)
        s = rr["_summary"]
        ts.append(t)
        star.append(s["reachable_direct"])
        mesh.append(s["reachable_mesh"])
        if abs(t - 60.0) < DT / 2:                # snapshot la mijloc
            snapshots = {"nodes": dict(nodes), "rr": rr, "t": t}
        t += DT

    # bilant numeric
    avg_star = sum(star) / len(star)
    avg_mesh = sum(mesh) / len(mesh)
    print("--- SIL mesh: stea vs mesh (4 drone, lawnmower, raza ~22 m) ---")
    print(f"  noduri conectate la GCS, mediat pe {int(T_MAX)} s:")
    print(f"    STEA (doar direct): {avg_star:.2f} / {N}")
    print(f"    MESH (multi-hop):   {avg_mesh:.2f} / {N}")
    print(f"  castig mediu din releu: {avg_mesh - avg_star:.2f} noduri")
    if snapshots:
        print(f"\n  snapshot la t={snapshots['t']:.0f} s:")
        for d in (f"d{i+1}" for i in range(N)):
            i = snapshots["rr"][d]
            ruta = " -> ".join(i["path"]) if i["path"] else "(izolat)"
            print(f"    {d}: direct={'DA' if i['direct'] else 'NU'} "
                  f"mesh={'DA' if i['mesh'] else 'NU'} ruta: {ruta}")

    _try_plot(ts, star, mesh, snapshots)
    return avg_mesh >= avg_star


def _try_plot(ts, star, mesh, snap):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("\n  (matplotlib indisponibil - sar peste figuri)")
        return
    # 1) reachability in timp
    fig, ax = plt.subplots(figsize=(8, 3.4), dpi=130)
    ax.step(ts, mesh, where="post", lw=2.2, color="#1C7293", label="mesh (multi-hop)")
    ax.step(ts, star, where="post", lw=2.2, color="#C0504D", label="stea (doar direct)")
    ax.fill_between(ts, star, mesh, step="post", alpha=0.18, color="#1C7293")
    ax.set_xlabel("timp [s]"); ax.set_ylabel("noduri conectate la GCS")
    ax.set_ylim(-0.2, N + 0.3); ax.set_yticks(range(N + 1))
    ax.set_title("Reachability catre GCS: stea vs mesh (lant care se intinde)")
    ax.grid(alpha=0.3); ax.legend(loc="lower left")
    fig.tight_layout(); fig.savefig("sil_mesh_reachability.png")
    print("  [figura] sil_mesh_reachability.png")

    # 2) snapshot spatial cu rutele mesh
    if not snap:
        return
    fig, ax = plt.subplots(figsize=(6, 5.2), dpi=130)
    nodes = snap["nodes"]; rr = snap["rr"]
    # muchiile rutelor
    for d, info in rr.items():
        if d == "_summary" or not info["path"]:
            continue
        for a, b in zip(info["path"], info["path"][1:]):
            xa, ya = nodes[a]; xb, yb = nodes[b]
            ax.plot([xa, xb], [ya, yb], "-", color="#1C7293", lw=1.4, alpha=0.7, zorder=1)
    for nid, (x, y) in nodes.items():
        if nid == "GCS":
            ax.scatter([x], [y], s=180, marker="s", color="#21295C", zorder=3)
            ax.annotate("GCS", (x, y), textcoords="offset points", xytext=(8, 6))
        else:
            direct = rr[nid]["direct"]
            col = "#2E73CC" if direct else "#9B59B6"
            ax.scatter([x], [y], s=120, color=col, zorder=3)
            ax.annotate(nid, (x, y), textcoords="offset points", xytext=(8, 4))
    ax.set_title(f"Snapshot t={snap['t']:.0f}s  (mov = ajunge doar prin releu)")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.grid(alpha=0.3)
    ax.set_aspect("equal", adjustable="datalim")
    fig.tight_layout(); fig.savefig("sil_mesh_snapshot.png")
    print("  [figura] sil_mesh_snapshot.png")


if __name__ == "__main__":
    sys.exit(0 if run() else 1)


def main():
    """Wrapper pentru entry-point 'ros2 run' (nu propaga bool-ul ca exit code)."""
    run()
