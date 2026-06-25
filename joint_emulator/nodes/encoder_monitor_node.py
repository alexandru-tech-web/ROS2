#!/usr/bin/env python3
"""encoder_monitor_node.py -- pluginul de cinematica al bancului: ia
pozitia (encoderul) din /joint/state, o trece prin estimatorul
alpha-beta-gamma si publica viteza + acceleratia CURATE, cu jurnal CSV
pentru grafice. Functioneaza identic peste simulare si peste fier
(sursa lui /joint/state e emulator_node, indiferent de backend).

  sub /joint/state       {"0":{"t":..,"th":..},...}  (de la emulator_node)
  pub /joint/kinematics  {"0":{"t":..,"th":..,"om":..,"acc":..,
                                "om_raw":..},...}    (rate_hz, implicit 50)
CSV: ~/sar_data/encoders.csv  (t_s,pair,th_raw,th,om,acc)
Parametri: state_topic, out_topic, rate_hz, csv_path,
           alpha, beta, gamma, quantize_cpr (0 = pozitia vine deja
           cuantizata de la fier; >0 = recuantizeaza, util in simulare)
"""
import json
import math
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from encoder_core import EncoderModel, NaiveDiff, KinematicEstimator, EncoderLogger


class EncoderMonitor(Node):
    def __init__(self):
        super().__init__("encoder_monitor")
        p = self.declare_parameter
        p("state_topic", "/joint/state")
        p("out_topic", "/joint/kinematics")
        p("rate_hz", 50.0)
        p("csv_path", "~/sar_data/encoders.csv")
        p("alpha", 0.25); p("beta", 0.02); p("gamma", 0.0005)
        p("quantize_cpr", 4096)
        g = lambda n: self.get_parameter(n).value
        self.cpr = int(g("quantize_cpr"))
        self.enc = EncoderModel(self.cpr) if self.cpr > 0 else None
        mk = lambda: KinematicEstimator(alpha=float(g("alpha")),
                                        beta=float(g("beta")),
                                        gamma=float(g("gamma")))
        self.est = {}
        self.naiv = {}
        self.mk = mk
        self.t_last = {}
        self.out = {}
        self.log = EncoderLogger(os.path.expanduser(str(g("csv_path"))))
        self.create_subscription(String, str(g("state_topic")),
                                 self.on_state, 30)
        self.pub = self.create_publisher(String, str(g("out_topic")), 10)
        self.create_timer(1.0 / float(g("rate_hz")), self.report)

    def on_state(self, msg):
        d = json.loads(msg.data)
        for pid, st in d.items():
            t, th_true = float(st["t"]), float(st["th"])
            dt = t - self.t_last.get(pid, t - 0.005)
            if dt <= 0:
                continue
            self.t_last[pid] = t
            th_raw = self.enc.read(th_true) if self.enc else th_true
            if pid not in self.est:
                self.est[pid] = self.mk()
                self.naiv[pid] = NaiveDiff()
            om_raw, _ = self.naiv[pid].step(th_raw, dt)
            th, om, acc = self.est[pid].step(th_raw, dt)
            self.out[pid] = {"t": round(t, 4), "th": round(th, 5),
                             "om": round(om, 4), "acc": round(acc, 3),
                             "om_raw": round(om_raw, 3)}
            self.log.row(t, pid, th_raw, th, om, acc)

    def report(self):
        if self.out:
            self.pub.publish(String(data=json.dumps(self.out)))


def main():
    rclpy.init()
    n = EncoderMonitor()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.log.close(); n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
