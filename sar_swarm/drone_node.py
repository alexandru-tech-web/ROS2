#!/usr/bin/env python3
"""
drone_node.py -- Nodul ROS 2 al unei drone SAR (localizare + navigatie +
perceptie + comm bridge + health, intr-un singur nod compact).

Acelasi nucleu ca SIL-ul (sar_core/swarm_core). Doua moduri:
  use_gazebo:=true   citeste odometria din Gazebo si publica cmd_vel
  use_gazebo:=false  integreaza cinematica intern (demo fara Gazebo)

Degradarea retelei (injectata de fault_injector pe /sar/linkstate) se aplica
LA RECEPTIE: mesajele de pe legaturi cazute se ignora, cele de pe legaturi
lente se proceseaza cu intarzierea configurata. Telemetria catre GCS cazut
intra in tamponul STORE-AND-FORWARD si se livreaza la restabilire; harta se
sincronizeaza cu confirmari monotone (from/upto), robuste la duplicate.

Topicuri: sub /sar/cmd/{id}, /sar/linkstate, /sar/probe/ping
          pub /sar/telemetry, /sar/probe/pong, /sar/pose/{id}
"""

import json
import math
import os
import sys

import random
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sar_core import (GridWorld, DiscoveredMap, FallbackPolicy,
                      LOCAL_EXPLORE, RETURN_TO_LINK, LOITER)
from swarm_core import DroneKinematics, goto_velocity, separation_velocity
from world_config import WORLD, ALT, SENSE_R


class DroneNode(Node):
    def __init__(self):
        super().__init__("sar_drone")
        self.declare_parameter("id", "d1")
        self.declare_parameter("x0", 3.0)
        self.declare_parameter("y0", 3.0)
        self.declare_parameter("use_gazebo", False)
        self.id = self.get_parameter("id").value
        self.use_gz = bool(self.get_parameter("use_gazebo").value)

        self.world = GridWorld(**WORLD)
        self.map = DiscoveredMap(self.world)
        self.kin = DroneKinematics(
            x=float(self.get_parameter("x0").value),
            y=float(self.get_parameter("y0").value), z=0.0)
        self.home = self.world.to_cell(self.kin.x, self.kin.y)
        self.op = None          # comanda explicita a operatorului (hold/goto/rth)
        self.fallback = FallbackPolicy(t_local=15.0)
        self.fallback.last_link_pos = (self.kin.x, self.kin.y)
        self.target = None
        self.path = []
        self.others = {}                 # pozitiile celorlalte drone (din /sar/telemetry)
        self.pending = []                # celule neconfirmate
        self.cells_base = 0
        self.victims = set()
        self.saf_buffer = []             # store-and-forward catre GCS
        os.makedirs(os.path.expanduser("~/sar_data"), exist_ok=True)
        self.dlog = open(os.path.expanduser(
            f"~/sar_data/drone_{self.id}_log.csv"), "w")
        self.dlog.write(
            "t_s,x,y,state,gcs_up,saf_buffered,cells_pending,dist_link\n")
        self._t0 = self.get_clock().now().nanoseconds * 1e-9

        # starea legaturilor (de la fault_injector)
        self.links_down = set()          # {"gcs-d1", ...}
        self.lat_ms = {}                 # cheie legatura -> latenta
        self.loss_p = {}                 # cheie legatura -> prob. pierdere
        self.jit_ms = {}                 # cheie legatura -> jitter
        self.inbox = []                  # (t_proc, handler, payload)

        self.tele_pub = self.create_publisher(String, "/sar/telemetry", 20)
        self.pong_pub = self.create_publisher(String, "/sar/probe/pong", 20)
        self.pose_pub = self.create_publisher(String, f"/sar/pose/{self.id}", 10)
        self.create_subscription(String, f"/sar/cmd/{self.id}", self.on_cmd_raw, 20)
        self.create_subscription(String, "/sar/linkstate", self.on_linkstate, 10)
        self.create_subscription(String, "/sar/probe/ping", self.on_ping_raw, 20)
        self.create_subscription(String, "/sar/telemetry", self.on_peer, 30)

        if self.use_gz:
            self.cmd_pub = self.create_publisher(
                Twist, f"/model/{self.id}/cmd_vel", 10)
            self.create_subscription(
                Odometry, f"/model/{self.id}/odometry", self.on_odom, 20)
        self.create_timer(0.05, self.tick)          # 20 Hz control
        self.create_timer(0.2, self.send_telemetry) # 5 Hz telemetrie
        self.get_logger().info(
            f"drona {self.id} pornita (use_gazebo={self.use_gz})")

    # ---------- legatura cu GCS: gating + intarziere la receptie ----------
    def _link(self, other):
        return "-".join(sorted((self.id, other)))

    def gcs_up(self):
        return self._link("gcs") not in self.links_down

    def _enqueue(self, other, handler, payload):
        k = self._link(other)
        if k in self.links_down:
            return                                   # legatura cazuta: pierdut
        if random.random() < self.loss_p.get(k, 0.0):
            return                                   # pierdere de pachet
        jit = self.jit_ms.get(k, 0.0)
        lat = max(0.0, self.lat_ms.get(k, 0.0)
                  + random.uniform(-jit, jit)) / 1000.0
        t_proc = self.get_clock().now().nanoseconds * 1e-9 + lat
        self.inbox.append((t_proc, handler, payload))

    def on_linkstate(self, msg: String):
        d = json.loads(msg.data)
        was_up = self.gcs_up()
        self.links_down = set(d.get("down", []))
        self.lat_ms = d.get("lat_ms", {})
        self.loss_p = d.get("loss", {})
        self.jit_ms = d.get("jit_ms", {})
        now_up = self.gcs_up()
        if was_up and not now_up:
            self.fallback.on_link_lost(
                self.get_clock().now().nanoseconds * 1e-9)
            self.get_logger().warn(f"{self.id}: legatura GCS PIERDUTA -> fallback")
        if not was_up and now_up and self.saf_buffer:
            self.get_logger().info(
                f"{self.id}: legatura restabilita -- livrez "
                f"{len(self.saf_buffer)} mesaje din tamponul S&F")
            for m in self.saf_buffer:
                self.tele_pub.publish(String(data=m))
            self.saf_buffer.clear()

    def on_cmd_raw(self, msg: String):
        self._enqueue("gcs", self.on_cmd, json.loads(msg.data))

    def on_ping_raw(self, msg: String):
        d = json.loads(msg.data)
        if d.get("to") == self.id:
            self._enqueue("gcs", self.on_ping, d)

    def on_cmd(self, d):
        self.fallback.on_gcs_contact((self.kin.x, self.kin.y))
        if d["k"] == "goto_frontier":
            self.target = tuple(d["cell"])
            self.path = []
        elif d["k"] == "op":
            self._on_op(d)
        elif d["k"] == "map_ack":
            adv = d["upto"] - self.cells_base
            if adv > 0:
                del self.pending[:min(adv, len(self.pending))]
                self.cells_base = d["upto"]

    def on_ping(self, d):
        self.pong_pub.publish(String(data=json.dumps(
            {"id": self.id, "seq": d["seq"], "t": d["t"]})))

    # ------- comenzile explicite ale operatorului (relayate de GCS) -------
    def _on_op(self, d):
        a, cid = d.get("a"), d.get("cmd_id", 0)
        if a == "resume":
            self.op = None
            self.target, self.path = None, []
        elif a == "hold":
            self.op = {"mode": "hold", "cmd_id": cid}
            self.target, self.path = None, []
        elif a in ("goto", "rth"):
            cell = tuple(d["cell"]) if a == "goto" else self.home
            self.op = {"mode": a, "cell": cell, "cmd_id": cid}
            self.target, self.path = cell, []
        else:
            return
        self.get_logger().info(f"{self.id}: comanda operator '{a}' (cmd {cid})")
        self._op_event(cid, "ack")

    def _op_event(self, cmd_id, phase):
        payload = json.dumps({"k": "op_event", "id": self.id,
                              "cmd_id": cmd_id, "phase": phase})
        if self.gcs_up():
            self.tele_pub.publish(String(data=payload))
        elif len(self.saf_buffer) < 500:
            self.saf_buffer.append(payload)          # S&F si pentru ack-uri

    def _state_str(self):
        return self.op["mode"].upper() if self.op else self.fallback.state

    def on_peer(self, msg: String):
        d = json.loads(msg.data)
        if d.get("id") != self.id and "pos" in d:
            self.others[d["id"]] = tuple(d["pos"][:2])

    def on_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        self.kin.x, self.kin.y, self.kin.z = p.x, p.y, p.z

    # ---------- bucla de control (identica logic cu SIL) ----------
    def tick(self):
        t = self.get_clock().now().nanoseconds * 1e-9
        # proceseaza mesajele scadente (intarzierea legaturii)
        due = [m for m in self.inbox if m[0] <= t]
        self.inbox = [m for m in self.inbox if m[0] > t]
        for _, h, payload in due:
            h(payload)

        px, py = self.kin.x, self.kin.y
        st = self.fallback.tick(
            t, (px, py),
            math.hypot(px - self.fallback.last_link_pos[0],
                       py - self.fallback.last_link_pos[1]) < 2.0)
        if self.op is not None:     # operatorul are prioritate peste fallback
            if self.op["mode"] == "hold":
                self.target, self.path = None, []
            else:
                self.target = self.op["cell"]
            st = "OP"               # dezactiveaza ramurile de fallback
        if st == LOCAL_EXPLORE and (self.target is None or not self.gcs_up()):
            fr = self.map.frontiers()
            if fr:
                ci, cj = self.world.to_cell(px, py)
                fr.sort(key=lambda f: (f[0]-ci)**2 + (f[1]-cj)**2)
                self.target = fr[0]
        if st == RETURN_TO_LINK:
            self.target = self.world.to_cell(*self.fallback.last_link_pos)
            self.path = []
        if st == LOITER:
            ang = t * 0.5
            tgt = (self.fallback.last_link_pos[0] + 3.0 * math.cos(ang),
                   self.fallback.last_link_pos[1] + 3.0 * math.sin(ang))
        else:
            if self.target is not None and not self.path:
                self.path = self.map.astar(
                    self.world.to_cell(px, py), self.target) or []
                if (not self.path and self.op
                        and self.op["mode"] in ("goto", "rth")
                        and not self.op.get("done")
                        and self.world.to_cell(px, py) != self.target):
                    self.op["done"] = True            # tinta inaccesibila
                    self._op_event(self.op["cmd_id"], "fail")
                    self.op = {"mode": "hold", "cmd_id": self.op["cmd_id"]}
                    self.target = None
            if self.path:
                while len(self.path) > 1 and math.hypot(
                        self.world.to_xy(*self.path[0])[0] - px,
                        self.world.to_xy(*self.path[0])[1] - py) < 1.2:
                    self.path.pop(0)
                tgt = self.world.to_xy(*self.path[0])
            else:
                tgt = (px, py)

        vx, vy, vz = goto_velocity(px, py, self.kin.z, tgt[0], tgt[1], ALT)
        sx, sy = separation_velocity(px, py, list(self.others.values()))
        if self.use_gz:
            tw = Twist()
            tw.linear.x, tw.linear.y, tw.linear.z = vx + sx, vy + sy, vz
            self.cmd_pub.publish(tw)
        else:
            self.kin.step(vx + sx, vy + sy, vz, 0.05)

        cells, found = self.map.reveal_disc(self.kin.x, self.kin.y, SENSE_R)
        self.pending.extend(cells)
        self.victims.update(map(tuple, found))
        if self.target and self.world.to_cell(self.kin.x, self.kin.y) == self.target:
            if (self.op and self.op["mode"] in ("goto", "rth")
                    and not self.op.get("done")):
                self.op["done"] = True
                self._op_event(self.op["cmd_id"], "done")
                self.op = {"mode": "hold", "cmd_id": self.op["cmd_id"]}
            self.target, self.path = None, []
        self.pose_pub.publish(String(data=json.dumps(
            {"id": self.id, "pos": [self.kin.x, self.kin.y, self.kin.z],
             "state": self._state_str()})))

    def send_telemetry(self):
        payload = json.dumps({
            "k": "telemetry", "id": self.id,
            "pos": [self.kin.x, self.kin.y, self.kin.z],
            "state": self._state_str(),
            "t": self.get_clock().now().nanoseconds * 1e-9,  # timp emisie (e2e)
            "from": self.cells_base, "cells": self.pending[:600],
            "victims": sorted(self.victims)})
        if self.gcs_up():
            self.tele_pub.publish(String(data=payload))
        elif len(self.saf_buffer) < 500:
            self.saf_buffer.append(payload)         # store-and-forward
        # jurnal LOCAL (complet si in timpul deconectarii!)
        t = self.get_clock().now().nanoseconds * 1e-9 - self._t0
        dl = math.hypot(self.kin.x - self.fallback.last_link_pos[0],
                        self.kin.y - self.fallback.last_link_pos[1])
        self.dlog.write(f"{t:.2f},{self.kin.x:.2f},{self.kin.y:.2f},"
                        f"{self._state_str()},{int(self.gcs_up())},"
                        f"{len(self.saf_buffer)},{len(self.pending)},"
                        f"{dl:.2f}\n")
        self.dlog.flush()


def main():
    rclpy.init()
    node = DroneNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.dlog.close()
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
