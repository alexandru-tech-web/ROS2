#!/usr/bin/env python3
"""
latency_estimator.py
Estimare online a latentei in canalul de teleoperare.

DE CE CONTEAZA: masurat in runda 3, o eroare de +/-20% pe tau taie pragul de
stabilitate al buclei LQR+Smith de la 300-400 ms la 100-150 ms -- acelasi
efect ca o eroare de 30% pe masa robotului. Si supraestimarea strica la fel
de mult ca subestimarea, deci nu exista 'conservatorism' prin marirea lui
tau_est. Acest nod nu e un accesoriu, e o componenta critica a buclei.

Mecanism:
  1. publica ping cu timestamp pe /latency_ping
  2. partea remota (nodul latency_echo, rulat langa robot) da echo pe
     /latency_pong cu ACELASI timestamp
  3. RTT = t_receive - t_send;  tau ~ RTT/2
  4. EWMA + respingere de outlieri, cu protectie contra blocarii

Publica:
  /estimated_delay (std_msgs/Float64)          -- tau estimat [s]
  /delay_stats (std_msgs/Float64MultiArray)    -- [mean, std, min, max, loss]

Autor: PhD Research - Predictive Haptic Shared Control
"""

from collections import deque

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float64, Float64MultiArray, Header


class LatencyEstimator(Node):
    def __init__(self):
        super().__init__('latency_estimator')

        self.declare_parameter('window_size', 50)
        self.declare_parameter('alpha_ewma', 0.3)
        self.declare_parameter('outlier_threshold', 3.0)
        self.declare_parameter('ping_rate', 20.0)
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('tau_init', 0.05)
        self.declare_parameter('tau_max', 1.0)
        # Dupa atatia outlieri consecutivi acceptam valoarea si resetam
        # fereastra: altfel o schimbare REALA si sustinuta a latentei ar fi
        # respinsa la nesfarsit ca 'outlier' si estimatorul ar ramane blocat
        # pe regimul vechi -- exact ce nu-ti permiti intr-o teza despre
        # latenta variabila.
        self.declare_parameter('outlier_streak_max', 8)
        # Dupa cate perioade de ping fara pong consideram pachetul pierdut
        self.declare_parameter('loss_timeout_periods', 5.0)

        self.window = int(self.get_parameter('window_size').value)
        self.alpha = float(self.get_parameter('alpha_ewma').value)
        self.k_out = float(self.get_parameter('outlier_threshold').value)
        self.tau_est = float(self.get_parameter('tau_init').value)
        self.tau_max = float(self.get_parameter('tau_max').value)
        self.streak_max = int(self.get_parameter('outlier_streak_max').value)
        ping_rate = float(self.get_parameter('ping_rate').value)
        pub_rate = float(self.get_parameter('publish_rate').value)
        self.loss_timeout = (float(self.get_parameter('loss_timeout_periods').value)
                             / max(ping_rate, 1e-6))

        self.rtt_buffer = deque(maxlen=self.window)
        self.outlier_streak = 0
        self.n_sent = 0
        self.n_recv = 0
        self.last_pong_t = None

        self.pub_ping = self.create_publisher(Header, '/latency_ping', 10)
        self.pub_delay = self.create_publisher(Float64, '/estimated_delay', 10)
        self.pub_stats = self.create_publisher(
            Float64MultiArray, '/delay_stats', 10)

        self.sub_pong = self.create_subscription(
            Header, '/latency_pong', self.pong_callback, 10)

        self.create_timer(1.0 / ping_rate, self.send_ping)
        self.create_timer(1.0 / pub_rate, self.publish_delay)

        self.get_logger().info(
            f"Latency Estimator: ping {ping_rate:.0f} Hz, alpha={self.alpha}, "
            f"fereastra={self.window}, tau_init={self.tau_est*1000:.0f} ms")

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def send_ping(self):
        """Emite un ping cu timestamp. Partea remota trebuie sa dea echo."""
        msg = Header()
        msg.stamp = self.get_clock().now().to_msg()
        msg.frame_id = 'phsc_latency_ping'
        self.pub_ping.publish(msg)
        self.n_sent += 1

    def pong_callback(self, msg: Header):
        """Primeste echo-ul si actualizeaza estimarea."""
        t_send = msg.stamp.sec + msg.stamp.nanosec * 1e-9
        rtt = self._now() - t_send

        if not np.isfinite(rtt) or rtt < 0.0 or rtt > 2.0 * self.tau_max:
            self.get_logger().warn(
                f"RTT invalid ({rtt*1000:.1f} ms), ignorat.",
                throttle_duration_sec=2.0)
            return

        self.n_recv += 1
        self.last_pong_t = self._now()

        # Respingere de outlieri, dar cu iesire de urgenta: daca vin la rand
        # prea multi, inseamna ca regimul s-a schimbat, nu ca sunt anomalii.
        if len(self.rtt_buffer) > 5:
            mu = float(np.mean(self.rtt_buffer))
            sd = float(np.std(self.rtt_buffer))
            if sd > 1e-9 and abs(rtt - mu) > self.k_out * sd:
                self.outlier_streak += 1
                if self.outlier_streak < self.streak_max:
                    self.get_logger().warn(
                        f"RTT outlier {rtt*1000:.1f} ms "
                        f"(medie {mu*1000:.1f} ms), ignorat "
                        f"[{self.outlier_streak}/{self.streak_max}]",
                        throttle_duration_sec=2.0)
                    return
                # regim nou: repornim fereastra de la valoarea curenta
                self.get_logger().info(
                    f"{self.outlier_streak} outlieri consecutivi -> "
                    f"accept schimbarea de regim, tau ~ {rtt/2*1000:.1f} ms")
                self.rtt_buffer.clear()

        self.outlier_streak = 0
        self.rtt_buffer.append(rtt)

        # tau ~ RTT/2 presupune canal simetric. Pe legaturi asimetrice
        # (uplink != downlink) estimarea e partinitoare; de verificat pe HIL.
        tau_new = 0.5 * rtt
        self.tau_est = self.alpha * tau_new + (1.0 - self.alpha) * self.tau_est
        self.tau_est = float(np.clip(self.tau_est, 0.0, self.tau_max))

    def publish_delay(self):
        # Daca pong-urile s-au oprit, nu publicam o valoare veche ca si cum
        # ar fi proaspata -- consumatorul (MPC) trebuie sa afle.
        if self.last_pong_t is not None:
            gap = self._now() - self.last_pong_t
            if gap > self.loss_timeout:
                self.get_logger().error(
                    f"Fara pong de {gap*1000:.0f} ms -- legatura cazuta?",
                    throttle_duration_sec=2.0)

        self.pub_delay.publish(Float64(data=float(self.tau_est)))

        if self.rtt_buffer:
            r = np.asarray(self.rtt_buffer) * 0.5
            loss = 1.0 - (self.n_recv / self.n_sent) if self.n_sent else 0.0
            self.pub_stats.publish(Float64MultiArray(data=[
                float(r.mean()), float(r.std()),
                float(r.min()), float(r.max()),
                float(max(0.0, loss)),
            ]))

        self.get_logger().info(
            f"tau_est = {self.tau_est*1000:.1f} ms "
            f"(n={len(self.rtt_buffer)}, pierdere={100*max(0.0, 1.0 - (self.n_recv/self.n_sent if self.n_sent else 1)):.1f}%)",
            throttle_duration_sec=2.0)


class LatencyEcho(Node):
    """
    Partea remota: da echo la ping pastrand timestamp-ul original.
    Se ruleaza langa robot. Fara ea, estimatorul nu are ce masura.
    """

    def __init__(self):
        super().__init__('latency_echo')
        self.pub = self.create_publisher(Header, '/latency_pong', 10)
        self.sub = self.create_subscription(
            Header, '/latency_ping', self.cb, 10)
        self.n = 0
        self.get_logger().info("Latency Echo pornit (/latency_ping -> /latency_pong).")

    def cb(self, msg: Header):
        # Republicam EXACT acelasi stamp: diferenta o masoara emitatorul.
        self.pub.publish(msg)
        self.n += 1


def _spin(node):
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def main(args=None):
    rclpy.init(args=args)
    _spin(LatencyEstimator())


def main_echo(args=None):
    rclpy.init(args=args)
    _spin(LatencyEcho())


if __name__ == '__main__':
    main()
