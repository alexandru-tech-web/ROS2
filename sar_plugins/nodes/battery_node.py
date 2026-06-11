#!/usr/bin/env python3
"""battery_node.py — baterie per drona + failsafe energetic RTL/LAND.

Deriveaza viteza fiecarei drone din pozele succesive de pe pose_topic
(nu cere niciun topic nou), integreaza consumul si publica la 1 Hz:
  /swarm/battery : {"d1": {"soc":..,"state":"NORMAL|RTL|LAND",...}, ...}

La tranzitia NORMAL->RTL (sau ->LAND) publica O SINGURA DATA o comanda de
failsafe pe failsafe_cmd_topic, construita din failsafe_template, in care
%ID% si %STATE% se inlocuiesc — astfel se cupleaza la ORICE schema de
comanda are coordonatorul tau, fara sa-i modifici codul:
  -p failsafe_template:='{"action":"rtl","id":"%ID%"}'

Pragul RTL e dinamic optional (dynamic:=true + home_x/home_y): tine cont
de energia necesara intoarcerii de la distanta curenta.
"""
import json
import math
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_utils import qos_best_effort, qos_reliable, now_s, parse_poses
from battery import BatteryModel


class BatteryNode(Node):
    def __init__(self):
        super().__init__("battery_monitor")
        p = self.declare_parameter
        p("capacity_wh", 60.0), p("p_hover_w", 120.0), p("k_v_w", 8.0)
        p("soc_rtl", 0.30), p("soc_land", 0.10)
        p("v_rtl", 4.0), p("dynamic", True), p("dynamic_margin", 1.5)
        p("home_x", 0.0), p("home_y", 0.0)
        p("pose_topic", "/swarm/telemetry")
        p("state_topic", "/swarm/battery")
        p("failsafe_cmd_topic", "")    # "" = doar monitorizare
        p("failsafe_template", '{"action":"rtl","id":"%ID%"}')
        p("csv_path", "~/sar_data/battery.csv")
        g = lambda n: self.get_parameter(n).value
        self.cfg = dict(capacity_wh=float(g("capacity_wh")),
                        p_hover_w=float(g("p_hover_w")),
                        k_v_w=float(g("k_v_w")), soc_rtl=float(g("soc_rtl")),
                        soc_land=float(g("soc_land")), v_rtl=float(g("v_rtl")),
                        dynamic_margin=float(g("dynamic_margin")))
        self.home = (float(g("home_x")), float(g("home_y")))
        self.dynamic = bool(g("dynamic"))
        self.tmpl = str(g("failsafe_template"))

        self.bats = {}                 # id -> BatteryModel
        self.last = {}                 # id -> (t, x, y)
        self.announced = {}            # id -> ultima stare anuntata
        self.t0 = now_s(self)

        path = os.path.expanduser(str(g("csv_path")))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.log = open(path, "w")
        self.log.write(BatteryModel.CSV_HEADER)

        self.pub_state = self.create_publisher(String, str(g("state_topic")),
                                               qos_best_effort())
        self.pub_cmd = None
        if str(g("failsafe_cmd_topic")):
            self.pub_cmd = self.create_publisher(
                String, str(g("failsafe_cmd_topic")), qos_reliable())

        self.create_subscription(String, str(g("pose_topic")),
                                 self.on_pose, qos_best_effort(30))
        self.create_timer(1.0, self.tick)
        self.get_logger().info(
            f"baterie: {self.cfg['capacity_wh']} Wh, RTL la "
            f"{self.cfg['soc_rtl']*100:.0f}% "
            f"(dinamic={'da' if self.dynamic else 'nu'})")

    def on_pose(self, msg):
        t = now_s(self)
        for did, (x, y, _z) in parse_poses(msg.data).items():
            bat = self.bats.setdefault(did, BatteryModel(**self.cfg))
            if did in self.last:
                t0, x0, y0 = self.last[did]
                dt = t - t0
                if dt > 0:
                    speed = math.hypot(x - x0, y - y0) / dt
                    dist_home = (math.hypot(x - self.home[0],
                                            y - self.home[1])
                                 if self.dynamic else None)
                    prev = bat.state
                    bat.update(dt, speed=speed, t=round(t - self.t0, 2),
                               dist_home=dist_home)
                    if bat.state != prev:
                        self.on_transition(did, bat)
            self.last[did] = (t, x, y)

    def on_transition(self, did, bat):
        self.get_logger().warn(
            f"{did}: {bat.state} la SOC={bat.soc()*100:.1f}%")
        if self.announced.get(did) != bat.state:
            self.announced[did] = bat.state
            if self.pub_cmd is not None:
                cmd = self.tmpl.replace("%ID%", str(did)) \
                               .replace("%STATE%", bat.state)
                self.pub_cmd.publish(String(data=cmd))

    def tick(self):
        if not self.bats:
            return
        t = round(now_s(self) - self.t0, 2)
        out = {}
        for did, bat in self.bats.items():
            s = bat.summary()
            out[did] = s
            self.log.write(f"{t},{did},{s['soc']},{s['state']},"
                           f"{s['used_wh']}\n")
        self.log.flush()
        self.pub_state.publish(String(data=json.dumps(out)))


def main():
    rclpy.init()
    node = BatteryNode()
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
