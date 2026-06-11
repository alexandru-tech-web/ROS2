#!/usr/bin/env python3
"""fake_camera_pub.py — publica un flux CAMERA SINTETIC (ROS 2), ca sa testezi
detector_node.py FARA Gazebo (fara randare/GPU).

Construieste o imagine cu un dreptunghi colorat (culoarea = param), il misca usor
ca sa para un obiect real, il codeaza JPEG si il publica ca sensor_msgs/CompressedImage
pe /camera/image/compressed (QoS best_effort, ca senzorul real).

Rulare:
    python3 fake_camera_pub.py --ros-args -p color:=red -p cx:=170
"""
import math
import os
import sys
import time

import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import CompressedImage

BGR = {"red": (0, 0, 255), "green": (0, 255, 0),
       "blue": (255, 0, 0), "yellow": (0, 255, 255)}


class FakeCamera(Node):
    def __init__(self):
        super().__init__("fake_camera")
        p = self.declare_parameter
        p("topic", "/camera/image/compressed")
        p("color", "red")
        p("width", 320); p("height", 240)
        p("cx", 160); p("cy", 150)        # centrul tintei (cy jos = mai aproape)
        p("size", 40); p("rate", 15.0)
        g = lambda k: self.get_parameter(k).value
        self.W, self.H = int(g("width")), int(g("height"))
        self.bgr = BGR.get(str(g("color")), (0, 0, 255))
        self.cx, self.cy, self.sz = int(g("cx")), int(g("cy")), int(g("size"))
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST, depth=5)
        self.pub = self.create_publisher(CompressedImage, str(g("topic")), qos)
        self.k = 0
        self.create_timer(1.0 / float(g("rate")), self.tick)
        self.get_logger().info(
            f"camera sintetica: tinta {str(g('color'))} pe {str(g('topic'))}")

    def tick(self):
        img = np.zeros((self.H, self.W, 3), np.uint8)
        # leganare usoara, ca sa para obiect real
        dx = int(12 * math.sin(self.k * 0.1))
        x, y, s = self.cx + dx, self.cy, self.sz
        cv2.rectangle(img, (x - s, y - s), (x + s, y + s), self.bgr, -1)
        ok, buf = cv2.imencode(".jpg", img)
        if ok:
            m = CompressedImage()
            m.format = "jpeg"
            m.data = buf.tobytes()
            self.pub.publish(m)
        self.k += 1


def main():
    rclpy.init()
    n = FakeCamera()
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
