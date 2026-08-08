#!/usr/bin/env python3
"""
mpc_controller_node.py
Nod ROS 2 pentru MPC neliniar cu compensare de delay variabil.

Subscrie:
    /robot_state (std_msgs/Float64MultiArray) - stare [p, p_dot, theta, theta_dot]
    /human_cmd (geometry_msgs/Twist) - referinta umana

Publica:
    /robot_cmd (geometry_msgs/Twist) - comanda MPC compensata
    /haptic_feedback (geometry_msgs/Wrench) - feedback haptic predictiv

Parametri ROS:
    ~N (int, default: 20) - orizont de predictie MPC
    ~dt (double, default: 0.05) - pas discretizare MPC [s]
    ~u_max (double, default: 100.0) - limita control [N]
    ~tau_est (double, default: 0.08) - latenta estimata [s]
    ~Q_diag (double_array) - diagonala matricei Q
    ~R (double, default: 0.01) - penalizare control
    ~P_diag (double_array) - diagonala matricei P (cost terminal)

Autor: PhD Research - Predictive Haptic Shared Control
"""

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float64, Float64MultiArray
from geometry_msgs.msg import Twist, Wrench
import numpy as np

from phsc_mechanical_analogies.cartpole_model import CartPoleModel
from phsc_mechanical_analogies.mpc_controller import MPCParams, DelayCompensatedMPC


class MPCControllerNode(Node):
    def __init__(self):
        super().__init__('mpc_controller_node')

        # Declarare parametri
        self.declare_parameter('N', 20)
        self.declare_parameter('dt', 0.05)
        self.declare_parameter('u_max', 100.0)
        self.declare_parameter('tau_est', 0.08)
        self.declare_parameter('Q_diag', [10.0, 1.0, 100.0, 1.0])
        self.declare_parameter('R', 0.01)
        self.declare_parameter('P_diag', [50.0, 5.0, 500.0, 5.0])
        self.declare_parameter('theta_max', 0.5)
        # Erau prezenti in mpc_tuning.yaml dar NEDECLARATI -> rclpy ii ignora
        # in silentiu. Declarati acum, deci fisierul de tuning are efect real.
        self.declare_parameter('tau_var', 0.02)
        self.declare_parameter('R_du', 0.5)
        self.declare_parameter('max_iter', 200)
        self.declare_parameter('ftol', 1.0e-6)
        # 'hard' = constrangere exacta (~2x timp de solve), 'soft' = penalizare
        # in cost (aproape gratis, fara garantie), 'none' = neimpus
        self.declare_parameter('theta_mode', 'hard')
        self.declare_parameter('n_pred', 20)
        self.declare_parameter('tau_stale_s', 0.5)

        # Citire parametri
        N = self.get_parameter('N').value
        dt = self.get_parameter('dt').value
        u_max = self.get_parameter('u_max').value
        tau_est = self.get_parameter('tau_est').value
        Q_diag = self.get_parameter('Q_diag').value
        R = self.get_parameter('R').value
        P_diag = self.get_parameter('P_diag').value
        theta_max = self.get_parameter('theta_max').value
        tau_var = self.get_parameter('tau_var').value
        R_du = self.get_parameter('R_du').value
        max_iter = self.get_parameter('max_iter').value
        ftol = self.get_parameter('ftol').value
        theta_mode = self.get_parameter('theta_mode').value
        n_pred = self.get_parameter('n_pred').value
        self.tau_stale_s = float(self.get_parameter('tau_stale_s').value)

        self.get_logger().info(
            f"MPC Params: N={N}, dt={dt}s, u_max={u_max}N, tau_est={tau_est}s, "
            f"R={R}, R_du={R_du}, theta_max={theta_max}rad"
        )

        # Initializare model si MPC
        self.model = CartPoleModel(M=1.0, m=0.1, L=0.5, g=9.81, b=0.1)
        params = MPCParams(
            N=N, dt=dt, u_max=u_max, tau_est=tau_est,
            theta_max=theta_max, tau_var=tau_var,
            Q=np.diag(Q_diag),
            R=np.array([[R]]),
            R_du=np.array([[R_du]]),
            P=np.diag(P_diag),
            max_iter=max_iter, ftol=ftol,
            theta_mode=theta_mode, n_pred=n_pred
        )
        self.mpc = DelayCompensatedMPC(self.model, params)

        # Stare curenta si referinta
        self.x_current = np.zeros(4)
        self.x_ref = np.zeros(4)
        self.has_state = False

        # Subscriptori
        self.sub_state = self.create_subscription(
            Float64MultiArray,
            '/robot_state',
            self.state_callback,
            10
        )
        self.sub_human = self.create_subscription(
            Twist,
            '/human_cmd',
            self.human_cmd_callback,
            10
        )
        # Latenta estimata online (de la latency_estimator). Cat timp nu vine
        # nimic, se foloseste tau_est static din parametri. Masurat in runda 3:
        # +/-20% eroare pe tau taie pragul de stabilitate la jumatate, deci
        # valoarea statica din YAML e doar o solutie de rezerva, nu tinta.
        self.tau_online = None
        self.tau_online_t = None
        self.sub_delay = self.create_subscription(
            Float64,
            '/estimated_delay',
            self.delay_callback,
            10
        )

        # Publicatori
        self.pub_cmd = self.create_publisher(Twist, '/robot_cmd', 10)
        self.pub_haptic = self.create_publisher(Wrench, '/haptic_feedback', 10)

        # Timer MPC nominal la 1/dt Hz. ATENTIE: rata NOMINALA. Vezi garda de
        # timp real din mpc_step() -- rata efectiva masurata este mult mai mica.
        self.timer_period = dt
        self.t0 = self.get_clock().now().nanoseconds / 1e9
        self.cycle_count = 0
        self.overrun_count = 0
        self.timer = self.create_timer(dt, self.mpc_step)

        self.get_logger().info("MPC Controller Node initializat.")

    def state_callback(self, msg: Float64MultiArray):
        """Callback stare robot, cu validare (lungime + finititate)."""
        if len(msg.data) < 4:
            self.get_logger().warn(
                f"/robot_state are {len(msg.data)} elemente, sunt necesare 4. Ignorat.",
                throttle_duration_sec=2.0)
            return

        x = np.asarray(msg.data[:4], dtype=float)
        if not np.all(np.isfinite(x)):
            # Fara aceasta garda, un NaN trece prin fallback-ul LQR
            # (u = -(K @ x)) si se publica o forta NaN pe /robot_cmd.
            self.get_logger().error(
                f"/robot_state contine NaN/Inf: {msg.data[:4]}. Ignorat.",
                throttle_duration_sec=2.0)
            return

        self.x_current = x
        self.has_state = True

    def delay_callback(self, msg: Float64):
        """Latenta estimata de latency_estimator."""
        tau = float(msg.data)
        if not np.isfinite(tau) or tau < 0.0 or tau > 1.0:
            self.get_logger().warn(
                f"/estimated_delay invalid ({tau}), ignorat.",
                throttle_duration_sec=2.0)
            return
        self.tau_online = tau
        self.tau_online_t = self.get_clock().now().nanoseconds / 1e9

    def current_tau(self) -> float:
        """
        tau online daca a sosit recent, altfel cel static. O estimare veche e
        mai periculoasa decat una implicita: daca legatura a cazut, valoarea
        veche nu mai descrie canalul.
        """
        if self.tau_online is not None and self.tau_online_t is not None:
            age = self.get_clock().now().nanoseconds / 1e9 - self.tau_online_t
            if age < self.tau_stale_s:
                return self.tau_online
            self.get_logger().warn(
                f"/estimated_delay vechi de {age*1000:.0f} ms; "
                f"revin la tau_est static ({self.mpc.params.tau_est*1000:.0f} ms).",
                throttle_duration_sec=5.0)
        return self.mpc.params.tau_est

    def human_cmd_callback(self, msg: Twist):
        """Callback comanda umana - mapare la referinta de stare."""
        # Simplificare: referinta umana = pozitie dorita a caruciorului
        # In viitor: pot fi integrate si alte DOF
        self.x_ref[0] = msg.linear.x
        self.x_ref[1] = 0.0
        self.x_ref[2] = 0.0  # verticala dorita
        self.x_ref[3] = 0.0

    def mpc_step(self):
        """Pas MPC periodic."""
        if not self.has_state:
            self.get_logger().warn("Stare robot necunoscuta. Astept /robot_state...", throttle_duration_sec=2.0)
            return

        # Latenta folosita de compensare: masurata online daca e proaspata,
        # altfel valoarea statica din parametri (degradare eleganta).
        tau_now = self.current_tau()
        tau_func = lambda t: tau_now

        # Timp RELATIV la pornirea nodului. Cu ceasul absolut (epoch ~1.79e9 s)
        # faza lui sin(2t) era o functie irreproductibila de momentul lansarii.
        t = self.get_clock().now().nanoseconds / 1e9 - self.t0

        t_cycle0 = time.perf_counter()

        try:
            u_opt, U_seq, success = self.mpc.step(
                self.x_current, self.x_ref, tau_func, t
            )

            if not success:
                self.get_logger().warn("MPC nu a convergent. Folosesc LQR fallback.")
                K = self.model.lqr_gain()
                u_opt = -(K @ self.x_current)[0]

            # Publicare comanda
            cmd_msg = Twist()
            cmd_msg.linear.x = float(u_opt)
            self.pub_cmd.publish(cmd_msg)

            # Feedback haptic predictiv
            x_pred = self.mpc.predict_state_delay(
                self.x_current, np.array([u_opt]), self.mpc.params.tau_est
            )
            force_6d = self.mpc.compute_haptic_feedback(x_pred, self.x_ref, self.x_current)

            haptic_msg = Wrench()
            haptic_msg.force.x = float(force_6d[0])
            haptic_msg.force.y = float(force_6d[1])
            haptic_msg.force.z = float(force_6d[2])
            haptic_msg.torque.x = float(force_6d[3])
            haptic_msg.torque.y = float(force_6d[4])
            haptic_msg.torque.z = float(force_6d[5])
            self.pub_haptic.publish(haptic_msg)

            # Garda de timp real: face VIZIBILA depasirea perioadei.
            # Masurat pe aceasta masina: un solve SLSQP cu N=20 dureaza
            # ~250-500 ms, deci timer-ul de 50 ms este depasit de ~5-10x si
            # rata efectiva este ~2-4 Hz, NU 20 Hz.
            t_cycle = time.perf_counter() - t_cycle0
            self.cycle_count += 1
            if t_cycle > self.timer_period:
                self.overrun_count += 1
                self.get_logger().warn(
                    f"DEPASIRE timp real: ciclul MPC a durat {t_cycle*1000:.0f} ms > "
                    f"perioada {self.timer_period*1000:.0f} ms "
                    f"(rata efectiva ~{1.0/t_cycle:.1f} Hz; "
                    f"{self.overrun_count}/{self.cycle_count} cicluri depasite)",
                    throttle_duration_sec=5.0)

        except Exception as e:
            self.get_logger().error(f"Eroare MPC step: {e}")

    def destroy_node(self):
        self.mpc.reset()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MPCControllerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # ExternalShutdownException e ce arunca efectiv spin() la SIGINT in
        # Jazzy; doar KeyboardInterrupt (varianta initiala) NU o prindea.
        pass
    finally:
        node.destroy_node()
        # try_shutdown(), NU shutdown(): vezi comentariul din
        # shared_control_mixer.py -- shutdown() dublu arunca RCLError la Ctrl-C.
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
