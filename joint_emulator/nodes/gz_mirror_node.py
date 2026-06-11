#!/usr/bin/env python3
"""gz_mirror_node.py — oglinda Gazebo: citeste /joint/state (emulator sau
fier) si publica pozitiile spre JointPositionController-ele din lumea
gz (prin ros_gz_bridge). Gazebo NU simuleaza fizica articulatiilor —
doar urmareste; o singura sursa de adevar."""
import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, String

N_PAIRS = 3


class GzMirror(Node):
    def __init__(self):
        super().__init__("gz_mirror")
        self.pubs = [self.create_publisher(Float64, f"/bench/pair{k}_cmd_pos", 10)
                     for k in range(N_PAIRS)]
        self.create_subscription(String, "/joint/state", self.on_state, 30)

    def on_state(self, msg):
        d = json.loads(msg.data)
        for pid, st in d.items():
            k = int(pid)
            if k < N_PAIRS:
                self.pubs[k].publish(Float64(data=float(st.get("th", 0.0))))


def main():
    rclpy.init()
    n = GzMirror()
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
