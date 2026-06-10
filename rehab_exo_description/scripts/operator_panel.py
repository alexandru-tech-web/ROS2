#!/usr/bin/env python3
"""
operator_panel.py — Interfata grafica a OPERATORULUI (Tkinter).

Trei zone:
  1. EXERCITII: alegi exercitiul/sesiunea + repetarile, Start; STOP = revenire
     lina la postura sezut (exercitiul `neutral`).
  2. AJUSTARE LA PACIENT: glisiere pentru ridicarea scaunului si extensiile
     telescopice (coapsa/gamba, stanga/dreapta); Aplica trimite tintele —
     controlerul le taie la valorile sigure (regula shank_ext <= lift+0.03)
     si le aplica cu rampa lenta.
  3. INREGISTRARE: porneste/opreste salvarea datelor de la senzori in CSV
     (~/rehab_data/), prin nodul sensor_recorder.

Functioneaza identic peste RViz (operator.launch.py) si peste Gazebo
(gazebo.launch.py) — panoul vorbeste doar pe topicuri.

Necesita:  sudo apt install -y python3-tk
Rulare:    ros2 run rehab_exo_description operator_panel.py
"""

import json
import os
import sys
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float64MultiArray

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exercise_core as core

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("Lipseste Tkinter: sudo apt install -y python3-tk", file=sys.stderr)
    sys.exit(1)


class PanelNode(Node):
    def __init__(self):
        super().__init__("operator_panel")
        self.ex_pub = self.create_publisher(String, "exercise_cmd", 10)
        self.adj_pub = self.create_publisher(Float64MultiArray, "adjust_cmd", 10)
        self.rec_pub = self.create_publisher(String, "record_cmd", 10)

    def send_exercise(self, name, reps):
        self.ex_pub.publish(String(data=json.dumps(
            {"exercise": name, "reps": int(reps)})))
        self.get_logger().info(f"comanda exercitiu: {name} x{reps}")

    def send_stop(self):
        self.ex_pub.publish(String(data="neutral"))
        self.get_logger().info("STOP -> revenire lina la postura sezut")

    def send_adjust(self, values):
        msg = Float64MultiArray()
        msg.data = [float(v) for v in values]
        self.adj_pub.publish(msg)
        self.get_logger().info("comanda ajustare: " + ", ".join(
            f"{j}={v:.3f}" for j, v in zip(core.ADJUST_JOINT_NAMES, values)))

    def send_record(self, text):
        self.rec_pub.publish(String(data=text))


def build_gui(node: PanelNode):
    root = tk.Tk()
    root.title("Panou operator — Sistem de reabilitare (6 servomotoare)")
    root.geometry("460x560")
    pad = {"padx": 10, "pady": 6}

    # ===== 1. EXERCITII =====
    fx = ttk.LabelFrame(root, text="1. Exercitii / sesiuni")
    fx.pack(fill="x", **pad)
    names = sorted(core.EXERCISES) + sorted(core.SESSIONS)
    ex_var = tk.StringVar(value="full_extension")
    ttk.Label(fx, text="Program:").grid(row=0, column=0, sticky="w", **pad)
    ttk.Combobox(fx, textvariable=ex_var, values=names,
                 state="readonly", width=24).grid(row=0, column=1, **pad)
    ttk.Label(fx, text="Repetari:").grid(row=1, column=0, sticky="w", **pad)
    reps_var = tk.IntVar(value=2)
    ttk.Spinbox(fx, from_=1, to=10, textvariable=reps_var,
                width=6).grid(row=1, column=1, sticky="w", **pad)
    bt = ttk.Frame(fx); bt.grid(row=2, column=0, columnspan=2, **pad)
    ttk.Button(bt, text="▶ Start",
               command=lambda: node.send_exercise(ex_var.get(), reps_var.get())
               ).pack(side="left", padx=6)
    ttk.Button(bt, text="■ STOP (revenire lina)",
               command=node.send_stop).pack(side="left", padx=6)

    # ===== 2. AJUSTARE LA PACIENT =====
    fa = ttk.LabelFrame(root, text="2. Ajustare la pacient (rampa lenta, valori sigure)")
    fa.pack(fill="x", **pad)
    labels = ["Ridicare scaun [m]", "Extensie coapsa STG [m]", "Extensie coapsa DR [m]",
              "Extensie gamba STG [m]", "Extensie gamba DR [m]"]
    sliders = []
    for i, (lbl, j) in enumerate(zip(labels, core.ADJUST_JOINT_NAMES)):
        lo, hi = core.ADJUST_LIMITS[j]
        ttk.Label(fa, text=lbl).grid(row=i, column=0, sticky="w", padx=10, pady=2)
        var = tk.DoubleVar(value=0.0)
        s = ttk.Scale(fa, from_=lo, to=hi, variable=var, length=180)
        s.grid(row=i, column=1, padx=6, pady=2)
        val = ttk.Label(fa, text="0.000", width=6)
        val.grid(row=i, column=2, padx=4)
        var.trace_add("write", lambda *_a, v=var, l=val: l.config(text=f"{v.get():.3f}"))
        sliders.append(var)
    ttk.Label(fa, foreground="#a55",
              text="Nota: extensia gambei e limitata automat la lift+0.03 (garda la sol)."
              ).grid(row=5, column=0, columnspan=3, sticky="w", padx=10, pady=2)
    ttk.Button(fa, text="Aplica ajustarile",
               command=lambda: node.send_adjust([v.get() for v in sliders])
               ).grid(row=6, column=0, columnspan=3, pady=8)

    # ===== 3. INREGISTRARE =====
    fr = ttk.LabelFrame(root, text="3. Inregistrare date senzori (CSV in ~/rehab_data/)")
    fr.pack(fill="x", **pad)
    ttk.Label(fr, text="Nume fisier (optional):").grid(row=0, column=0, sticky="w", **pad)
    name_var = tk.StringVar()
    ttk.Entry(fr, textvariable=name_var, width=22).grid(row=0, column=1, **pad)
    br = ttk.Frame(fr); br.grid(row=1, column=0, columnspan=2, **pad)
    status = ttk.Label(fr, text="oprit", foreground="#777")
    status.grid(row=2, column=0, columnspan=2, **pad)

    def rec_start():
        n = name_var.get().strip()
        node.send_record(f"start {n}" if n else "start")
        status.config(text="INREGISTREAZA...", foreground="#c33")

    def rec_stop():
        node.send_record("stop")
        status.config(text="oprit", foreground="#777")

    ttk.Button(br, text="● Start inregistrare", command=rec_start).pack(side="left", padx=6)
    ttk.Button(br, text="■ Stop", command=rec_stop).pack(side="left", padx=6)

    ttk.Label(root, foreground="#888", justify="left", wraplength=420,
              text="Valorile exercitiilor sunt de demonstratie, nu prescriptii clinice. "
                   "Pe hardware real: limitare de cuplu si oprire de urgenta independente."
              ).pack(fill="x", padx=12, pady=8)
    return root


def main():
    rclpy.init()
    node = PanelNode()
    spin = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin.start()
    root = build_gui(node)
    try:
        root.mainloop()
    finally:
        # oprim intai executorul (spin se incheie), apoi distrugem nodul —
        # altfel inchiderea ferestrei produce 'terminate called without an
        # active exception' (cursa intre firul de spin si shutdown).
        rclpy.try_shutdown()
        spin.join(timeout=2.0)
        node.destroy_node()


if __name__ == "__main__":
    main()
