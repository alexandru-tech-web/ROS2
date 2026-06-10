#!/usr/bin/env python3
"""
telemetry_display.py — Afisaj LIVE de telemetrie pentru simulare.

O fereastra cu trei grafice derulante (ultimele ~12 s) pentru cele 6
servomotoare: POZITIE [rad], VITEZA [rad/s] si TORQUE [N*m] (efortul
actuatorului din Gazebo; in RViz torque-ul este 0 — fara fizica).
Deasupra: cifrele-cheie ale momentului — timpul, viteza maxima curenta,
torque-ul maxim curent (si pe ce articulatie), pozitiile axelor de ajustare.

Stiluri: sold albastru, genunchi verde, glezna portocaliu;
         stanga linie plina, dreapta linie intrerupta.

Functioneaza peste Gazebo (gazebo.launch.py) sau peste RViz
(operator.launch.py) — citeste doar /joint_states.

Necesita:  sudo apt install -y python3-tk   (matplotlib e deja prezent cu ROS)
Rulare:    ros2 run rehab_exo_description telemetry_display.py
"""

import collections
import os
import sys
import threading

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exercise_core as core

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("Lipseste Tkinter: sudo apt install -y python3-tk", file=sys.stderr)
    sys.exit(1)

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

EXJ = core.JOINT_NAMES
ADJ = core.ADJUST_JOINT_NAMES
COLOR = {"hip": "#2E73CC", "knee": "#2E8B57", "ankle": "#C77F2E"}
SHORT = {"hip": "sold", "knee": "genunchi", "ankle": "glezna"}


def joint_style(j):
    base = j.split("_")[1]
    return COLOR[base], "-" if j.startswith("left") else "--"


class TelemetryNode(Node):
    """Colecteaza /joint_states in buffere circulare (thread-safe)."""

    def __init__(self, window_sec: float):
        super().__init__("telemetry_display")
        self.win = window_sec
        self.lock = threading.Lock()
        self.t0 = None
        self.t = collections.deque()
        self.pos = {j: collections.deque() for j in EXJ}
        self.vel = {j: collections.deque() for j in EXJ}
        self.eff = {j: collections.deque() for j in EXJ}
        self.adj = {j: 0.0 for j in ADJ}
        self.samples = 0
        self.create_subscription(JointState, "joint_states", self.on_js, 50)

    def on_js(self, msg: JointState):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if self.t0 is None:
            self.t0 = t
        tr = t - self.t0
        idx = {n: i for i, n in enumerate(msg.name)}

        def get(arr, i):
            return arr[i] if i is not None and i < len(arr) else float("nan")

        with self.lock:
            self.t.append(tr)
            for j in EXJ:
                i = idx.get(j)
                self.pos[j].append(get(msg.position, i))
                self.vel[j].append(get(msg.velocity, i))
                self.eff[j].append(get(msg.effort, i))
            for j in ADJ:
                i = idx.get(j)
                if i is not None and i < len(msg.position):
                    self.adj[j] = msg.position[i]
            while self.t and self.t[0] < tr - self.win:
                self.t.popleft()
                for j in EXJ:
                    self.pos[j].popleft()
                    self.vel[j].popleft()
                    self.eff[j].popleft()
            self.samples += 1

    def snapshot(self):
        with self.lock:
            t = list(self.t)
            data = {q: {j: list(d[j]) for j in EXJ}
                    for q, d in (("pos", self.pos), ("vel", self.vel), ("eff", self.eff))}
            return t, data, dict(self.adj), self.samples


def build_gui(node: TelemetryNode):
    root = tk.Tk()
    root.title("Telemetrie — torque, viteza, pozitie (6 servomotoare)")
    root.geometry("980x760")

    # ---- cifrele-cheie ----
    top = ttk.Frame(root)
    top.pack(fill="x", padx=10, pady=6)
    v_t = tk.StringVar(value="t = 0.0 s")
    v_v = tk.StringVar(value="|v|max: —")
    v_e = tk.StringVar(value="|τ|max: —")
    v_a = tk.StringVar(value="ajustari: scaun 0.000 m")
    for var, w in ((v_t, 12), (v_v, 30), (v_e, 30)):
        ttk.Label(top, textvariable=var, font=("TkDefaultFont", 11, "bold"),
                  width=w).pack(side="left", padx=8)
    ttk.Label(root, textvariable=v_a, foreground="#555").pack(fill="x", padx=18)

    # ---- graficele ----
    fig = Figure(figsize=(9.4, 6.2), dpi=100)
    axes = fig.subplots(3, 1, sharex=True)
    titles = ["Pozitie [rad]", "Viteza [rad/s]", "Torque (effort) [N*m] — doar in Gazebo"]
    lines = {q: {} for q in ("pos", "vel", "eff")}
    for ax, ttl, q in zip(axes, titles, ("pos", "vel", "eff")):
        ax.set_ylabel(ttl, fontsize=9)
        ax.grid(alpha=0.3)
        for j in EXJ:
            c, ls = joint_style(j)
            (ln,) = ax.plot([], [], color=c, ls=ls, lw=1.6,
                            label=("stg " if j.startswith("left") else "dr  ")
                                  + SHORT[j.split("_")[1]])
        # pastram referintele in ordinea EXJ
        for ln, j in zip(ax.get_lines(), EXJ):
            lines[q][j] = ln
    axes[1].axhline(core.VEL_MAX, ls=":", c="#999", lw=1)
    axes[1].axhline(-core.VEL_MAX, ls=":", c="#999", lw=1)
    axes[0].legend(ncol=6, fontsize=7, loc="upper right")
    axes[2].set_xlabel("timp [s]")
    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=4)

    def tick():
        t, data, adj, n = node.snapshot()
        if t:
            for q, ax in zip(("pos", "vel", "eff"), axes):
                for j in EXJ:
                    lines[q][j].set_data(t, data[q][j])
                ax.relim(); ax.autoscale_view(scalex=False, scaley=True)
            axes[0].set_xlim(max(0.0, t[-1] - node.win), t[-1] + 0.2)
            v_t.set(f"t = {t[-1]:.1f} s")
            lastv = {j: data["vel"][j][-1] for j in EXJ if data["vel"][j]}
            laste = {j: data["eff"][j][-1] for j in EXJ if data["eff"][j]}
            if lastv:
                jv = max(lastv, key=lambda k: abs(lastv[k] or 0.0))
                v_v.set(f"|v|max acum: {abs(lastv[jv]):.2f} rad/s "
                        f"({SHORT[jv.split('_')[1]]} {'stg' if jv.startswith('left') else 'dr'})")
            if laste and not all((x != x) for x in laste.values()):
                je = max(laste, key=lambda k: abs(laste[k] or 0.0))
                v_e.set(f"|τ|max acum: {abs(laste[je]):.1f} N*m "
                        f"({SHORT[je.split('_')[1]]} {'stg' if je.startswith('left') else 'dr'})")
            v_a.set("ajustari: scaun {:.3f} m | coapsa stg {:.3f} / dr {:.3f} | "
                    "gamba stg {:.3f} / dr {:.3f}   ({} esantioane)".format(
                        adj["seat_lift_joint"],
                        adj["left_thigh_ext_joint"], adj["right_thigh_ext_joint"],
                        adj["left_shank_ext_joint"], adj["right_shank_ext_joint"], n))
            canvas.draw_idle()
        root.after(100, tick)

    root.after(200, tick)
    return root


def main():
    rclpy.init()
    node = TelemetryNode(window_sec=12.0)
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
