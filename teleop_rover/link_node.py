#!/usr/bin/env python3
"""link_node.py — "legatura" dintre operator si rover: publica parametrii
de degradare pe /teleop/linkstate (5 Hz), setabili la pornire (parametri)
sau LIVE pe /teleop/operator ({"action":"set_all","ms":..,"jit":..,
"loss":..,"down":bool}). Nodurile aplica degradarea la receptie."""
import json
import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from std_msgs.msg import String

LINK = "op-rob"

class LinkNode(Node):
    def __init__(self):
        super().__init__("teleop_link")
        dyn = ParameterDescriptor(dynamic_typing=True)
        for p, v in (("lat_ms", 0.0), ("jit_ms", 0.0), ("loss", 0.0),
                     ("down", False)):
            self.declare_parameter(p, v, dyn)   # accepta si 200, si 200.0
        g = lambda p: self.get_parameter(p).value
        self.lat, self.jit = float(g("lat_ms")), float(g("jit_ms"))
        self.loss, self.down = float(g("loss")), bool(g("down"))
        self.pub = self.create_publisher(String, "/teleop/linkstate", 10)
        self.create_subscription(String, "/teleop/operator", self.on_op, 10)
        self.create_timer(0.2, self.tick)
        self.get_logger().info(f"legatura: lat={self.lat} ms jit={self.jit} "
                               f"loss={self.loss} down={self.down}")

    def on_op(self, msg):
        c = json.loads(msg.data)
        if c.get("action") != "set_all":
            return
        if c.get("ms") is not None: self.lat = float(c["ms"])
        if c.get("jit") is not None: self.jit = float(c["jit"])
        if c.get("loss") is not None: self.loss = float(c["loss"])
        if c.get("down") is not None: self.down = bool(c["down"])
        self.get_logger().warn(f"legatura schimbata LIVE: lat={self.lat} "
                               f"jit={self.jit} loss={self.loss} down={self.down}")

    def tick(self):
        self.pub.publish(String(data=json.dumps(
            {"down": [LINK] if self.down else [],
             "lat_ms": {LINK: self.lat}, "jit_ms": {LINK: self.jit},
             "loss": {LINK: self.loss}})))

def main():
    rclpy.init(); n = LinkNode()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        n.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
