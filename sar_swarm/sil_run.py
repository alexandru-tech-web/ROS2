#!/usr/bin/env python3
"""
sil_run.py — Simulator software-in-the-loop al misiunii SAR multi-drona,
FARA ROS/Gazebo: aceeasi logica (nuclee identice cu nodurile ROS), rulabila
oriunde, pentru experimente repetabile si figuri.

Fluxul: GCS trimite misiunea -> dronele decoleaza, exploreaza frontierele
alocate de GCS (harti fuzionate cooperativ), ocolesc ruinele (A*), se evita
reciproc (separare), detecteaza victimele; canalul aplica degradarea din
FISIERUL DE SCENARIU (latenta/jitter/pierdere/izolare/partitie); la pierderea
GCS dronele trec pe comportamentele de avarie; store-and-forward livreaza
telemetria restanta la reconectare.

Utilizare:
    $ python3 sil_run.py scenarios/baseline.yaml [--out results/]
Iesiri per scenariu: metrics.csv (serii de timp), summary.json,
harta misiunii (PNG cu ruine/fum/victime/traiectorii/acoperire).
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sar_core import (GridWorld, DiscoveredMap, allocate_frontiers, cohesion,
                      FallbackPolicy, LINKED, LOCAL_EXPLORE, RETURN_TO_LINK,
                      LOITER, FREE_SEEN, OBSTACLE_SEEN)
from netem_core import Channel, load_scenario, apply_due_events
from swarm_core import DroneKinematics, goto_velocity, separation_velocity

from world_config import WORLD, ALT, SENSE_R
DT = 0.1
TELEM_HZ = 5.0
PROBE_HZ = 2.0


class SilDrone:
    def __init__(self, did, x, y, world):
        self.id = did
        self.kin = DroneKinematics(x=x, y=y, z=0.0)
        self.map = DiscoveredMap(world)
        self.fallback = FallbackPolicy(t_local=15.0)
        self.fallback.last_link_pos = (x, y)
        self.target = None          # (ci, cj) frontiera curenta
        self.path = []              # celule A*
        self.trail = [(x, y)]
        self.pending_cells = []     # diff de harta nesincronizat cu GCS
        self.cells_base = 0         # index monoton: celule confirmate de GCS
        self.victims_found = set()


def run(scen_path, out_dir):
    sc = load_scenario(scen_path)
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(scen_path))[0]
    world = GridWorld(**WORLD)
    ids = ["d1", "d2", "d3", "d4"]
    starts = [(3, 3), (3, 6), (6, 3), (6, 6)]
    drones = {d: SilDrone(d, x, y, world) for d, (x, y) in zip(ids, starts)}
    ch = Channel(["gcs"] + ids, default=sc["default_link"],
                 overrides=sc["link_overrides"],
                 store_and_forward=sc["store_and_forward"], seed=11)

    dlogs = {}
    for d in ids:
        dlogs[d] = open(os.path.join(out_dir, f"{name}_drone_{d}.csv"), "w")
        dlogs[d].write(
            "t_s,x,y,state,gcs_up,saf_buffered,cells_pending,dist_link\n")
    gcs_map = DiscoveredMap(world)
    gcs_last_seen = {d: 0.0 for d in ids}
    gcs_targets = {}
    victims_global = set()
    probe_sent = {d: {} for d in ids}     # seq -> t emis (RTT la GCS)
    rtt_log = []

    rows = []
    t, t_prev_ev = 0.0, -1.0
    next_telem = {d: 0.0 for d in ids}
    next_probe = 0.0
    next_alloc = 0.0
    done_t = None
    seq = 0

    while t < sc["duration_s"]:
        apply_due_events(ch, sc["events"], t_prev_ev, t)
        t_prev_ev = t

        # ---- GCS: sonda de latenta + realocare frontiere ----
        if t >= next_probe:
            next_probe = t + 1.0 / PROBE_HZ
            for d in ids:
                seq += 1
                probe_sent[d][seq] = t
                ch.send("gcs", d, {"k": "ping", "seq": seq}, t)
        if t >= next_alloc:
            next_alloc = t + 1.0
            pos_cells = {d: world.to_cell(*drones[d].trail[-1])
                         for d in ids if t - gcs_last_seen[d] < 4.0}
            alloc = allocate_frontiers(pos_cells, gcs_map.frontiers())
            for d, tgt in alloc.items():
                gcs_targets[d] = tgt
                ch.send("gcs", d, {"k": "goto_frontier", "cell": tgt}, t)

        # ---- livrarea mesajelor scadente ----
        for src, dst, msg, t0, t_del in ch.deliver(t):
            if dst == "gcs":
                if msg["k"] == "telemetry":
                    d = msg["id"]
                    gcs_last_seen[d] = t
                    gcs_map.merge_cells(msg["cells"])
                    for v in msg["victims"]:
                        victims_global.add(tuple(v))
                    # confirmare: drona poate uita celulele receptionate
                    ch.send("gcs", d, {"k": "map_ack",
                                       "upto": msg["from"] + len(msg["cells"])},
                            t_del)
                elif msg["k"] == "pong":
                    t_emit = probe_sent[msg["id"]].pop(msg["seq"], None)
                    if t_emit is not None:
                        rtt_log.append((t_del, msg["id"],
                                        (t_del - t_emit) * 1000.0))
            else:
                dr = drones[dst]
                if msg["k"] == "ping":
                    ch.send(dst, "gcs", {"k": "pong", "id": dst,
                                         "seq": msg["seq"]}, t_del)
                elif msg["k"] == "map_ack":
                    adv = msg["upto"] - dr.cells_base
                    if adv > 0:                      # ack-urile vechi: ignorate
                        del dr.pending_cells[:min(adv, len(dr.pending_cells))]
                        dr.cells_base = msg["upto"]
                elif msg["k"] == "goto_frontier":
                    dr.fallback.on_gcs_contact(drones[dst].trail[-1])
                    dr.target = tuple(msg["cell"])
                    dr.path = []

        # ---- dronele: fallback, planificare, miscare, percepere ----
        positions = {d: (drones[d].kin.x, drones[d].kin.y) for d in ids}
        for d in ids:
            dr = drones[d]
            if not ch.link_up("gcs", d):
                dr.fallback.on_link_lost(t)
            px, py = dr.kin.x, dr.kin.y
            st = dr.fallback.tick(
                t, (px, py),
                math.hypot(px - dr.fallback.last_link_pos[0],
                           py - dr.fallback.last_link_pos[1]) < 2.0)

            # tinta efectiva dupa stare
            if st == LOCAL_EXPLORE and (dr.target is None or not ch.link_up("gcs", d)):
                fr = dr.map.frontiers()
                if fr:
                    ci, cj = world.to_cell(px, py)
                    fr.sort(key=lambda f: (f[0]-ci)**2 + (f[1]-cj)**2)
                    dr.target = fr[0]
            if st == RETURN_TO_LINK:
                dr.target = world.to_cell(*dr.fallback.last_link_pos)
                dr.path = []
            if st == LOITER:
                ang = t * 0.5
                tx = dr.fallback.last_link_pos[0] + 3.0 * math.cos(ang)
                ty = dr.fallback.last_link_pos[1] + 3.0 * math.sin(ang)
                tgt_xy = (tx, ty)
            else:
                if dr.target is not None and not dr.path:
                    dr.path = dr.map.astar(world.to_cell(px, py), dr.target) or []
                if dr.path:
                    # avanseaza pe drum: sare celulele deja atinse
                    while len(dr.path) > 1 and \
                            math.hypot(*(a - b for a, b in
                                         zip(world.to_xy(*dr.path[0]), (px, py)))) < 1.2:
                        dr.path.pop(0)
                    tgt_xy = world.to_xy(*dr.path[0])
                else:
                    tgt_xy = (px, py)

            vx, vy, vz = goto_velocity(px, py, dr.kin.z,
                                       tgt_xy[0], tgt_xy[1], ALT)
            sx, sy = separation_velocity(px, py,
                                         [positions[o] for o in ids if o != d])
            dr.kin.step(vx + sx, vy + sy, vz, DT)
            dr.trail.append((dr.kin.x, dr.kin.y))

            cells, found = dr.map.reveal_disc(dr.kin.x, dr.kin.y, SENSE_R)
            dr.pending_cells.extend(cells)
            for v in found:
                if v not in dr.victims_found:
                    dr.victims_found.add(v)
            if dr.target and world.to_cell(dr.kin.x, dr.kin.y) == dr.target:
                dr.target = None
                dr.path = []

            if t >= next_telem[d]:
                next_telem[d] = t + 1.0 / TELEM_HZ
                # trimite fereastra neconfirmata (idempotent la GCS);
                # se goleste DOAR la map_ack -> robust la pierderi
                ch.send(d, "gcs", {"k": "telemetry", "id": d,
                                   "from": dr.cells_base,
                                   "cells": dr.pending_cells[:600],
                                   "victims": sorted(dr.victims_found)}, t)
                dl = ((dr.kin.x - dr.fallback.last_link_pos[0]) ** 2
                      + (dr.kin.y - dr.fallback.last_link_pos[1]) ** 2) ** 0.5
                dlogs[d].write(f"{t:.2f},{dr.kin.x:.2f},{dr.kin.y:.2f},"
                               f"{dr.fallback.state},,,"
                               f"{len(dr.pending_cells)},{dl:.2f}\n")

        cov = gcs_map.coverage()
        rows.append((round(t, 2), round(cov, 4), len(victims_global),
                     round(cohesion(positions), 3),
                     sum(1 for d in ids if drones[d].fallback.state != LINKED)))
        if done_t is None and cov >= 0.95 and \
                len(victims_global) == len(world.victims):
            done_t = t
            break
        t += DT

    # ---------- iesiri ----------
    name = os.path.splitext(os.path.basename(scen_path))[0]
    with open(os.path.join(out_dir, f"{name}_metrics.csv"), "w") as f:
        f.write("t_s,coverage,victims_found,cohesion,drones_in_fallback\n")
        for r in rows:
            f.write(",".join(map(str, r)) + "\n")
    for fh in dlogs.values():
        fh.close()
    stats = ch.stats()
    gcs_links = {k: v for k, v in stats.items() if "gcs" in k}
    summary = {
        "scenario": sc["name"],
        "mission_time_s": done_t if done_t is not None else sc["duration_s"],
        "completed": done_t is not None,
        "coverage_final": rows[-1][1],
        "victims_found": rows[-1][2], "victims_total": len(world.victims),
        "cohesion_mean": round(sum(r[3] for r in rows) / len(rows), 3),
        "disconnected_total_s": round(sum(v["down_total_s"]
                                          for v in gcs_links.values()), 1),
        "recovery_time_mean_s": round(
            (lambda rt: sum(rt) / len(rt) if rt else 0.0)
            ([x for v in gcs_links.values() for x in v["recovery_times_s"]]), 2),
        "loss_measured_gcs": round(
            sum(v["lost"] for v in gcs_links.values())
            / max(1, sum(v["sent"] for v in gcs_links.values())), 3),
        "rtt_p95_ms": round(
            (lambda L: sorted(L)[int(0.95 * (len(L) - 1))] if L else 0.0)
            ([r[2] for r in rtt_log if r[2] < 5000.0]), 1),
        "probe_timeouts": sum(1 for r in rtt_log if r[2] >= 5000.0)
                          + sum(len(v) for v in probe_sent.values()),
        "links": stats,
    }
    with open(os.path.join(out_dir, f"{name}_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    render_map(world, gcs_map, drones, victims_global,
               os.path.join(out_dir, f"{name}_map.png"), sc["name"])
    return summary


def render_map(world, gmap, drones, victims_found, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    img = np.zeros((world.h, world.w, 3))
    for j in range(world.h):
        for i in range(world.w):
            st = gmap.state[j][i]
            img[j, i] = ((0.15, 0.15, 0.18) if st == 0 else
                         (0.55, 0.75, 0.55) if st == FREE_SEEN else
                         (0.35, 0.25, 0.22))
    fig, ax = plt.subplots(figsize=(7.6, 7.2))
    ax.imshow(img, origin="lower",
              extent=[0, world.w * world.cell, 0, world.h * world.cell])
    for sx, sy, r in world.smoke:
        ax.add_patch(plt.Circle((sx, sy), r, color="gray", alpha=0.35))
    for (vi, vj) in world.victims:
        x, y = world.to_xy(vi, vj)
        ok = (vi, vj) in victims_found
        ax.plot(x, y, "*", ms=16, color="#ffd24d" if ok else "#d04444",
                mec="k", label=None)
    colors = ["#2E73CC", "#d8702e", "#2E8B57", "#9b59b6"]
    for c, (d, dr) in zip(colors, sorted(drones.items())):
        xs, ys = zip(*dr.trail)
        ax.plot(xs, ys, color=c, lw=1.2, label=d)
        ax.plot(xs[-1], ys[-1], "o", color=c, ms=8, mec="k")
    ax.set_title(f"Misiune SAR — {title}\n(verde=cartografiat, maro=ruine, "
                 f"gri=fum, stea galbena=victima gasita)", fontsize=10)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    scen = sys.argv[1] if len(sys.argv) > 1 else "scenarios/baseline.yaml"
    out = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--out" else "results"
    s = run(scen, out)
    print(json.dumps({k: v for k, v in s.items() if k != "links"}, indent=1))
