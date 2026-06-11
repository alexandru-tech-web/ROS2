#!/usr/bin/env python3
"""obstacle_guard_node.py — autonomie locala: oprire la obstacol pe lidar.

Proxy intre operator si rover: asculta scanarea (sensor_msgs/LaserScan de
la ros_gz_bridge) si comanda de pe in_topic, filtreaza inaintarea prin
ObstacleGuard si republica pe out_topic. In launch doar remapezi:
operatorul publica in continuare pe /teleop/cmd, roverul asculta
/teleop/cmd_safe — niciun nod existent nu se modifica.

Doua formate de comanda (param msg):
  msg:=json  — std_msgs/String cu {"v":..,"w":..,...} (conventia proiectului;
               toate celelalte chei se pastreaza neatinse)
  msg:=twist — geometry_msgs/Twist (linear.x / angular.z), util pe
               /model/rover/cmd_vel direct

Starea garzii se publica la 5 Hz pe status_topic:
  {"dmin":..,"scale":..,"blocked":..}
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_utils import qos_best_effort, qos_reliable
from guard import ObstacleGuard


class ObstacleGuardNode(Node):
    def __init__(self):
        super().__init__("obstacle_guard")
        p = self.declare_parameter
        p("scan_topic", "/scan")
        p("in_topic", "/teleop/cmd")
        p("out_topic", "/teleop/cmd_safe")
        p("status_topic", "/teleop/guard")
        p("msg", "json")               # json | twist
        p("d_stop", 0.6), p("d_slow", 1.5), p("sector_deg", 70.0)
        p("release_factor", 1.25)
        g = lambda n: self.get_parameter(n).value

        self.guard = ObstacleGuard(d_stop=float(g("d_stop")),
                                   d_slow=float(g("d_slow")),
                                   sector_deg=float(g("sector_deg")),
                                   release_factor=float(g("release_factor")))
        self.mode = str(g("msg")).lower()
        self.last_info = {"dmin": None, "scale": 1.0, "blocked": False}

        self.create_subscription(LaserScan, str(g("scan_topic")),
                                 self.on_scan, qos_best_effort(5))
        if self.mode == "twist":
            self.pub = self.create_publisher(Twist, str(g("out_topic")),
                                             qos_reliable())
            self.create_subscription(Twist, str(g("in_topic")),
                                     self.on_twist, qos_reliable(30))
        else:
            self.pub = self.create_publisher(String, str(g("out_topic")),
                                             qos_reliable())
            self.create_subscription(String, str(g("in_topic")),
                                     self.on_json, qos_reliable(30))
        self.pub_status = self.create_publisher(
            String, str(g("status_topic")), qos_best_effort())
        self.create_timer(0.2, self.tick_status)
        self.get_logger().info(
            f"garda: d_stop={g('d_stop')} m, d_slow={g('d_slow')} m, "
            f"sector={g('sector_deg')} deg, mod={self.mode}")

    def on_scan(self, msg):
        self.guard.min_front(msg.ranges, msg.angle_min, msg.angle_increment)

    def on_json(self, msg):
        try:
            d = json.loads(msg.data)
        except ValueError:
            return
        v = float(d.get("v", 0.0))
        w = float(d.get("w", 0.0))
        v2, w2, info = self.guard.filter_cmd(v, w)
        self.last_info = info
        d["v"], d["w"] = v2, w2
        if info["blocked"] and v > 0:
            d["guard_blocked"] = True
        self.pub.publish(String(data=json.dumps(d)))

    def on_twist(self, msg):
        v2, w2, info = self.guard.filter_cmd(msg.linear.x, msg.angular.z)
        self.last_info = info
        out = Twist()
        out.linear.x = v2
        out.angular.z = w2
        self.pub.publish(out)

    def tick_status(self):
        self.pub_status.publish(String(data=json.dumps(self.last_info)))


def main():
    rclpy.init()
    node = ObstacleGuardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
