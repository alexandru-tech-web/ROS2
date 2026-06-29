#!/usr/bin/env python3
"""link_predictor_node.py -- nodul ROS 2 SUBTIRE al predictorului de link (M22 CAPSTONE).

Toata invatarea sta in link_predictor_core (testat fara ROS). Acest nod doar:
  1. la pornire INCARCA modelul salvat (.npz); daca lipseste, il ANTRENEAZA pe loc
     din datele sintetice (date_sar.make_link_usability_dataset) si il salveaza;
  2. se ABONEAZA la un topic de feature-uri de link (std_msgs/String cu JSON, ex.
     {p95_ms, loss_frac, jitter_ms, base_lat_ms, mw_zenoh, distance_m});
  3. PUBLICA predictia pe /link_predictor/state (std_msgs/String cu JSON, ex.
     {usable: bool, prob: float, label: int}) -- consumabila de link_adaptive (C3).

Acesta este CAPSTONE-ul care inchide cursul inapoi in teza: un model ML antrenat
offline, impachetat intr-un nod ROS subtire ce expune o DECIZIE, exact ca
link_adaptive_node. JSON pe std_msgs/String, ca tot depozitul.

ONESTITATE: modelul implicit e antrenat pe date SINTETICE (semanate din C1/M);
de inlocuit cu un model antrenat pe date reale de campanie inainte de orice
folosire in misiune.

Topicuri:
  asculta:  <features_topic>          {p95_ms, loss_frac, ...}  (fereastra de link)
  publica:  /link_predictor/state     {usable, prob, label}

Rulare (pe masina cu ROS, dupa colcon build + source install/setup.bash):
  ros2 run curs_ml link_predictor_node --ros-args \
      -p features_topic:=/link/features -p model_path:=/tmp/link_predictor.npz
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_predictor_core import (  # noqa: E402
    LinkUsabilityPredictor, train_from_dataset, FEATURE_NAMES,
)

QOS = 10


class LinkPredictorNode(Node):
    def __init__(self):
        super().__init__("link_predictor_node")
        p = self.declare_parameter
        p("features_topic", "/link/features")
        p("state_topic", "/link_predictor/state")
        default_model = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "link_predictor.npz")
        p("model_path", default_model)
        g = lambda n: self.get_parameter(n).value

        self.model = self._load_or_train(str(g("model_path")))

        self.pub_state = self.create_publisher(String, str(g("state_topic")), QOS)
        self.create_subscription(String, str(g("features_topic")), self.on_features, QOS)
        self.get_logger().info(
            "link_predictor_node pornit (features<-%s, state->%s)"
            % (g("features_topic"), g("state_topic")))

    def _load_or_train(self, model_path):
        """Incarca modelul salvat; daca lipseste, il antreneaza pe date sintetice
        si il salveaza pentru rulari ulterioare."""
        if os.path.exists(model_path):
            self.get_logger().info("incarc modelul din %s" % model_path)
            return LinkUsabilityPredictor.load(model_path)
        self.get_logger().warn(
            "model lipsa la %s -- antrenez pe date SINTETICE la pornire" % model_path)
        from date_sar import make_link_usability_dataset
        df = make_link_usability_dataset(n_per_cond=200, seed=1)
        model = train_from_dataset(df, seed=0)
        try:
            model.save(model_path)
            self.get_logger().info("model salvat la %s" % model_path)
        except OSError as e:
            self.get_logger().warn("nu am putut salva modelul (%s)" % e)
        return model

    def on_features(self, msg):
        """Primeste o fereastra de feature-uri (JSON), prezice si publica starea."""
        try:
            feats = json.loads(msg.data)
        except (ValueError, TypeError):
            self.get_logger().warn("JSON invalid pe topicul de feature-uri")
            return
        try:
            label, prob = self.model.predict(feats)
        except (ValueError, RuntimeError) as e:
            self.get_logger().warn("nu pot prezice (%s)" % e)
            return
        out = {"usable": bool(label), "prob": round(prob, 4), "label": int(label)}
        self.pub_state.publish(String(data=json.dumps(out)))


def main():
    rclpy.init()
    node = LinkPredictorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
