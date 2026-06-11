#!/usr/bin/env python3
"""coverage_node.py — urmarirea acoperirii zonei de cautare.

Asculta pozele dronelor (JSON pe pose_topic), vopseste discul senzorului
in grila si publica periodic:
  /mission/coverage : {"t":..,"pct":..,"cells":..,"total":..,
                       "milestones": {"50": t, ...}}
plus jurnal CSV in ~/sar_data/coverage.csv (acelasi analizor ca restul).

Rulare:
  ros2 run <pkg> coverage_node.py --ros-args -p xmin:=-30.0 -p xmax:=30.0 \
    -p ymin:=-30.0 -p ymax:=30.0 -p cell:=1.0 -p sensor_r:=6.0
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_utils import qos_best_effort, now_s, parse_poses
from coverage import CoverageGrid


class CoverageNode(Node):
    def __init__(self):
        super().__init__("coverage_tracker")
        p = self.declare_parameter
        p("xmin", -30.0), p("xmax", 30.0), p("ymin", -30.0), p("ymax", 30.0)
        p("cell", 1.0), p("sensor_r", 6.0)
        p("pose_topic", "/swarm/telemetry")
        p("coverage_topic", "/mission/coverage")
        p("rate_hz", 1.0)
        p("csv_path", "~/sar_data/coverage.csv")
        g = lambda n: self.get_parameter(n).value

        self.grid = CoverageGrid(float(g("xmin")), float(g("xmax")),
                                 float(g("ymin")), float(g("ymax")),
                                 cell=float(g("cell")))
        self.r = float(g("sensor_r"))
        self.t0 = now_s(self)

        path = os.path.expanduser(str(g("csv_path")))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.log = open(path, "w")
        self.log.write(CoverageGrid.CSV_HEADER)

        self.pub = self.create_publisher(String, str(g("coverage_topic")),
                                         qos_best_effort())
        self.create_subscription(String, str(g("pose_topic")),
                                 self.on_pose, qos_best_effort(30))
        self.create_timer(1.0 / max(float(g("rate_hz")), 0.1), self.tick)
        self.get_logger().info(
            f"coverage: {self.grid.nx}x{self.grid.ny} celule, r={self.r} m")

    def on_pose(self, msg):
        t = now_s(self) - self.t0
        for (x, y, _z) in parse_poses(msg.data).values():
            self.grid.mark_disc(x, y, self.r, t=t)

    def tick(self):
        t = now_s(self) - self.t0
        s = self.grid.summary(t)
        s["milestones"] = {str(k): round(v, 2)
                           for k, v in s["milestones"].items()}
        self.pub.publish(String(data=json.dumps(s)))
        self.log.write(self.grid.csv_row(t))
        self.log.flush()


def main():
    rclpy.init()
    node = CoverageNode()
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
