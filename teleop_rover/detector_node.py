#!/usr/bin/env python3
"""detector_node.py — RECUNOASTERE de obiecte din camera (ROS 2, zero-build).

Ruleaza pe robot: se aboneaza la camera (/camera/image/compressed), decodeaza
fara cv_bridge (np.frombuffer + cv2.imdecode), detecteaza pete colorate cu
vision_core (HSV) si PROIECTEAZA detectia in coordonatele lumii folosind ultima
poza a roverului (model pinhole + sol-plat, refinabil cu lidar). Publica tinta
estimata pe /teleop/target si scrie ~/teleop_data/detections.csv.

Lantul decode->detect->project->publish e testabil FARA Gazebo cu
fake_camera_pub.py (cadre sintetice).
"""
import json
import math
import os
import sys
import time

import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import String
from sensor_msgs.msg import CompressedImage, LaserScan

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vision_core import detect_blobs, pixel_to_bearing, project_to_world


def qos_best_effort(depth=5):
    """Profil QoS pentru telemetrie tolerantă la pierderi (camera, lidar)."""
    return QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                      history=HistoryPolicy.KEEP_LAST, depth=depth)


class DetectorNode(Node):
    def __init__(self):
        super().__init__("teleop_detector")
        p = self.declare_parameter
        p("image_topic", "/camera/image/compressed")
        p("pose_topic", "/teleop/pose")
        p("target_topic", "/teleop/target")
        p("scan_topic", "")               # gol = fara refinare lidar
        p("target_class", "")             # gol = orice culoare; altfel filtreaza
        p("min_area", 120)
        # intrinseci camera (potrivite cu senzorul din gen_rough_world.py)
        p("hfov", 1.0472); p("vfov", 0.818)
        p("cam_h", 0.35); p("pitch", 0.2)
        p("width", 320); p("height", 240)
        g = lambda k: self.get_parameter(k).value
        self.cam = {"width": float(g("width")), "height": float(g("height")),
                    "hfov": float(g("hfov")), "vfov": float(g("vfov")),
                    "cam_h": float(g("cam_h")), "pitch": float(g("pitch"))}
        self.min_area = float(g("min_area"))
        self.want = str(g("target_class"))
        self.pose = (0.0, 0.0, 0.0)
        self.scan = None

        self.tgt_pub = self.create_publisher(String, str(g("target_topic")), 10)
        self.create_subscription(CompressedImage, str(g("image_topic")),
                                 self.on_frame, qos_best_effort(5))
        self.create_subscription(String, str(g("pose_topic")), self.on_pose, 20)
        if str(g("scan_topic")):
            self.create_subscription(LaserScan, str(g("scan_topic")),
                                     self.on_scan, qos_best_effort(5))
        os.makedirs(os.path.expanduser("~/teleop_data"), exist_ok=True)
        self.log = open(os.path.expanduser("~/teleop_data/detections.csv"), "w")
        self.log.write("t_s,cx,cy,area,color,bearing,range,wx,wy\n")
        self.t0 = time.time()
        self.get_logger().info("detector pornit: HSV blobs -> /teleop/target "
                               f"(filtru culoare: {self.want or 'orice'})")

    def on_pose(self, msg):
        d = json.loads(msg.data)
        self.pose = (d["x"], d["y"], d["th"])

    def on_scan(self, msg):
        self.scan = msg

    def _lidar_range_at(self, bearing):
        """Range-ul lidar la unghiul bearing (rad), pentru refinarea proiectiei."""
        s = self.scan
        if s is None:
            return None
        i = int(round((bearing - s.angle_min) / s.angle_increment))
        if 0 <= i < len(s.ranges):
            r = s.ranges[i]
            if math.isfinite(r) and s.range_min <= r <= s.range_max:
                return float(r)
        return None

    def on_frame(self, msg):
        arr = np.frombuffer(msg.data, np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return
        dets = detect_blobs(bgr, min_area=self.min_area)
        if self.want:
            dets = [d for d in dets if d["color"] == self.want]
        if not dets:
            return
        det = dets[0]                                 # cea mai mare = tinta
        bearing = pixel_to_bearing(det["cx"], self.cam["width"], self.cam["hfov"])
        lr = self._lidar_range_at(bearing)
        world = project_to_world(det, self.pose, self.cam, lidar_range=lr)
        if world is None:
            return
        wx, wy = world
        # range-ul folosit (lidar daca exista, altfel monocular) doar pt. jurnal
        rng = lr if lr is not None else math.hypot(wx - self.pose[0],
                                                   wy - self.pose[1])
        now = time.time()
        conf = min(1.0, det["area"] / (self.cam["width"] * self.cam["height"] * 0.1))
        self.tgt_pub.publish(String(data=json.dumps(
            {"x": wx, "y": wy, "t": now, "class": det["color"], "conf": conf})))
        self.log.write(f"{now - self.t0:.2f},{det['cx']:.1f},{det['cy']:.1f},"
                       f"{det['area']:.0f},{det['color']},{bearing:.3f},"
                       f"{rng:.2f},{wx:.2f},{wy:.2f}\n")
        self.log.flush()


def main():
    rclpy.init()
    n = DetectorNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            n.log.close()
        except Exception:
            pass
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
