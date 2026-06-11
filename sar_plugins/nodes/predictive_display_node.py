#!/usr/bin/env python3
"""predictive_display_node.py — "fantoma" predictiva pentru operator.

Ruleaza PE PARTEA OPERATORULUI (vede comenzile la emisie, fara intarziere,
si pozele DUPA ce au trecut prin legatura degradata). Publica la 20 Hz
predictia pozitiei curente a roverului pe pred_topic:
  {"t":..,"x":..,"y":..,"th":..,"age":<varsta ultimei poze>,"extrap":..}

Cand soseste o poza noua, compara predictia facuta pentru momentul ei cu
realitatea si scrie eroarea in ~/sar_data/predict.csv — exact metrica
pentru articolul de teleoperare: cat reduce predictia eroarea perceputa,
ca functie de latenta legaturii.

Scheme asteptate (conventia proiectului, chei configurabile mai jos):
  poza:    {"t":..,"x":..,"y":..,"th":..}   pe /teleop/pose
  comanda: {"v":..,"w":..[,"t":..]}         pe /teleop/cmd
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
from node_utils import qos_best_effort, qos_reliable, now_s
from predictor import DeadReckoningPredictor


class PredictiveDisplayNode(Node):
    def __init__(self):
        super().__init__("predictive_display")
        p = self.declare_parameter
        p("pose_topic", "/teleop/pose")
        p("cmd_topic", "/teleop/cmd")
        p("pred_topic", "/teleop/pose_pred")
        p("rate_hz", 20.0)
        p("max_extrapolation_s", 2.0)
        p("key_t", "t"), p("key_x", "x"), p("key_y", "y"), p("key_th", "th")
        p("key_v", "v"), p("key_w", "w")
        p("csv_path", "~/sar_data/predict.csv")
        g = lambda n: self.get_parameter(n).value
        self.k = {n: str(g("key_" + n)) for n in
                  ("t", "x", "y", "th", "v", "w")}

        self.pred = DeadReckoningPredictor(
            max_extrapolation_s=float(g("max_extrapolation_s")))
        self.pending = None            # ultima predictie publicata (t,x,y)

        path = os.path.expanduser(str(g("csv_path")))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.log = open(path, "w")
        self.log.write("t_s,age_s,err_pred_m,err_naiv_m\n")
        self.prev_pose = None          # (t, x, y, th) — pt. eroarea naiva

        self.pub = self.create_publisher(String, str(g("pred_topic")),
                                         qos_best_effort())
        self.create_subscription(String, str(g("cmd_topic")),
                                 self.on_cmd, qos_reliable(30))
        self.create_subscription(String, str(g("pose_topic")),
                                 self.on_pose, qos_best_effort(30))
        self.create_timer(1.0 / max(float(g("rate_hz")), 1.0), self.tick)
        self.get_logger().info("predictive display activ")

    def on_cmd(self, msg):
        try:
            d = json.loads(msg.data)
            t = float(d.get(self.k["t"], now_s(self)))
            self.pred.on_cmd_sent(t, float(d.get(self.k["v"], 0.0)),
                                  float(d.get(self.k["w"], 0.0)))
        except (ValueError, TypeError):
            pass

    def on_pose(self, msg):
        try:
            d = json.loads(msg.data)
            t = float(d[self.k["t"]])
            x, y = float(d[self.k["x"]]), float(d[self.k["y"]])
            th = float(d.get(self.k["th"], 0.0))
        except (ValueError, TypeError, KeyError):
            return
        # evaluarea predictiei anterioare pentru momentul acestei poze
        res = self.pred.predict(t)
        if res is not None and self.prev_pose is not None:
            xp, yp, _, age, _ = res
            err_pred = math.hypot(xp - x, yp - y)
            err_naiv = math.hypot(self.prev_pose[1] - x,
                                  self.prev_pose[2] - y)
            self.log.write(f"{t:.3f},{age:.3f},{err_pred:.4f},"
                           f"{err_naiv:.4f}\n")
            self.log.flush()
        self.prev_pose = (t, x, y, th)
        self.pred.on_pose(t, x, y, th)

    def tick(self):
        t = now_s(self)
        res = self.pred.predict(t)
        if res is None:
            return
        x, y, th, age, ex = res
        self.pub.publish(String(data=json.dumps(
            {"t": round(t, 3), "x": round(x, 3), "y": round(y, 3),
             "th": round(th, 4), "age": round(age, 3),
             "extrap": round(ex, 3)})))


def main():
    rclpy.init()
    node = PredictiveDisplayNode()
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
