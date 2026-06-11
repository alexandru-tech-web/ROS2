#!/usr/bin/env python3
"""
exercise_controller.py — v3. Comanda cele 6 servomotoare de exercitiu si
cele 5 axe de ajustare (scaun + segmente telescopice).

Backend-uri (parametrul `backend`):
  "joint_states"  -> publica TOATE cele 11 articulatii pe /joint_states
                     (pozitie + viteza) la 50 Hz, pentru RViz.
  "trajectory"    -> trimite JointTrajectory (cele 6 articulatii de exercitiu)
                     la /leg_trajectory_controller/joint_trajectory si
                     comenzile de ajustare la /adjust_position_controller/commands
                     (ros2_control in Gazebo / pe servomotoarele reale).

Topicuri de comanda (de la panoul de operator sau din terminal):
  /exercise_cmd  std_msgs/String   nume simplu ("ankle_pump", "knee_session",
                                   "neutral" = STOP lin) sau JSON
                                   {"exercise": "...", "reps": N}
  /adjust_cmd    std_msgs/Float64MultiArray, ordinea:
                 [seat_lift, left_thigh_ext, right_thigh_ext,
                  left_shank_ext, right_shank_ext]  (metri)

Siguranta: comutarea de exercitiu porneste din POZITIA CURENTA (fara salt);
ajustarile sunt taiate la limite + regula de cuplare shank_ext <= lift+0.03
(garda la sol, demonstrata prin FK) si aplicate cu rampa la 0.03 m/s.
"""

import json
import os
import sys

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String, Float64MultiArray
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from rclpy.duration import Duration

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exercise_core as core

ALL_JOINTS = core.JOINT_NAMES + core.ADJUST_JOINT_NAMES


class ExerciseController(Node):
    def __init__(self):
        super().__init__("exercise_controller")

        self.declare_parameter("exercise", "neutral")
        self.declare_parameter("reps", 3)
        self.declare_parameter("backend", "joint_states")
        self.declare_parameter("rate_hz", 50.0)
        self.declare_parameter("loop", False)

        self.backend = self.get_parameter("backend").value
        self.loop = bool(self.get_parameter("loop").value)
        self.rate = float(self.get_parameter("rate_hz").value)

        # starea curenta a tuturor articulatiilor
        self.q_cur = {j: 0.0 for j in core.JOINT_NAMES}
        self.q_prev = dict(self.q_cur)
        self.adj_cur = {j: 0.0 for j in core.ADJUST_JOINT_NAMES}
        self.adj_target = dict(self.adj_cur)

        # comenzi de la operator
        self.create_subscription(String, "exercise_cmd", self.on_exercise_cmd, 10)
        self.create_subscription(Float64MultiArray, "adjust_cmd", self.on_adjust_cmd, 10)

        name = self.get_parameter("exercise").value
        reps = int(self.get_parameter("reps").value)

        if self.backend == "trajectory":
            # in Gazebo, pozitia curenta vine din /joint_states (broadcaster)
            self.create_subscription(JointState, "joint_states", self.on_js_feedback, 10)
            self.traj_pub = self.create_publisher(
                JointTrajectory, "/leg_trajectory_controller/joint_trajectory", 10)
            self.adj_pub = self.create_publisher(
                Float64MultiArray, "/adjust_position_controller/commands", 10)
            self.adj_timer = self.create_timer(0.05, self.tick_adjust_trajectory)
            self._pending = (name, reps)
            self.once = self.create_timer(1.5, self.start_pending)
        else:
            self.js_pub = self.create_publisher(JointState, "joint_states", 10)
            self._build(name, reps)
            self.t0 = self.get_clock().now()
            self.finished_logged = False
            self.timer = self.create_timer(1.0 / self.rate, self.tick_joint_states)

    # ---------------- constructie / comenzi ----------------
    def _build(self, name, reps):
        try:
            prog = core.build(name, reps, q_init=dict(self.q_cur))
        except ValueError as e:
            self.get_logger().error(str(e))
            prog = core.build("neutral", 1, q_init=dict(self.q_cur))
        self.player = core.Player(prog)
        self.get_logger().info(
            f"exercitiu: {prog.name} x{prog.reps}, durata {prog.total_time:.1f} s "
            f"(pornire din pozitia curenta)")

    def on_exercise_cmd(self, msg: String):
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
        self._build(name, reps)
        if self.backend == "trajectory":
            self.send_trajectory()
        else:
            self.t0 = self.get_clock().now()
            self.finished_logged = False

    def on_adjust_cmd(self, msg: Float64MultiArray):
        vals = list(msg.data)
        if len(vals) != len(core.ADJUST_JOINT_NAMES):
            self.get_logger().error(
                f"/adjust_cmd asteapta {len(core.ADJUST_JOINT_NAMES)} valori "
                f"(ordinea: {core.ADJUST_JOINT_NAMES}), a primit {len(vals)}")
            return
        raw = dict(zip(core.ADJUST_JOINT_NAMES, vals))
        safe = core.clamp_adjust(raw)
        for j in core.ADJUST_JOINT_NAMES:
            if abs(safe[j] - raw.get(j, 0.0)) > 1e-6:
                self.get_logger().warn(
                    f"ajustare taiata la valoarea sigura: {j} "
                    f"{raw.get(j, 0.0):.3f} -> {safe[j]:.3f} m")
        self.adj_target = safe

    # ---------------- backend RViz: /joint_states ----------------
    def tick_joint_states(self):
        dt = 1.0 / self.rate
        t = (self.get_clock().now() - self.t0).nanoseconds * 1e-9
        q, done = self.player.sample(t)
        self.q_prev, self.q_cur = self.q_cur, q
        # rampa axelor de ajustare (viteza constanta ADJUST_VEL)
        step = core.ADJUST_VEL * dt
        for j in core.ADJUST_JOINT_NAMES:
            d = self.adj_target[j] - self.adj_cur[j]
            self.adj_cur[j] += max(-step, min(step, d))
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(ALL_JOINTS)
        msg.position = [q[j] for j in core.JOINT_NAMES] + \
                       [self.adj_cur[j] for j in core.ADJUST_JOINT_NAMES]
        msg.velocity = [(q[j] - self.q_prev[j]) / dt for j in core.JOINT_NAMES] + \
                       [0.0] * len(core.ADJUST_JOINT_NAMES)
        self.js_pub.publish(msg)
        if done:
            if self.loop:
                self.t0 = self.get_clock().now()
            elif not self.finished_logged:
                self.get_logger().info("exercitiu terminat — mentin pozitia "
                                       "(trimite altul pe /exercise_cmd)")
                self.finished_logged = True

    # ---------------- backend ros2_control ----------------
    def on_js_feedback(self, msg: JointState):
        for n, p in zip(msg.name, msg.position):
            if n in self.q_cur:
                self.q_cur[n] = p
            elif n in self.adj_cur:
                self.adj_cur[n] = p

    def start_pending(self):
        self.once.cancel()
        name, reps = self._pending
        self._build(name, reps)
        self.send_trajectory()

    def send_trajectory(self):
        traj = JointTrajectory()
        traj.joint_names = list(core.JOINT_NAMES)
        t, dt = 0.0, 0.1
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
            f"{self.player.p.total_time:.1f} s")

    def tick_adjust_trajectory(self):
        # rampa + publicarea comenzilor de pozitie pentru axele de ajustare
        step = core.ADJUST_VEL * 0.05
        moved = False
        for j in core.ADJUST_JOINT_NAMES:
            d = self.adj_target[j] - self.adj_cur[j]
            if abs(d) > 1e-6:
                self.adj_cur[j] += max(-step, min(step, d))
                moved = True
        if moved:
            out = Float64MultiArray()
            out.data = [self.adj_cur[j] for j in core.ADJUST_JOINT_NAMES]
            self.adj_pub.publish(out)


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
