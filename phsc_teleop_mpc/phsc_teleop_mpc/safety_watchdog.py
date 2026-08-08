#!/usr/bin/env python3
"""
safety_watchdog.py
Garzi de siguranta intre controller si robot.

Pe cart-pole simulat, o comanda gresita inseamna un pendul cazut. Pe UR3
inseamna un brat real in miscare, deci nodul asta trebuie sa fie in cale
(in serie), nu doar sa observe.

Lantul: /robot_cmd -> [watchdog] -> /robot_cmd_safe -> driver robot

Functii:
  1. Watchdog pe /robot_state -- e-stop daca starea lipseste prea mult
     (inclusiv daca nu a venit NICIODATA -- vezi nota de mai jos)
  2. Limita de unghi + limita de comanda (clamp)
  3. Limita de rata (slew) pe comanda: fara ea, un salt de la -u_max la
     +u_max e o treapta pe care hardware-ul o simte ca soc
  4. E-stop extern pe /estop_trigger, cu resetare explicita pe /estop_reset
  5. Cand e-stop e activ, publica ACTIV zero, repetat -- nu doar tace

Publica:
  /robot_cmd_safe (geometry_msgs/Twist)
  /safety_status (std_msgs/Bool)   True = safe

Autor: PhD Research - Predictive Haptic Shared Control
"""

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Float64MultiArray


class SafetyWatchdog(Node):
    def __init__(self):
        super().__init__('safety_watchdog')

        self.declare_parameter('state_timeout_ms', 200.0)
        self.declare_parameter('theta_limit_deg', 30.0)
        self.declare_parameter('u_max', 50.0)
        self.declare_parameter('slew_max_N_per_s', 500.0)
        self.declare_parameter('rate_hz', 50.0)
        # Daca nu a venit NICIODATA o stare, dupa cat timp de la pornire
        # declaram e-stop. Varianta initiala nu verifica acest caz: cu
        # last_state_time = None watchdog-ul nu declansa niciodata, deci un
        # robot care nu publica deloc starea trecea drept 'safe'.
        self.declare_parameter('startup_grace_s', 5.0)

        self.state_timeout = float(self.get_parameter('state_timeout_ms').value) / 1000.0
        self.theta_limit = np.radians(float(self.get_parameter('theta_limit_deg').value))
        self.u_max = float(self.get_parameter('u_max').value)
        self.slew = float(self.get_parameter('slew_max_N_per_s').value)
        rate = float(self.get_parameter('rate_hz').value)
        self.grace = float(self.get_parameter('startup_grace_s').value)

        self.last_state_t = None
        self.t_start = self._now()
        self.e_stop = False
        self.motiv = ''
        self.u_last = 0.0
        self.t_last_cmd = self._now()

        self.create_subscription(Float64MultiArray, '/robot_state',
                                 self.state_cb, 10)
        self.create_subscription(Twist, '/robot_cmd', self.cmd_cb, 10)
        self.create_subscription(Bool, '/estop_trigger', self.estop_cb, 10)
        self.create_subscription(Bool, '/estop_reset', self.reset_cb, 10)

        self.pub_safe = self.create_publisher(Twist, '/robot_cmd_safe', 10)
        self.pub_status = self.create_publisher(Bool, '/safety_status', 10)

        self.create_timer(1.0 / rate, self.step)

        self.get_logger().info(
            f"Safety Watchdog: timeout={self.state_timeout*1000:.0f} ms, "
            f"|theta|<={np.degrees(self.theta_limit):.0f} grade, "
            f"|u|<={self.u_max:.0f} N, slew<={self.slew:.0f} N/s")

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def state_cb(self, msg: Float64MultiArray):
        if len(msg.data) < 4:
            return
        x = np.asarray(msg.data[:4], dtype=float)
        if not np.all(np.isfinite(x)):
            self.trip('stare cu NaN/Inf')
            return
        self.last_state_t = self._now()
        if abs(x[2]) > self.theta_limit:
            self.trip(f'theta={np.degrees(x[2]):.1f} grade peste limita '
                      f'{np.degrees(self.theta_limit):.0f}')

    def cmd_cb(self, msg: Twist):
        u = float(msg.linear.x)
        if not np.isfinite(u):
            self.trip('comanda NaN/Inf')
            return
        self.u_req = u

    def estop_cb(self, msg: Bool):
        if msg.data:
            self.trip('e-stop extern')

    def reset_cb(self, msg: Bool):
        """
        Resetarea e EXPLICITA si separata de declansare. Un e-stop care se
        auto-reseteaza cand starea revine ar putea reporni bratul singur.
        """
        if not msg.data:
            return
        if self.e_stop:
            self.get_logger().warn(f"E-stop RESETAT (era: {self.motiv})")
        self.e_stop = False
        self.motiv = ''
        self.u_last = 0.0
        # Dupa reset repornim perioada de gratie de la zero, in loc sa dam
        # doar state_timeout. Altfel, daca sursa de stare nu e inca activa
        # (discovery ROS dureaza ~1-2 s), watchdog-ul re-declanseaza imediat
        # si resetul pare ca nu functioneaza. Verificat pe banc.
        self.last_state_t = None
        self.t_start = self._now()

    def trip(self, motiv: str):
        if not self.e_stop:
            self.e_stop = True
            self.motiv = motiv
            self.get_logger().error(f"!!! E-STOP: {motiv} !!!")
            self.u_last = 0.0
            self.pub_safe.publish(Twist())

    def step(self):
        now = self._now()

        if self.last_state_t is None:
            if now - self.t_start > self.grace:
                self.trip(f'nicio stare primita in {self.grace:.0f} s de la pornire')
        else:
            dt = now - self.last_state_t
            if dt > self.state_timeout:
                self.trip(f'stare lipsa de {dt*1000:.0f} ms')

        if self.e_stop:
            # publicam ACTIV zero, continuu, cat timp e-stop e activ
            self.pub_safe.publish(Twist())
        else:
            u_req = getattr(self, 'u_req', 0.0)
            u = float(np.clip(u_req, -self.u_max, self.u_max))
            # limitare de rata
            dt = max(1e-6, now - self.t_last_cmd)
            du_max = self.slew * dt
            u = float(np.clip(u, self.u_last - du_max, self.u_last + du_max))
            self.u_last = u
            m = Twist()
            m.linear.x = u
            self.pub_safe.publish(m)

        self.t_last_cmd = now
        self.pub_status.publish(Bool(data=not self.e_stop))


def main(args=None):
    rclpy.init(args=args)
    node = SafetyWatchdog()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
