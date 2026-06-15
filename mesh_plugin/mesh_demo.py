#!/usr/bin/env python3
"""mesh_demo.py -- demonstratia LIVE a retelei mesh multi-hop.

Fereastra Tkinter care arata, in timp real, cum se comporta reteaua mesh cand
blochezi drone. Doua moduri:

  STANDALONE (implicit, fara ROS): dronele se misca dupa un scenariu intern
    (se imprastie de la GCS); poti rula oriunde, inclusiv la aparare/prezentare.
      python3 mesh_demo.py

  ROS (daca rclpy + roiul sunt disponibili): citeste pozitiile reale din
    /sar/telemetry si publica blocarile pe /mesh/control.
      python3 mesh_demo.py --ros

Ce vezi pe harta:
  * GCS (stea aurie) in coltul de jos-stanga;
  * fiecare drona ca un cerc:
      ALBASTRU = are legatura DIRECTA cu GCS (1 hop, ca in stea);
      PORTOCALIU = ajunge la GCS doar prin RELAY multi-hop (mesh o salveaza);
      ROSU = IZOLATA (nici macar mesh-ul nu o mai conecteaza);
      GRI taiat = BLOCATA de tine (drona doborata);
  * linii VERZI = ruta multi-hop efectiva spre GCS (next-hop cu next-hop);
  * un buton sub fiecare drona: "blocheaza" / "deblocheaza".

Sub harta: bilantul star vs mesh (cate ajung direct, cate sunt recuperate de
mesh, cate raman izolate) -- exact metrica contributiei C3.

Toata logica de retea vine din mesh_core (testat 31/31); aici e doar
vizualizare + interactiune.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from radio_link import make_link
from mesh_core import MeshGraph, ETX_INF, star_reachable, mesh_vs_star

try:
    import tkinter as tk
except ImportError:
    sys.exit("tkinter lipseste (sudo apt install python3-tk)")


# ------------------------------- config -------------------------------
IDS = ["d1", "d2", "d3", "d4"]
GCS = (0.0, 0.0)
PROFILE = "urban_rubble"
PDR_MIN = 0.10

# zona desenata [m]
XMIN, XMAX, YMIN, YMAX = -15.0, 130.0, -25.0, 60.0
CANVAS_W, CANVAS_H = 760, 460

COL_DIRECT = "#2E73CC"     # link direct la GCS
COL_RELAY = "#d8702e"      # ajunge prin relay multi-hop
COL_ISOLATED = "#c0392b"   # izolat complet
COL_BLOCKED = "#777777"    # blocat de operator
COL_EDGE = "#bcd6c2"       # muchii radio utilizabile
COL_ROUTE = "#2E8B57"      # ruta efectiva spre GCS


# tinte finale (scenariul standalone): d1/d2 raman in raza, d3/d4 pleaca departe
TARGETS = {
    "d1": (45.0, 0.0),
    "d2": (45.0, 35.0),
    "d3": (100.0, 0.0),
    "d4": (100.0, 35.0),
}
STARTS = {d: (8.0, 5.0 + i * 6) for i, d in enumerate(IDS)}


class MeshState:
    """Starea retelei: pozitii + blocari + graful. Sursa unica de adevar
    pentru desen, indiferent de modul standalone/ROS."""

    def __init__(self, profile=PROFILE, pdr_min=PDR_MIN):
        self.link = make_link(profile, shadow_sigma_db=0.0)
        self.graph = MeshGraph(self.link, pdr_min=pdr_min)
        self.poses = {"gcs": GCS}
        self.blocked = set()
        self.t = 0.0

    def set_pose(self, did, x, y):
        self.poses[did] = (float(x), float(y))

    def toggle_block(self, did):
        if did in self.blocked:
            self.blocked.discard(did)
        else:
            self.blocked.add(did)

    def recompute(self):
        self.poses["gcs"] = GCS
        self.graph.set_positions(self.poses)
        self.graph.down_nodes = set(self.blocked)
        self.graph._rebuild_edges()
        dist, nh = self.graph.shortest_paths_to("gcs")
        star = star_reachable(self.graph, "gcs")
        bil = mesh_vs_star(self.graph, "gcs")
        return dist, nh, star, bil

    # scenariul intern de miscare (standalone)
    def step_standalone(self, dt=0.1, t_spread=12.0):
        self.t += dt
        frac = min(1.0, self.t / t_spread)
        for d in IDS:
            sx, sy = STARTS[d]
            tx, ty = TARGETS[d]
            self.set_pose(d, sx + (tx - sx) * frac, sy + (ty - sy) * frac)


def build_gui(state, ros_hook=None):
    """ros_hook: optional dict cu callbacks {'publish_block': fn(did, blocked)}
    pentru modul ROS. In standalone e None."""
    root = tk.Tk()
    root.title("mesh_plugin -- demo multi-hop (blocheaza drone, vezi relay-ul)")

    cv = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg="#f4f1ea",
                   highlightthickness=0)
    cv.grid(row=0, column=0, columnspan=len(IDS) + 1, padx=6, pady=6)

    # bara de butoane (un buton per drona)
    btns = {}
    for i, d in enumerate(IDS):
        b = tk.Button(root, text=f"blocheaza {d}", width=14,
                      command=lambda dd=d: on_toggle(dd))
        b.grid(row=1, column=i, padx=3, pady=3)
        btns[d] = b
    reset_btn = tk.Button(root, text="reset (deblocheaza tot)", width=20,
                          command=lambda: on_reset())
    reset_btn.grid(row=1, column=len(IDS), padx=3, pady=3)

    status_var = tk.StringVar(value="")
    status = tk.Label(root, textvariable=status_var, font=("TkDefaultFont", 11),
                      justify="left", anchor="w")
    status.grid(row=2, column=0, columnspan=len(IDS) + 1, sticky="w", padx=8,
                pady=(0, 8))

    legend_var = tk.StringVar(value=(
        "albastru = link direct la GCS   |   portocaliu = ajunge prin RELAY "
        "(mesh o salveaza)   |   rosu = izolat   |   gri = blocat de tine"))
    tk.Label(root, textvariable=legend_var, fg="#444").grid(
        row=3, column=0, columnspan=len(IDS) + 1, sticky="w", padx=8,
        pady=(0, 8))

    def on_toggle(did):
        state.toggle_block(did)
        if ros_hook:
            ros_hook["publish_block"](did, did in state.blocked)
        btns[did].config(text=("deblocheaza " + did) if did in state.blocked
                         else ("blocheaza " + did))

    def on_reset():
        for d in list(state.blocked):
            if ros_hook:
                ros_hook["publish_block"](d, False)
        state.blocked.clear()
        for d in IDS:
            btns[d].config(text="blocheaza " + d)

    def P(x, y):
        """lume -> canvas (y in sus)."""
        cx = (x - XMIN) / (XMAX - XMIN) * CANVAS_W
        cy = CANVAS_H - (y - YMIN) / (YMAX - YMIN) * CANVAS_H
        return cx, cy

    def draw():
        # in standalone, dronele se misca singure
        if ros_hook is None:
            state.step_standalone()
        dist, nh, star, bil = state.recompute()
        cv.delete("all")

        # muchiile radio utilizabile (fundal)
        for (a, b) in state.graph.edges:
            ax, ay = state.poses[a]
            bx, by = state.poses[b]
            x0, y0 = P(ax, ay)
            x1, y1 = P(bx, by)
            cv.create_line(x0, y0, x1, y1, fill=COL_EDGE, width=1)

        # rutele efective spre GCS (next-hop in lant) -- linii verzi groase
        for d in IDS:
            if d in state.blocked or dist.get(d, ETX_INF) == ETX_INF:
                continue
            cur = d
            guard = 0
            while cur != "gcs" and guard < 10:
                nxt = nh.get(cur)
                if nxt is None:
                    break
                ax, ay = state.poses[cur]
                bx, by = state.poses[nxt]
                x0, y0 = P(ax, ay)
                x1, y1 = P(bx, by)
                cv.create_line(x0, y0, x1, y1, fill=COL_ROUTE, width=3,
                               arrow=tk.LAST)
                cur = nxt
                guard += 1

        # GCS
        gx, gy = P(*GCS)
        cv.create_text(gx, gy - 18, text="GCS", font=("TkDefaultFont", 11,
                       "bold"))
        cv.create_polygon(gx, gy - 12, gx + 11, gy + 9, gx - 11, gy + 9,
                          fill="gold", outline="black")

        # dronele
        for d in IDS:
            x, y = state.poses[d]
            cx, cy = P(x, y)
            if d in state.blocked:
                col = COL_BLOCKED
            elif d in star:
                col = COL_DIRECT
            elif dist.get(d, ETX_INF) < ETX_INF:
                col = COL_RELAY
            else:
                col = COL_ISOLATED
            r = 13
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col,
                           outline="black", width=2)
            cv.create_text(cx, cy, text=d, fill="white",
                           font=("TkDefaultFont", 10, "bold"))
            # eticheta hopuri / stare
            if d in state.blocked:
                tag = "blocata"
                cv.create_line(cx - r, cy - r, cx + r, cy + r, fill="black",
                               width=2)
            elif d in star:
                tag = "direct"
            elif dist.get(d, ETX_INF) < ETX_INF:
                h = state.graph.hop_count_to("gcs").get(d, "?")
                tag = f"relay {h} hop"
            else:
                tag = "IZOLATA"
            cv.create_text(cx, cy + r + 10, text=tag, fill=col,
                           font=("TkDefaultFont", 9, "bold"))

        # bilantul star vs mesh
        recovered = ", ".join(bil["recovered_by_mesh"]) or "-"
        isolated = ", ".join(bil["isolated_even_in_mesh"]) or "-"
        status_var.set(
            f"STEA: {bil['n_star']}/{bil['n_total']} drone ajung direct la GCS"
            f"      MESH: {bil['n_mesh']}/{bil['n_total']} ajung "
            f"(prin relay multi-hop)\n"
            f"recuperate DOAR de mesh: {recovered}        "
            f"izolate complet: {isolated}        "
            f"blocate de tine: {', '.join(sorted(state.blocked)) or '-'}")

        root.after(100, draw)

    draw()
    return root


# ------------------------------- ROS hook -------------------------------
def run_ros():
    """Mod ROS: citeste /sar/telemetry, publica /mesh/control. Necesita rclpy
    si roiul pornit."""
    import json
    import threading
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    from node_utils import qos_best_effort
    from mesh_node import parse_telemetry

    state = MeshState()

    class Bridge(Node):
        def __init__(self):
            super().__init__("mesh_demo_bridge")
            self.create_subscription(String, "/sar/telemetry",
                                     self.on_tel, qos_best_effort(30))
            self.ctrl = self.create_publisher(String, "/mesh/control", 10)

        def on_tel(self, msg):
            for did, (x, y) in parse_telemetry(msg.data).items():
                state.set_pose(did, x, y)

        def publish_block(self, did, blocked):
            self.ctrl.publish(String(data=json.dumps(
                {"action": "block" if blocked else "unblock", "id": did})))

    rclpy.init()
    bridge = Bridge()
    spin = threading.Thread(target=rclpy.spin, args=(bridge,), daemon=True)
    spin.start()
    root = build_gui(state, ros_hook={"publish_block": bridge.publish_block})
    try:
        root.mainloop()
    finally:
        bridge.destroy_node()
        rclpy.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ros", action="store_true",
                    help="citeste pozitii reale din /sar/telemetry")
    a = ap.parse_args()
    if a.ros:
        run_ros()
    else:
        state = MeshState()
        root = build_gui(state, ros_hook=None)
        root.mainloop()


if __name__ == "__main__":
    main()
