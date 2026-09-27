#!/usr/bin/env python3
"""bench_echo_server.py -- ecoul microbenchmarkului: /bench/ping -> /bench/pong
imediat, neschimbat. RTT-ul masurat de client = 2 x drumul prin RMW + netem
(corect intre ceasuri diferite -- nu cere sincronizare intre masini)."""
import argparse, os, sys, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import qos_arg

class Echo(Node):
    def __init__(self, istorie="keep_last", adancime=50, contori=None):
        super().__init__("bench_echo")
        q = qos_arg(istorie, adancime)            # implicit: 50, adica exact ce era
        self.pub = self.create_publisher(String, "/bench/pong", q)
        if contori is None:
            self.create_subscription(String, "/bench/ping",
                                     lambda m: self.pub.publish(m), q)
        else:
            # --contori (DIAG-Z, 27.09.2026): primite / trimise inapoi, scrise o data pe secunda cu flush,
            # ca un ecou mort sau detasat sa se vada si fara traceback (A002, A009). Fara --contori: nimic schimbat.
            self.rx = self.tx = 0
            self.t_ultim_rx = None
            nou = not os.path.exists(contori)
            self.f_contori = open(contori, "a", buffering=1)
            if nou:
                self.f_contori.write("t,pid,rmw,rx,tx,t_ultim_rx\n")
            self.create_subscription(String, "/bench/ping", self._ecou_numarat, q)
            self.create_timer(1.0, self.scrie_contori)
        self.get_logger().info("ecou pornit pe /bench/ping -> /bench/pong (qos %s/%d)"
                               % (istorie, adancime))

    def _ecou_numarat(self, m):
        self.rx += 1
        self.t_ultim_rx = time.time()
        self.pub.publish(m)
        self.tx += 1

    def scrie_contori(self):
        self.f_contori.write("%.3f,%d,%s,%d,%d,%s\n" % (
            time.time(), os.getpid(), os.environ.get("RMW_IMPLEMENTATION", "default"), self.rx, self.tx,
            "" if self.t_ultim_rx is None else "%.3f" % self.t_ultim_rx))

def main():
    # Politica de coada si la ecou: K3 intreaba ce face publicatorul cand coada se umple, iar
    # in drumul dus-intors publica AMBELE capete. Implicitul lasa ecoul exact cum era.
    ap = argparse.ArgumentParser()
    ap.add_argument("--qos-history", choices=("keep_last", "keep_all"), default="keep_last")
    ap.add_argument("--qos-depth", type=int, default=50)
    ap.add_argument("--contori", default=None,
                    help="CSV cu t,pid,rmw,rx,tx,t_ultim_rx scris la 1 Hz (implicit: nimic)")
    a = ap.parse_args()
    rclpy.init(); n = Echo(a.qos_history, a.qos_depth, a.contori)
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        if a.contori:
            n.scrie_contori()                 # ultima linie la oprire curata (SIGINT)
        n.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
