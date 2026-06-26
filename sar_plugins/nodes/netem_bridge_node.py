#!/usr/bin/env python3
"""netem_bridge_node.py -- punte SIL->HIL: asculta /sar/linkstate si construieste comanda tc netem
(via rf_interference.linkstate_to_netem). DRY-RUN implicit (logheaza comanda, NU o executa); pe HIL,
parametrul enable=true o executa cu sudo pe interfata reala. Refoloseste modelul TESTAT -> ce a rulat
in SIL (gemodel) ruleaza identic pe fier. Toata logica de constructie a comenzii e in rf_interference.

Parametri: topic (/sar/linkstate), iface (lo), enable (False = dry-run, sigur)."""
import json
import os
import subprocess
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rf_interference as rf   # noqa: E402


class NetemBridgeNode(Node):
    def __init__(self):
        super().__init__("netem_bridge")
        for k, v in {"topic": "/sar/linkstate", "iface": "lo", "enable": False}.items():
            self.declare_parameter(k, v)
        g = lambda k: self.get_parameter(k).value
        self.iface = str(g("iface"))
        self.enable = bool(g("enable"))
        self.last = None
        self.create_subscription(String, str(g("topic")), self._on_ls, 10)
        self.get_logger().info("netem_bridge: iface=%s enable=%s (DRY-RUN cand enable=false)"
                               % (self.iface, self.enable))

    def _on_ls(self, msg):
        try:
            ls = json.loads(msg.data)
        except (ValueError, TypeError):
            return
        if ls.get("down"):
            return
        cmd = rf.linkstate_to_netem(ls, self.iface)
        if cmd == self.last:
            return                      # nu re-aplica aceeasi conditie
        self.last = cmd
        if self.enable:
            subprocess.run(["sudo", "bash", "-c", cmd], check=False)
            self.get_logger().info("aplicat: %s" % cmd)
        else:
            self.get_logger().info("[dry] %s" % cmd)


def main():
    rclpy.init()
    node = NetemBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
