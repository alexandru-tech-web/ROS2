#!/usr/bin/env python3
"""punte_telemetrie.py -- nod SUBTIRE: /sar/telemetry (un singur topic, cum publica sar_swarm/drone_node.py) ->
/sar/telemetry/<id> (cate un topic per drona, cum ingereaza mesh_plugin: mesh_plugins.launch.py INGEST_PREFIX + d).

id-ul vine din CAMPUL "id" al mesajului JSON: sar_swarm/drone_node.py:279 `"k": "telemetry", "id": self.id, ...`
(si :180 pentru "op_event", tot cu "id"). Parametrul `id_camp` (implicit "id") il poate schimba; `prefix` = /sar/telemetry/.
Fara alta logica: nu filtreaza, nu modifica payload-ul, nu deduplica. Bucla egress -> punte se evita in launch
(mesh egress_topic:=/sar/telemetry_mesh, nu /sar/telemetry).
  python3 punte_telemetrie.py --selftest
"""
import json
import sys

PREFIX = "/sar/telemetry/"


def tinta(data, prefix=PREFIX, id_camp="id"):
    """Topicul-tinta pentru un mesaj JSON, sau None daca nu are campul id (functie pura)."""
    try:
        d = json.loads(data)
    except (ValueError, TypeError):
        return None
    i = d.get(id_camp) if isinstance(d, dict) else None
    if not isinstance(i, str) or not i or "/" in i:
        return None
    return prefix + i


def _selftest():
    assert tinta('{"k": "telemetry", "id": "d1", "pos": [1, 2, 0]}') == "/sar/telemetry/d1"
    assert tinta('{"k": "op_event", "id": "d4"}') == "/sar/telemetry/d4"
    assert tinta('{"k": "telemetry"}') is None and tinta("nu e json") is None and tinta('{"id": 3}') is None
    assert tinta('{"drone": "d2"}', id_camp="drone") == "/sar/telemetry/d2" and tinta('{"id": "a/b"}') is None
    print("SELFTEST punte_telemetrie OK (4 cazuri: id string -> prefix+id; fara id / json invalid / id ne-string / id cu '/' -> None).")
    return 0


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    class Punte(Node):
        def __init__(self):
            super().__init__("punte_telemetrie")
            self.declare_parameter("sursa", "/sar/telemetry")
            self.declare_parameter("prefix", PREFIX)
            self.declare_parameter("id_camp", "id")
            self.prefix = str(self.get_parameter("prefix").value)
            self.id_camp = str(self.get_parameter("id_camp").value)
            self.pubs = {}
            self.n = {"in": 0, "out": 0, "fara_id": 0}
            self.create_subscription(String, str(self.get_parameter("sursa").value), self._pe_mesaj, 30)
            self.create_timer(10.0, lambda: self.get_logger().info("punte: in=%d out=%d fara_id=%d topicuri=%s" % (
                self.n["in"], self.n["out"], self.n["fara_id"], sorted(self.pubs))))
            self.get_logger().info("punte_telemetrie: %s -> %s<%s>" % (self.get_parameter("sursa").value, self.prefix, self.id_camp))

        def _pe_mesaj(self, msg):
            self.n["in"] += 1
            t = tinta(msg.data, self.prefix, self.id_camp)
            if t is None:
                self.n["fara_id"] += 1
                return
            if t not in self.pubs:
                self.pubs[t] = self.create_publisher(String, t, 30)
            self.pubs[t].publish(msg)
            self.n["out"] += 1

    rclpy.init(args=args)
    n = Punte()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        print("punte_telemetrie: in=%d out=%d fara_id=%d" % (n.n["in"], n.n["out"], n.n["fara_id"]), file=sys.stderr)
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    main()
