#!/usr/bin/env python3
"""mesh_node.py - nodul ROS2 al stratului mesh (unul per drona + unul pentru GCS).

Toata logica de rutare e in mesh_core (testata fara ROS). Nodul:
  1. emite periodic un BEACON cu pozitia proprie (descoperire de vecini);
  2. reconstruieste topologia din beacon-urile auzite (mesh_core);
  3. publica tabela de rutare proprie spre GCS (observabilitate);
  4. RELEAZA pachete DIRIJAT, hop-cu-hop: fiecare pachet poarta campul `next`
     (vecinul care trebuie sa-l preia); doar acel vecin il proceseaza, isi
     recalculeaza propriul next si il trimite mai departe. Fara flooding.

Optional (integrare in roi): poate INGESTA telemetria proprie a unei drone si
o transporta multi-hop pana la GCS, care o republica pe egress_topic
(ex. /sar/telemetry) pentru consumatorii existenti (coverage_node, dashboard).
Astfel telemetria unei drone fara legatura DIRECTA ajunge totusi la GCS.

Topicuri (JSON pe std_msgs/String):
  publica:  /mesh/beacon        {id, x, y, t, seq}
            /mesh/relay         {src, dst, seq, ttl, next, path, payload?}
            /mesh/route/<id>    {next, hops, etx, path, reachable}
            <egress_topic>      (doar GCS) telemetria livrata, repusa in circuit
  asculta:  /mesh/beacon        (de la toti)
            /mesh/relay         (proceseaza doar ce ii e adresat: next==id)
            <pose_topic>        pozitia proprie (daca nu e pozitie statica)
            <ingest_topic>      (daca ingest=true) telemetria proprie a dronei

Rulare:
  ros2 run mesh_plugin mesh_node --ros-args -p id:=d3 -p gcs:=GCS \
      -p pose_topic:=/sar/pose/d3
  (vezi mesh_plugins.launch.py pentru roiul intreg)
"""
import json
import math
import os
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_core import MeshTopology, routing_table   # noqa: E402

QOS = 10
BEACON_TTL_S = 3.0          # un beacon mai vechi de atat = vecin pierdut


class MeshNode(Node):
    def __init__(self):
        super().__init__("mesh_node")
        p = self.declare_parameter
        p("id", "d1")
        p("gcs", "GCS")
        p("pose_topic", "/sar/pose/d1")
        p("static_x", 9.0e9), p("static_y", 9.0e9)   # setate -> pozitie fixa (GCS)
        p("beacon_hz", 2.0)
        p("route_hz", 1.0)
        p("pdr_min", 0.10)
        p("relay_ttl", 8)
        # parametrii radio (aceeasi semantica precum mesh_core)
        p("tx_dbm", 0.0), p("path_loss_n", 3.0)
        p("sens_dbm", -40.0), p("width_db", 3.0)
        # integrare telemetrie (optional)
        p("ingest", False)              # daca true: impacheteaza telemetria proprie
        p("ingest_topic", "")           # de unde citeste telemetria proprie a dronei
        p("egress_topic", "")           # unde repune GCS telemetria livrata
        g = lambda n: self.get_parameter(n).value

        self.id = str(g("id"))
        self.gcs = str(g("gcs"))
        self.pdr_min = float(g("pdr_min"))
        self.ttl0 = int(g("relay_ttl"))
        self.radio = {"tx_dbm": float(g("tx_dbm")), "n": float(g("path_loss_n")),
                      "sens_dbm": float(g("sens_dbm")), "width_db": float(g("width_db"))}
        sx, sy = float(g("static_x")), float(g("static_y"))
        self.static = sx < 8.0e9 and sy < 8.0e9
        self.my_xy = (sx, sy) if self.static else (0.0, 0.0)
        self.ingest = bool(g("ingest"))
        self.egress_topic = str(g("egress_topic"))

        self.bseq = 0              # contor beacon
        self.pseq = 0              # contor pachete (telemetrie)
        self.pos = {}              # id -> (x, y) din beacon-uri
        self.last_seen = {}        # id -> t (expirarea vecinilor)
        self.seen = set()          # (src, seq) deja procesate (anti-bucla/duplicat)

        self.pub_beacon = self.create_publisher(String, "/mesh/beacon", QOS)
        self.pub_relay = self.create_publisher(String, "/mesh/relay", QOS)
        self.pub_route = self.create_publisher(String, f"/mesh/route/{self.id}", QOS)
        self.pub_egress = (self.create_publisher(String, self.egress_topic, QOS)
                           if self.egress_topic else None)

        self.create_subscription(String, "/mesh/beacon", self.on_beacon, QOS)
        self.create_subscription(String, "/mesh/relay", self.on_relay, QOS)
        if not self.static:
            self.create_subscription(String, str(g("pose_topic")), self.on_pose, QOS)
        it = str(g("ingest_topic"))
        if self.ingest and it:
            self.create_subscription(String, it, self.on_ingest, QOS)

        self.create_timer(1.0 / max(float(g("beacon_hz")), 0.1), self.tick_beacon)
        self.create_timer(1.0 / max(float(g("route_hz")), 0.1), self.tick_route)
        self.get_logger().info(
            f"mesh_node '{self.id}' pornit (sink={self.gcs}, static={self.static}, "
            f"ingest={self.ingest})")

    # ---------------- intrari ----------------
    def on_pose(self, msg):
        try:
            d = json.loads(msg.data)
            self.my_xy = (float(d.get("x", 0.0)), float(d.get("y", 0.0)))
        except Exception:
            pass

    def on_beacon(self, msg):
        try:
            d = json.loads(msg.data)
        except Exception:
            return
        nid = d.get("id")
        if nid is None or nid == self.id:
            return
        self.pos[nid] = (float(d["x"]), float(d["y"]))
        self.last_seen[nid] = time.monotonic()

    def on_ingest(self, msg):
        """Telemetria proprie intra in mesh: o impachetez si o trimit spre GCS
        prin next-hop-ul curent (rutare dirijata multi-hop)."""
        nxt = self._next_hop(self.gcs)
        if nxt is None:
            return                  # nicio ruta acum -> pachetul se pierde (ca in stea)
        self.pseq += 1
        pkt = {"src": self.id, "dst": self.gcs, "seq": self.pseq, "ttl": self.ttl0,
               "next": nxt, "path": [self.id], "payload": msg.data}
        self.seen.add((self.id, self.pseq))
        self.pub_relay.publish(String(data=json.dumps(pkt)))

    def on_relay(self, msg):
        """Forwardare DIRIJATA: procesez doar daca pachetul imi e adresat
        (next == eu). Daca sunt destinatia (tipic GCS), consum si republic la
        egress. Altfel imi recalculez next-hop-ul si trimit mai departe."""
        try:
            d = json.loads(msg.data)
        except Exception:
            return
        if d.get("next") != self.id:
            return                  # nu e pentru mine -> ignor (fara flooding)
        if d.get("dst") == self.id:
            if self.pub_egress is not None and "payload" in d:
                self.pub_egress.publish(String(data=str(d["payload"])))
            return
        key = (d.get("src"), d.get("seq"))
        if key in self.seen:
            return                  # deja vazut (bucla / duplicat)
        ttl = int(d.get("ttl", 0)) - 1
        if ttl <= 0:
            self.get_logger().warn(f"TTL expirat, arunc {key}")
            return
        nxt = self._next_hop(d.get("dst"))
        if nxt is None:
            return                  # ruta s-a rupt -> pica aici
        self.seen.add(key)
        d["ttl"] = ttl
        d["next"] = nxt
        d.setdefault("path", []).append(self.id)
        self.pub_relay.publish(String(data=json.dumps(d)))

    # ---------------- iesiri periodice ----------------
    def tick_beacon(self):
        self.bseq += 1
        self.pub_beacon.publish(String(data=json.dumps(
            {"id": self.id, "x": self.my_xy[0], "y": self.my_xy[1],
             "t": time.time(), "seq": self.bseq})))

    def tick_route(self):
        topo = self._topology()
        if topo is None:
            return
        info = routing_table(topo, self.gcs).get(self.id)
        if info is None:
            return
        self.pub_route.publish(String(data=json.dumps({
            "id": self.id, "next": info["next"], "hops": info["hops"],
            "etx": None if math.isinf(info["etx"]) else round(info["etx"], 3),
            "path": info["path"], "reachable": info["reachable"]})))

    # ---------------- ajutoare ----------------
    def _topology(self):
        now = time.monotonic()
        live = {nid: xy for nid, xy in self.pos.items()
                if now - self.last_seen.get(nid, 0) < BEACON_TTL_S}
        live[self.id] = self.my_xy
        if self.gcs not in live:
            return None             # nu am auzit inca GCS-ul -> nu rutez
        return MeshTopology(live, gcs=self.gcs, pdr_min=self.pdr_min, radio=self.radio)

    def _next_hop(self, dst):
        topo = self._topology()
        if topo is None:
            return None
        info = routing_table(topo, dst or self.gcs).get(self.id)
        return info["next"] if info and info["reachable"] else None


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
