#!/usr/bin/env python3
"""bench_echo_server.py — ecoul microbenchmarkului: /bench/ping -> /bench/pong
imediat, neschimbat. RTT-ul masurat de client = 2 x drumul prin RMW + netem
(corect intre ceasuri diferite — nu cere sincronizare intre masini)."""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class Echo(Node):
    def __init__(self):
        super().__init__("bench_echo")
        self.pub = self.create_publisher(String, "/bench/pong", 50)
        self.create_subscription(String, "/bench/ping",
                                 lambda m: self.pub.publish(m), 50)
        self.get_logger().info("ecou pornit pe /bench/ping -> /bench/pong")

def main():
    rclpy.init(); n = Echo()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        n.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
