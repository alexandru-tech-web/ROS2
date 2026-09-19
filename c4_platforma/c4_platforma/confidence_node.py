#!/usr/bin/env python3
"""confidence_node.py -- ROLUL ROVER: publica /network_confidence (alpha) si /network_age (age_sonda) la 10 Hz, din
confidence_core, pe baza mostrelor /c4/ping -> /c4/pong (ecoul operatorului). Ceasuri: t_tx si t_rx sunt ceasul LOCAL
monoton al roverului; stamp-ul din pong e ceasul perechii si intra DOAR in age_stamp (jurnalizata, nu publicata in control).
Jurnal CSV (parametrul `jurnal`, gol = fara): t, seq_ultim, alpha, age_sonda, age_stamp, rtt_ultim.
Parametri: T_dead (0.25 s), W (20), hz (10), jurnal."""
import json
import os
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)
import confidence_core                                            # noqa: E402


class Confidence(Node):
    def __init__(self):
        super().__init__("c4_confidence_rover")
        self.declare_parameter("T_dead", 0.25)
        self.declare_parameter("W", 20)
        self.declare_parameter("hz", 10.0)
        self.declare_parameter("jurnal", "")
        g = lambda k: self.get_parameter(k).value                          # noqa: E731
        self.f = confidence_core.Fereastra(float(g("T_dead")), int(g("W")), t_start=time.monotonic())
        self.pa = self.create_publisher(Float32, "/network_confidence", 10)
        self.pg = self.create_publisher(Float32, "/network_age", 10)
        self.pp = self.create_publisher(String, "/c4/ping", 20)
        self.create_subscription(String, "/c4/pong", self._pe_pong, 20)
        self.create_timer(1.0 / float(g("hz")), self._tick)
        self.jurnal = open(os.path.expanduser(g("jurnal")), "w") if g("jurnal") else None
        if self.jurnal:
            self.jurnal.write("t,seq_ultim,alpha,age_sonda,age_stamp,rtt_ultim\n")
        self.n_pong = 0; self.n_tick = 0
        self.get_logger().info("c4 confidence (rover): T_dead=%.3f W=%d hz=%.1f; age_stamp DOAR jurnalizata" % (self.f.T_dead, self.f.W, float(g("hz"))))

    def _pe_pong(self, msg):
        d = json.loads(msg.data)
        self.f.intoarsa(int(d["seq"]), time.monotonic(), d.get("stamp"))
        self.n_pong += 1

    def _tick(self):
        now = time.monotonic()
        self.f.trimite(now)
        self.pp.publish(String(data=json.dumps({"seq": self.f.seq, "t_tx": now})))
        a = self.f.alpha(now); b = self.f.age_sonda(now)
        self.pa.publish(Float32(data=float(a))); self.pg.publish(Float32(data=float(b)))
        self.n_tick += 1
        if self.jurnal:
            st = self.f.age_stamp(self.get_clock().now().nanoseconds * 1e-9)
            self.jurnal.write("%.4f,%d,%.4f,%.4f,%s,%s\n" % (now, self.f.seq, a, b, "" if st is None else "%.4f" % st,
                                                            "" if self.f.ultim is None else "%.4f" % self.f.ultim[3]))
        if self.n_tick % 100 == 0:
            self.get_logger().info("c4: alpha=%.2f age_sonda=%.3f s pong=%d" % (a, b, self.n_pong))


def main(args=None):
    rclpy.init(args=args)
    n = Confidence()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        if n.jurnal:
            n.jurnal.close()
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
