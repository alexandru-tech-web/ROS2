#!/usr/bin/env python3
"""robot_node.py — ROVERUL teleoperat (ROS 2, zero-build).

Primeste comenzi pe /teleop/cmd DOAR prin "legatura" degradata (gating la
receptie din /teleop/linkstate: cadere + pierdere + latenta + jitter), le
trece prin stratul de siguranta (watchdog 0.4 s + respingerea comenzilor
invechite) si abia apoi le aplica — pe cinematica interna (use_gazebo:=false)
sau pe modelul din Gazebo (publica Twist pe /model/rover/cmd_vel si citeste
odometria). Publica poza pe /teleop/pose (20 Hz) si scrie jurnalul-traseu
~/teleop_data/robot_log.csv (acelasi format ca SIL -> acelasi analizor).
"""
import json
import math
import os
import random
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rover_core import DiffDrive, Course, SafetyGate

LINK = "op-rob"


class RobotNode(Node):
    def __init__(self):
        super().__init__("teleop_robot")
        self.declare_parameter("use_gazebo", False)
        self.use_gz = bool(self.get_parameter("use_gazebo").value)
        self.declare_parameter("use_hardware", False)
        self.declare_parameter("port", "loop")
        self.use_hw = bool(self.get_parameter("use_hardware").value)
        self.hw = None
        if self.use_hw:
            from hw_link import HwLink
            self.hw = HwLink(str(self.get_parameter("port").value))
        self.rover = DiffDrive()
        self.course = Course()          # doar pentru CTE in jurnal
        self.gate = SafetyGate()
        self.down, self.lat, self.jit, self.loss = False, 0.0, 0.0, 0.0
        self.inbox = []                 # (t_proc, t_emis, v, w)
        self.t0 = time.time()

        self.pose_pub = self.create_publisher(String, "/teleop/pose", 20)
        self.create_subscription(String, "/teleop/cmd", self.on_cmd, 30)
        self.create_subscription(String, "/teleop/linkstate", self.on_link, 10)
        if self.use_gz:
            self.tw_pub = self.create_publisher(Twist, "/model/rover/cmd_vel", 10)
            self.create_subscription(Odometry, "/model/rover/odometry",
                                     self.on_odom, 30)
        os.makedirs(os.path.expanduser("~/teleop_data"), exist_ok=True)
        self.log = open(os.path.expanduser("~/teleop_data/robot_log.csv"), "w")
        self.log.write("t_s,x,y,cte,cmd_age,fb_age,stopped\n")
        self.create_timer(0.02, self.tick)          # 50 Hz control
        self.create_timer(0.05, self.send_pose)     # 20 Hz feedback
        self.get_logger().info(f"rover pornit (gazebo={self.use_gz}, hardware={self.use_hw}); "
                               "watchdog 0.4 s, comenzi >1 s respinse")

    # ---------- legatura degradata, aplicata la receptie ----------
    def on_link(self, msg):
        d = json.loads(msg.data)
        self.down = LINK in d.get("down", [])
        self.lat = float(d.get("lat_ms", {}).get(LINK, 0.0))
        self.jit = float(d.get("jit_ms", {}).get(LINK, 0.0))
        self.loss = float(d.get("loss", {}).get(LINK, 0.0))

    def on_cmd(self, msg):
        if self.down or random.random() < self.loss:
            return                                   # pierdut pe drum
        d = json.loads(msg.data)
        lat = max(0.0, self.lat + random.uniform(-self.jit, self.jit)) / 1000.0
        self.inbox.append((time.time() + lat, d["t"], d["v"], d["w"]))

    def on_odom(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.rover.x, self.rover.y = p.x, p.y
        self.rover.th = math.atan2(2 * (q.w * q.z + q.x * q.y),
                                   1 - 2 * (q.y * q.y + q.z * q.z))

    # ---------- bucla de control ----------
    def tick(self):
        now = time.time()
        due = [m for m in self.inbox if m[0] <= now]
        self.inbox = [m for m in self.inbox if m[0] > now]
        for _, t_emis, v, w in due:
            self.gate.on_command(now, t_emis, v, w)
        v, w, stopped = self.gate.output(now)
        if self.use_hw:                       # HARDWARE (sau loopback HIL)
            self.hw.send_cmd(v, w)
            pose = self.hw.poll()
            if pose is not None:
                self.rover.x, self.rover.y, self.rover.th = pose
        elif self.use_gz:
            tw = Twist()
            tw.linear.x, tw.angular.z = v, w
            self.tw_pub.publish(tw)
        else:
            self.rover.step(v, w, 0.02)
        # jurnalul-traseu (adevarul de la sol; analizabil cu plot_trace.py)
        t = now - self.t0
        cte = self.course.cross_track(self.rover.x, self.rover.y)
        self.course.advance(self.rover.x, self.rover.y)
        age = "" if self.gate.t_rx is None else f"{now - self.gate.t_rx:.3f}"
        self.log.write(f"{t:.2f},{self.rover.x:.3f},{self.rover.y:.3f},"
                       f"{cte:.3f},{age},,{int(stopped)}\n")

    def send_pose(self):
        self.log.flush()
        now = time.time()
        age = None if self.gate.t_rx is None else round(now - self.gate.t_rx, 3)
        self.pose_pub.publish(String(data=json.dumps(
            {"x": self.rover.x, "y": self.rover.y, "th": self.rover.th,
             "t": now, "cmd_age": age,
             "stopped": self.gate.output(now)[2],
             "done": self.course.done,
             "stops": self.gate.stop_events})))


def main():
    rclpy.init()
    n = RobotNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            n.log.close()
        except Exception:
            pass
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
