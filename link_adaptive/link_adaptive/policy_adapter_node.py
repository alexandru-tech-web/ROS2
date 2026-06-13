#!/usr/bin/env python3
"""policy_adapter_node.py - aplica politica link_adaptive pe un flux (nod subtire).

Inchide bucla C3 fara sa modifice drone_node/gcs_node: sta in calea telemetriei
(intra pe in_topic, iese pe out_topic) si, dupa politica de pe /link_adaptive/policy:
  - limiteaza debitul la rate_hz;
  - arunca esantioanele mai vechi de max_staleness_ms (vezi nota despre stamp);
  - reduce payload-ul (FULL/REDUCED/CRITICAL);
  - schimba QoS-ul publisher-ului de iesire (reliable<->best-effort) recreandu-l
    (in ROS 2 QoS-ul nu se poate schimba pe un publisher existent).

Toata logica de decizie a forward-arii e in policy_applier (testata 13/13 fara ROS).

Atasare in roi (o singura remapare, fara cod nou in drone_node), ex.:
  drone_node ... -r /sar/telemetry:=/sar/telemetry/raw
  ros2 run link_adaptive policy_adapter_node --ros-args \
      -p in_topic:=/sar/telemetry/raw -p out_topic:=/sar/telemetry
GCS-ul citeste /sar/telemetry ca inainte; intre timp curge prin adaptor.

Nota despre prospetime: varsta = acum - stamp, unde stamp se citeste din campul
'stamp_field' (implicit gol = aruncarea pe vechime e DEZACTIVATA, age=0). Pentru
a o activa, telemetria trebuie sa poarte un timestamp pe ceas de perete (secunde)
in acel camp. Limitarea ratei si reducerea payload-ului merg oricum.
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from policy_applier import PolicyApplier, DEFAULT_REDUCED, DEFAULT_CRITICAL   # noqa: E402


class PolicyAdapterNode(Node):
    def __init__(self):
        super().__init__("policy_adapter")
        p = self.declare_parameter
        p("in_topic", "/sar/telemetry/raw")
        p("out_topic", "/sar/telemetry")
        p("policy_topic", "/link_adaptive/policy")
        p("stamp_field", "")          # gol = nu se arunca pe vechime
        p("depth", 10)
        p("reduced_fields", list(DEFAULT_REDUCED))
        p("critical_fields", list(DEFAULT_CRITICAL))
        g = lambda n: self.get_parameter(n).value

        self.in_topic = str(g("in_topic"))
        self.out_topic = str(g("out_topic"))
        self.stamp_field = str(g("stamp_field"))
        self.depth = int(g("depth"))
        self.applier = PolicyApplier(reduced_fields=list(g("reduced_fields")),
                                     critical_fields=list(g("critical_fields")))

        # publisher de iesire: porneste reliable (NOMINAL); se recreeaza la schimbare
        self.cur_reliable = True
        self.out_pub = self.create_publisher(String, self.out_topic, self._qos(True))

        # politica: QoS fiabil (rata mica, o vrem sigur)
        self.create_subscription(String, str(g("policy_topic")), self.on_policy,
                                 self._qos(True))
        # telemetria de intrare: best-effort (debit mare; compatibil cu orice producator)
        self.create_subscription(String, self.in_topic, self.on_in, self._qos(False))

        self.get_logger().info(
            f"policy_adapter pornit: {self.in_topic} -> {self.out_topic} "
            f"(politica <- {g('policy_topic')}; prospetime "
            f"{'pe ' + self.stamp_field if self.stamp_field else 'dezactivata'})")

    def _qos(self, reliable):
        return QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE if reliable else ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST, depth=self.depth)

    def on_policy(self, msg):
        try:
            d = json.loads(msg.data)
        except Exception:
            return
        changed = self.applier.set_policy(d)
        if changed:
            # QoS-ul s-a schimbat: recreeaza publisher-ul de iesire
            self.destroy_publisher(self.out_pub)
            self.cur_reliable = self.applier.policy.reliable
            self.out_pub = self.create_publisher(String, self.out_topic,
                                                 self._qos(self.cur_reliable))
            self.get_logger().info(
                f"politica {self.applier.policy.payload} @ {self.applier.policy.rate_hz:.0f}Hz; "
                f"QoS recreat reliable={self.cur_reliable}")

    def on_in(self, msg):
        try:
            payload = json.loads(msg.data)
        except Exception:
            return
        now = self.get_clock().now().nanoseconds * 1e-9
        age_s = 0.0
        if self.stamp_field and isinstance(payload, dict) and self.stamp_field in payload:
            try:
                age_s = max(0.0, now - float(payload[self.stamp_field]))
            except (TypeError, ValueError):
                age_s = 0.0
        out = self.applier.on_sample(now, now - age_s, payload)
        if out is not None:
            self.out_pub.publish(String(data=json.dumps(out)))


def main():
    rclpy.init()
    node = PolicyAdapterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
