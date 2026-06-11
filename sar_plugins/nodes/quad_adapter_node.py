#!/usr/bin/env python3
"""quad_adapter_node.py — puntea catre fizica REALA de multicopter din Gazebo.

Gazebo (Harmonic, perechea lui Jazzy) are deja plugin-urile de multicopter:
  gz::sim::systems::MulticopterMotorModel    (dinamica fiecarui rotor)
  gz::sim::systems::MulticopterVelocityControl (urmarire de viteza)
Lumea-exemplu oficiala: gz sim multicopter_velocity_control.sdf — modelele
X3/X4 asculta Twist pe "<model>/gazebo/command/twist".

Acest nod e adaptorul de backend promis de arhitectura roiului: aceleasi
comenzi JSON pe care coordonatorul le trimite simularii cinematice
({"id":"d1","vx":..,"vy":..,"vz":..,"wz":..}) sunt traduse in
geometry_msgs/Twist pe topicul fiecarui model. Schimbi UN nod si roiul
zboara pe fizica reala — coordonatorul si GCS raman neatinse, exact ca la
comutarea RMW.

Necesita podul ros_gz pentru fiecare drona (vezi gz/bridge_swarm.yaml):
  ros2 run ros_gz_bridge parameter_bridge --ros-args \
    -p config_file:=gz/bridge_swarm.yaml
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from node_utils import qos_reliable


class QuadAdapterNode(Node):
    def __init__(self):
        super().__init__("quad_adapter")
        p = self.declare_parameter
        p("cmd_topic", "/swarm/cmd_vel")
        p("out_template", "/%ID%/gazebo/command/twist")
        p("key_id", "id")
        p("key_vx", "vx"), p("key_vy", "vy"), p("key_vz", "vz")
        p("key_wz", "wz")
        g = lambda n: self.get_parameter(n).value
        self.tmpl = str(g("out_template"))
        self.k = {n: str(g("key_" + n)) for n in ("id", "vx", "vy",
                                                  "vz", "wz")}
        self.pubs = {}                 # id -> publisher (create lazily)
        self.create_subscription(String, str(g("cmd_topic")),
                                 self.on_cmd, qos_reliable(30))
        self.get_logger().info(
            f"quad adapter: {g('cmd_topic')} -> {self.tmpl}")

    def pub_for(self, did):
        if did not in self.pubs:
            topic = self.tmpl.replace("%ID%", str(did))
            self.pubs[did] = self.create_publisher(Twist, topic,
                                                   qos_reliable())
            self.get_logger().info(f"publisher nou: {topic}")
        return self.pubs[did]

    def on_cmd(self, msg):
        try:
            d = json.loads(msg.data)
        except ValueError:
            return
        if not isinstance(d, dict) or self.k["id"] not in d:
            return
        tw = Twist()
        tw.linear.x = float(d.get(self.k["vx"], 0.0))
        tw.linear.y = float(d.get(self.k["vy"], 0.0))
        tw.linear.z = float(d.get(self.k["vz"], 0.0))
        tw.angular.z = float(d.get(self.k["wz"], 0.0))
        self.pub_for(str(d[self.k["id"]])).publish(tw)


def main():
    rclpy.init()
    node = QuadAdapterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
