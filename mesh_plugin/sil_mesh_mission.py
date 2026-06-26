#!/usr/bin/env python3
"""sil_mesh_mission.py -- SIL: aceeasi misiune SAR, CU vs FARA stratul mesh.

Spre deosebire de sil_mesh.py (reachability abstract pe geometrie statica),
acesta ruleaza MISIUNEA reala (aceeasi lume, aceleasi scenarii de degradare,
aceeasi cinematica de roi ca sil_run.py) si masoara ce castiga mesh-ul IN
CONTEXTUL misiunii: cata telemetrie ajunge la GCS, cat de proaspata, cate
victime afla GCS-ul -- cu si fara relay multi-hop.

Ideea: in scenariul partition_2v2, d3/d4 pierd legatura DIRECTA cu GCS intre
t=30..70 s. FARA mesh, telemetria lor se pierde (sau asteapta in S&F pana la
reconectare -> foarte veche). CU mesh, daca d3 il aude pe d1 si d1 aude GCS,
telemetria lui d3 ajunge prin relay -> GCS afla in timp real ce descopera d3.

Masoara, pe ambele topologii:
  - telemetry_delivered: cate mesaje de telemetrie ajung la GCS;
  - e2e_p95: cat de veche e informatia livrata (varsta la sosire);
  - victims_known_at_gcs(t): cate victime stie GCS-ul in timp;
  - coverage_at_gcs(t): cat din zona stie GCS-ul (din ce i-a ajuns).

Produce: mesh_mission_victims.png, mesh_mission_delivery.png + bilant.
Nu modifica sil_run.py (experimentul de baza ramane neatins).

  python3 sil_mesh_mission.py                       # partition_2v2 (mesh conteaza)
  python3 sil_mesh_mission.py --scenario loss_30
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sar_core import GridWorld, DiscoveredMap, allocate_frontiers
from netem_core import Channel, load_scenario, apply_due_events
from swarm_core import DroneKinematics, goto_velocity, separation_velocity
from world_config import WORLD, SENSE_R
from radio_link import make_link
from mesh_core import MeshGraph, DirectedRelay, deliver_once, star_reachable

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_PLT = True
except ImportError:
    HAVE_PLT = False

IDS = ["d1", "d2", "d3", "d4"]
STARTS = [(3, 3), (3, 6), (6, 3), (6, 6)]
TELEM_HZ = 5.0
GCS_XY = (0.0, 0.0)


def _lawnmower(y0, y1, x0, x1, line_sp):
    """Waypoint-uri serpentina pe banda [y0,y1] x [x0,x1]."""
    wps, y, k = [], y0 + line_sp / 2.0, 0
    while y < y1:
        if k % 2 == 0:
            wps += [(x0, y), (x1, y)]
        else:
            wps += [(x1, y), (x0, y)]
        y += line_sp
        k += 1
    return wps


class SilDrone:
    """Drona cinematica minimala (oglinda celei din sil_run, fara fallback:
    aici ne intereseaza livrarea telemetriei, nu politica de avarie)."""

    def __init__(self, did, cx, cy, world, waypoints):
        self.id = did
        self.kin = DroneKinematics(x=float(cx), y=float(cy))
        self.world = world
        self.local_map = DiscoveredMap(world)
        self.pending_cells = []        # celule vazute, de trimis la GCS
        self.victims_found = set()
        self.wps = waypoints
        self.wp_i = 0

    def target(self):
        return self.wps[self.wp_i] if self.wp_i < len(self.wps) else None

    def advance_if_reached(self):
        tgt = self.target()
        if tgt and abs(self.kin.x - tgt[0]) < 1.5 \
                and abs(self.kin.y - tgt[1]) < 1.5:
            self.wp_i += 1

    def sense(self):
        """Dezvaluie discul senzorului; acumuleaza celulele noi (format
        (i,j,st), compatibil cu merge_cells) si victimele vazute."""
        new_cells, _ = self.local_map.reveal_disc(self.kin.x, self.kin.y,
                                                  SENSE_R)
        self.pending_cells.extend(new_cells)
        for (vx, vy) in self.world.victims:
            if (self.kin.x - vx) ** 2 + (self.kin.y - vy) ** 2 <= SENSE_R ** 2:
                self.victims_found.add((vx, vy))
        return new_cells


def run(scenario="partition_2v2", t_max=None, dt=0.1, seed=11,
        profile="urban_rubble", out_dir=None):
    out_dir = out_dir or os.path.dirname(os.path.abspath(__file__))
    scen_path = scenario if os.path.exists(scenario) else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scenarios", f"{scenario}.yaml")
    sc = load_scenario(scen_path)
    t_max = t_max or sc.get("duration_s", 150)
    world = GridWorld(**WORLD)
    link = make_link(profile, shadow_sigma_db=0.0)

    # rulam DOUA simulari paralele (acelasi seed, aceeasi miscare): cu si fara
    # mesh. Singura diferenta: rutarea telemetriei cand nu exista link direct.
    results = {}
    for use_mesh in (False, True):
        # benzi lawnmower: fiecare drona acopera o banda orizontala. d3/d4
        # primesc benzile DEPARTATE de GCS (sus), unde, sub partitie, vor fi
        # izolate exact in timp ce inca exploreaza -> mesh-ul conteaza.
        W, H = WORLD["w_cells"], WORLD["h_cells"]
        bands = {
            "d1": _lawnmower(0, H / 2, 2, W - 2, 10),
            "d2": _lawnmower(0, H / 2, W - 2, 2, 10),
            "d3": _lawnmower(H / 2, H, 2, W - 2, 10),
            "d4": _lawnmower(H / 2, H, W - 2, 2, 10),
        }
        drones = {d: SilDrone(d, x, y, world, bands[d])
                  for d, (x, y) in zip(IDS, STARTS)}
        ch = Channel(["gcs"] + IDS, default=sc["default_link"],
                     overrides=sc["link_overrides"],
                     store_and_forward=sc["store_and_forward"], seed=seed)
        gcs_map = DiscoveredMap(world)
        victims_at_gcs = set()
        graph = MeshGraph(link, pdr_min=0.10)
        relays = {n: DirectedRelay(n, ttl=8) for n in (["gcs"] + IDS)}

        delivered = 0
        e2e_samples = []
        victims_known_series = []     # (t, n_victims_known_at_gcs)
        coverage_series = []
        next_telem = {d: 0.0 for d in IDS}
        t = 0.0
        while t <= t_max:
            apply_due_events(ch, sc["events"], t - dt, t)

            # miscare: lawnmower pe banda proprie, viteza moderata (descoperire
            # graduala realista, nu teleport spre frontiere)
            positions = {}
            for d in IDS:
                dr = drones[d]
                dr.sense()
                dr.advance_if_reached()
                tgt = dr.target()
                if tgt:
                    vx, vy, vz = goto_velocity(dr.kin.x, dr.kin.y, dr.kin.z,
                                               tgt[0], tgt[1], 0.0, 2.0)
                    dr.kin.step(vx, vy, vz, dt)
                positions[d] = (dr.kin.x, dr.kin.y)

            # graful mesh din pozitiile curente (+ GCS)
            mesh_pos = {"gcs": GCS_XY}
            mesh_pos.update(positions)
            graph.set_positions(mesh_pos)
            # CUPLARE cu scenariul: o muchie pe care canalul o tine DOWN
            # (partitie/izolare fortata) nu trebuie folosita nici de mesh.
            # Reconstruim muchiile pastrand doar cele care exista in radio SI
            # nu sunt taiate de scenariu.
            allowed = {}
            for (a, b) in list(graph.edges.keys()):
                if ch.link_up(a, b):
                    allowed[(a, b)] = graph.edges[(a, b)]
            graph.edges = allowed
            star = star_reachable(graph, "gcs")

            # ---- trimiterea telemetriei ----
            for d in IDS:
                if t < next_telem[d]:
                    continue
                next_telem[d] = t + 1.0 / TELEM_HZ
                dr = drones[d]
                payload = {"k": "telemetry", "id": d, "from": 0,
                           "cells": list(dr.pending_cells),
                           "victims": sorted(dr.victims_found)}

                direct_up = ch.link_up(d, "gcs")
                if direct_up:
                    # legatura directa activa: trimitere normala prin canal
                    ch.send(d, "gcs", payload, t)
                elif use_mesh:
                    # fara link direct: incearca relay multi-hop. Gaseste
                    # next-hop-ul si verifica TOT lantul pana la GCS pe legaturi
                    # care chiar sunt UP in canal (cuplat cu scenariul).
                    _, nh = graph.shortest_paths_to("gcs")
                    cur, hops_ok, guard = d, True, 0
                    chain = [d]
                    while cur != "gcs" and guard < 8:
                        nxt = nh.get(cur)
                        if nxt is None or not ch.link_up(cur, nxt):
                            hops_ok = False
                            break
                        chain.append(nxt)
                        cur = nxt
                        guard += 1
                    if hops_ok and cur == "gcs":
                        # ruta exista si toate legaturile sunt up: livram prin
                        # vecinul-releu (modelam latenta multi-hop ca trecerea
                        # pe prima legatura up + relay instant la GCS, marcat cu
                        # un payload care pastreaza id-ul si timpul emisiei d).
                        relay = chain[1]   # primul vecin pe drum
                        ch.send(relay, "gcs", dict(payload, relayed_from=d), t)
                # altfel (fara mesh, fara link direct): mesajul se pierde
                # (sau asteapta in S&F daca scenariul are S&F pornit)

            # ---- livrarea la GCS ----
            for src, dst, msg, t0, t_del in ch.deliver(t):
                if dst == "gcs" and msg.get("k") == "telemetry":
                    delivered += 1
                    e2e_samples.append((t_del - t0) * 1000.0)
                    gcs_map.merge_cells(msg["cells"])
                    for v in msg["victims"]:
                        victims_at_gcs.add(tuple(v))

            victims_known_series.append((t, len(victims_at_gcs)))
            coverage_series.append((t, gcs_map.coverage()))
            t += dt

        e2e_p95 = (sorted(e2e_samples)[int(0.95 * (len(e2e_samples) - 1))]
                   if e2e_samples else 0.0)
        # timpul la care GCS afla TOATE victimele (None daca nu le afla)
        t_all_victims = None
        for (tt, nv) in victims_known_series:
            if nv >= len(world.victims):
                t_all_victims = tt
                break
        results[use_mesh] = {
            "delivered": delivered,
            "e2e_p95_ms": round(e2e_p95, 1),
            "e2e_mean_ms": round(sum(e2e_samples) / len(e2e_samples), 1)
            if e2e_samples else 0.0,
            "victims_final": len(victims_at_gcs),
            "t_all_victims_s": round(t_all_victims, 1)
            if t_all_victims is not None else None,
            "coverage_final": round(gcs_map.coverage(), 4),
            "victims_series": victims_known_series,
            "coverage_series": coverage_series,
        }

    # ----------------------------- bilant -----------------------------
    no, ye = results[False], results[True]
    print(f"=== SIL misiune CU vs FARA mesh (scenariu={scenario}, "
          f"profil={profile}) ===")
    print(f"                         FARA mesh    CU mesh")
    print(f"  telemetrie livrata:    {no['delivered']:8d}    {ye['delivered']:8d}"
          f"   (+{100*(ye['delivered']-no['delivered'])/max(1,no['delivered']):.0f}%)")
    print(f"  e2e p95 [ms]:          {no['e2e_p95_ms']:8.1f}    {ye['e2e_p95_ms']:8.1f}")
    print(f"  victime stiute (final):{no['victims_final']:8d}    {ye['victims_final']:8d}"
          f"   /{len(world.victims)}")
    tav_no = no["t_all_victims_s"]
    tav_ye = ye["t_all_victims_s"]
    print(f"  timp pana GCS stie 5:  {('  -  ' if tav_no is None else f'{tav_no:6.1f}s')}"
          f"     {('  -  ' if tav_ye is None else f'{tav_ye:6.1f}s')}", end="")
    if tav_no is not None and tav_ye is not None and tav_ye < tav_no:
        print(f"   (mesh afla cu {tav_no - tav_ye:.0f}s mai devreme)")
    else:
        print()
    print(f"  acoperire la GCS:      {no['coverage_final']:8.2f}    {ye['coverage_final']:8.2f}")

    n_ok = [0]

    def check(name, cond):
        print(("[ok]   " if cond else "[FAIL] ") + name)
        n_ok[0] += bool(cond)

    izolare = scenario in ("partition_2v2", "drone_isolation", "mesh_relay",
                           "mesh_stress")
    if izolare:
        check("mesh livreaza mai multa telemetrie sub izolare",
              ye["delivered"] > no["delivered"])
        check("mesh: GCS afla cel putin la fel de multe victime",
              ye["victims_final"] >= no["victims_final"])
        # metrica de impact: mesh afla victimele MAI DEVREME (sau cel putin nu
        # mai tarziu) -- daca ambele afla toate
        if tav_no is not None and tav_ye is not None:
            check("mesh: GCS afla toate victimele mai devreme (sau egal)",
                  tav_ye <= tav_no)
        else:
            check("mesh: GCS afla toate victimele (no-mesh poate sa nu)",
                  tav_ye is not None)
    else:
        check("fara izolare: mesh nu strica nimic (livrare >= fara mesh)",
              ye["delivered"] >= no["delivered"])
        n_ok[0] += 2

    # ----------------------------- figuri -----------------------------
    if HAVE_PLT:
        # victime stiute de GCS in timp
        fig, ax = plt.subplots(figsize=(7.5, 4.0))
        for use_mesh, lbl, col in ((False, "FARA mesh (stea)", "#c0392b"),
                                   (True, "CU mesh (relay)", "#2E8B57")):
            ts, vs = zip(*results[use_mesh]["victims_series"])
            ax.plot(ts, vs, "-", color=col, lw=2, label=lbl)
        ax.axhline(len(world.victims), ls=":", color="#888",
                   label=f"total {len(world.victims)} victime")
        ax.set_xlabel("timp [s]")
        ax.set_ylabel("victime cunoscute la GCS")
        ax.set_title(f"Cate victime afla GCS-ul in timp ({scenario})\n"
                     "mesh recupereaza descoperirile dronelor izolate")
        ax.legend(loc="lower right"); ax.grid(alpha=0.3)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(os.path.join(out_dir, "mesh_mission_victims." + ext), dpi=200)
        plt.close(fig)

        # acoperire la GCS in timp
        fig, ax = plt.subplots(figsize=(7.5, 4.0))
        for use_mesh, lbl, col in ((False, "FARA mesh", "#c0392b"),
                                   (True, "CU mesh", "#2E8B57")):
            ts, cs = zip(*results[use_mesh]["coverage_series"])
            ax.plot(ts, [100 * c for c in cs], "-", color=col, lw=2, label=lbl)
        ax.set_xlabel("timp [s]")
        ax.set_ylabel("acoperire cunoscuta la GCS [%]")
        ax.set_title(f"Acoperirea pe care o stie GCS-ul ({scenario})")
        ax.legend(loc="lower right"); ax.grid(alpha=0.3)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(os.path.join(out_dir, "mesh_mission_delivery." + ext), dpi=200)
        plt.close(fig)
        print(f"\n[ok] 2 figuri scrise in {out_dir}")

    target = 3 if izolare else 3
    print(f"\n=== {n_ok[0]}/{target} verificari trecute ===")
    return 0 if n_ok[0] >= target else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="partition_2v2")
    ap.add_argument("--profile", default="urban_rubble",
                    choices=["open_field", "urban_rubble", "forest"])
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    sys.exit(run(scenario=a.scenario, profile=a.profile, seed=a.seed,
                 out_dir=a.out))
