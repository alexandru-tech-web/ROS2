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
from tf2_msgs.msg import TFMessage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rover_core import DiffDrive, Course, SafetyGate

LINK = "op-rob"


class RobotNode(Node):
    def __init__(self):
        super().__init__("teleop_robot")
        self.declare_parameter("use_gazebo", False)
        self.use_gz = bool(self.get_parameter("use_gazebo").value)
        # POZA ABSOLUTA in lume: turnul rosu = (8,3) real, indiferent de spawn/yaw.
        # Topicul de poza din Gazebo are uneori child_frame_id GOL; atunci roverul
        # se identifica drept transformul cel mai DEPARTE de origine (link-urile sunt
        # relative la baza, deci au pozitii mici < ~1 m). Daca poza-lume lipseste,
        # cadem automat pe odometria relativa (fallback).
        self.declare_parameter("use_world_pose", True)
        self.use_world_pose = bool(self.get_parameter("use_world_pose").value)
        self.declare_parameter("model_name", "rover")
        self.model_name = str(self.get_parameter("model_name").value)
        self.declare_parameter("world_name", "teleop_rough")
        self.world_name = str(self.get_parameter("world_name").value)
        # link-urile rover sunt < ~1 m de baza; spawn/tinta sunt la |pos| mare.
        self.declare_parameter("pose_min_dist", 2.0)
        self.pose_min_dist = float(self.get_parameter("pose_min_dist").value)
        self._have_world_pose = False
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
        # --- metrici end-to-end (degradare) ---
        self._cmd_rx = 0            # comenzi PRIMITE (au trecut de link)
        self._cmd_drop = 0          # comenzi PIERDUTE pe link (down sau loss)
        self._last_exec_t = None    # wall-clock al ultimei comenzi NOI executate
        self._last_emit_t = None    # t_emis al ultimei comenzi NOI executate
        self._prev_stopped = True   # pt. numararea tranzitiilor 0->1 (opriri)
        self._stop_events = 0

        self.pose_pub = self.create_publisher(String, "/teleop/pose", 20)
        self.create_subscription(String, "/teleop/cmd", self.on_cmd, 30)
        self.create_subscription(String, "/teleop/linkstate", self.on_link, 10)
        if self.use_gz:
            self.tw_pub = self.create_publisher(Twist, "/model/rover/cmd_vel", 10)
            self.create_subscription(Odometry, "/model/rover/odometry",
                                     self.on_odom, 30)
            if self.use_world_pose:
                topic = f"/world/{self.world_name}/dynamic_pose/info"
                self.create_subscription(TFMessage, topic, self.on_world_pose, 30)
        os.makedirs(os.path.expanduser("~/teleop_data"), exist_ok=True)
        self.log = open(os.path.expanduser("~/teleop_data/robot_log.csv"), "w")
        self.log.write("t_s,x,y,cte,cmd_age,fb_age,stopped,e2e_lat,cmd_jitter,cmd_gap,stops,drop_rate\n")
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
            self._cmd_drop += 1                      # pierdut pe drum
            return
        self._cmd_rx += 1
        d = json.loads(msg.data)
        lat = max(0.0, self.lat + random.uniform(-self.jit, self.jit)) / 1000.0
        self.inbox.append((time.time() + lat, d["t"], d["v"], d["w"]))

    def _yaw_from_quat(self, q):
        return math.atan2(2 * (q.w * q.z + q.x * q.y),
                          1 - 2 * (q.y * q.y + q.z * q.z))

    def on_world_pose(self, msg):
        """Poza ABSOLUTA in lume. Identifica roverul prin:
        (a) child_frame_id care contine numele modelului, daca e setat; altfel
        (b) transformul cel mai departe de origine (baza rover; link-urile sunt
            relative la baza, deci < ~1 m). Asa merge si cand frame_id e gol.
        """
        best = None
        best_d = -1.0
        for tr in msg.transforms:
            cf = tr.child_frame_id or ""
            t = tr.transform.translation
            # (a) potrivire dupa nume, daca topicul seteaza child_frame_id
            if self.model_name and self.model_name in cf:
                if not self._have_world_pose:
                    self.t0 = time.time()      # porneste cronometrul la prima poza reala
                self.rover.x, self.rover.y = t.x, t.y
                self.rover.th = self._yaw_from_quat(tr.transform.rotation)
                self._have_world_pose = True
                return
            # (b) candidat: cel mai departe de origine
            d = (t.x * t.x + t.y * t.y) ** 0.5
            if d > best_d:
                best_d = d
                best = tr
        # daca niciun nume nu s-a potrivit, foloseste candidatul cel mai indepartat
        if best is not None and best_d >= self.pose_min_dist:
            if not self._have_world_pose:
                self.t0 = time.time()          # porneste cronometrul la prima poza reala
            t = best.transform.translation
            self.rover.x, self.rover.y = t.x, t.y
            self.rover.th = self._yaw_from_quat(best.transform.rotation)
            self._have_world_pose = True

    def on_odom(self, msg):
        # FALLBACK: doar daca NU avem poza-lume (odometrie relativa la spawn)
        if self.use_world_pose and self._have_world_pose:
            return
        p = msg.pose.pose.position
        self.rover.x, self.rover.y = p.x, p.y
        self.rover.th = self._yaw_from_quat(msg.pose.pose.orientation)

    # ---------- bucla de control ----------
    def tick(self):
        now = time.time()
        # asteapta prima poza-LUME valida: altfel am loga pozitia-fantoma (0,0)
        # de dinainte ca dynamic_pose/info sa publice, ceea ce strica start-ul in analiza
        if self.use_world_pose and not self._have_world_pose:
            return
        due = [m for m in self.inbox if m[0] <= now]
        self.inbox = [m for m in self.inbox if m[0] > now]
        # metrici end-to-end: doar pe comenzile NOI executate acum
        e2e_lat = ""
        cmd_jitter = ""
        cmd_gap = ""
        for _, t_emis, v, w in due:
            accepted = self.gate.on_command(now, t_emis, v, w)
            if accepted:
                # e2e: emitere (goto) -> executie (robot), include link+jitter+coada
                e2e = (now - t_emis) * 1000.0
                e2e_lat = f"{e2e:.1f}"
                if self._last_exec_t is not None:
                    # jitter = variatia intervalului real intre comenzi executate
                    cmd_jitter = f"{(now - self._last_exec_t) * 1000.0:.1f}"
                self._last_exec_t = now
                self._last_emit_t = t_emis
        # gap = cat timp a trecut de la ultima comanda executata (creste sub loss)
        if self._last_exec_t is not None:
            cmd_gap = f"{(now - self._last_exec_t) * 1000.0:.1f}"
        v, w, stopped = self.gate.output(now)
        # numara tranzitiile activ->oprit (opriri de siguranta)
        if stopped and not self._prev_stopped:
            self._stop_events += 1
        self._prev_stopped = stopped
        # drop_rate cumulativ: pierdute / (primite + pierdute)
        tot = self._cmd_rx + self._cmd_drop
        drop_rate = f"{self._cmd_drop / tot:.3f}" if tot else ""
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
                       f"{cte:.3f},{age},,{int(stopped)},"
                       f"{e2e_lat},{cmd_jitter},{cmd_gap},{self._stop_events},{drop_rate}\n")

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
