#!/usr/bin/env python3
"""Reda in Gazebo/HMI planul suitei, NUMAI peste emulatorul ROS SIM.

Nu testeaza un drive si nu calculeaza verdictul PASS/FAIL: acela apartine
suitei offline din vipro_experiment.py. Citeste /joint/state pentru a
verifica sursa, ESTOP, oprirea axelor si confirmarea fiecarei comenzi.
La iesire normala, Ctrl+C sau SIGTERM publica zero pe toate cele 3 A.
"""
import argparse
import json
import math
import os
import signal
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vipro_experiment import build_suite_plan


class SuitePlayer(Node):
    def __init__(self):
        super().__init__("vipro_suite_player")
        self.latest = None
        self.last_state_wall = None
        self.command = [0.0] * 3
        self.command_wall = [0.0] * 3
        self.k_initial = None
        self.sim_confirmed = False
        self.create_subscription(String, "/joint/state", self.on_state, 10)
        self.pub = self.create_publisher(String, "/joint/cmd_a", 10)

    def on_state(self, msg):
        try:
            data = json.loads(msg.data)
            if not isinstance(data, dict):
                return
            self.latest = data
            self.last_state_wall = time.monotonic()
        except (json.JSONDecodeError, TypeError):
            return

    def _check_source(self):
        self.sim_confirmed = False
        if self.latest is None or any(str(pair) not in self.latest
                                      for pair in range(3)):
            raise RuntimeError("lipseste starea celor trei perechi")
        for pair in range(3):
            state = self.latest[str(pair)]
            motors = state.get("motors", {})
            if (not isinstance(motors, dict) or
                    any(motors.get(side, {}).get("source") != "sim"
                        for side in ("A", "B"))):
                raise RuntimeError("sursa nu este emulatorul SIM; nu trimit cuplu")
        self.sim_confirmed = True
        for pair in range(3):
            state = self.latest[str(pair)]
            if state.get("estopped"):
                raise RuntimeError("ESTOP activ; suita a fost intrerupta")
            if state.get("reaction_mode") != "impedance":
                raise RuntimeError("suita cere reaction_mode=impedance")
            k = float(state["k_ef"])
            if not math.isfinite(k) or k <= 0.0:
                raise RuntimeError("K efectiv invalid")
            if self.k_initial is not None and abs(k - self.k_initial[pair]) > 0.05:
                raise RuntimeError("K s-a schimbat in timpul suitei")

    def _spin_checked(self):
        rclpy.spin_once(self, timeout_sec=0.02)
        if self.last_state_wall is None or time.monotonic() - self.last_state_wall > 0.5:
            raise RuntimeError("telemetria /joint/state lipseste de peste 0.5 s")
        self._check_source()
        now = time.monotonic()
        for pair in range(3):
            if now - self.command_wall[pair] < 0.25:
                continue
            actual = float(self.latest[str(pair)].get("tau_a_cmd", 0.0))
            if abs(actual - self.command[pair]) > 0.005:
                raise RuntimeError(
                    f"A{pair} nu confirma cuplul comandat; HMI sau alt nod a intervenit")

    def wait_ready(self, timeout_s=10.0):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            if self.latest is None or self.pub.get_subscription_count() == 0:
                continue
            self._check_source()
            for pair in range(3):
                state = self.latest[str(pair)]
                if abs(float(state.get("tau_a_cmd", 0.0))) > 0.005:
                    raise RuntimeError("pune toate comenzile A la zero inainte de suita")
                if abs(float(state.get("om", 0.0))) > 0.05:
                    raise RuntimeError("asteapta oprirea axelor inainte de suita")
            self.k_initial = [float(self.latest[str(pair)]["k_ef"])
                              for pair in range(3)]
            self.last_state_wall = time.monotonic()
            self.command_wall = [self.last_state_wall] * 3
            return float(self.latest["0"]["t"])
        raise RuntimeError("nu gasesc emulatorul SIM pe /joint/state in 10 s")

    def send(self, pair, tau):
        self.command[pair] = tau
        self.command_wall[pair] = time.monotonic()
        self.pub.publish(String(data=json.dumps({"pair": pair, "tau": tau})))

    def zero_all(self):
        if not self.sim_confirmed:
            return
        # Publicari repetate, pentru ca ultimul mesaj sa aiba timp sa ajunga.
        for _ in range(3):
            for pair in range(3):
                self.pub.publish(String(data=json.dumps({"pair": pair, "tau": 0.0})))
            rclpy.spin_once(self, timeout_sec=0.05)

    def play(self, plan, duration):
        start_t = self.wait_ready()
        print("Emulator SIM confirmat; K_ef initial: " +
              ", ".join(f"p{i}={k:.2f}" for i, k in enumerate(self.k_initial)))
        transitions = []
        for case in plan:
            transitions.append((case["onset_s"], case["pair"], case["tau_a_nm"],
                                case["case_id"]))
            transitions.append((case["release_s"], case["pair"], 0.0,
                                case["case_id"]))
        transitions.sort()
        for when, pair, tau, case_id in transitions:
            while float(self.latest["0"]["t"]) - start_t < when:
                self._spin_checked()
            self.send(pair, tau)
            value = "0.00 (pauza)" if tau == 0.0 else f"{tau:+.2f}"
            print(f"caz {case_id:02d}: A{pair} = {value} Nm")
        while float(self.latest["0"]["t"]) - start_t < duration:
            self._spin_checked()
        print("Suita vizuala terminata; comenzile A au revenit la zero.")


def _interrupt(_signum, _frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(
        description="Reda cele 12 trepte in Gazebo, doar cu emulator SIM")
    parser.add_argument("--levels", type=float, nargs="+", default=[0.25, 0.5])
    parser.add_argument("--hold-s", type=float, default=1.0)
    parser.add_argument("--rest-s", type=float, default=0.6)
    args = parser.parse_args()
    plan, duration = build_suite_plan(args.levels, args.hold_s, args.rest_s)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, _interrupt)
    player = SuitePlayer()
    try:
        player.play(plan, duration)
    except KeyboardInterrupt:
        print("Suita intrerupta; trimit cuplu zero pe toate A.")
    except RuntimeError as exc:
        print(f"Suita oprita: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        player.zero_all()
        player.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
