#!/usr/bin/python3
"""
exercise_controller.py  -- v3. Comanda cele 6 servomotoare de exercitiu si
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
        # viteza: factor pe axa TIMPULUI, nu pe amplitudine. Traiectoria are exact
        # aceleasi unghiuri, parcurse mai repede sau mai incet. Amplitudinea nu se
        # atinge niciodata dintr-un buton de viteza -- ar schimba exercitiul, nu
        # ritmul lui, si limitele articulare sunt limite, nu sugestii.
        self.declare_parameter("viteza", 1.0)

        self.backend = self.get_parameter("backend").value
        self.loop = bool(self.get_parameter("loop").value)
        self.rate = float(self.get_parameter("rate_hz").value)
        v = float(self.get_parameter("viteza").value)
        if not 0.1 <= v <= 3.0:
            self.get_logger().warn(
                "viteza=%.2f in afara intervalului 0.1..3.0; o limitez" % v)
            v = min(3.0, max(0.1, v))
        self.viteza = v

        # GARDIANUL DE CONVENTIE. Modelul isi declara versiunea in URDF; fisierul de
        # traiectorii pe a lui. Cat timp difera, nu se ruleaza NIMIC. Un exercitiu
        # rulat in conventia gresita nu da eroare: misca robotul altundeva, linistit.
        self._conventie_ok = None
        from rclpy.qos import (QoSProfile, QoSDurabilityPolicy,
                               QoSHistoryPolicy, QoSReliabilityPolicy)
        qos = QoSProfile(depth=1, history=QoSHistoryPolicy.KEEP_LAST,
                         reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, "/robot_description", self._descriere, qos)

        # starea curenta a tuturor articulatiilor
        self.q_cur = {j: 0.0 for j in core.JOINT_NAMES}
        self.q_prev = dict(self.q_cur)
        self.feedback_seen = set()
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
            self._asteptare_feedback_logata = False
            # Nu folosim un delay fix: cu use_sim_time primul /clock poate sari
            # direct la cateva secunde si timerul ar porni inainte de feedback.
            self.once = self.create_timer(0.10, self.start_pending)
        else:
            self.js_pub = self.create_publisher(JointState, "joint_states", 10)
            self._build(name, reps)
            self.t0 = self.get_clock().now()
            self.finished_logged = False
            self.timer = self.create_timer(1.0 / self.rate, self.tick_joint_states)

    def _descriere(self, msg):
        """Extrage versiunea de conventie din URDF si da verdictul, o singura data."""
        import re as _re
        m = _re.search(r'conventie_versiune"\s*>\s*([^<\s]+)\s*<', msg.data)
        a_modelului = m.group(1) if m else None
        ok, motiv = core.verdict_conventie(a_modelului)
        self._conventie_ok = ok
        if ok:
            self.get_logger().info(motiv)
        else:
            self.get_logger().error(motiv)
            self.get_logger().error(
                "NU trimit nicio traiectorie. Reconversia e punctul 7 din planul de "
                "geometrie; pana atunci exercitiile sunt blocate deliberat.")

    def _pot_rula(self):
        if self._conventie_ok is None:
            self.get_logger().warn(
                "inca nu am primit /robot_description; nu pot verifica conventia, "
                "deci nu trimit nimic (un 'nu stiu' nu e un 'da')")
            return False
        return self._conventie_ok

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
                # Viteza este un factor temporal, nu modifica amplitudinea.
                # HMI-ul o poate schimba intre programe, dar nu in timpul unei
                # traiectorii deja trimise controlerului.
                viteza = float(d.get("viteza", self.viteza))
                if not 0.1 <= viteza <= 3.0:
                    raise ValueError("viteza trebuie sa fie in intervalul 0.1..3.0")
                self.viteza = viteza
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                self.get_logger().error(f"comanda invalida pe /exercise_cmd: {e}")
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
        if not self._pot_rula():
            return
        dt = 1.0 / self.rate
        t = (self.get_clock().now() - self.t0).nanoseconds * 1e-9
        q, done = self.player.sample(t * self.viteza)
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
                self.get_logger().info("exercitiu terminat; mentin pozitia "
                                       "(trimite altul pe /exercise_cmd)")
                self.finished_logged = True

    # ---------------- backend ros2_control ----------------
    def on_js_feedback(self, msg: JointState):
        for n, p in zip(msg.name, msg.position):
            if n in self.q_cur:
                self.q_cur[n] = p
                self.feedback_seen.add(n)
            elif n in self.adj_cur:
                self.adj_cur[n] = p

    def start_pending(self):
        lipsa = [j for j in core.JOINT_NAMES if j not in self.feedback_seen]
        if lipsa or self._conventie_ok is None:
            if not self._asteptare_feedback_logata:
                self.get_logger().info(
                    "astept feedback pentru toate cele 6 axe si confirmarea "
                    "conventiei inainte de prima traiectorie")
                self._asteptare_feedback_logata = True
            return
        self.once.cancel()
        name, reps = self._pending
        self._build(name, reps)
        self.send_trajectory()

    def send_trajectory(self):
        if not self._pot_rula():
            return
        traj = JointTrajectory()
        traj.joint_names = list(core.JOINT_NAMES)
        t, dt = 0.0, 0.1
        while t <= self.player.p.total_time + 1e-9:
            q, _ = self.player.sample(t)
            pt = JointTrajectoryPoint()
            pt.positions = [q[j] for j in core.JOINT_NAMES]
            pt.time_from_start = Duration(seconds=t / self.viteza).to_msg()
            traj.points.append(pt)
            t += dt
        self.traj_pub.publish(traj)
        self.get_logger().info(
            f"traiectorie trimisa: {len(traj.points)} puncte, "
            f"{self.player.p.total_time / self.viteza:.1f} s "
            f"(viteza x{self.viteza:g})")

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
    except RuntimeError as exc:
        # Jazzy poate invalida subscription-ul exact cand SIGINT intrerupe
        # executorul. O acceptam numai pentru semnatura cunoscuta de shutdown.
        if rclpy.ok() and "Unable to convert call argument" not in str(exc):
            raise
    finally:
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
