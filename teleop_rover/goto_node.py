#!/usr/bin/env python3
"""goto_node.py — NAVIGATOR go-to-goal (ROS 2, zero-build).

Inlocuieste operatorul: vede roverul DOAR prin pozele care supravietuiesc
legaturii degradate (acelasi gating la receptie ca operator_node) si publica
comenzi pe /teleop/cmd in ACELASI format JSON ca pilotul. De aceea e un
OPERATOR drop-in: comenzile lui curg prin link + SafetyGate + jurnal + RMW
(Zenoh/Cyclone) NESCHIMBAT — exact ce vrem ca sa masuram navigarea autonoma
sub middleware degradat.

Tinta (gx, gy) vine din:
  goal_source:=waypoint  -> parametrii goal_x, goal_y (coordonata data);
  goal_source:=object    -> ultima tinta de pe /teleop/target (obiectul
                            recunoscut de detector_node).
"""
import json
import os
import random
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nav_core import goto_command, goal_reached

LINK = "op-rob"


class GotoNode(Node):
    def __init__(self):
        super().__init__("teleop_goto")
        p = self.declare_parameter
        p("goal_source", "waypoint")      # waypoint | object
        p("goal_x", 8.0); p("goal_y", 3.0)
        p("target_class", "")             # ce culoare urmarim (gol = orice)
        p("arrive_r", 0.5)
        g = lambda k: self.get_parameter(k).value
        self.source = str(g("goal_source"))
        self.goal = (float(g("goal_x")), float(g("goal_y")))
        self.want = str(g("target_class"))
        self.arrive_r = float(g("arrive_r"))

        self.known = (0.0, 0.0, 0.0)
        self.known_t = 0.0
        self.robot_info = {}
        self.down, self.lat, self.jit, self.loss = False, 0.0, 0.0, 0.0
        self.inbox = []
        self.t0 = time.time()
        self.arrived_announced = False

        self.cmd_pub = self.create_publisher(String, "/teleop/cmd", 30)
        self.create_subscription(String, "/teleop/pose", self.on_pose, 30)
        self.create_subscription(String, "/teleop/linkstate", self.on_link, 10)
        if self.source == "object":
            self.create_subscription(String, "/teleop/target", self.on_target, 10)
        self.create_timer(0.05, self.tick)          # 20 Hz comenzi
        self.get_logger().info(
            f"navigator pornit (sursa={self.source}, tinta initiala={self.goal})")

    # ---- legatura degradata, aplicata la receptie (ca operator_node) ----
    def on_link(self, msg):
        d = json.loads(msg.data)
        self.down = LINK in d.get("down", [])
        self.lat = float(d.get("lat_ms", {}).get(LINK, 0.0))
        self.jit = float(d.get("jit_ms", {}).get(LINK, 0.0))
        self.loss = float(d.get("loss", {}).get(LINK, 0.0))

    def on_pose(self, msg):
        if self.down or random.random() < self.loss:
            return                                   # feedback pierdut
        lat = max(0.0, self.lat + random.uniform(-self.jit, self.jit)) / 1000.0
        self.inbox.append((time.time() + lat, json.loads(msg.data)))

    def on_target(self, msg):
        d = json.loads(msg.data)
        if self.want and d.get("class") != self.want:
            return
        self.goal = (float(d["x"]), float(d["y"]))   # tinta din obiectul vazut

    def tick(self):
        now = time.time()
        due = [m for m in self.inbox if m[0] <= now]
        self.inbox = [m for m in self.inbox if m[0] > now]
        for _, d in due:
            if d["t"] > self.known_t:
                self.known = (d["x"], d["y"], d["th"])
                self.known_t = d["t"]
                self.robot_info = d
        gx, gy = self.goal
        v, w, arrived = goto_command(self.known[0], self.known[1],
                                     self.known[2], gx, gy,
                                     arrive_r=self.arrive_r)
        self.cmd_pub.publish(String(data=json.dumps({"v": v, "w": w, "t": now})))
        if arrived and not self.arrived_announced:
            self.arrived_announced = True
            self.get_logger().info(
                f"TINTA ATINSA ({gx:.1f},{gy:.1f}) in {now - self.t0:.1f} s — "
                f"opriri de siguranta: {self.robot_info.get('stops', 0)}; "
                f"jurnal: ~/teleop_data/robot_log.csv")
        elif arrived and self.source == "object":
            self.arrived_announced = False           # re-armeaza pt. tinta noua


def main():
    rclpy.init()
    n = GotoNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
