#!/usr/bin/env python3
"""ecou_node.py -- ROLUL OPERATOR: agentul sondei C4. Primeste /c4/ping (JSON {seq, t_tx}) si intoarce /c4/pong cu acelasi
seq si t_tx, plus stamp = ceasul LOCAL al operatorului (wall) + deviatie_s. `deviatie_s` (parametru ROS, implicit 0.0) e
o DEVIATIE DE CEAS INJECTATA SOFTWARE pe marcajele emitatorului -- ceasul de sistem nu se atinge. Fara alta logica."""
import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Ecou(Node):
    def __init__(self):
        super().__init__("c4_ecou_operator")
        self.declare_parameter("deviatie_s", 0.0)
        self.pub = self.create_publisher(String, "/c4/pong", 20)
        self.create_subscription(String, "/c4/ping", self._pe_ping, 20)
        self.n = 0
        self.get_logger().info("c4 ecou (operator): /c4/ping -> /c4/pong, deviatie stamp = %.3f s" % self.get_parameter("deviatie_s").value)

    def _pe_ping(self, msg):
        d = json.loads(msg.data)
        d["stamp"] = self.get_clock().now().nanoseconds * 1e-9 + float(self.get_parameter("deviatie_s").value)
        self.pub.publish(String(data=json.dumps(d)))
        self.n += 1


def main(args=None):
    rclpy.init(args=args)
    n = Ecou()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
