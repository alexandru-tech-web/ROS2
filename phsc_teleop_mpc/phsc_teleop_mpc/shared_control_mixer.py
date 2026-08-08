#!/usr/bin/env python3
"""
shared_control_mixer.py
Nod ROS 2 pentru mixare autoritate uman-robot.

Analogie mecanica: doi operatori (uman si robot) trag de un sistem
prin arcuri cu rigiditati variabile. Autoritatea = raportul rigiditatilor.

Subscrie:
    /human_cmd (geometry_msgs/Twist)
    /robot_cmd (geometry_msgs/Twist)

Publica:
    /mixed_cmd (geometry_msgs/Twist)

Parametri ROS:
    ~alpha (double, default: 0.5) - autoritate umana [0,1]
    ~alpha_mode (string, default: "fixed") - "fixed" | "adaptive" | "haptic"

Autor: PhD Research - Predictive Haptic Shared Control
"""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from geometry_msgs.msg import Twist
import numpy as np


class SharedControlMixer(Node):
    def __init__(self):
        super().__init__('shared_control_mixer')

        self.declare_parameter('alpha', 0.5)
        self.declare_parameter('alpha_mode', 'fixed')

        self.alpha = self.get_parameter('alpha').value
        self.alpha_mode = self.get_parameter('alpha_mode').value

        self.get_logger().info(
            f"Shared Control Mixer: alpha={self.alpha}, mode={self.alpha_mode}"
        )
        if self.alpha_mode == 'adaptive':
            self.get_logger().warn(
                "alpha_mode='adaptive' NU este implementat: se comporta "
                "identic cu 'fixed'. Vezi compute_alpha_adaptive().")
        self.get_logger().warn(
            "/mixed_cmd nu are inca niciun abonat: bucla de shared control "
            "este DESCHISA, deci alpha nu influenteaza planta.")

        self.u_human = np.zeros(6)
        self.u_robot = np.zeros(6)
        self.has_human = False
        self.has_robot = False

        self.sub_human = self.create_subscription(
            Twist, '/human_cmd', self.human_callback, 10)
        self.sub_robot = self.create_subscription(
            Twist, '/robot_cmd', self.robot_callback, 10)
        self.pub_mixed = self.create_publisher(Twist, '/mixed_cmd', 10)

        self.timer = self.create_timer(0.05, self.mix_step)

    def human_callback(self, msg: Twist):
        self.u_human = np.array([
            msg.linear.x, msg.linear.y, msg.linear.z,
            msg.angular.x, msg.angular.y, msg.angular.z
        ])
        self.has_human = True

    def robot_callback(self, msg: Twist):
        self.u_robot = np.array([
            msg.linear.x, msg.linear.y, msg.linear.z,
            msg.angular.x, msg.angular.y, msg.angular.z
        ])
        self.has_robot = True

    def compute_alpha_adaptive(self) -> float:
        """
        NEIMPLEMENTAT. Intoarce alpha fix.

        Intentia: autoritate adaptiva in functie de eroarea de predictie --
        daca robotul prezice bine, alpha scade si robotul preia controlul.
        Ar avea nevoie de un semnal de incredere (norma erorii MPC sau
        covarianta unui EKF), care momentan nu e publicat de nimeni.

        Nodul avertizeaza explicit la pornire daca e selectat modul
        'adaptive', ca sa nu para ca adapteaza cand de fapt nu adapteaza.
        """
        return self.alpha

    def mix_step(self):
        if not self.has_human and not self.has_robot:
            return

        if self.alpha_mode == 'adaptive':
            alpha = self.compute_alpha_adaptive()
        else:
            alpha = self.alpha

        # Mixare liniara: u_mixed = alpha * u_human + (1-alpha) * u_robot
        u_mixed = alpha * self.u_human + (1.0 - alpha) * self.u_robot

        msg = Twist()
        msg.linear.x = float(u_mixed[0])
        msg.linear.y = float(u_mixed[1])
        msg.linear.z = float(u_mixed[2])
        msg.angular.x = float(u_mixed[3])
        msg.angular.y = float(u_mixed[4])
        msg.angular.z = float(u_mixed[5])

        self.pub_mixed.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SharedControlMixer()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # In Jazzy, SIGINT ajunge la handler-ul rclpy, care inchide contextul;
        # spin() arunca atunci ExternalShutdownException, NU KeyboardInterrupt.
        # Fara ambele, Ctrl-C afisa traceback si 'ros2 run' iesea cu cod 1.
        pass
    finally:
        node.destroy_node()
        # try_shutdown(), NU shutdown(): la SIGINT handler-ul de semnal al
        # rclpy a inchis deja contextul, iar un shutdown() explicit arunca
        # RCLError "rcl_shutdown already called" -> 'ros2 run' raporteaza
        # eroare desi nodul a rulat corect (gotcha din CLAUDE.md).
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
