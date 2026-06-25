#!/usr/bin/env python3
"""operator_panel_node.py -- PANOUL OPERATORULUI: cuplul motoarelor de
comanda (A) pe slidere, impedanta (K, B) si degradarea legaturii (ms)
reglabile live, ESTOP rosu, si GRAFICELE DE REACTIE citite de encoderele
motoarelor slave (B): pozitie, viteza filtrata (+bruta), acceleratie si
cuplul de reactie tau_b.

Publica:  /joint/cmd_a {"pair":k,"tau":...}
          /joint/impedance {"pair":k,"k":...,"b":...}
          /teleop/linkstate {"ms":...}
          /joint/estop {}
Asculta:  /joint/state (tau_b, k_ef), /joint/kinematics (th, om, acc, om_raw)

Ruleaza:  python3 nodes/operator_panel_node.py
(necesita desktop; emulatorul + monitorul de encodere pornite separat)
"""
import json
import threading
from collections import deque

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

N_PAIRS = 3
BUF = 600          # ~30 s la 20 Hz
COL = ["tab:blue", "tab:green", "tab:purple"]


class PanelNode(Node):
    def __init__(self):
        super().__init__("operator_panel")
        self.lock = threading.Lock()
        mk = lambda: {k: deque(maxlen=BUF) for k in
                      ("t", "th", "om", "om_raw", "acc", "tau_b")}
        self.buf = [mk() for _ in range(N_PAIRS)]
        self.k_ef = [0.0] * N_PAIRS
        self.pub_cmd = self.create_publisher(String, "/joint/cmd_a", 10)
        self.pub_imp = self.create_publisher(String, "/joint/impedance", 10)
        self.pub_lnk = self.create_publisher(String, "/teleop/linkstate", 10)
        self.pub_stp = self.create_publisher(String, "/joint/estop", 10)
        self.create_subscription(String, "/joint/state", self.on_state, 30)
        self.create_subscription(String, "/joint/kinematics", self.on_kin, 30)

    def on_state(self, msg):
        d = json.loads(msg.data)
        with self.lock:
            for pid, st in d.items():
                k = int(pid)
                if k < N_PAIRS:
                    self.buf[k]["tau_b"].append(
                        (float(st["t"]), float(st.get("tau_b", 0.0))))
                    self.k_ef[k] = float(st.get("k_ef", 0.0))

    def on_kin(self, msg):
        d = json.loads(msg.data)
        with self.lock:
            for pid, st in d.items():
                k = int(pid)
                if k < N_PAIRS:
                    t = float(st["t"])
                    b = self.buf[k]
                    b["t"].append(t)
                    b["th"].append((t, float(st.get("th", 0.0))))
                    b["om"].append((t, float(st.get("om", 0.0))))
                    b["om_raw"].append((t, float(st.get("om_raw", 0.0))))
                    b["acc"].append((t, float(st.get("acc", 0.0))))

    # --- comenzile (apelate din thread-ul UI) ---
    def send_tau(self, pair, tau):
        self.pub_cmd.publish(String(data=json.dumps(
            {"pair": pair, "tau": round(float(tau), 4)})))

    def send_imp(self, k, b):
        for p in range(N_PAIRS):
            self.pub_imp.publish(String(data=json.dumps(
                {"pair": p, "k": round(float(k), 3), "b": round(float(b), 3)})))

    def send_link(self, ms):
        self.pub_lnk.publish(String(data=json.dumps({"ms": round(float(ms), 1)})))

    def send_estop(self):
        self.pub_stp.publish(String(data="{}"))


def build_ui(node):
    fig = plt.figure("Panoul operatorului -- joint_emulator", figsize=(13, 7.5))
    gs = fig.add_gridspec(4, 2, left=0.32, right=0.98, hspace=0.45)
    ax_th = fig.add_subplot(gs[0, :]); ax_th.set_ylabel("pozitie [rad]")
    ax_om = fig.add_subplot(gs[1, :]); ax_om.set_ylabel("viteza [rad/s]")
    ax_ac = fig.add_subplot(gs[2, :]); ax_ac.set_ylabel("accel [rad/s^2]")
    ax_tb = fig.add_subplot(gs[3, :]); ax_tb.set_ylabel("reactia tau_b [Nm]")
    ax_tb.set_xlabel("timpul simularii [s]")
    axes = (ax_th, ax_om, ax_ac, ax_tb)
    lines = {}
    for k in range(N_PAIRS):
        lines[("th", k)], = ax_th.plot([], [], color=COL[k], lw=1.4,
                                       label=f"perechea {k}")
        lines[("om", k)], = ax_om.plot([], [], color=COL[k], lw=1.4)
        lines[("acc", k)], = ax_ac.plot([], [], color=COL[k], lw=1.2)
        lines[("tau_b", k)], = ax_tb.plot([], [], color=COL[k], lw=1.4)
    lines[("om_raw", 0)], = ax_om.plot([], [], color="lightgray", lw=0.7,
                                       label="om brut (perechea 0)")
    ax_th.legend(loc="upper left", fontsize=8, ncol=4)
    ax_om.legend(loc="upper left", fontsize=8)
    for ax in axes:
        ax.grid(alpha=0.3)
    titlu = fig.text(0.32, 0.965, "", fontsize=10)

    # --- coloana de comenzi ---
    sliders = []
    y = 0.86
    for k in range(N_PAIRS):
        ax = fig.add_axes([0.06, y, 0.18, 0.03])
        s = Slider(ax, f"tau_A p{k} [Nm]", -2.0, 2.0, valinit=0.0)
        s.on_changed(lambda v, kk=k: node.send_tau(kk, v))
        sliders.append(s); y -= 0.07
    ax_k = fig.add_axes([0.06, y, 0.18, 0.03]); y -= 0.07
    s_k = Slider(ax_k, "K [Nm/rad]", 0.5, 40.0, valinit=20.0)
    ax_b = fig.add_axes([0.06, y, 0.18, 0.03]); y -= 0.07
    s_b = Slider(ax_b, "B [Nms/rad]", 0.0, 2.0, valinit=0.8)
    s_k.on_changed(lambda v: node.send_imp(s_k.val, s_b.val))
    s_b.on_changed(lambda v: node.send_imp(s_k.val, s_b.val))
    ax_ms = fig.add_axes([0.06, y, 0.18, 0.03]); y -= 0.10
    s_ms = Slider(ax_ms, "link [ms]", 0.0, 120.0, valinit=0.0)
    s_ms.on_changed(lambda v: node.send_link(v))
    ax_e = fig.add_axes([0.06, y, 0.085, 0.06])
    b_e = Button(ax_e, "ESTOP", color="crimson", hovercolor="red")
    ax_z = fig.add_axes([0.155, y, 0.085, 0.06])
    b_z = Button(ax_z, "tau=0", color="lightgray")

    def on_estop(_):
        node.send_estop()
        for s in sliders:
            s.set_val(0.0)
    b_e.on_clicked(on_estop)
    b_z.on_clicked(lambda _: [s.set_val(0.0) for s in sliders])

    def refresh(_=None):
        with node.lock:
            for k in range(N_PAIRS):
                for key in ("th", "om", "acc", "tau_b"):
                    pts = list(node.buf[k][key])
                    if pts:
                        lines[(key, k)].set_data([p[0] for p in pts],
                                                 [p[1] for p in pts])
            pts = list(node.buf[0]["om_raw"])
            if pts:
                lines[("om_raw", 0)].set_data([p[0] for p in pts],
                                              [p[1] for p in pts])
            kef = ", ".join(f"p{k}: {node.k_ef[k]:.1f}" for k in range(N_PAIRS))
        titlu.set_text(f"K_ef [{kef}]   link: {s_ms.val:.0f} ms")
        for ax in axes:
            ax.relim(); ax.autoscale_view()
        fig.canvas.draw_idle()

    timer = fig.canvas.new_timer(interval=150)
    timer.add_callback(refresh)
    timer.start()
    plt.show()


def main():
    rclpy.init()
    node = PanelNode()
    th = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    th.start()
    try:
        build_ui(node)            # blocheaza pana inchizi fereastra
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
