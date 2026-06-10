#!/usr/bin/env python3
"""operator_node.py — OPERATORUL de la distanta (ROS 2, zero-build).

Vede roverul DOAR prin pozele care supravietuiesc legaturii degradate
(gating la receptie din /teleop/linkstate) si trimite comenzi pe
/teleop/cmd la 20 Hz. Doua moduri:

  mode:=pilot   (implicit) — operatorul-MODEL (pure pursuit pe feedback
                intarziat): rulari perfect repetabile pentru masuratori;
  mode:=manual  — fereastra Tk: conduci cu W/A/S/D, vezi traseul, punctul
                ULTIMEI poze primite (atat stie operatorul!), varsta
                feedback-ului si varsta comenzii raportata de robot —
                senzatia reala de teleoperare cu 500 ms de latenta.

La terminarea traseului afiseaza rezumatul (timp, varsta medie a
feedback-ului, opririle de siguranta raportate de robot).
"""
import json
import os
import random
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rover_core import Course, PilotModel

LINK = "op-rob"


class OperatorNode(Node):
    def __init__(self):
        super().__init__("teleop_operator")
        self.declare_parameter("mode", "pilot")
        self.mode = str(self.get_parameter("mode").value)
        self.course = Course()
        self.pilot = PilotModel(self.course)
        self.known = (0.0, 0.0, 0.0)
        self.known_t = 0.0
        self.robot_info = {}
        self.down, self.lat, self.jit, self.loss = False, 0.0, 0.0, 0.0
        self.inbox = []
        self.keys = set()               # pentru modul manual
        self.t0 = time.time()
        self.done_announced = False

        self.cmd_pub = self.create_publisher(String, "/teleop/cmd", 30)
        self.create_subscription(String, "/teleop/pose", self.on_pose, 30)
        self.create_subscription(String, "/teleop/linkstate", self.on_link, 10)
        self.create_timer(0.05, self.tick)          # 20 Hz comenzi
        self.get_logger().info(f"operator pornit (mode={self.mode})")

    def on_link(self, msg):
        d = json.loads(msg.data)
        self.down = LINK in d.get("down", [])
        self.lat = float(d.get("lat_ms", {}).get(LINK, 0.0))
        self.jit = float(d.get("jit_ms", {}).get(LINK, 0.0))
        self.loss = float(d.get("loss", {}).get(LINK, 0.0))

    def on_pose(self, msg):
        if self.down or random.random() < self.loss:
            return                                   # feedback pierdut
        d = json.loads(msg.data)
        lat = max(0.0, self.lat + random.uniform(-self.jit, self.jit)) / 1000.0
        self.inbox.append((time.time() + lat, d))

    def tick(self):
        now = time.time()
        due = [m for m in self.inbox if m[0] <= now]
        self.inbox = [m for m in self.inbox if m[0] > now]
        for _, d in due:
            if d["t"] > self.known_t:
                self.known = (d["x"], d["y"], d["th"])
                self.known_t = d["t"]
                self.robot_info = d
        if self.mode == "manual":
            v = 0.8 * (("w" in self.keys) - ("s" in self.keys))
            w = 1.5 * (("a" in self.keys) - ("d" in self.keys))
        else:
            v, w = self.pilot.command(*self.known)
        self.cmd_pub.publish(String(data=json.dumps(
            {"v": v, "w": w, "t": now})))
        if self.robot_info.get("done") and not self.done_announced:
            self.done_announced = True
            self.get_logger().info(
                f"TRASEU TERMINAT in {now - self.t0:.1f} s — "
                f"opriri de siguranta: {self.robot_info.get('stops', 0)}; "
                f"jurnalul-traseu: ~/teleop_data/robot_log.csv")


# ---------------- fereastra modului manual ----------------
def build_gui(node: OperatorNode):
    import tkinter as tk
    from tkinter import ttk
    S, M = 28, 60                       # scara px/m, margine
    pts = node.course.pts
    W = int((max(p[0] for p in pts) + 2) * S) + M
    H = int((max(abs(p[1]) for p in pts) + 2) * 2 * S)
    root = tk.Tk()
    root.title("Teleoperare — operator MANUAL (W/A/S/D)")
    cv = tk.Canvas(root, width=W, height=H, bg="#1b1b22")
    cv.pack(padx=6, pady=6)
    info = tk.StringVar(value="astept feedback...")
    ttk.Label(root, textvariable=info).pack(anchor="w", padx=8, pady=(0, 6))

    def P(x, y):
        return M / 2 + x * S, H / 2 - y * S

    root.bind("<KeyPress>", lambda e: node.keys.add(e.keysym.lower()))
    root.bind("<KeyRelease>", lambda e: node.keys.discard(e.keysym.lower()))

    def draw():
        cv.delete("all")
        for i in range(len(pts) - 1):
            cv.create_line(*P(*pts[i]), *P(*pts[i + 1]),
                           fill="#555", dash=(4, 3))
        for (gx, gy) in pts[1:]:
            for dy in (+0.9, -0.9):
                x, y = P(gx, gy + dy)
                cv.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#d8702e")
        x, y, th = node.known
        cx, cy = P(x, y)
        cv.create_oval(cx - 7, cy - 7, cx + 7, cy + 7,
                       fill="#2E73CC", outline="white")
        import math as m
        cv.create_line(cx, cy, cx + 14 * m.cos(th), cy - 14 * m.sin(th),
                       fill="white", width=2)
        age = time.time() - node.known_t if node.known_t else None
        ri = node.robot_info
        info.set(f"varsta feedback: {age:.2f} s   "
                 f"varsta comenzii la robot: {ri.get('cmd_age', '—')} s   "
                 f"oprit (watchdog): {'DA' if ri.get('stopped') else 'nu'}   "
                 f"opriri: {ri.get('stops', 0)}"
                 if age is not None else "astept feedback...")
        root.after(80, draw)

    root.after(200, draw)
    return root


def main():
    rclpy.init()
    node = OperatorNode()
    if node.mode == "manual":
        spin = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        spin.start()
        root = build_gui(node)
        try:
            root.mainloop()
        finally:
            rclpy.try_shutdown()
            spin.join(timeout=2.0)
            node.destroy_node()
    else:
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == "__main__":
    main()
