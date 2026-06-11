#!/usr/bin/env python3
"""victim_node.py — victime simulate + detectie, ca nod ROS2.

La pornire plaseaza N victime (reproductibil cu seed) si publica pozitiile
o singura data, latched (TRANSIENT_LOCAL), pe /mission/victims_static —
dashboard-ul le poate desena oricand s-ar abona. Apoi, la 10 Hz, verifica
dronele aflate in raza senzorului si emite evenimente de detectie pe
/mission/victims: {"victim":i,"t":..,"by":"d2","x":..,"y":..}.
Jurnal CSV in ~/sar_data/victims.csv.

Rulare:
  ros2 run <pkg> victim_node.py --ros-args -p n:=6 -p seed:=3 \
    -p sensor_r:=6.0 -p p_detect:=2.0
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_utils import qos_best_effort, qos_latched, now_s, parse_poses
from victims import VictimField


class VictimNode(Node):
    def __init__(self):
        super().__init__("victim_field")
        p = self.declare_parameter
        p("n", 6), p("seed", 3), p("min_sep", 5.0)
        p("xmin", -30.0), p("xmax", 30.0), p("ymin", -30.0), p("ymax", 30.0)
        p("sensor_r", 6.0)
        p("p_detect", 2.0)             # rata Poisson [1/s] in raza
        p("pose_topic", "/swarm/telemetry")
        p("events_topic", "/mission/victims")
        p("static_topic", "/mission/victims_static")
        p("csv_path", "~/sar_data/victims.csv")
        g = lambda n: self.get_parameter(n).value

        self.field = VictimField(int(g("n")), float(g("xmin")),
                                 float(g("xmax")), float(g("ymin")),
                                 float(g("ymax")), seed=int(g("seed")),
                                 min_sep=float(g("min_sep")))
        self.r = float(g("sensor_r"))
        self.p_det = float(g("p_detect"))
        self.poses = {}
        self.t0 = now_s(self)
        self.t_last = self.t0

        path = os.path.expanduser(str(g("csv_path")))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.log = open(path, "w")
        self.log.write(VictimField.CSV_HEADER)

        self.pub_ev = self.create_publisher(String, str(g("events_topic")),
                                            qos_best_effort())
        pub_st = self.create_publisher(String, str(g("static_topic")),
                                       qos_latched())
        pub_st.publish(String(data=json.dumps(self.field.positions())))
        self.pub_st = pub_st

        self.create_subscription(String, str(g("pose_topic")),
                                 self.on_pose, qos_best_effort(30))
        self.create_timer(0.1, self.tick)            # 10 Hz detectie
        self.get_logger().info(
            f"victime: {self.field.n_total} plasate (seed={g('seed')})")

    def on_pose(self, msg):
        self.poses.update(parse_poses(msg.data))

    def tick(self):
        t = now_s(self)
        dt = max(t - self.t_last, 0.0)
        self.t_last = t
        if not self.poses:
            return
        events = self.field.step(t - self.t0, self.poses, self.r,
                                 self.p_det, dt)
        for ev in events:
            self.pub_ev.publish(String(data=json.dumps(ev)))
            self.log.write(f"{ev['t']},{ev['victim']},{ev['by']},"
                           f"{ev['x']},{ev['y']}\n")
            self.log.flush()
            self.get_logger().info(
                f"VICTIMA {ev['victim']} detectata de {ev['by']} "
                f"la t={ev['t']} s "
                f"({self.field.n_detected}/{self.field.n_total})")
            # republicam starea statica actualizata (latched)
            self.pub_st.publish(
                String(data=json.dumps(self.field.positions())))


def main():
    rclpy.init()
    node = VictimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.log.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
