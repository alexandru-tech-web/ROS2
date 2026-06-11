#!/usr/bin/env python3
"""video_link_node.py — fluxul video al operatorului prin legatura degradata.

Intercepteaza sensor_msgs/CompressedImage de pe in_topic (camera din Gazebo
prin ros_gz_bridge) si il livreaza pe out_topic prin acelasi DegradedChannel
folosit peste tot — parametrii vin LIVE de pe linkstate_topic (schema
/teleop/linkstate sau cea agregata; pentru agregat se foloseste link_id).

Publica la 1 Hz statistici pe stats_topic:
  {"in_fps":..,"out_fps":..,"age_ms":..,"ratio":..,"pending":..}
— acestea sunt cifrele pentru sectiunea de "constiinta situationala a
operatorului sub degradare": cate cadre/s ajung de fapt si cat de vechi sunt.
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import CompressedImage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_utils import qos_best_effort, now_s
from channel import DegradedChannel


class VideoLinkNode(Node):
    def __init__(self):
        super().__init__("video_link")
        p = self.declare_parameter
        p("in_topic", "/camera/image/compressed")
        p("out_topic", "/teleop/video")
        p("linkstate_topic", "/teleop/linkstate")
        p("link_id", "")               # pt. linkstate agregat: id-ul tintei
        p("stats_topic", "/teleop/video_stats")
        p("seed", 1)
        g = lambda n: self.get_parameter(n).value

        self.ch = DegradedChannel(seed=int(g("seed")))
        self.link_id = str(g("link_id"))
        self.n_in = 0
        self.n_out = 0
        self.last_age_ms = 0.0

        self.pub = self.create_publisher(CompressedImage, str(g("out_topic")),
                                         qos_best_effort(5))
        self.pub_stats = self.create_publisher(String, str(g("stats_topic")),
                                               qos_best_effort())
        self.create_subscription(CompressedImage, str(g("in_topic")),
                                 self.on_frame, qos_best_effort(5))
        self.create_subscription(String, str(g("linkstate_topic")),
                                 self.on_linkstate, qos_best_effort())
        self.create_timer(0.01, self.pump)           # 100 Hz livrare
        self.create_timer(1.0, self.tick_stats)
        self.get_logger().info("video link activ")

    def on_linkstate(self, msg):
        try:
            d = json.loads(msg.data)
        except ValueError:
            return
        if self.link_id and isinstance(d.get(self.link_id), dict):
            d = d[self.link_id]        # extragem tinta din schema agregata
        if isinstance(d, dict) and ("ms" in d or "loss" in d or "down" in d):
            self.ch.set_from_dict(d)

    def on_frame(self, msg):
        self.n_in += 1
        t = now_s(self)
        self.ch.push(t, (t, msg))      # pastram timpul emisiei

    def pump(self):
        t = now_s(self)
        for _t_del, (t_emis, frame) in self.ch.pop_ready(t):
            self.last_age_ms = max(0.0, (t - t_emis) * 1000.0)
            self.pub.publish(frame)
            self.n_out += 1

    def tick_stats(self):
        s = self.ch.stats()
        self.pub_stats.publish(String(data=json.dumps(
            {"in_fps": self.n_in, "out_fps": self.n_out,
             "age_ms": round(self.last_age_ms, 1),
             "ratio": s["ratio"], "pending": s["pending"]})))
        self.n_in = 0
        self.n_out = 0


def main():
    rclpy.init()
    node = VideoLinkNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
