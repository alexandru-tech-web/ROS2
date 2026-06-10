#!/usr/bin/env python3
"""
exercise_controller.py — Nodul ROS 2 care comanda cele 6 servomotoare
(2 sold + 2 genunchi + 2 glezna) executand programele din exercise_core.

Doua backend-uri (parametrul `backend`):
  "joint_states"  -> publica sensor_msgs/JointState pe /joint_states la 50 Hz.
                     Folosit cu robot_state_publisher + RViz (demo-ul local).
  "trajectory"    -> construieste o trajectory_msgs/JointTrajectory completa
                     si o trimite la /leg_trajectory_controller/joint_trajectory
                     (ros2_control in Gazebo sau pe servomotoarele reale —
                     ACEEASI comanda, alt executant).

Rulare (cu mediul ROS sourced):
    $ python3 exercise_controller.py --ros-args -p exercise:=full_extension -p reps:=3

Comutare LIVE a exercitiului, din alt terminal:
    $ ros2 topic pub --once /exercise_cmd std_msgs/msg/String "data: ankle_pump"
    $ ros2 topic pub --once /exercise_cmd std_msgs/msg/String \
        'data: "{\"exercise\": \"alternating_march\", \"reps\": 2}"'

NOTA MEDICALA: valorile exercitiilor sunt de demonstratie, nu prescriptii
clinice. Pe hardware real: limitare de cuplu + oprire de urgenta obligatorii.
"""

import json
import os
import sys

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from rclpy.duration import Duration

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exercise_core as core


class ExerciseController(Node):
    def __init__(self):
        super().__init__("exercise_controller")

        self.declare_parameter("exercise", "knee_extension")
        self.declare_parameter("reps", 3)
        self.declare_parameter("backend", "joint_states")
        self.declare_parameter("rate_hz", 50.0)
        self.declare_parameter("loop", False)

        self.backend = self.get_parameter("backend").value
        self.loop = bool(self.get_parameter("loop").value)
        rate = float(self.get_parameter("rate_hz").value)

        name = self.get_parameter("exercise").value
        reps = int(self.get_parameter("reps").value)
        self._build_player(name, reps)

        # comutare live a exercitiului
        self.create_subscription(String, "exercise_cmd", self.on_cmd, 10)

        if self.backend == "trajectory":
            self.traj_pub = self.create_publisher(
                JointTrajectory, "/leg_trajectory_controller/joint_trajectory", 10)
            # o singura trimitere, dupa 1 s (lasa timp de descoperire DDS)
            self.once = self.create_timer(1.0, self.send_trajectory_once)
        else:
            self.js_pub = self.create_publisher(JointState, "joint_states", 10)
            self.t0 = self.get_clock().now()
            self.finished_logged = False
            self.timer = self.create_timer(1.0 / rate, self.on_timer)

    # ---------------- constructia programului ----------------
    def _build_player(self, name, reps):
        try:
            prog = core.build(name, reps)
        except ValueError as e:
            self.get_logger().error(str(e))
            prog = core.build("knee_extension", 1)
        self.player = core.Player(prog)
        self.get_logger().info(
            f"exercitiu: {prog.name} x{prog.reps} repetari, "
            f"durata totala {prog.total_time:.1f} s")

    def on_cmd(self, msg: String):
        """Accepta fie numele exercitiului, fie JSON {"exercise":..., "reps":...}."""
        text = msg.data.strip()
        name, reps = text, int(self.get_parameter("reps").value)
        if text.startswith("{"):
            try:
                d = json.loads(text)
                name = d.get("exercise", name)
                reps = int(d.get("reps", reps))
            except json.JSONDecodeError as e:
                self.get_logger().error(f"JSON invalid pe /exercise_cmd: {e}")
                return
        self._build_player(name, reps)
        if self.backend == "trajectory":
            self.send_trajectory_once()
        else:
            self.t0 = self.get_clock().now()
            self.finished_logged = False

    # ---------------- backend RViz: /joint_states ----------------
    def on_timer(self):
        t = (self.get_clock().now() - self.t0).nanoseconds * 1e-9
        q, done = self.player.sample(t)
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = core.JOINT_NAMES
        msg.position = [q[j] for j in core.JOINT_NAMES]
        self.js_pub.publish(msg)
        if done:
            if self.loop:
                self.t0 = self.get_clock().now()
            elif not self.finished_logged:
                self.get_logger().info(
                    "exercitiu terminat — mentin pozitia finala "
                    "(trimite alt exercitiu pe /exercise_cmd)")
                self.finished_logged = True

    # ---------------- backend ros2_control: JointTrajectory ----------------
    def send_trajectory_once(self):
        if hasattr(self, "once"):
            self.once.cancel()
        traj = JointTrajectory()
        traj.joint_names = list(core.JOINT_NAMES)
        dt = 0.1
        t = 0.0
        while t <= self.player.p.total_time + 1e-9:
            q, _ = self.player.sample(t)
            pt = JointTrajectoryPoint()
            pt.positions = [q[j] for j in core.JOINT_NAMES]
            pt.time_from_start = Duration(seconds=t).to_msg()
            traj.points.append(pt)
            t += dt
        self.traj_pub.publish(traj)
        self.get_logger().info(
            f"traiectorie trimisa: {len(traj.points)} puncte, "
            f"{self.player.p.total_time:.1f} s, catre /leg_trajectory_controller")


def main():
    rclpy.init()
    node = ExerciseController()
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
