#!/usr/bin/env python3
"""emulator_node.py -- nodul ROS2 al bancului SIM. Backend-ul ABB real nu
este identificat si nu este conectat. Per pereche:
A primeste comenzi de cuplu; B ruleaza legea de impedanta (fixa sau
adaptiva) cu amortizarea LOCALA -- lectia verificata in teste.

Topicuri (std_msgs/String, JSON -- stilul repo-ului):
  sub /joint/cmd_a      {"pair":0,"tau":0.5}        cuplul motorului A
  sub /joint/impedance  {"pair":0,"k":20,"b":0.8,"th0":0,"adaptive":true}
  sub /joint/estop      orice mesaj => cuplu zero pe tot
  sub /joint/reset_estop orice mesaj => rearmare SIM daca axele sunt lente
  sub /joint/linkstate  {"ms":..,"jit":..,"loss":..,"down":..} (optional:
                        degradarea masurii spre legea B -- tele-impedanta)
  pub /joint/state      {"0":{"t":..,"th":..,"motors":{"A":..,"B":..},
                             "tau_b":..,"k_ef":..},..}
Parametri: backend:=sim, n_pairs:=3, rate_hz:=200, k:=20.0, b:=0.8,
tau_max:=2.0, adaptive:=false, state_hz:=50,
reaction_mode:=impedance|contact, contact_angle_deg:=5.0.
Fizica si controlul SIM folosesc subpasi interni de cel mult 0.5 ms.
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
from drive_iface import SimBackend
from joint_core import (ImpedanceLaw, SafetyGate, EnergyMonitor,
                        VirtualStopLaw, simulation_substeps)
from teleimpedance import DegradedMeasure, AdaptiveImpedance
from session_export import (SessionEventLogger, SessionStateLogger,
                            checked_session_id, session_path, utc_now,
                            write_config)


DEFAULT_DATA_DIR = "/home/ubuntu/Analiza_Teza/ViPRO/DATE"


class EmulatorNode(Node):
    def __init__(self):
        super().__init__("joint_emulator")
        p = self.declare_parameter
        p("backend", "sim"); p("n_pairs", 3); p("rate_hz", 200.0)
        p("k", 20.0); p("b", 0.8); p("tau_max", 2.0)
        p("adaptive", False); p("state_hz", 50.0); p("estop_energy", 0.0)
        p("link_topic", "/joint/linkstate")
        p("reaction_mode", "impedance"); p("contact_angle_deg", 5.0)
        p("data_dir", DEFAULT_DATA_DIR)
        p("session_id", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        g = lambda n: self.get_parameter(n).value
        self.n = int(g("n_pairs"))
        if g("backend") != "sim":
            raise SystemExit("[X] doar backend:=sim pana identificam "
                             "drive-urile (vezi modbus_backend.py)")
        rate_hz = float(g("rate_hz"))
        # Bucla ROS ramane la rate_hz, dar controlul/fizica SIM primesc
        # subpasi de cel mult 0.5 ms. Astfel amortizarea adaptiva nu
        # destabilizeaza Euler la B=2 si link=120 ms din intervalul HMI.
        self.substeps, self.inner_dt = simulation_substeps(rate_hz)
        self.dt = self.substeps * self.inner_dt
        self.hw = SimBackend(n_pairs=self.n, dt=self.inner_dt)
        self.reaction_mode = str(g("reaction_mode"))
        if self.reaction_mode not in ("impedance", "contact"):
            raise ValueError("reaction_mode trebuie sa fie impedance/contact")
        angle_deg = float(g("contact_angle_deg"))
        if not math.isfinite(angle_deg) or angle_deg < 0.0:
            raise ValueError("contact_angle_deg trebuie sa fie >= 0")
        self.contact_angle_deg = angle_deg
        self.adaptive = bool(g("adaptive")) and self.reaction_mode == "impedance"
        self.tau_max = float(g("tau_max"))
        if self.reaction_mode == "contact":
            mk = lambda: VirtualStopLaw(
                k=float(g("k")), b=float(g("b")),
                contact_angle_rad=math.radians(self.contact_angle_deg),
                tau_max=self.tau_max)
        elif self.adaptive:
            mk = lambda: AdaptiveImpedance(k0=float(g("k")),
                                           b0=float(g("b")),
                                           tau_max=self.tau_max)
        else:
            mk = lambda: ImpedanceLaw(k_nm_rad=float(g("k")),
                                      b_nms_rad=float(g("b")),
                                      tau_max=self.tau_max)
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
        self.estopped = False
        self.reset_status = ""
        self.command_a = [0.0] * self.n
        for k in range(self.n):
            self.hw.enable(2 * k); self.hw.enable(2 * k + 1)

        self.create_subscription(String, "/joint/cmd_a", self.on_cmd_a, 10)
        self.create_subscription(String, "/joint/impedance", self.on_imp, 10)
        self.create_subscription(String, "/joint/estop", self.on_estop, 10)
        self.create_subscription(String, "/joint/reset_estop", self.on_reset, 10)
        self.create_subscription(String, str(g("link_topic")), self.on_link, 10)
        self.pub = self.create_publisher(String, "/joint/state", 10)
        self.last = {}
        self.session_id = checked_session_id(g("session_id"))
        data_dir = os.path.expanduser(str(g("data_dir")))
        write_config(session_path(data_dir, self.session_id, "sim_config"), {
            "start_time_utc": utc_now(), "backend": "sim",
            "n_pairs": self.n, "rate_hz": rate_hz,
            "state_hz": float(g("state_hz")),
            "physics_substeps": self.substeps,
            "physics_inner_dt_s": self.inner_dt,
            "adaptive": self.adaptive,
            "reaction_mode": self.reaction_mode,
            "contact_angle_deg": self.contact_angle_deg,
            "initial_k_nm_rad": float(g("k")),
            "initial_b_nms_rad": float(g("b")),
            "tau_max_nm": self.tau_max,
            "estop_energy_j": self.estop_energy,
        })
        self.state_log = SessionStateLogger(
            session_path(data_dir, self.session_id, "states"))
        self.event_log = SessionEventLogger(
            session_path(data_dir, self.session_id, "events"))
        self.event_log.row(0.0, "start", status="SIM")
        initial_utc = utc_now()
        for k in range(self.n):
            initial = {
                "t": 0.0, "th": 0.0, "om": 0.0,
                "motors": {
                    "A": {"th": 0.0, "om": 0.0, "source": "sim"},
                    "B": {"th": 0.0, "om": 0.0, "source": "sim"}},
                "tau_a_cmd": 0.0, "tau_b": 0.0,
                "k_ef": getattr(self.laws[k], "k_ef",
                                 getattr(self.laws[k], "k", 0.0)),
                "win_energy": 0.0, "reaction_mode": self.reaction_mode,
                "contact_angle_deg": self.contact_angle_deg,
                "estopped": False, "reset_status": "",
            }
            self.state_log.row(k, initial, self.laws[k], self.links[k],
                               time_utc=initial_utc)
        self.get_logger().info(f"Jurnal sesiune: {self.state_log.path}")
        self.create_timer(1.0 / float(g("rate_hz")), self.tick)
        self.create_timer(1.0 / float(g("state_hz")), self.report)

    def log_event(self, event, pair="", status="", **values):
        self.event_log.row(self.hw.read(0)[0], event, pair=pair,
                           status=status, **values)

    def on_cmd_a(self, msg):
        if self.estopped:
            return
        try:
            d = json.loads(msg.data)
            k = int(d.get("pair", 0))
            requested = float(d.get("tau", 0.0))
            if not math.isfinite(requested):
                raise ValueError("cuplul trebuie sa fie finit")
        except (json.JSONDecodeError, AttributeError, TypeError,
                ValueError) as exc:
            self.get_logger().warn(f"Comanda A ignorata: {exc}")
            return
        if 0 <= k < self.n:
            tau = max(-self.tau_max, min(self.tau_max, requested))
            self.hw.set_torque(2 * k, tau)
            self.command_a[k] = tau
            self.log_event("cmd_a", pair=k, tau_a_cmd_nm=tau)
            if abs(tau) > 1e-12 and self.reset_status.startswith("RESET reusit"):
                self.reset_status = ""

    def on_imp(self, msg):
        try:
            d = json.loads(msg.data)
            k = int(d.get("pair", 0))
            if not 0 <= k < self.n:
                return
            law = self.laws[k]
            k_value = float(d.get("k", getattr(law, "k0",
                                               getattr(law, "k", 20.0))))
            b_value = float(d.get("b", getattr(law, "b0",
                                               getattr(law, "b", 0.8))))
            th0_value = float(d.get("th0", law.th0))
            if (not math.isfinite(k_value) or not 0.0 <= k_value <= 40.0 or
                    not math.isfinite(b_value) or not 0.0 <= b_value <= 2.0 or
                    not math.isfinite(th0_value)):
                raise ValueError("K/B/th0 in afara domeniului SIM")
        except (json.JSONDecodeError, AttributeError, TypeError,
                ValueError) as exc:
            self.get_logger().warn(f"Mesaj impedance ignorat: {exc}")
            return
        if isinstance(law, AdaptiveImpedance):
            law.k0 = k_value; law.b0 = b_value
            law.th0 = th0_value
        else:
            law.k = k_value; law.b = b_value
            law.th0 = th0_value
        self.log_event("impedance", pair=k, k_set_nm_rad=k_value,
                       b_set_nms_rad=b_value)

    def on_link(self, msg):
        try:
            d = json.loads(msg.data)
            for lk in self.links:
                lk.set_from_dict(d)
            self.log_event("linkstate", link_ms=self.links[0].ms)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            self.get_logger().warn(f"Mesaj linkstate ignorat: {exc}")

    def on_estop(self, _msg):
        self.trip_estop("comanda primita")

    def on_reset(self, _msg):
        """Rearmeaza simularea fara salt de cuplu si fara comenzi A latente."""
        if not self.estopped:
            return
        max_speed = max(abs(self.hw.read(2 * k)[2]) for k in range(self.n))
        if max_speed > 0.05:
            self.reset_status = (f"RESET refuzat: viteza {max_speed:.3f} "
                                 "rad/s; asteapta oprirea axelor")
            self.get_logger().warn(self.reset_status)
            self.log_event("reset_estop", status=self.reset_status)
            return
        if (self.reaction_mode == "impedance" and
                any(lk.down or lk.loss >= 1.0 for lk in self.links)):
            self.reset_status = "RESET refuzat: legatura encoder indisponibila"
            self.get_logger().warn(self.reset_status)
            self.log_event("reset_estop", status=self.reset_status)
            return

        # Pozitia curenta devine noul punct neutru. B nu incearca sa
        # recupereze brusc pozitia dinaintea opririi.
        for k in range(self.n):
            self.laws[k].th0 = self.hw.read(2 * k)[1]
            if isinstance(self.laws[k], ImpedanceLaw):
                self.laws[k]._last = 0.0
            old = self.links[k]
            self.links[k] = DegradedMeasure(ms=old.ms, jit=old.jit,
                                            loss=old.loss, down=old.down)
            self.gates[k] = SafetyGate(timeout_s=0.1, tau_max=self.tau_max)
            self.energy[k] = EnergyMonitor(
                window_s=1.0,
                estop_energy=(self.estop_energy if self.estop_energy > 0
                              else 1e9))
        self.hw.rearm()
        self.command_a = [0.0] * self.n
        self.estopped = False
        self.reset_status = "RESET reusit; comanda A este zero"
        self.get_logger().info(self.reset_status)
        self.log_event("reset_estop", status=self.reset_status)

    def trip_estop(self, reason):
        """Oprire globala memorata; nu exista rearmare implicita."""
        already_estopped = self.estopped
        self.estopped = True
        self.hw.estop()
        self.command_a = [0.0] * self.n
        self.reset_status = "ESTOP activ; asteapta oprirea axelor, apoi RESET"
        if not already_estopped:
            self.get_logger().warn(
                f"ESTOP ({reason}): cuplu zero pe toate perechile")
            self.log_event("estop", status=reason)

    def tick(self):
        for _ in range(self.substeps):
            self.tick_inner()

    def tick_inner(self):
        # Un singur pas atomic pentru toate perechile. Citirile de mai jos nu
        # trebuie sa schimbe timpul sau starea simulatorului.
        self.hw.step(self.inner_dt)
        for k in range(self.n):
            _, th_a, om_a = self.hw.read(2 * k)
            t, th, om = self.hw.read(2 * k + 1)
            if self.estopped:
                tau = 0.0
            else:
                gate = self.gates[k]
                law = self.laws[k]
                if isinstance(law, VirtualStopLaw):
                    # Contactul este o reactie LOCALA; linkul degradat nu
                    # intarzie amortizarea si nu afecteaza acest mod.
                    gate.feed(t)
                    tau = gate.gate(t, law.torque(th, om))
                else:
                    self.links[k].push(t, th, om)
                    m = self.links[k].latest(t)
                    if m is None:
                        tau = gate.gate(t, 0.0)
                    else:
                        th_m, om_m, age = m
                        gate.feed(t - age)
                        if isinstance(law, AdaptiveImpedance):
                            tau = law.torque(th_m, om_m, age_s=age,
                                             om_local=om)
                        else:
                            tau = law.torque(th_m, om_m)
                        tau = gate.gate(t, tau)
                self.hw.set_torque(2 * k + 1, tau)
            em = self.energy[k]
            em.step(tau, om, self.inner_dt)
            if self.estop_energy > 0 and em.estopped:
                self.trip_estop(f"energie excesiva pe perechea {k}")
                tau = 0.0
            self.last[str(k)] = {"t": round(t, 4), "th": round(th, 5),
                                 "om": round(om, 4),
                                 "motors": {
                                     "A": {"th": round(th_a, 6),
                                           "om": round(om_a, 5),
                                           "source": "sim"},
                                     "B": {"th": round(th, 6),
                                           "om": round(om, 5),
                                           "source": "sim"}},
                                 "tau_a_cmd": round(self.command_a[k], 4),
                                 "tau_b": round(tau, 4),
                                 "k_ef": round(getattr(self.laws[k], "k_ef",
                                               getattr(self.laws[k], "k", 0)), 2),
                                 "win_energy": round(em.win_energy, 4),
                                 "reaction_mode": self.reaction_mode,
                                 "contact_angle_deg": self.contact_angle_deg,
                                 "estopped": bool(self.estopped),
                                 "reset_status": self.reset_status}

        # Daca o pereche a declansat oprirea in acest ciclu, starea publicata
        # trebuie sa fie coerenta pentru toate perechile.
        if self.estopped:
            for state in self.last.values():
                state["tau_b"] = 0.0
                state["estopped"] = True

    def report(self):
        time_utc = utc_now()
        for pid, state in self.last.items():
            k = int(pid)
            self.state_log.row(k, state, self.laws[k], self.links[k],
                               time_utc=time_utc)
        self.pub.publish(String(data=json.dumps(self.last)))


def main():
    rclpy.init()
    n = EmulatorNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        # ros2 launch poate trimite SIGINT si procesului, si grupului.
        # Ignoram al doilea semnal in timpul inchiderii fisierelor si ROS.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        n.hw.estop()
        n.state_log.close()
        n.event_log.close()
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
