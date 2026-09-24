#!/usr/bin/python3
"""HMI pentru operarea si observarea twin-ului robotului LLR.

Separă programul pasiv, reglajele antropometrice, canalele de senzori LLR si
trasabilitatea datelor. STOP-ul HMI cere revenire controlata, nu este E-STOP/STO.
Modurile asistiv si activ nu sunt declarate implementate pana cand nu exista o
bucla bazata pe interactiunea pacientului si validare experimentala.
"""

import json
import math
import os
import sys
import threading

import rclpy
from geometry_msgs.msg import WrenchStamped
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                       QoSReliabilityPolicy)
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64, Float64MultiArray, String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exercise_core as core

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("Lipseste Tkinter: sudo apt install -y python3-tk", file=sys.stderr)
    sys.exit(1)


# ID-urile sunt stabile in ROS/CSV; operatorul vede denumiri de domeniu.
# Acestea sunt protocoale demonstrative, nu prescriptii clinice.
EXERCITII = {
    "ankle_pump": "Glezne — flexie/extensie bilaterala",
    "ankle_alternating": "Glezne — alternant stanga/dreapta",
    "ankle_holds": "Glezne — mentinere la capete",
    "knee_extension": "Genunchi — extensie bilaterala",
    "knee_alternating": "Genunchi — extensie alternanta",
    "knee_pulses": "Genunchi — repetari scurte",
    "hip_raise": "Sold — flexie bilaterala",
    "hip_alternating": "Sold — flexie alternanta",
    "hip_hold": "Sold — mentinere",
    "alternating_march": "Combinat — mers alternant simulat",
    "full_extension": "Combinat — extensie coordonata",
    "leg_wave": "Combinat — unda sold-genunchi-glezna",
    "ankle_session": "SERIE — glezne",
    "knee_session": "SERIE — genunchi",
    "hip_session": "SERIE — sold",
    "combined_session": "SERIE — combinata",
}
ID_DIN_ETICHETA = {v: k for k, v in EXERCITII.items()}


def _fmt(value, unit=""):
    """Lipsa informatiei ramane N/A; nu este transformata in zero."""
    try:
        value = float(value)
        if not math.isfinite(value):
            return "N/A"
        return f"{value:+.3f} {unit}".strip()
    except (TypeError, ValueError):
        return "—"


class PanelNode(Node):
    """Adaptor ROS: regulile de traiectorie raman in exercise_core/controller."""

    def __init__(self):
        super().__init__("panou_operator_reabilitare")
        self.ex_pub = self.create_publisher(String, "/exercise_cmd", 10)
        self.adj_pub = self.create_publisher(Float64MultiArray, "/adjust_cmd", 10)
        self.latest = {"provenienta": "astept eticheta senzorilor",
                       "supervizor": "astept stare", "cale": "astept recorderul"}
        self.create_subscription(JointState, "/joint_states", self._joint_states, 20)
        self.create_subscription(String, "/rehab/senzori/eticheta",
                                 lambda m: self._set("provenienta", m.data), 10)
        self.create_subscription(String, "/rehab/supervizor/stare",
                                 lambda m: self._set("supervizor", m.data), 10)
        qos = QoSProfile(depth=1, history=QoSHistoryPolicy.KEEP_LAST,
                         reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, "/rehab/inregistrare/cale",
                                 lambda m: self._set("cale", m.data), qos)
        for parte in ("left", "right"):
            for articulatie in ("hip", "knee"):
                self.create_subscription(
                    Float64, f"/rehab/cuplu/{parte}_{articulatie}",
                    self._scalar(f"cuplu.{parte}.{articulatie}"), 20)
            self.create_subscription(Float64, f"/rehab/unghi_glezna/{parte}",
                                     self._scalar(f"unghi.{parte}"), 20)
            self.create_subscription(Float64, f"/rehab/rigla_gamba/{parte}",
                                     self._scalar(f"rigla.{parte}"), 20)
            self.create_subscription(WrenchStamped, f"/rehab/forta_6d/{parte}",
                                     self._wrench(parte), 20)

    def _set(self, key, value):
        self.latest[key] = value

    def _scalar(self, key):
        return lambda msg: self._set(key, msg.data)

    def _wrench(self, parte):
        def callback(msg):
            # Conventia documentata in senzori_core.py.
            self.latest[f"forta.{parte}.Ff"] = msg.wrench.force.x
            self.latest[f"forta.{parte}.FN"] = msg.wrench.force.z
            self.latest[f"forta.{parte}.MC"] = msg.wrench.torque.y
        return callback

    def _joint_states(self, msg):
        for i, name in enumerate(msg.name):
            if name not in core.JOINT_NAMES:
                continue
            if i < len(msg.position):
                self.latest[f"q.{name}"] = msg.position[i]
            if i < len(msg.velocity):
                self.latest[f"dq.{name}"] = msg.velocity[i]
            if i < len(msg.effort):
                self.latest[f"effort_sim.{name}"] = msg.effort[i]

    def send_exercise(self, name, reps, viteza):
        payload = {"exercise": name, "reps": int(reps), "viteza": float(viteza)}
        self.ex_pub.publish(String(data=json.dumps(payload)))
        self.get_logger().info(
            f"program pasiv: {name} x{int(reps)}, factor temporal {float(viteza):.2f}")

    def send_stop(self):
        self.ex_pub.publish(String(data="neutral"))
        self.get_logger().warn("STOP HMI -> revenire controlata; NU este E-STOP")

    def send_adjust(self, values):
        msg = Float64MultiArray()
        msg.data = [float(v) for v in values]
        self.adj_pub.publish(msg)


def build_gui(node, close_callback):
    root = tk.Tk()
    root.title("LLR Rehab — panou operator si achizitie")
    root.geometry("1080x760")
    root.minsize(900, 650)
    tabs = ttk.Notebook(root)
    tabs.pack(fill="both", expand=True, padx=8, pady=8)

    # Exercitii si serii.
    ex = ttk.Frame(tabs, padding=16)
    tabs.add(ex, text="Exercitii")
    ttk.Label(ex, text="Control de reabilitare — model LLR",
              font=("TkDefaultFont", 16, "bold")).grid(
                  row=0, column=0, columnspan=4, sticky="w", pady=(0, 14))
    ttk.Label(ex, text="Mod implementat:").grid(row=1, column=0, sticky="w")
    ttk.Label(ex, text="PASIV — traiectorie de pozitie predefinita",
              foreground="#075985").grid(row=1, column=1, columnspan=3, sticky="w")
    ttk.Label(ex,
              text="Asistiv si activ necesita o bucla bazata pe forta/intentia "
                   "pacientului; sunt directii viitoare, nu functii simulate aici.",
              foreground="#8a4b08", wraplength=760).grid(
                  row=2, column=0, columnspan=4, sticky="w", pady=(2, 18))
    ids = list(core.EXERCISES) + list(core.SESSIONS)
    etichete = [EXERCITII[i] for i in ids]
    program = tk.StringVar(value=EXERCITII["knee_extension"])
    repetari = tk.IntVar(value=2)
    viteza = tk.DoubleVar(value=1.0)
    ttk.Label(ex, text="Exercitiu / serie:").grid(row=3, column=0, sticky="w", pady=6)
    ttk.Combobox(ex, textvariable=program, values=etichete, state="readonly",
                 width=52).grid(row=3, column=1, columnspan=3, sticky="ew", pady=6)
    ttk.Label(ex, text="Repetari:").grid(row=4, column=0, sticky="w", pady=6)
    ttk.Spinbox(ex, from_=1, to=10, textvariable=repetari,
                width=8).grid(row=4, column=1, sticky="w")
    ttk.Label(ex, text="Factor temporal (0.1–3.0):").grid(
        row=5, column=0, sticky="w", pady=6)
    ttk.Scale(ex, from_=0.1, to=3.0, variable=viteza, length=300).grid(
        row=5, column=1, sticky="w")
    viteza_text = ttk.Label(ex, width=8)
    viteza_text.grid(row=5, column=2, sticky="w")
    viteza.trace_add("write", lambda *_: viteza_text.configure(
        text=f"×{viteza.get():.2f}"))
    viteza_text.configure(text="×1.00")
    ttk.Button(ex, text="Porneste programul pasiv",
               command=lambda: node.send_exercise(
                   ID_DIN_ETICHETA[program.get()], repetari.get(), viteza.get())).grid(
                       row=6, column=0, columnspan=2, sticky="ew", pady=(18, 6))
    ttk.Button(ex, text="STOP controlat — revenire la postura de lucru",
               command=node.send_stop).grid(
                   row=6, column=2, columnspan=2, sticky="ew", padx=(8, 0), pady=(18, 6))
    ttk.Label(ex,
              text="STOP-ul software nu este E-STOP/STO. Programele sunt "
                   "demonstrative si necesita validare clinica inainte de utilizare.",
              foreground="#b91c1c", wraplength=820).grid(
                  row=7, column=0, columnspan=4, sticky="w", pady=12)
    ex.columnconfigure(1, weight=1)

    # Reglaje antropometrice.
    adj = ttk.Frame(tabs, padding=16)
    tabs.add(adj, text="Reglaje pacient")
    ttk.Label(adj, text="Reglaje antropometrice cu rampa lenta",
              font=("TkDefaultFont", 15, "bold")).grid(
                  row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
    labels = ["Ridicare scaun [m]", "Extensie coapsa stanga [m]",
              "Extensie coapsa dreapta [m]", "Extensie gamba stanga [m]",
              "Extensie gamba dreapta [m]"]
    sliders = []
    for row, (label, joint) in enumerate(zip(labels, core.ADJUST_JOINT_NAMES), 1):
        lo, hi = core.ADJUST_LIMITS[joint]
        ttk.Label(adj, text=label).grid(row=row, column=0, sticky="w", pady=7)
        var = tk.DoubleVar(value=0.0)
        ttk.Scale(adj, from_=lo, to=hi, variable=var, length=420).grid(
            row=row, column=1, sticky="ew", padx=8)
        shown = ttk.Label(adj, text="0.000", width=10)
        shown.grid(row=row, column=2)
        var.trace_add("write", lambda *_a, v=var, s=shown:
                      s.configure(text=f"{v.get():.3f}"))
        sliders.append(var)
    ttk.Button(adj, text="Aplica reglajele",
               command=lambda: node.send_adjust([v.get() for v in sliders])).grid(
                   row=7, column=0, columnspan=3, sticky="ew", pady=18)
    ttk.Label(adj, text="Controlerul limiteaza valorile si impune garda la sol.",
              wraplength=780).grid(row=8, column=0, columnspan=3, sticky="w")
    adj.columnconfigure(1, weight=1)

    # Canalele documentate pentru LLR.
    sensors = ttk.Frame(tabs, padding=12)
    tabs.add(sensors, text="Senzori LLR")
    ttk.Label(sensors, text="Canale documentate si stare curenta",
              font=("TkDefaultFont", 15, "bold")).grid(
                  row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
    for col, text in enumerate(("Marime", "Stanga", "Dreapta", "Sursa PDF")):
        ttk.Label(sensors, text=text, font=("TkDefaultFont", 10, "bold")).grid(
            row=1, column=col, sticky="w", padx=6, pady=4)
    rows = [
        ("Cuplu sold", "cuplu.left.hip", "cuplu.right.hip", "M2210B", "Nm"),
        ("Cuplu genunchi", "cuplu.left.knee", "cuplu.right.knee", "M2210B", "Nm"),
        ("Unghi glezna", "unghi.left", "unghi.right", "BWK216", "rad"),
        ("Lungime gamba", "rigla.left", "rigla.right", "rigla 406", "m"),
        ("Talpa Ff", "forta.left.Ff", "forta.right.Ff", "TR69-1500", "N"),
        ("Talpa FN", "forta.left.FN", "forta.right.FN", "TR69-1500", "N"),
        ("Talpa MC", "forta.left.MC", "forta.right.MC", "TR69-1500", "Nm"),
    ]
    sensor_labels = []
    for row, (name, kl, kr, source, unit) in enumerate(rows, 2):
        ttk.Label(sensors, text=name).grid(row=row, column=0, sticky="w", padx=6, pady=5)
        left, right = ttk.Label(sensors, text="—", width=18), ttk.Label(
            sensors, text="—", width=18)
        left.grid(row=row, column=1, sticky="w", padx=6)
        right.grid(row=row, column=2, sticky="w", padx=6)
        ttk.Label(sensors, text=source).grid(row=row, column=3, sticky="w", padx=6)
        sensor_labels.append((left, right, kl, kr, unit))
    provenance = ttk.Label(sensors, wraplength=900, foreground="#7c2d12")
    provenance.grid(row=10, column=0, columnspan=4, sticky="w", padx=6, pady=(18, 5))
    ttk.Label(sensors,
              text="La LLR, talpa masoara forte/moment. Encoderul liniar al pedalei "
                   "din PDF apartine aparatului LTE, nu acestui robot.",
              wraplength=900).grid(row=11, column=0, columnspan=4, sticky="w", padx=6)

    # Date si siguranta.
    data = ttk.Frame(tabs, padding=16)
    tabs.add(data, text="Date si siguranta")
    ttk.Label(data, text="Trasabilitatea sesiunii",
              font=("TkDefaultFont", 15, "bold")).pack(anchor="w", pady=(0, 12))
    cale = ttk.Label(data, text="astept recorderul", wraplength=920)
    cale.pack(anchor="w", pady=6)
    supervizor = ttk.Label(data, text="astept stare", wraplength=920)
    supervizor.pack(anchor="w", pady=6)
    ttk.Label(data,
              text="Recorderul porneste cu demo_c4 si scrie din primul feedback valid "
                   "pana la Ctrl+C. Dupa oprire, ruleaza plot_sesiune.py pentru PNG "
                   "sau session_report.py pentru PDF, CSV/JSON de metrici si raport "
                   "Markdown, pe directorul afisat aici.", wraplength=920).pack(
                       anchor="w", pady=14)

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

    def refresh():
        if closing["value"]:
            return
        for left, right, kl, kr, unit in sensor_labels:
            left.configure(text=_fmt(node.latest.get(kl), unit))
            right.configure(text=_fmt(node.latest.get(kr), unit))
        provenance.configure(text="Provenienta curenta: " +
                             str(node.latest.get("provenienta", "—")))
        cale.configure(text="CSV sesiune: " + str(node.latest.get("cale", "—")))
        supervizor.configure(text="Supervizor: " +
                             str(node.latest.get("supervizor", "—")))
        try:
            after_id["value"] = root.after(250, refresh)
        except tk.TclError:
            pass

    root.protocol("WM_DELETE_WINDOW", close_window)
    after_id["value"] = root.after(250, refresh)
    root._rehab_close = close_window
    return root


def main():
    rclpy.init()
    node = PanelNode()

    def spin_ros():
        # Inchiderea ferestrei opreste contextul in timp ce firul poate astepta
        # mesaje. ExternalShutdownException este terminarea normala a acelui fir.
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
