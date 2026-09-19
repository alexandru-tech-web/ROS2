#!/usr/bin/env python3
"""encoder_monitor_node.py -- pluginul de cinematica al bancului: ia
pozitia (encoderul) din /joint/state, o trece prin estimatorul
alpha-beta-gamma si publica viteza + acceleratia CURATE, cu jurnal CSV
pentru grafice. Functioneaza identic peste simulare si peste fier
(sursa lui /joint/state e emulator_node, indiferent de backend).

  sub /joint/state       {"0":{"t":..,"th":..},...}  (de la emulator_node)
  pub /joint/kinematics  {"0":{"t":..,"th":..,"om":..,"acc":..,
                                "om_raw":..},...}    (rate_hz, implicit 50)
  pub /joint/motor_kinematics  {"0":{"A":{...},"B":{...},
                                     "delta_th":..},...}
CSV: /home/ubuntu/Analiza_Teza/ViPRO/DATE/encoders_<session_id>.csv
     (t_s,time_utc,pair,th_raw,th,om,acc; fara suprascriere)
     /home/ubuntu/Analiza_Teza/ViPRO/DATE/motor_encoders_<session_id>.csv
Parametri: state_topic, out_topic, rate_hz, data_dir, session_id, csv_path,
           alpha, beta, gamma, quantize_cpr (0 = pozitia vine deja
           cuantizata de la fier; >0 = recuantizeaza, util in simulare)
"""
import json
import math
import os
import signal
import sys
from datetime import datetime, timezone

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from encoder_core import (EncoderModel, NaiveDiff, KinematicEstimator,
                          EncoderLogger, MotorEncoderBank,
                          MotorEncoderLogger)
from session_export import (checked_session_id, session_path, utc_now,
                            write_config)

DEFAULT_DATA_DIR = "/home/ubuntu/Analiza_Teza/ViPRO/DATE"


class EncoderMonitor(Node):
    def __init__(self):
        super().__init__("encoder_monitor")
        p = self.declare_parameter
        p("state_topic", "/joint/state")
        p("out_topic", "/joint/kinematics")
        p("motor_out_topic", "/joint/motor_kinematics")
        p("rate_hz", 50.0)
        p("data_dir", DEFAULT_DATA_DIR)
        data_dir = os.path.expanduser(str(self.get_parameter("data_dir").value))
        p("session_id", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        stamp = checked_session_id(self.get_parameter("session_id").value)
        default_csv = os.path.join(data_dir, f"encoders_{stamp}.csv")
        p("csv_path", default_csv)
        p("motor_csv_path", os.path.join(data_dir,
                                          f"motor_encoders_{stamp}.csv"))
        p("n_pairs", 3)
        p("alpha", 0.25); p("beta", 0.02); p("gamma", 0.0005)
        p("quantize_cpr", 4096)
        g = lambda n: self.get_parameter(n).value
        self.cpr = int(g("quantize_cpr"))
        write_config(session_path(data_dir, stamp, "encoder_config"), {
            "start_time_utc": utc_now(),
            "n_pairs": int(g("n_pairs")),
            "monitor_rate_hz": float(g("rate_hz")),
            "counts_per_rev": self.cpr,
            "alpha": float(g("alpha")),
            "beta": float(g("beta")),
            "gamma": float(g("gamma")),
            "state_topic": str(g("state_topic")),
        })
        self.enc = EncoderModel(self.cpr) if self.cpr > 0 else None
        mk = lambda: KinematicEstimator(alpha=float(g("alpha")),
                                        beta=float(g("beta")),
                                        gamma=float(g("gamma")))
        self.est = {}
        self.naiv = {}
        self.mk = mk
        self.t_last = {}
        self.out = {}
        self.motor_out = {}
        self.motor_bank = MotorEncoderBank(
            n_pairs=int(g("n_pairs")), counts_per_rev=self.cpr,
            alpha=float(g("alpha")), beta=float(g("beta")),
            gamma=float(g("gamma")))
        csv_path = os.path.expanduser(str(g("csv_path")))
        self.log = EncoderLogger(csv_path)
        self.get_logger().info(f"Jurnal encoder: {csv_path}")
        motor_csv_path = os.path.expanduser(str(g("motor_csv_path")))
        self.motor_log = MotorEncoderLogger(motor_csv_path)
        self.get_logger().info(f"Jurnal 6 encodere: {motor_csv_path}")
        self.create_subscription(String, str(g("state_topic")),
                                 self.on_state, 30)
        self.pub = self.create_publisher(String, str(g("out_topic")), 10)
        self.motor_pub = self.create_publisher(
            String, str(g("motor_out_topic")), 10)
        self.create_timer(1.0 / float(g("rate_hz")), self.report)

    def on_state(self, msg):
        d = json.loads(msg.data)
        time_utc = utc_now()
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
            self.log.row(t, pid, th_raw, th, om, acc, time_utc=time_utc)
            motor_states = st.get("motors")
            if (not isinstance(motor_states, dict) or
                    any(not isinstance(motor_states.get(side), dict) or
                        "th" not in motor_states[side]
                        for side in ("A", "B"))):
                # Nu inventam doua encodere dintr-o singura citire veche.
                continue
            samples = {}
            for side, index in (("A", 0), ("B", 1)):
                motor = motor_states[side]
                motor_t = float(motor.get("t", t))
                motor_th = float(motor["th"])
                sample = self.motor_bank.sample(2 * int(pid) + index,
                                                motor_t, motor_th)
                if sample is not None:
                    samples[side] = sample
                    self.motor_log.row(
                        pid, side, sample, time_utc=time_utc,
                        source=str(motor.get("source", "unknown")))
            if len(samples) == 2:
                self.motor_out[pid] = {
                    "t": t, "A": samples["A"], "B": samples["B"],
                    "delta_th": samples["A"]["th"] - samples["B"]["th"],
                    "source": motor_states["A"].get("source", "unknown")}

    def report(self):
        if self.out:
            self.pub.publish(String(data=json.dumps(self.out)))
        if self.motor_out:
            self.motor_pub.publish(String(data=json.dumps(self.motor_out)))


def main():
    rclpy.init()
    n = EncoderMonitor()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        n.log.close(); n.motor_log.close(); n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
