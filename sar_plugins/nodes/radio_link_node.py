#!/usr/bin/env python3
"""radio_link_node.py — legatura radio dependenta de DISTANTA fata de GCS.

Doua moduri de folosire, combinabile:

1) PUBLISHER de linkstate (implicit): citeste pozele dronelor de pe
   pose_topic, calculeaza starea legaturii per drona din modelul log-distance
   si publica pe linkstate_topic:
     - aggregat:  {"d1": {"ms":..,"jit":..,"loss":..,"down":..}, ...}
     - sau, daca exista o singura tinta si flat_compat=true, schema PLATA
       identica cu /teleop/linkstate => gating-ul existent din robot_node.py
       functioneaza NEMODIFICAT (doar remapezi topicul).

2) PROXY (optional, proxy_in != ""): intercepteaza mesajele JSON de pe
   proxy_in si le livreaza pe proxy_out prin canalul degradat al dronei
   ("id" din mesaj); fara "id", mesajul e difuzat prin canalul fiecarei
   drone, cu campul "_link_id" adaugat. Zero modificari in nodurile tale:
   remapezi doar topicurile in launch.

Rulare:
  ros2 run <pkg> radio_link_node.py --ros-args \
    -p gcs_x:=0.0 -p gcs_y:=0.0 -p profile:=open_field -p seed:=1 \
    -p pose_topic:=/swarm/telemetry -p linkstate_topic:=/swarm/linkstate
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_utils import qos_best_effort, qos_reliable, now_s, parse_poses
from radio_link import make_link
from channel import DegradedChannel


class RadioLinkNode(Node):
    def __init__(self):
        super().__init__("radio_link")
        p = self.declare_parameter
        p("gcs_x", 0.0), p("gcs_y", 0.0), p("gcs_z", 0.0)
        p("pose_topic", "/swarm/telemetry")
        p("linkstate_topic", "/swarm/linkstate")
        p("rate_hz", 5.0)
        p("profile", "open_field")     # open_field | urban_rubble | forest
        p("seed", 1)
        p("shadowed", True)
        p("d_max", 0.0)                # 0 = fara cutoff dur
        p("overrides", "{}")           # JSON cu parametri LogDistanceRadioLink
        p("flat_compat", True)         # schema plata cand exista o tinta
        p("proxy_in", "")              # "" = proxy dezactivat
        p("proxy_out", "/swarm/cmd_degraded")

        g = lambda n: self.get_parameter(n).value
        ov = {}
        try:
            ov = json.loads(g("overrides")) or {}
        except ValueError:
            self.get_logger().warn("overrides invalid — ignor")
        if float(g("d_max")) > 0:
            ov["d_max"] = float(g("d_max"))
        ov["seed"] = int(g("seed"))
        self.link = make_link(str(g("profile")), **ov)
        self.gcs = (float(g("gcs_x")), float(g("gcs_y")), float(g("gcs_z")))
        self.shadowed = bool(g("shadowed"))
        self.flat = bool(g("flat_compat"))

        self.poses = {}                # id -> (x, y, z)
        self.states = {}               # id -> stare legatura
        self.chans = {}                # id -> DegradedChannel (pt. proxy)

        self.pub_ls = self.create_publisher(String, str(g("linkstate_topic")),
                                            qos_best_effort())
        self.create_subscription(String, str(g("pose_topic")),
                                 self.on_pose, qos_best_effort(30))
        self.create_timer(1.0 / max(float(g("rate_hz")), 0.1), self.tick)

        self.proxy_in = str(g("proxy_in"))
        if self.proxy_in:
            self.pub_proxy = self.create_publisher(
                String, str(g("proxy_out")), qos_reliable())
            self.create_subscription(String, self.proxy_in,
                                     self.on_proxy, qos_reliable(30))
            self.create_timer(0.02, self.pump)       # 50 Hz livrare
        self.get_logger().info(
            f"radio_link: GCS={self.gcs[:2]} profil={g('profile')} "
            f"proxy={'ON' if self.proxy_in else 'off'}")

    # ---- telemetrie pozitii ----
    def on_pose(self, msg):
        self.poses.update(parse_poses(msg.data))

    # ---- recalcularea si publicarea starii legaturilor ----
    def tick(self):
        if not self.poses:
            return
        self.states = self.link.states_for_positions(
            self.gcs, self.poses, shadowed=self.shadowed)
        for did, st in self.states.items():
            ch = self.chans.setdefault(did, DegradedChannel())
            ch.set_from_dict(st)
        if self.flat and len(self.states) == 1:
            payload = next(iter(self.states.values()))   # schema plata
        else:
            payload = self.states
        self.pub_ls.publish(String(data=json.dumps(payload)))

    # ---- modul proxy ----
    def on_proxy(self, msg):
        t = now_s(self)
        try:
            d = json.loads(msg.data)
        except ValueError:
            return
        if isinstance(d, dict) and "id" in d and str(d["id"]) in self.chans:
            self.chans[str(d["id"])].push(t, msg.data)
        else:                           # difuzare prin fiecare canal
            for did, ch in self.chans.items():
                if isinstance(d, dict):
                    dd = dict(d)
                    dd["_link_id"] = did
                    ch.push(t, json.dumps(dd))
                else:
                    ch.push(t, msg.data)

    def pump(self):
        t = now_s(self)
        for ch in self.chans.values():
            for _, payload in ch.pop_ready(t):
                self.pub_proxy.publish(String(data=payload))


def main():
    rclpy.init()
    node = RadioLinkNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
