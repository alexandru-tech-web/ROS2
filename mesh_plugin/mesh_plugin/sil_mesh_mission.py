#!/usr/bin/env python3
"""sil_mesh_mission.py - experiment de misiune: cat recupereaza mesh-ul vs stea.

Intrebarea de cercetare a stratului mesh: in topologia in stea, acoperirea se
crediteaza la GCS DOAR din telemetria livrata, deci o drona izolata zboara dar
zona ei ramane goala pe harta. Cat din acoperire si cate victime recupereaza
releul multi-hop?

Scenariu (de tip partition, realist SAR): cautare in ADANCIME a unui coridor
care pleaca de la GCS (ex. o aripa de cladire avariata). Patru drone, fiecare
in zona ei de adancime, baleiaza in lawnmower. Dronele departate nu au legatura
DIRECTA la GCS, dar formeaza un lant de relee prin vecinii mai apropiati.

La fiecare pas, pentru fiecare drona:
  - se marcheaza acoperirea FIZICA (ce a survolat efectiv);
  - daca e accesibila DIRECT  -> acoperirea ei se crediteaza pe harta STEA;
  - daca e accesibila prin MESH -> acoperirea ei se crediteaza pe harta MESH;
  - victimele din raza se inregistreaza la GCS sub aceeasi conditie.

Compara: acoperire% si victime, stea vs mesh vs plafon fizic. Produce
sil_mesh_mission.png (harta + evolutie in timp) - figura de rezultat.

  python3 sil_mesh_mission.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_core import MeshTopology, reachability   # noqa: E402

# -------------------- scenariul (coridor in adancime) --------------------
N = 4                      # drone
ZD = 14.0                  # adancimea unei zone [m]
WIDTH = 22.0               # latimea coridorului [m] (y in [-W/2, W/2])
GCS = (0.0, 0.0)           # statia, la gura coridorului
SENSOR_R = 6.0             # raza senzorului [m]
LINE_SP = 1.6 * SENSOR_R   # distanta intre liniile lawnmower
V = 3.0                    # viteza [m/s]
DT = 0.5
CELL = 1.0                 # rezolutia grilei de acoperire [m]
# prag de accesibilitate: o legatura crediteaza telemetrie doar daca e
# suficient de buna (PDR >= 0.30 -> ETX <= ~11). Strange raza utila la ~20 m,
# realist pentru creditare fiabila, nu doar "se aude slab".
RADIO = {}
PDR_MIN = 0.30
N_VICTIMS = 5
HOP_MS = 20.0              # latenta estimata per hop [ms] (pentru costul releului)

DEPTH = N * ZD             # adancimea totala a coridorului
Y0, Y1 = -WIDTH / 2, WIDTH / 2


# ------------------------------ grila de acoperire ------------------------------
class Grid:
    def __init__(self, x0, x1, y0, y1, cell):
        self.x0, self.y0, self.cell = x0, y0, cell
        self.nx = int(math.ceil((x1 - x0) / cell))
        self.ny = int(math.ceil((y1 - y0) / cell))
        self.g = bytearray(self.nx * self.ny)
        self.total = self.nx * self.ny

    def mark_disc(self, x, y, r):
        c = self.cell
        i0 = max(0, int((x - r - self.x0) / c)); i1 = min(self.nx - 1, int((x + r - self.x0) / c))
        j0 = max(0, int((y - r - self.y0) / c)); j1 = min(self.ny - 1, int((y + r - self.y0) / c))
        r2 = r * r
        for i in range(i0, i1 + 1):
            cx = self.x0 + (i + 0.5) * c
            for j in range(j0, j1 + 1):
                cy = self.y0 + (j + 0.5) * c
                if (cx - x) ** 2 + (cy - y) ** 2 <= r2:
                    self.g[i * self.ny + j] = 1

    def count(self):
        return sum(self.g)

    def percent(self):
        return 100.0 * self.count() / self.total


# ------------------------------ lawnmower pe zona ------------------------------
def zone_waypoints(zx0, zx1):
    """Serpentina in sub-dreptunghiul [zx0,zx1] x [Y0,Y1]."""
    wps, x, k = [], zx0 + LINE_SP / 2, 0
    while x < zx1:
        ya, yb = (Y0, Y1) if k % 2 == 0 else (Y1, Y0)
        wps += [(x, ya), (x, yb)]
        x += LINE_SP
        k += 1
    return wps


def victims_layout():
    """5 victime esalonate in adancime (una aproape, restul tot mai departe)."""
    xs = [0.18, 0.40, 0.60, 0.78, 0.93]
    ys = [0.0, 0.5, -0.5, 0.35, -0.3]
    return [(DEPTH * fx, (Y1 - Y0) * fy) for fx, fy in zip(xs, ys)]


# ------------------------------ simularea ------------------------------
def run():
    # drone pre-desfasurate, fiecare in zona ei de adancime
    drones = {}
    for i in range(N):
        zx0, zx1 = i * ZD, (i + 1) * ZD
        wps = zone_waypoints(zx0, zx1)
        drones[f"d{i+1}"] = {"pos": wps[0], "wps": wps, "wi": 0, "done": False}

    g_phys = Grid(0, DEPTH, Y0, Y1, CELL)   # plafon fizic (ce s-a survolat)
    g_star = Grid(0, DEPTH, Y0, Y1, CELL)   # creditat sub stea
    g_mesh = Grid(0, DEPTH, Y0, Y1, CELL)   # creditat sub mesh
    victims = victims_layout()
    found_star, found_mesh = set(), set()

    ts, cov_phys, cov_star, cov_mesh = [], [], [], []
    # acumulatori de COST (latura platita a compromisului)
    sum_hops = sum_etx = n_mesh_s = n_relayed_s = 0
    max_hops = 0
    snap = None
    t = 0.0
    T_CAP = 600.0
    while t <= T_CAP and not all(d["done"] for d in drones.values()):
        # avans pe waypoints
        for d in drones.values():
            if d["done"]:
                continue
            tx, ty = d["wps"][d["wi"]]
            x, y = d["pos"]
            dx, dy = tx - x, ty - y
            dist = math.hypot(dx, dy)
            step = V * DT
            if dist <= step:
                d["pos"] = (tx, ty)
                d["wi"] += 1
                if d["wi"] >= len(d["wps"]):
                    d["done"] = True
            else:
                d["pos"] = (x + step * dx / dist, y + step * dy / dist)

        # topologia curenta + accesibilitatea fiecarei drone
        nodes = {"GCS": GCS, **{k: v["pos"] for k, v in drones.items()}}
        topo = MeshTopology(nodes, gcs="GCS", radio=RADIO, pdr_min=PDR_MIN)
        rr = reachability(topo)

        for k, d in drones.items():
            x, y = d["pos"]
            g_phys.mark_disc(x, y, SENSOR_R)             # fizic, mereu
            if rr[k]["direct"]:
                g_star.mark_disc(x, y, SENSOR_R)
            if rr[k]["mesh"]:
                g_mesh.mark_disc(x, y, SENSOR_R)
                h = rr[k]["hops"]
                sum_hops += h; n_mesh_s += 1; max_hops = max(max_hops, h)
                if math.isfinite(rr[k]["etx"]):
                    sum_etx += rr[k]["etx"]
                if h > 1:
                    n_relayed_s += 1
            # victime in raza -> creditate sub conditia de accesibilitate
            for vi, (vx, vy) in enumerate(victims):
                if (vx - x) ** 2 + (vy - y) ** 2 <= SENSOR_R ** 2:
                    if rr[k]["direct"]:
                        found_star.add(vi)
                    if rr[k]["mesh"]:
                        found_mesh.add(vi)

        ts.append(t)
        cov_phys.append(g_phys.percent())
        cov_star.append(g_star.percent())
        cov_mesh.append(g_mesh.percent())
        if snap is None and t >= 0.6 * T_CAP:
            pass
        t += DT

    snap = {"nodes": nodes, "rr": rr}     # ultima stare (toate in zonele lor)

    # ---- bilant ----
    ph, st, me = g_phys.percent(), g_star.percent(), g_mesh.percent()
    print("--- SIL misiune: stea vs mesh (coridor in adancime, 4 drone) ---")
    print(f"  acoperire creditata la GCS:")
    print(f"    plafon fizic (survolat): {ph:5.1f}%")
    print(f"    STEA (doar direct):      {st:5.1f}%")
    print(f"    MESH (multi-hop):        {me:5.1f}%")
    rec = (me - st) / ph * 100 if ph else 0
    print(f"  acoperire recuperata de mesh: +{me - st:.1f} puncte "
          f"({rec:.0f}% din plafonul fizic)")
    print(f"  victime gasite (raportate la GCS):")
    print(f"    STEA: {len(found_star)}/{N_VICTIMS}    MESH: {len(found_mesh)}/{N_VICTIMS}")
    # ---- costul releului (latura platita) ----
    if n_mesh_s:
        avg_hops = sum_hops / n_mesh_s
        avg_etx = sum_etx / n_mesh_s
        relayed_pct = 100.0 * n_relayed_s / n_mesh_s
        extra_ms = (avg_hops - 1) * HOP_MS
        print(f"  COST (compromisul reachability vs latenta/energie):")
        print(f"    hopuri medii pe livrare: {avg_hops:.2f} (max {max_hops})")
        print(f"    ETX mediu pe cale:       {avg_etx:.2f} transmisii")
        print(f"    esantioane prin releu:   {relayed_pct:.0f}% (>1 hop)")
        print(f"    latenta suplimentara estimata: ~{extra_ms:.0f} ms/livrare "
              f"(la {HOP_MS:.0f} ms/hop) fata de legatura directa")

    _plot(ts, cov_phys, cov_star, cov_mesh, g_star, g_mesh, g_phys,
          victims, found_star, found_mesh, snap)
    return me >= st


# ------------------------------ figura ------------------------------
def _plot(ts, ph, st, me, g_star, g_mesh, g_phys, victims, fs, fm, snap):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:
        print("\n  (matplotlib indisponibil - sar peste figura)")
        return

    fig = plt.figure(figsize=(12, 4.6), dpi=130)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.22)

    # --- panou A: harta cine a creditat ce ---
    axA = fig.add_subplot(gs[0, 0])
    nx, ny = g_phys.nx, g_phys.ny
    cat = np.zeros((ny, nx))     # 0 nimic, 1 fizic-necreditat, 2 mesh-only, 3 stea
    for i in range(nx):
        for j in range(ny):
            idx = i * ny + j
            if g_star.g[idx]:
                cat[j, i] = 3
            elif g_mesh.g[idx]:
                cat[j, i] = 2
            elif g_phys.g[idx]:
                cat[j, i] = 1
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#FFFFFF", "#D9D9D9", "#1C7293", "#3FA34D"])
    axA.imshow(cat, origin="lower", cmap=cmap, vmin=0, vmax=3,
               extent=[0, DEPTH, Y0, Y1], aspect="auto", interpolation="nearest")
    # GCS, drone, victime, relee
    nodes, rr = snap["nodes"], snap["rr"]
    axA.scatter([GCS[0]], [GCS[1]], s=150, marker="s", color="#21295C", zorder=5)
    axA.annotate("GCS", GCS, textcoords="offset points", xytext=(6, 6), fontsize=9, color="#21295C")
    for d, info in rr.items():
        if d == "_summary" or not info["path"]:
            continue
        for a, b in zip(info["path"], info["path"][1:]):
            (xa, ya), (xb, yb) = nodes[a], nodes[b]
            axA.plot([xa, xb], [ya, yb], "-", color="#444", lw=1.0, alpha=0.6, zorder=4)
    for k, v in nodes.items():
        if k == "GCS":
            continue
        col = "#2E73CC" if rr[k]["direct"] else "#9B59B6"
        axA.scatter([v[0]], [v[1]], s=70, color=col, edgecolor="white", lw=0.8, zorder=6)
    for vi, (vx, vy) in enumerate(victims):
        marker = "*"
        col = "#3FA34D" if vi in fm else "#C0392B"
        axA.scatter([vx], [vy], s=190, marker=marker, color=col,
                    edgecolor="black", lw=0.6, zorder=7)
    axA.set_title("Acoperire creditata la GCS (snapshot final)")
    axA.set_xlabel("adancime in coridor [m]"); axA.set_ylabel("y [m]")
    # legenda manuala
    from matplotlib.patches import Patch
    leg = [Patch(facecolor="#3FA34D", label="creditat de stea"),
           Patch(facecolor="#1C7293", label="recuperat de mesh"),
           Patch(facecolor="#D9D9D9", label="survolat, necreditat")]
    axA.legend(handles=leg, loc="lower right", fontsize=8, framealpha=0.9)

    # --- panou B: acoperire in timp ---
    axB = fig.add_subplot(gs[0, 1])
    axB.plot(ts, ph, "--", color="#888", lw=1.8, label="plafon fizic")
    axB.plot(ts, me, "-", color="#1C7293", lw=2.4, label="mesh (multi-hop)")
    axB.plot(ts, st, "-", color="#C0504D", lw=2.4, label="stea (doar direct)")
    axB.fill_between(ts, st, me, color="#1C7293", alpha=0.15)
    axB.set_xlabel("timp [s]"); axB.set_ylabel("acoperire creditata [%]")
    axB.set_ylim(0, 100); axB.grid(alpha=0.3); axB.legend(loc="lower right", fontsize=9)
    axB.set_title("Evolutia acoperirii")

    fig.suptitle("Stratul mesh recupereaza acoperirea pe care topologia in stea o pierde",
                 fontsize=13, y=1.02)
    fig.savefig("sil_mesh_mission.png", bbox_inches="tight")
    print("\n  [figura] sil_mesh_mission.png")


if __name__ == "__main__":
    sys.exit(0 if run() else 1)


def main():
    """Wrapper pentru entry-point 'ros2 run' (nu propaga bool-ul ca exit code)."""
    run()
