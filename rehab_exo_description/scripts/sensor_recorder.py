#!/usr/bin/env python3
"""
sensor_recorder.py — Inregistreaza datele de la senzori in CSV.

Surse (din /joint_states):
  - hip, knee:  encoder absolut       -> coloana *_pos [rad]
  - ankle:      senzor de unghi       -> coloana *_pos [rad]
  - toate:      viteza                -> *_vel [rad/s sau m/s]
  - toate:      senzor de torque      -> *_eff [N*m sau N]
                (in Gazebo: efortul aplicat de actuator; in RViz: 0 —
                 fara fizica nu exista torque)
  - axele de ajustare (prismatice)    -> pozitii [m]

Comenzi pe /record_cmd (std_msgs/String):
  "start"             -> incepe inregistrarea in ~/rehab_data/sesiune_<timestamp>.csv
  "start nume_fisier" -> incepe in ~/rehab_data/nume_fisier.csv
  "stop"              -> opreste si inchide fisierul

Rulare:
    $ ros2 run rehab_exo_description sensor_recorder.py
"""

import csv
import os
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exercise_core as core

ALL_JOINTS = core.JOINT_NAMES + core.ADJUST_JOINT_NAMES
OUT_DIR = os.path.expanduser("~/rehab_data")


class SensorRecorder(Node):
    def __init__(self):
        super().__init__("sensor_recorder")
        self.file = None
        self.writer = None
        self.t0 = None
        self.rows = 0
        self.create_subscription(JointState, "joint_states", self.on_js, 50)
        self.create_subscription(String, "record_cmd", self.on_cmd, 10)
        self.get_logger().info(
            "inregistrator pregatit — trimite 'start' / 'stop' pe /record_cmd; "
            f"fisierele merg in {OUT_DIR}/")

    def on_cmd(self, msg: String):
        parts = msg.data.strip().split(None, 1)
        cmd = parts[0].lower() if parts else ""
        if cmd == "start":
            self.start(parts[1].strip() if len(parts) > 1 else None)
        elif cmd == "stop":
            self.stop()
        else:
            self.get_logger().warn(f"comanda necunoscuta pe /record_cmd: '{msg.data}'")

    def start(self, name=None):
        if self.file:
            self.stop()
        os.makedirs(OUT_DIR, exist_ok=True)
        if not name:
            name = time.strftime("sesiune_%Y%m%d_%H%M%S")
        path = os.path.join(OUT_DIR, f"{name}.csv")
        self.file = open(path, "w", newline="")
        self.writer = csv.writer(self.file)
        # antet cu semantica senzorilor
        self.file.write("# hip/knee: encoder absolut [rad]; ankle: senzor de unghi [rad]; "
                        "axe ajustare [m]; eff: senzor torque [N*m] (Gazebo)\n")
        header = ["t_sec"]
        for j in ALL_JOINTS:
            header += [f"{j}_pos", f"{j}_vel", f"{j}_eff"]
        self.writer.writerow(header)
        self.t0 = None
        self.rows = 0
        self.get_logger().info(f"INREGISTRARE pornita: {path}")

    def stop(self):
        if not self.file:
            self.get_logger().info("nimic de oprit — nu inregistrez")
            return
        path = self.file.name
        self.file.close()
        self.file = self.writer = None
        self.get_logger().info(f"INREGISTRARE oprita: {path} ({self.rows} esantioane)")

    def on_js(self, msg: JointState):
        if not self.writer:
            return
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if self.t0 is None:
            self.t0 = t
        idx = {n: i for i, n in enumerate(msg.name)}
        row = [f"{t - self.t0:.4f}"]
        for j in ALL_JOINTS:
            i = idx.get(j)
            if i is None:
                row += ["", "", ""]
                continue
            pos = msg.position[i] if i < len(msg.position) else ""
            vel = msg.velocity[i] if i < len(msg.velocity) else ""
            eff = msg.effort[i] if i < len(msg.effort) else ""
            row += [f"{pos:.5f}" if pos != "" else "",
                    f"{vel:.5f}" if vel != "" else "",
                    f"{eff:.5f}" if eff != "" else ""]
        self.writer.writerow(row)
        self.rows += 1
        if self.rows % 500 == 0:
            self.file.flush()


def main():
    rclpy.init()
    node = SensorRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
