#!/usr/bin/python3
"""
telemetry_display.py — Afisaj LIVE de telemetrie pentru simulare.

O fereastra cu trei grafice derulante (ultimele 30 s) pentru cele 6
servomotoare: POZITIE [rad], VITEZA [rad/s] si EFORT [N*m] (efortul
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
import math
import os
import sys
import threading

import rclpy
from control_msgs.msg import JointTrajectoryControllerState
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
        self.cmd = {j: collections.deque() for j in EXJ}
        self.cmd_current = {j: float("nan") for j in EXJ}
        self.adj = {j: 0.0 for j in ADJ}
        self.samples = 0
        self.create_subscription(JointState, "joint_states", self.on_js, 50)
        self.create_subscription(JointTrajectoryControllerState,
                                 "/leg_trajectory_controller/controller_state",
                                 self.on_controller_state, 50)

    def on_controller_state(self, msg: JointTrajectoryControllerState):
        with self.lock:
            for name, value in zip(msg.joint_names, msg.reference.positions):
                if name in self.cmd_current:
                    self.cmd_current[name] = value

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
                self.cmd[j].append(self.cmd_current[j])
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
                    self.cmd[j].popleft()
            self.samples += 1

    def snapshot(self):
        with self.lock:
            t = list(self.t)
            data = {q: {j: list(d[j]) for j in EXJ}
                    for q, d in (("pos", self.pos), ("vel", self.vel), ("eff", self.eff))}
            cmd = {j: list(self.cmd[j]) for j in EXJ}
            return t, data, cmd, dict(self.adj), self.samples


def build_gui(node: TelemetryNode, close_callback):
    root = tk.Tk()
    root.title("Rehab — telemetrie SIMULATA pentru 6 servomotoare")
    root.geometry("980x760")

    # ---- cifrele-cheie ----
    top = ttk.Frame(root)
    top.pack(fill="x", padx=10, pady=6)
    v_t = tk.StringVar(value="t = 0.0 s")
    v_v = tk.StringVar(value="|v|max: —")
    v_e = tk.StringVar(value="|τ|max: —")
    v_err = tk.StringVar(value="|e|max: —")
    v_a = tk.StringVar(value="ajustari: scaun 0.000 m")
    for var, w in ((v_t, 12), (v_v, 27), (v_e, 27), (v_err, 20)):
        ttk.Label(top, textvariable=var, font=("TkDefaultFont", 11, "bold"),
                  width=w).pack(side="left", padx=8)
    ttk.Label(root, textvariable=v_a, foreground="#555").pack(fill="x", padx=18)

    # ---- graficele ----
    fig = Figure(figsize=(9.4, 6.2), dpi=100)
    axes = fig.subplots(3, 1, sharex=True)
    titles = ["Pozitie encoder simulat [rad]", "Viteza simulata [rad/s]",
              "Efort actuator Gazebo [Nm] — NU cuplu fizic masurat"]
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
    # Referintele controlerului sunt punctate. Fara ele, graficul de pozitie nu
    # poate arata eroarea de urmarire si este doar un osciloscop al encoderului.
    cmd_lines = {}
    for j in EXJ:
        c, _ = joint_style(j)
        (cmd_lines[j],) = axes[0].plot([], [], color=c, ls=":", lw=1.0,
                                      alpha=.8, label="_referinta")
    axes[2].set_xlabel("timp [s]")
    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=4)

    closing = {"value": False}
    after_id = {"value": None}

    def close_window():
        if closing["value"]:
            return
        closing["value"] = True
        if after_id["value"] is not None:
            try:
                root.after_cancel(after_id["value"])
            except tk.TclError:
                pass
        close_callback()
        try:
            root.quit()
            root.destroy()
        except tk.TclError:
            pass

    def tick():
        if closing["value"]:
            return
        t, data, cmd, adj, n = node.snapshot()
        if t:
            for q, ax in zip(("pos", "vel", "eff"), axes):
                for j in EXJ:
                    lines[q][j].set_data(t, data[q][j])
                ax.relim(); ax.autoscale_view(scalex=False, scaley=True)
            for j in EXJ:
                cmd_lines[j].set_data(t, cmd[j])
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
            errors = {j: abs(data["pos"][j][-1] - cmd[j][-1]) for j in EXJ
                      if data["pos"][j] and math.isfinite(data["pos"][j][-1])
                      and cmd[j] and math.isfinite(cmd[j][-1])}
            if errors:
                je = max(errors, key=errors.get)
                v_err.set(f"|e|max: {errors[je]:.4f} rad")
            v_a.set("ajustari: scaun {:.3f} m | coapsa stg {:.3f} / dr {:.3f} | "
                    "gamba stg {:.3f} / dr {:.3f}   ({} esantioane)".format(
                        adj["seat_lift_joint"],
                        adj["left_thigh_ext_joint"], adj["right_thigh_ext_joint"],
                        adj["left_shank_ext_joint"], adj["right_shank_ext_joint"], n))
            try:
                canvas.draw_idle()
            except tk.TclError:
                return
        try:
            after_id["value"] = root.after(100, tick)
        except tk.TclError:
            pass

    root.protocol("WM_DELETE_WINDOW", close_window)
    after_id["value"] = root.after(200, tick)
    root._rehab_close = close_window
    return root


def main():
    rclpy.init()
    node = TelemetryNode(window_sec=30.0)

    def spin_ros():
        from rclpy.executors import ExternalShutdownException
        try:
            rclpy.spin(node)
        except ExternalShutdownException:
            pass

    spin = threading.Thread(target=spin_ros, daemon=True)
    spin.start()
    root = build_gui(node, rclpy.try_shutdown)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        root._rehab_close()
    finally:
        rclpy.try_shutdown()
        spin.join(timeout=2.0)
        node.destroy_node()


if __name__ == "__main__":
    main()
