#!/usr/bin/env python3
"""link_adaptive_node.py - nodul ROS2 subtire al stratului adaptiv (contributia C3).

Toata logica e in link_adaptive_core (testata fara ROS). Acest nod doar:
  1. masoara starea legaturii din doua surse:
     - RTT dus-intors dintr-un topic de heartbeat/eco (JSON {rtt_ms}) -- ex. de
       la operator_heartbeat;
     - rata de pierdere din numerele de secventa de pe fluxul de telemetrie;
  2. ruleaza controlerul (histerezis + stationare) si decide modul + politica;
  3. PUBLICA politica curenta pe /link_adaptive/policy; ceilalti noduri
     (drone_node, gcs_node, bridge-ul de telemetrie) o citesc si isi ajusteaza
     rata / fiabilitatea / aruncarea esantioanelor vechi.

Nu reconfigureaza el QoS-ul altora -- expune DECIZIA, ca un controler curat,
exact cum mesh_node expune rutele. JSON pe std_msgs/String, ca tot depozitul.

Topicuri:
  publica:  /link_adaptive/policy  {mode, rate_hz, reliable, max_staleness_ms, payload}
            /link_adaptive/state    {rtt_p95_ms, loss, mode, transitions}
  asculta:  <rtt_topic>             {rtt_ms}        (sursa de RTT, ex. heartbeat)
            <telemetry_topic>       {seq, ...}      (pentru rata de pierdere)

Rulare:
  ros2 run link_adaptive link_adaptive_node --ros-args \
      -p rtt_topic:=/operator/heartbeat -p telemetry_topic:=/sar/telemetry
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_adaptive_core import AdaptiveController, LinkMonitor   # noqa: E402

QOS = 10


class LinkAdaptiveNode(Node):
    def __init__(self):
        super().__init__("link_adaptive_node")
        p = self.declare_parameter
        p("rtt_topic", "/operator/heartbeat")
        p("telemetry_topic", "/sar/telemetry")
        p("decide_hz", 5.0)
        p("min_dwell_s", 2.0)
        p("rtt_window", 50)
        p("seq_window", 100)
        g = lambda n: self.get_parameter(n).value

        self.mon = LinkMonitor(rtt_window=int(g("rtt_window")),
                               seq_window=int(g("seq_window")))
        self.ctrl = AdaptiveController(min_dwell_s=float(g("min_dwell_s")))
        self._t = 0.0
        self._period = 1.0 / max(float(g("decide_hz")), 0.1)

        self.pub_policy = self.create_publisher(String, "/link_adaptive/policy", QOS)
        self.pub_state = self.create_publisher(String, "/link_adaptive/state", QOS)
        self.create_subscription(String, str(g("rtt_topic")), self.on_rtt, QOS)
        self.create_subscription(String, str(g("telemetry_topic")), self.on_tele, QOS)
        self.create_timer(self._period, self.tick_decide)
        self.get_logger().info(
            f"link_adaptive_node pornit (rtt<-{g('rtt_topic')}, "
            f"loss<-{g('telemetry_topic')})")

    # ---- intrari ----
    def on_rtt(self, msg):
        try:
            d = json.loads(msg.data)
            if "rtt_ms" in d:
                self.mon.ingest_rtt(float(d["rtt_ms"]))
        except Exception:
            pass

    def on_tele(self, msg):
        try:
            d = json.loads(msg.data)
            if "seq" in d:
                self.mon.ingest_seq(int(d["seq"]))
        except Exception:
            pass

    # ---- decizie periodica ----
    def tick_decide(self):
        rtt_p95, loss = self.mon.metrics()
        burst = self.mon.max_run_of_gaps()
        prev = self.ctrl.mode
        mode, pol = self.ctrl.update(rtt_p95, loss, self._t, burst=burst)
        self._t += self._period
        self.pub_policy.publish(String(data=json.dumps(pol.as_dict())))
        self.pub_state.publish(String(data=json.dumps({
            "rtt_p95_ms": round(rtt_p95, 1), "loss": round(loss, 3),
            "max_burst": burst,
            "mode": mode, "transitions": self.ctrl.transitions})))
        if mode != prev:
            self.get_logger().info(
                f"tranzitie {prev} -> {mode}  (rtt_p95={rtt_p95:.0f}ms, loss={loss:.0%})")


def main():
    rclpy.init()
    node = LinkAdaptiveNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
