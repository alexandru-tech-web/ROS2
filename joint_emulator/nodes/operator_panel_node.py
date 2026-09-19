#!/usr/bin/env python3
"""operator_panel_node.py -- HMI in 3 coloane: comenzi A (slider + numar),
grafice A si grafice B. Fiecare latura are propriul canal de encoder SIM;
flansa rigida le da acelasi unghi ideal. K, B si link se regleaza live.
ESTOP, RESET SIM si export Excel sunt disponibile in coloana stanga.

Publica:  /joint/cmd_a {"pair":k,"tau":...}
          /joint/impedance {"pair":k,"k":...,"b":...}
          /joint/linkstate {"ms":...}
          /joint/estop {}
          /joint/reset_estop {}
Asculta:  /joint/state (tau_b, k_ef), /joint/kinematics (compatibilitate),
          /joint/motor_kinematics (sase canale de encoder)

Ruleaza:  python3 nodes/operator_panel_node.py
(necesita desktop; emulatorul + monitorul de encodere pornite separat)
"""
import json
import math
import os
import signal
import sys
import threading
from collections import deque
from datetime import datetime, timezone

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from panel_export import export_panel_csv
from session_export import checked_session_id, export_session_xlsx

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, TextBox

N_PAIRS = 3
BUF = 600          # ~30 s la 20 Hz
COL = ["tab:blue", "tab:green", "tab:purple"]
DEFAULT_DATA_DIR = "/home/ubuntu/Analiza_Teza/ViPRO/DATE"


class PanelNode(Node):
    def __init__(self):
        super().__init__("operator_panel")
        self.declare_parameter("data_dir", DEFAULT_DATA_DIR)
        self.declare_parameter(
            "session_id", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        self.lock = threading.Lock()
        mk = lambda: {k: deque(maxlen=BUF) for k in
                      ("th", "om", "om_raw", "acc", "th_a", "th_b",
                       "om_a", "om_b", "delta_th", "tau_a_cmd",
                       "tau_b", "k_ef", "win_energy")}
        self.buf = [mk() for _ in range(N_PAIRS)]
        self.k_ef = [0.0] * N_PAIRS
        self.win_e = [0.0] * N_PAIRS
        self.estopped = [False] * N_PAIRS
        self.reset_status = ""
        self.reaction_mode = "impedance"
        self.contact_angle_deg = 0.0
        self.pub_cmd = self.create_publisher(String, "/joint/cmd_a", 10)
        self.pub_imp = self.create_publisher(String, "/joint/impedance", 10)
        self.pub_lnk = self.create_publisher(String, "/joint/linkstate", 10)
        self.pub_stp = self.create_publisher(String, "/joint/estop", 10)
        self.pub_reset = self.create_publisher(String, "/joint/reset_estop", 10)
        self.create_subscription(String, "/joint/state", self.on_state, 30)
        self.create_subscription(String, "/joint/kinematics", self.on_kin, 30)
        self.create_subscription(String, "/joint/motor_kinematics",
                                 self.on_motor_kin, 30)

    def on_state(self, msg):
        d = json.loads(msg.data)
        with self.lock:
            for pid, st in d.items():
                k = int(pid)
                if k < N_PAIRS:
                    t = float(st["t"])
                    for key in ("tau_a_cmd", "tau_b", "k_ef", "win_energy"):
                        self.buf[k][key].append((t, float(st.get(key, 0.0))))
                    self.k_ef[k] = float(st.get("k_ef", 0.0))
                    self.win_e[k] = float(st.get("win_energy", 0.0))
                    self.estopped[k] = bool(st.get("estopped", False))
                    self.reset_status = str(st.get("reset_status", ""))
                    self.reaction_mode = str(st.get("reaction_mode", "impedance"))
                    self.contact_angle_deg = float(
                        st.get("contact_angle_deg", 0.0))

    def on_kin(self, msg):
        d = json.loads(msg.data)
        with self.lock:
            for pid, st in d.items():
                k = int(pid)
                if k < N_PAIRS:
                    t = float(st["t"])
                    b = self.buf[k]
                    b["th"].append((t, float(st.get("th", 0.0))))
                    b["om"].append((t, float(st.get("om", 0.0))))
                    b["om_raw"].append((t, float(st.get("om_raw", 0.0))))
                    b["acc"].append((t, float(st.get("acc", 0.0))))

    def on_motor_kin(self, msg):
        d = json.loads(msg.data)
        with self.lock:
            for pid, st in d.items():
                k = int(pid)
                if not 0 <= k < N_PAIRS:
                    continue
                b = self.buf[k]
                t = float(st["t"])
                if b["delta_th"] and b["delta_th"][-1][0] == t:
                    continue
                for side, suffix in (("A", "a"), ("B", "b")):
                    motor = st[side]
                    tm = float(motor["t"])
                    b[f"th_{suffix}"].append((tm, float(motor["th"])))
                    b[f"om_{suffix}"].append((tm, float(motor["om"])))
                b["delta_th"].append((t, float(st["delta_th"])))

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

    def send_reset(self):
        self.pub_reset.publish(String(data="{}"))

    def export_csv(self):
        with self.lock:
            snapshot = [{key: list(values) for key, values in pair.items()}
                        for pair in self.buf]
        name = datetime.now().strftime("joint_graphs_%Y%m%d_%H%M%S_%f.csv")
        directory = os.path.expanduser(
            str(self.get_parameter("data_dir").value))
        path = os.path.join(directory, name)
        count = export_panel_csv(snapshot, path)
        return path, count

    def export_session(self):
        data_dir = os.path.expanduser(str(self.get_parameter("data_dir").value))
        session_id = checked_session_id(self.get_parameter("session_id").value)
        return export_session_xlsx(data_dir, session_id)


def build_ui(node):
    fig = plt.figure("Panoul operatorului -- joint_emulator", figsize=(16, 9))
    fig.text(0.04, 0.96, "COMENZI -- A (albastru)", fontsize=12,
             weight="bold", color="#087fae")
    fig.text(0.36, 0.96, "MOTOARE A -- actioneaza", fontsize=12,
             weight="bold", color="#087fae")
    fig.text(0.69, 0.96, "MOTOARE B -- reactioneaza", fontsize=12,
             weight="bold", color="#252525")
    fig.text(0.36, 0.928,
             "Cuplaj rigid: 6 encodere simulate, 3 axe; delta A-B este diagnostic.",
             fontsize=9)
    summary = fig.text(0.36, 0.902, "", fontsize=9)
    status = fig.text(0.36, 0.858, "", fontsize=9)

    gs = fig.add_gridspec(3, 2, left=0.36, right=0.98, top=0.83,
                          bottom=0.12, wspace=0.29, hspace=0.48)
    ax_a = [fig.add_subplot(gs[row, 0]) for row in range(3)]
    ax_b = [fig.add_subplot(gs[row, 1]) for row in range(3)]
    ax_a[0].set_title("Cuplu comandat A [Nm]", fontsize=10)
    ax_b[0].set_title("Cuplu comandat B [Nm]", fontsize=10)
    ax_a[1].set_title("Unghi encoder A [rad]", fontsize=10)
    ax_b[1].set_title("Unghi encoder B [rad]", fontsize=10)
    ax_a[2].set_title("Viteza estimata A [rad/s]", fontsize=10)
    ax_b[2].set_title("Viteza estimata B [rad/s]", fontsize=10)
    for ax in (ax_a[2], ax_b[2]):
        ax.set_xlabel("timpul simularii [s]")
    axes = ax_a + ax_b
    plots = {}
    for k in range(N_PAIRS):
        for role, axis_set, signals in (
                ("A", ax_a, ("tau_a_cmd", "th_a", "om_a")),
                ("B", ax_b, ("tau_b", "th_b", "om_b"))):
            for row, signal in enumerate(signals):
                plots[(role, row, k)], = axis_set[row].plot(
                    [], [], color=COL[k], lw=1.5,
                    label=f"perechea {k}")
    ax_a[0].legend(loc="upper right", fontsize=8, ncol=3)
    ax_b[0].legend(loc="upper right", fontsize=8, ncol=3)
    for ax in axes:
        ax.grid(alpha=0.3)

    # Coloana 1: fiecare A are slider si intrare numerica exacta in Nm.
    sliders, boxes = [], []
    syncing = [False] * N_PAIRS
    y = 0.80
    for k in range(N_PAIRS):
        fig.text(0.04, y + 0.037, f"A{k} (stanga) -> B{k} (dreapta)",
                 fontsize=9, color=COL[k])
        ax = fig.add_axes([0.075, y, 0.125, 0.03])
        s = Slider(ax, f"A{k} [Nm]", -2.0, 2.0, valinit=0.0)
        s.valtext.set_visible(False)
        entry_ax = fig.add_axes([0.225, y - 0.004, 0.06, 0.043])
        entry = TextBox(entry_ax, "", initial="0.000")
        sliders.append(s)
        boxes.append(entry)
        y -= 0.11

    def slider_changed(value, index):
        if syncing[index]:
            return
        syncing[index] = True
        try:
            boxes[index].set_val(f"{value:.3f}")
        finally:
            syncing[index] = False
        node.send_tau(index, value)

    def text_submitted(raw, index):
        if syncing[index]:
            return
        try:
            value = float(raw)
            if not math.isfinite(value) or not -2.0 <= value <= 2.0:
                raise ValueError("in afara intervalului")
        except ValueError:
            status.set_text(f"A{index}: introdu un numar intre -2 si 2 Nm")
            syncing[index] = True
            try:
                boxes[index].set_val(f"{sliders[index].val:.3f}")
            finally:
                syncing[index] = False
            fig.canvas.draw_idle()
            return
        sliders[index].set_val(value)

    for k in range(N_PAIRS):
        sliders[k].on_changed(lambda v, kk=k: slider_changed(v, kk))
        boxes[k].on_submit(lambda raw, kk=k: text_submitted(raw, kk))

    ax_k = fig.add_axes([0.075, 0.405, 0.205, 0.028])
    s_k = Slider(ax_k, "K_B [Nm/rad]", 0.5, 40.0, valinit=20.0)
    ax_b_gain = fig.add_axes([0.075, 0.343, 0.205, 0.028])
    s_b = Slider(ax_b_gain, "B_B [Nms/rad]", 0.0, 2.0, valinit=0.8)
    s_k.on_changed(lambda v: node.send_imp(s_k.val, s_b.val))
    s_b.on_changed(lambda v: node.send_imp(s_k.val, s_b.val))
    ax_ms = fig.add_axes([0.075, 0.281, 0.205, 0.028])
    s_ms = Slider(ax_ms, "link [ms]", 0.0, 120.0, valinit=0.0)
    s_ms.on_changed(lambda v: node.send_link(v))
    ax_e = fig.add_axes([0.04, 0.197, 0.105, 0.057])
    b_e = Button(ax_e, "ESTOP", color="crimson", hovercolor="red")
    ax_z = fig.add_axes([0.165, 0.197, 0.12, 0.057])
    b_z = Button(ax_z, "tau=0", color="lightgray")
    ax_r = fig.add_axes([0.04, 0.12, 0.245, 0.055])
    b_r = Button(ax_r, "RESET ESTOP", color="lightgreen")
    ax_csv = fig.add_axes([0.04, 0.047, 0.245, 0.055])
    b_csv = Button(ax_csv, "Export Excel", color="lightblue")

    def on_estop(_):
        node.send_estop()
        for s in sliders:
            s.set_val(0.0)
    b_e.on_clicked(on_estop)
    b_z.on_clicked(lambda _: [s.set_val(0.0) for s in sliders])

    def on_reset(_):
        for s in sliders:
            s.set_val(0.0)
        node.send_reset()
        if not last_reset_status[0]:
            status.set_text("RESET trimis; asteapta confirmarea in stare")
        fig.canvas.draw_idle()

    def on_export(_):
        try:
            path = node.export_session()
            status.set_text(f"Excel: {path}")
            node.get_logger().info(f"Sesiune exportata: {path}")
        except (OSError, ValueError) as exc:
            status.set_text(f"Export Excel esuat: {exc}")
            node.get_logger().error(f"Export Excel esuat: {exc}")
        fig.canvas.draw_idle()

    b_r.on_clicked(on_reset)
    b_csv.on_clicked(on_export)

    def refresh(_=None):
        if not rclpy.ok():
            plt.close(fig)
            return
        with node.lock:
            snapshot = [{key: list(values) for key, values in pair.items()}
                        for pair in node.buf]
            kef = ", ".join(f"p{k}: {node.k_ef[k]:.1f}" for k in range(N_PAIRS))
            win_max = max(node.win_e) if node.win_e else 0.0
            any_estop = any(node.estopped)
            reset_status = node.reset_status
            angles = [snapshot[k]["th_a"][-1][1] if snapshot[k]["th_a"]
                      else 0.0 for k in range(N_PAIRS)]
            mismatch = [abs(snapshot[k]["delta_th"][-1][1])
                        if snapshot[k]["delta_th"] else 0.0
                        for k in range(N_PAIRS)]
            reaction_mode = node.reaction_mode
            contact_angle_deg = node.contact_angle_deg
        for k in range(N_PAIRS):
            for role, signals in (
                    ("A", ("tau_a_cmd", "th_a", "om_a")),
                    ("B", ("tau_b", "th_b", "om_b"))):
                for row, signal in enumerate(signals):
                    pts = snapshot[k][signal]
                    if pts:
                        plots[(role, row, k)].set_data(
                            [p[0] for p in pts], [p[1] for p in pts])
        angle_text = ", ".join(f"p{k}: {angles[k] * 57.2958:.1f} deg"
                               for k in range(N_PAIRS))
        mode_text = (f"contact local +/-{contact_angle_deg:.1f} deg"
                     if reaction_mode == "contact" else "impedanta")
        link_text = ("link nefolosit in contact local"
                     if reaction_mode == "contact" else
                     f"link {s_ms.val:.0f} ms")
        summary.set_text(
            f"unghi ax [{angle_text}]  |  K_ef [{kef}]  |  "
            f"max |delta A-B| {1000 * max(mismatch):.2f} mrad\n"
            f"mod {mode_text}  |  {link_text}  |  E1s {win_max:.2f} J" +
            ("   [ESTOP]" if any_estop else ""))
        if reset_status != last_reset_status[0]:
            if reset_status:
                status.set_text(reset_status)
            last_reset_status[0] = reset_status
        for ax in axes:
            ax.relim(); ax.autoscale_view()
        fig.canvas.draw_idle()

    timer = fig.canvas.new_timer(interval=150)
    last_reset_status = [""]
    timer.add_callback(refresh)
    timer.start()
    plt.show()
    return {"sliders": sliders, "boxes": boxes}


def main():
    rclpy.init()
    node = PanelNode()

    def spin_node():
        try:
            rclpy.spin(node)
        except ExternalShutdownException:
            pass

    def stop_ui(_signum, _frame):
        if rclpy.ok():
            rclpy.shutdown()
        plt.close("all")

    # Matplotlib/Tk ruleaza in thread-ul principal. Preluam semnalele aici
    # pentru ca Ctrl+C din ros2 launch sa inchida si fereastra, fara traceback.
    signal.signal(signal.SIGINT, stop_ui)
    signal.signal(signal.SIGTERM, stop_ui)

    th = threading.Thread(target=spin_node, daemon=True)
    th.start()
    try:
        build_ui(node)            # blocheaza pana inchizi fereastra
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        th.join(timeout=2.0)
        node.destroy_node()


if __name__ == "__main__":
    main()
