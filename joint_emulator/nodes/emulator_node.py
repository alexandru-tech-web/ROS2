#!/usr/bin/env python3
"""emulator_node.py -- nodul ROS2 al bancului (acelasi cod peste SimBackend
azi si peste ModbusBackend cand identificam drive-urile). Per pereche:
A primeste comenzi de cuplu; B ruleaza legea de impedanta (fixa sau
adaptiva) cu amortizarea LOCALA -- lectia verificata in teste.

Topicuri (std_msgs/String, JSON -- stilul repo-ului):
  sub /joint/cmd_a      {"pair":0,"tau":0.5}        cuplul motorului A
  sub /joint/impedance  {"pair":0,"k":20,"b":0.8,"th0":0,"adaptive":true}
  sub /joint/estop      orice mesaj => cuplu zero pe tot
  sub /teleop/linkstate {"ms":..,"jit":..,"loss":..,"down":..} (optional:
                        degradarea masurii spre legea B -- tele-impedanta)
  pub /joint/state      {"0":{"t":..,"th":..,"om":..,"tau_b":..,"k_ef":..},..}
Parametri: backend:=sim, n_pairs:=3, rate_hz:=200, k:=20.0, b:=0.8,
tau_max:=2.0, adaptive:=false, state_hz:=50
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from drive_iface import SimBackend
from joint_core import ImpedanceLaw, SafetyGate, EnergyMonitor
from teleimpedance import DegradedMeasure, AdaptiveImpedance


class EmulatorNode(Node):
    def __init__(self):
        super().__init__("joint_emulator")
        p = self.declare_parameter
        p("backend", "sim"); p("n_pairs", 3); p("rate_hz", 200.0)
        p("k", 20.0); p("b", 0.8); p("tau_max", 2.0)
        p("adaptive", False); p("state_hz", 50.0); p("estop_energy", 0.0)
        g = lambda n: self.get_parameter(n).value
        self.n = int(g("n_pairs"))
        if g("backend") != "sim":
            raise SystemExit("[X] doar backend:=sim pana identificam "
                             "drive-urile (vezi modbus_backend.py)")
        self.hw = SimBackend(n_pairs=self.n)
        self.adaptive = bool(g("adaptive"))
        self.tau_max = float(g("tau_max"))
        mk = (lambda: AdaptiveImpedance(k0=float(g("k")), b0=float(g("b")),
                                        tau_max=self.tau_max)) if self.adaptive \
            else (lambda: ImpedanceLaw(k_nm_rad=float(g("k")),
                                       b_nms_rad=float(g("b")),
                                       tau_max=self.tau_max))
        self.laws = [mk() for _ in range(self.n)]
        self.links = [DegradedMeasure() for _ in range(self.n)]
        self.gates = [SafetyGate(timeout_s=0.1, tau_max=self.tau_max)
                      for _ in range(self.n)]
        # margine de stabilitate glisanta (integ tau_B*om pe fereastra 1s) -> ESTOP optional.
        # estop_energy=0 (implicit) => prag 1e9 => doar monitorizeaza (win_energy informativ),
        # comportament neschimbat; estop_energy>0 => auto-ESTOP cand energia pe fereastra trece pragul.
        self.estop_energy = float(g("estop_energy"))
        thr = self.estop_energy if self.estop_energy > 0 else 1e9
        self.energy = [EnergyMonitor(window_s=1.0, estop_energy=thr)
                       for _ in range(self.n)]
        self.dt = 1.0 / float(g("rate_hz"))
        for k in range(self.n):
            self.hw.enable(2 * k); self.hw.enable(2 * k + 1)

        self.create_subscription(String, "/joint/cmd_a", self.on_cmd_a, 10)
        self.create_subscription(String, "/joint/impedance", self.on_imp, 10)
        self.create_subscription(String, "/joint/estop", self.on_estop, 10)
        self.create_subscription(String, "/teleop/linkstate", self.on_link, 10)
        self.pub = self.create_publisher(String, "/joint/state", 10)
        self.create_timer(1.0 / float(g("rate_hz")), self.tick)
        self.create_timer(1.0 / float(g("state_hz")), self.report)
        self.last = {}

    def on_cmd_a(self, msg):
        d = json.loads(msg.data)
        k = int(d.get("pair", 0))
        if 0 <= k < self.n:
            tau = max(-self.tau_max, min(self.tau_max, float(d.get("tau", 0))))
            self.hw.set_torque(2 * k, tau)

    def on_imp(self, msg):
        d = json.loads(msg.data)
        k = int(d.get("pair", 0))
        if not (0 <= k < self.n):
            return
        law = self.laws[k]
        if isinstance(law, AdaptiveImpedance):
            law.k0 = float(d.get("k", law.k0)); law.b0 = float(d.get("b", law.b0))
            law.th0 = float(d.get("th0", law.th0))
        else:
            law.k = float(d.get("k", law.k)); law.b = float(d.get("b", law.b))
            law.th0 = float(d.get("th0", law.th0))

    def on_link(self, msg):
        d = json.loads(msg.data)
        for lk in self.links:
            lk.set_from_dict(d)

    def on_estop(self, _msg):
        self.hw.estop()
        self.get_logger().warn("ESTOP: cuplu zero pe toate perechile")

    def tick(self):
        for k in range(self.n):
            t, th, om = self.hw.read(2 * k + 1)
            self.links[k].push(t, th, om)
            m = self.links[k].latest(t)
            gate = self.gates[k]
            if m is None:
                tau = gate.gate(t, 0.0)
            else:
                th_m, om_m, age = m
                gate.feed(t - age)
                law = self.laws[k]
                if isinstance(law, AdaptiveImpedance):
                    tau = law.torque(th_m, om_m, age_s=age, om_local=om)
                else:
                    tau = law.torque(th_m, om_m)
                tau = gate.gate(t, tau)
            self.hw.set_torque(2 * k + 1, tau)
            em = self.energy[k]
            em.step(tau, om, self.dt)
            if self.estop_energy > 0 and em.estopped:
                self.hw.estop()
            self.last[str(k)] = {"t": round(t, 4), "th": round(th, 5),
                                 "om": round(om, 4), "tau_b": round(tau, 4),
                                 "k_ef": round(getattr(self.laws[k], "k_ef",
                                               getattr(self.laws[k], "k", 0)), 2),
                                 "win_energy": round(em.win_energy, 4),
                                 "estopped": bool(em.estopped)}

    def report(self):
        self.pub.publish(String(data=json.dumps(self.last)))


def main():
    rclpy.init()
    n = EmulatorNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.hw.estop(); n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
