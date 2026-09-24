#!/usr/bin/env python3
"""bench_echo_server.py -- ecoul microbenchmarkului: /bench/ping -> /bench/pong
imediat, neschimbat. RTT-ul masurat de client = 2 x drumul prin RMW + netem
(corect intre ceasuri diferite -- nu cere sincronizare intre masini)."""
import argparse, os, sys
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import qos_arg

class Echo(Node):
    def __init__(self, istorie="keep_last", adancime=50):
        super().__init__("bench_echo")
        q = qos_arg(istorie, adancime)            # implicit: 50, adica exact ce era
        self.pub = self.create_publisher(String, "/bench/pong", q)
        self.create_subscription(String, "/bench/ping",
                                 lambda m: self.pub.publish(m), q)
        self.get_logger().info("ecou pornit pe /bench/ping -> /bench/pong (qos %s/%d)"
                               % (istorie, adancime))

def main():
    # Politica de coada si la ecou: K3 intreaba ce face publicatorul cand coada se umple, iar
    # in drumul dus-intors publica AMBELE capete. Implicitul lasa ecoul exact cum era.
    ap = argparse.ArgumentParser()
    ap.add_argument("--qos-history", choices=("keep_last", "keep_all"), default="keep_last")
    ap.add_argument("--qos-depth", type=int, default=50)
    a = ap.parse_args()
    rclpy.init(); n = Echo(a.qos_history, a.qos_depth)
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        n.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
