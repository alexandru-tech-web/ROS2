#!/usr/bin/env python3
"""
dashboard_node.py — ECRANUL CU DATE al misiunii SAR (Tkinter).

Stanga: harta live — ruine, zone de fum, victime (rosu = negasita,
auriu = gasita), dronele cu urme colorate si starea de fallback.
Dreapta: scenariul activ si timpul, acoperirea, victimele, si PER DRONA:
legatura (SUS/JOS), vechimea telemetriei, starea, RTT mediu/p95 si
pierderea pe fereastra de 10 s (de la sonda de latenta).

Surse: /sar/status (GCS), /sar/pose/{id}, /sar/probe/stats, /sar/linkstate.
Necesita: sudo apt install -y python3-tk
"""

import json
import os
import sys
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_config import WORLD, DRONES
import fault_panel

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("Lipseste Tkinter: sudo apt install -y python3-tk", file=sys.stderr)
    sys.exit(1)

IDS = sorted(DRONES)
COL = {"d1": "#2E73CC", "d2": "#d8702e", "d3": "#2E8B57", "d4": "#9b59b6"}
SCALE = 9  # pixeli / metru


class DashNode(Node):
    def __init__(self):
        super().__init__("sar_dashboard")
        self.lock = threading.Lock()
        self.status = {}
        self.linkstate = {}
        self.probe = {}
        self.pose = {d: DRONES[d] + (0,) for d in IDS}
        self.trail = {d: [] for d in IDS}
        self.create_subscription(String, "/sar/status", self._mk("status"), 10)
        self.create_subscription(String, "/sar/linkstate", self._mk("linkstate"), 10)
        self.create_subscription(String, "/sar/probe/stats", self._mk("probe"), 10)
        self.op_pub = self.create_publisher(String, "/sar/operator", 10)
        for d in IDS:
            self.create_subscription(String, f"/sar/pose/{d}",
                                     self._pose_cb(d), 20)

    def _mk(self, attr):
        def cb(msg):
            with self.lock:
                setattr(self, attr, json.loads(msg.data))
        return cb

    def _pose_cb(self, d):
        def cb(msg):
            p = json.loads(msg.data)
            with self.lock:
                self.pose[d] = tuple(p["pos"])
                self.trail[d].append(tuple(p["pos"][:2]))
                self.trail[d] = self.trail[d][-400:]
                self.pose_state = p.get("state", "?")
        return cb

    def send_op(self, payload: dict):
        self.op_pub.publish(String(data=json.dumps(payload)))


def build_gui(node: DashNode):
    W = WORLD["w_cells"] * SCALE
    root = tk.Tk()
    root.title("SAR Swarm — ecranul cu date al misiunii")
    cv = tk.Canvas(root, width=W, height=W, bg="#1b1b22")
    cv.grid(row=0, column=0, padx=6, pady=6)
    side = ttk.Frame(root)
    side.grid(row=0, column=1, sticky="ns", padx=8, pady=8)

    # ----- BARA DE CONTROL A OPERATORULUI (om-in-bucla) -----
    bar = ttk.Frame(root)
    bar.grid(row=1, column=0, columnspan=2, sticky="we", padx=6, pady=(0, 6))
    sel = tk.StringVar(value=IDS[0])
    op = node.send_op

    ttk.Label(bar, text="Misiune:").pack(side="left")
    for lbl, act in (("Start", "start"), ("Pauza", "pause"),
                     ("Reluare", "resume"), ("Abort->RTH", "abort")):
        ttk.Button(bar, text=lbl, width=10, command=lambda a=act: op(
            {"type": "mission", "action": a})).pack(side="left", padx=1)
    ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
    ttk.Label(bar, text="Drona:").pack(side="left")
    ttk.OptionMenu(bar, sel, IDS[0], *IDS).pack(side="left", padx=2)
    for lbl, act in (("Stationeaza", "hold"), ("Auto", "resume"),
                     ("Acasa", "rth")):
        ttk.Button(bar, text=lbl, width=11, command=lambda a=act: op(
            {"type": "drone", "id": sel.get(), "action": a})
            ).pack(side="left", padx=1)
    ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
    ttk.Label(bar, text="Defecte:").pack(side="left")
    ttk.Button(bar, text="Izoleaza sel.", command=lambda: op(
        {"type": "fault", "action": "isolate", "id": sel.get()})
        ).pack(side="left", padx=1)
    ttk.Button(bar, text="Restabileste sel.", command=lambda: op(
        {"type": "fault", "action": "restore", "id": sel.get()})
        ).pack(side="left", padx=1)
    ttk.Button(bar, text="Partitie 2v2", command=lambda: op(
        {"type": "fault", "action": "partition"})).pack(side="left", padx=1)
    ttk.Button(bar, text="Latenta 2 s", command=lambda: op(
        {"type": "fault", "action": "latency", "ms": 2000})
        ).pack(side="left", padx=1)

    def _heal():
        op({"type": "fault", "action": "set_all", "ms": 40, "jit": 0,
            "loss": 0, "down": False})
    ttk.Button(bar, text="Vindeca tot", command=_heal).pack(side="left", padx=1)
    ttk.Button(bar, text="Defecte custom…", command=lambda:
               fault_panel.open_panel(root, node.send_op)
               ).pack(side="left", padx=(8, 1))

    head = tk.StringVar(value="astept GCS...")
    ttk.Label(side, textvariable=head, font=("TkDefaultFont", 11, "bold"),
              wraplength=300).pack(anchor="w", pady=4)
    rows = {}
    for d in IDS:
        f = ttk.LabelFrame(side, text=f"drona {d}")
        f.pack(fill="x", pady=4)
        v = tk.StringVar(value="—")
        ttk.Label(f, textvariable=v, justify="left",
                  foreground=COL[d]).pack(anchor="w", padx=6, pady=3)
        rows[d] = v
    note = ttk.Label(side, foreground="#888", wraplength=300, justify="left",
                     text="CLICK pe harta = trimite drona selectata acolo "
                          "(goto). Legaturile cazute apar ca X pe drona. "
                          "RTT/pierdere: fereastra de 10 s a sondei.")
    note.pack(anchor="w", pady=8)

    def P(x, y):  # lume -> canvas (y in sus)
        return x * SCALE, W - y * SCALE

    def on_click(ev):           # click pe harta = goto pentru drona selectata
        ci, cj = int(ev.x / SCALE), int((W - ev.y) / SCALE)
        if 0 <= ci < WORLD["w_cells"] and 0 <= cj < WORLD["h_cells"]:
            node.send_op({"type": "drone", "id": sel.get(),
                          "action": "goto", "cell": [ci, cj]})
    cv.bind("<Button-1>", on_click)

    def tick():
        with node.lock:
            st, ls, pr = dict(node.status), dict(node.linkstate), dict(node.probe)
            pose = dict(node.pose)
            trail = {d: list(node.trail[d]) for d in IDS}
        cv.delete("all")
        # ruine / fum / victime
        for (x0, y0, x1, y1) in WORLD["ruins"]:
            cv.create_rectangle(*P(x0, y1 + 1), *P(x1 + 1, y0),
                                fill="#4a352c", outline="#2c1f1a")
        for (sx, sy, r) in WORLD["smoke"]:
            cv.create_oval(*P(sx - r, sy + r), *P(sx + r, sy - r),
                           fill="#777777", stipple="gray50", outline="")
        found = {tuple(v) for v in st.get("victims", [])}
        for (vi, vj) in WORLD["victims"]:
            x, y = P(vi + 0.5, vj + 0.5)
            c = "#ffd24d" if (vi, vj) in found else "#d04444"
            cv.create_text(x, y, text="★", fill=c, font=("TkDefaultFont", 16))
        # drone + urme
        down = set(map(tuple, [k.split("-") for k in ls.get("down", [])]))
        for d in IDS:
            if len(trail[d]) > 1:
                pts = [c for xy in trail[d] for c in P(*xy)]
                cv.create_line(*pts, fill=COL[d], width=2)
            x, y, *_ = pose[d]
            cx, cy = P(x, y)
            cv.create_oval(cx - 6, cy - 6, cx + 6, cy + 6,
                           fill=COL[d], outline="white")
            gcs_down = tuple(sorted((d, "gcs"))) in down
            if gcs_down:
                cv.create_text(cx, cy - 14, text="✕ GCS", fill="#ff6666",
                               font=("TkDefaultFont", 9, "bold"))
            cv.create_text(cx + 12, cy, text=d, fill="white", anchor="w")
        # panoul lateral
        if st:
            head.set(f"Scenariu: {ls.get('scenario','?')}   t={ls.get('t','?')} s\n"
                     f"Misiune: {st.get('mission','?')}   "
                     f"Acoperire: {100*st.get('coverage',0):.1f}%   "
                     f"Victime: {len(st.get('victims',[]))}/"
                     f"{st.get('victims_total','?')}")
        dr = st.get("drones", {})
        for d in IDS:
            i = dr.get(d, {})
            q = pr.get(d, {})
            rows[d].set(
                f"legatura: {'SUS' if i.get('link', True) else 'JOS'}   "
                f"stare: {i.get('state','?')}  mod: {i.get('mode','AUTO')}\n"
                f"telemetrie acum {i.get('age_s','?')} s   "
                f"RTT {q.get('rtt_mean_ms','—')} / p95 {q.get('rtt_p95_ms','—')} ms\n"
                f"pierdere (10 s): "
                f"{'—' if q.get('loss_10s') is None else f'{100*q['loss_10s']:.0f}%'}")
        root.after(200, tick)

    root.after(300, tick)
    return root


def main():
    rclpy.init()
    node = DashNode()
    spin = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin.start()
    root = build_gui(node)
    try:
        root.mainloop()
    finally:
        rclpy.try_shutdown()
        spin.join(timeout=2.0)
        node.destroy_node()


if __name__ == "__main__":
    main()
