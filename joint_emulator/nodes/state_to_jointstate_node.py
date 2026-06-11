#!/usr/bin/env python3
"""state_to_jointstate_node.py — podul spre lumea ROS standard: traduce
/joint/state (JSON-ul emulatorului) in sensor_msgs/JointState pe
/joint_states, ca robot_state_publisher + RViz (sau orice unealta ROS)
sa vada bancul miscandu-se. Perechea k -> articulatia pairk_joint."""
import json

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String


class StateBridge(Node):
    def __init__(self):
        super().__init__("state_to_jointstate")
        self.declare_parameter("state_topic", "/joint/state")
        self.pub = self.create_publisher(JointState, "/joint_states", 10)
        self.create_subscription(
            String, self.get_parameter("state_topic").value, self.on_state, 30)

    def on_state(self, msg):
        d = json.loads(msg.data)
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        for pid in sorted(d.keys()):
            js.name.append(f"pair{pid}_joint")
            js.position.append(float(d[pid].get("th", 0.0)))
            js.velocity.append(float(d[pid].get("om", 0.0)))
            js.effort.append(float(d[pid].get("tau_b", 0.0)))
        self.pub.publish(js)


def main():
    rclpy.init()
    n = StateBridge()
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
