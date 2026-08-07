#!/usr/bin/env python3
"""echo_node.py -- ecou minimal pentru testul de integrare offline: ce vine pe /c3/tx se
intoarce identic pe /c3/rx. Tine locul masinii a doua (M2) din campanie.
La iesire tipareste cate mesaje a vazut: daca RMW-urile s-ar scurge intre ele, ecoul unui
transport ar numara si mesajele celuilalt -- de aceea ambii agenti folosesc ACELASI nume de
topic, iar contoarele devin testul de scurgere."""
import sys
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String


class Ecou(Node):
    def __init__(self, eticheta):
        Node.__init__(self, "c3_ecou_%s" % eticheta)
        qos = QoSProfile(depth=50)
        self.pub = self.create_publisher(String, "/c3/rx", qos)
        self.create_subscription(String, "/c3/tx", self._pe_mesaj, qos)
        self.n = 0
        self.rmw = rclpy.get_rmw_implementation_identifier()

    def _pe_mesaj(self, msg):
        self.n += 1
        self.pub.publish(msg)


def main():
    eticheta = sys.argv[1] if len(sys.argv) > 1 else "x"
    rclpy.init()
    n = Ecou(eticheta)
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        print("ECOU %s rmw=%s primite=%d" % (eticheta, n.rmw, n.n), flush=True)
        n.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


main()
