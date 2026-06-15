#!/usr/bin/env python3
"""mesh_node.py -- nod ROS2 subtire peste mesh_core.

Asculta pozitiile dronelor (din /sar/telemetry), intretine un MeshGraph,
calculeaza rutele multi-hop spre GCS (Dijkstra pe ETX) si publica:
  /mesh/routes   (1 Hz, latched) : pentru fiecare drona -> next-hop, hopuri,
                  reachable in stea vs mesh; consumat de dashboard.
  /mesh/status   (1 Hz)          : bilantul star vs mesh (cate ajung, cine e
                  recuperat de mesh, cine ramane izolat).

Accepta comenzi pe /mesh/control (std_msgs/String JSON):
  {"action":"block",   "id":"d3"}   -> scoate d3 din retea (drona doborata)
  {"action":"unblock", "id":"d3"}   -> o readuce
  {"action":"reset"}                -> deblocheaza tot

Asa, din dashboard apesi "blocheaza drona" si vezi pe harta cum:
  - daca drona era un RELEU, nodurile din spatele ei devin izolate (sau isi
    gasesc alt drum);
  - daca era o frunza, restul retelei nu e afectat.

Toata logica de retea e in mesh_core (testat 31/31); nodul e doar I/O ROS.

Pornire:
  python3 mesh_node.py --ros-args \
      -p pose_topic:=/sar/telemetry -p profile:=urban_rubble \
      -p pdr_min:=0.10 -p gcs_x:=0.0 -p gcs_y:=0.0
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from node_utils import qos_best_effort, qos_latched, now_s
from radio_link import make_link
from mesh_core import MeshGraph, ETX_INF, star_reachable, mesh_vs_star


def parse_telemetry(text):
    """Extrage id -> (x, y) din telemetria roiului. Accepta:
      {"k":"telemetry","id":"d1","pos":[x,y,z]}   (drone_node.py)
      {"id":"d1","x":..,"y":..}                   (forma plata)
    Intoarce dict (eventual gol)."""
    try:
        d = json.loads(text)
    except (ValueError, TypeError):
        return {}
    out = {}
    if isinstance(d, dict):
        did = d.get("id")
        if did is not None and "pos" in d and isinstance(d["pos"], (list, tuple)):
            try:
                out[str(did)] = (float(d["pos"][0]), float(d["pos"][1]))
            except (IndexError, TypeError, ValueError):
                pass
        elif did is not None and "x" in d and "y" in d:
            try:
                out[str(did)] = (float(d["x"]), float(d["y"]))
            except (TypeError, ValueError):
                pass
    return out


class MeshNode(Node):
    def __init__(self):
        super().__init__("mesh_node")
        p = self.declare_parameter
        p("pose_topic", "/sar/telemetry")
        p("profile", "urban_rubble")
        p("pdr_min", 0.10)
        p("ttl", 8)
        p("gcs_x", 0.0)
        p("gcs_y", 0.0)
        p("rate_hz", 1.0)
        g = lambda k: self.get_parameter(k).value

        self.gcs = (float(g("gcs_x")), float(g("gcs_y")))
        link = make_link(str(g("profile")), shadow_sigma_db=0.0)
        self.graph = MeshGraph(link, pdr_min=float(g("pdr_min")))
        self.poses = {"gcs": self.gcs}
        self.blocked = set()

        self.pub_routes = self.create_publisher(
            String, "/mesh/routes", qos_latched(1))
        self.pub_status = self.create_publisher(String, "/mesh/status", 10)
        self.create_subscription(String, str(g("pose_topic")),
                                 self.on_pose, qos_best_effort(30))
        self.create_subscription(String, "/mesh/control",
                                 self.on_control, 10)
        self.create_timer(1.0 / max(float(g("rate_hz")), 0.1), self.tick)
        self.get_logger().info(
            f"mesh_node pornit: profil={g('profile')} pdr_min={g('pdr_min')} "
            f"GCS={self.gcs}")

    # ---- intrari ----
    def on_pose(self, msg):
        upd = parse_telemetry(msg.data)
        if upd:
            self.poses.update(upd)

    def on_control(self, msg):
        try:
            d = json.loads(msg.data)
        except (ValueError, TypeError):
            return
        action = d.get("action")
        did = d.get("id")
        if action == "block" and did:
            self.blocked.add(str(did))
            self.get_logger().info(f"[block] {did} scos din retea")
        elif action == "unblock" and did:
            self.blocked.discard(str(did))
            self.get_logger().info(f"[unblock] {did} readus in retea")
        elif action == "reset":
            self.blocked.clear()
            self.get_logger().info("[reset] toate dronele readuse")

    # ---- bucla principala ----
    def tick(self):
        # GCS-ul e mereu prezent; pozitiile dronelor vin din telemetrie
        self.poses["gcs"] = self.gcs
        self.graph.set_positions(self.poses)
        # aplica blocarile (drone doborate)
        self.graph.down_nodes = set(self.blocked)
        self.graph._rebuild_edges()

        dist, nh = self.graph.shortest_paths_to("gcs")
        hops = self.graph.hop_count_to("gcs")
        star = star_reachable(self.graph, "gcs")
        bil = mesh_vs_star(self.graph, "gcs")

        routes = {}
        for n in self.poses:
            if n == "gcs":
                continue
            routes[n] = {
                "next": nh.get(n),
                "hops": hops.get(n, -1),
                "etx": (None if dist.get(n, ETX_INF) == ETX_INF
                        else round(dist[n], 3)),
                "direct": n in star,                 # link direct la GCS?
                "reachable": dist.get(n, ETX_INF) < ETX_INF,
                "blocked": n in self.blocked,
            }
        self.pub_routes.publish(String(data=json.dumps({
            "t": round(now_s(self), 2), "gcs": list(self.gcs),
            "routes": routes})))

        self.pub_status.publish(String(data=json.dumps({
            "t": round(now_s(self), 2),
            "n_total": bil["n_total"],
            "n_star": bil["n_star"],
            "n_mesh": bil["n_mesh"],
            "recovered": sorted(bil["recovered_by_mesh"]),
            "isolated": sorted(bil["isolated_even_in_mesh"]),
            "blocked": sorted(self.blocked),
        })))


def main():
    rclpy.init()
    node = MeshNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
