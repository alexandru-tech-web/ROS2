#!/usr/bin/env python3
"""rf_channel_node.py -- nod ROS subtire care publica /sar/linkstate cu o stare RF variabila in
timp, folosind nucleul PUR rf_interference (BurstProcess Gilbert-Elliott). Imbogateste schema
linkstate ADITIV cu {loss, burst_len, instant_drop, p, r} -- subscriberii vechi ignora cheile noi
(decizia 5 din OVERNIGHT_PLAN_2.md). Toata logica e in rf_interference; nodul doar publica JSON.

Parametri: topic, rate_hz, lat_ms, jit_ms, p, r (Gilbert-Elliott), seed.
NU executa tc (asta o face netem_bridge_node)."""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_utils import qos_best_effort   # noqa: E402
import rf_interference as rf             # noqa: E402


class RfChannelNode(Node):
    def __init__(self):
        super().__init__("rf_channel")
        defaults = {"topic": "/sar/linkstate", "rate_hz": 5.0, "lat_ms": 40.0,
                    "jit_ms": 8.0, "p": 0.0857, "r": 0.2000, "seed": 0}
        for k, v in defaults.items():
            self.declare_parameter(k, v)
        g = lambda k: self.get_parameter(k).value
        self.lat = float(g("lat_ms"))
        self.jit = float(g("jit_ms"))
        self.bp = rf.BurstProcess(float(g("p")), float(g("r")), seed=int(g("seed")))
        self.pub = self.create_publisher(String, str(g("topic")), qos_best_effort())
        self.create_timer(1.0 / max(0.1, float(g("rate_hz"))), self._tick)
        self.get_logger().info("rf_channel: Gilbert p=%.4f r=%.4f (loss~%.2f, burst~%.1f)"
                               % (self.bp.p, self.bp.r, self.bp.steady_loss, self.bp.mean_burst_len))

    def _tick(self):
        drop = self.bp.draw()    # avanseaza canalul (Markov)
        ls = {"down": False, "lat_ms": self.lat, "jit_ms": self.jit,
              "loss": round(self.bp.steady_loss, 4),
              "burst_len": round(self.bp.mean_burst_len, 2),
              "instant_drop": bool(drop),
              "p": self.bp.p, "r": self.bp.r}
        self.pub.publish(String(data=json.dumps(ls)))


def main():
    rclpy.init()
    node = RfChannelNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
