#!/usr/bin/env python3
"""
safety_supervisor.py — Supervizor de siguranta pentru robotul de recuperare (rehab_exo).

Ruleaza PE PARTEA ROBOTULUI si vegheaza trei lucruri, independent de panou:

  1. CUPLURI:  |effort| peste limita per articulatie  -> STOP lin (neutral)
  2. VITEZE:   |velocity| peste limita per articulatie -> STOP lin (neutral)
  3. LEGATURA: heartbeat-ul operatorului lipseste > timeout -> STOP lin
               (relevant in modul telereabilitare; vezi parametrul enable_heartbeat)

"STOP lin" = publicarea comenzii de oprire pe /exercise_cmd (implicit "neutral"),
exact calea de STOP deja implementata in exercise_core/exercise_controller:
robotul revine lent la pozitia de sezut, fara blocare brusca a articulatiilor.

Suplimentar, nodul raspunde la heartbeat (echo) ca operatorul sa poata masura
RTT-ul si pierderea de pachete — perechea lui este operator_heartbeat.py.

Topicuri:
  sub  /joint_states            sensor_msgs/JointState   (efforturi de la gz_ros2_control)
  sub  /telerehab/heartbeat     std_msgs/String          ("seq;t_ns" de la operator)
  sub  /safety/reset            std_msgs/Empty           (rearmare dupa declansare)
  pub  /telerehab/heartbeat_echo std_msgs/String         (acelasi mesaj, intors)
  pub  /exercise_cmd            std_msgs/String          (comanda de STOP la declansare)
  pub  /safety/status           std_msgs/String          (periodic: OK / TRIPPED:<motiv>)
  pub  /safety/event            std_msgs/String          (o data, la fiecare declansare)

Parametri (vezi config/safety_limits.yaml):
  limits_file        cale catre YAML cu limitele per articulatie
  stop_command       textul publicat pe /exercise_cmd la declansare (implicit "neutral")
  enable_heartbeat   true doar in telereabilitare (implicit false, ca sa nu declanseze local)
  heartbeat_timeout  secunde fara heartbeat pana la failsafe (implicit 0.6)
  startup_grace      secunde ignorate la pornire (varfuri de effort la spawn; implicit 2.0)
  rate               frecventa buclei de supraveghere, Hz (implicit 50)
"""

import os
import time

import rclpy
import yaml
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Empty, String

# Articulatiile motorizate ale robotului (identice cu leg_trajectory_controller).
LEG_JOINTS = [
    "left_hip_joint", "left_knee_joint", "left_ankle_joint",
    "right_hip_joint", "right_knee_joint", "right_ankle_joint",
]

# Limite implicite, folosite daca YAML-ul lipseste sau e incomplet.
DEFAULT_LIMITS = {
    j: {"effort_max": 60.0 if "ankle" not in j else 30.0, "velocity_max": 1.5}
    for j in LEG_JOINTS
}


class SafetySupervisor(Node):
    def __init__(self):
        super().__init__("safety_supervisor")

        self.declare_parameter("limits_file", "")
        self.declare_parameter("stop_command", "neutral")
        self.declare_parameter("enable_heartbeat", False)
        self.declare_parameter("heartbeat_timeout", 0.6)
        self.declare_parameter("startup_grace", 2.0)
        self.declare_parameter("rate", 50.0)

        self.stop_command = self.get_parameter("stop_command").value
        self.enable_hb = bool(self.get_parameter("enable_heartbeat").value)
        self.hb_timeout = float(self.get_parameter("heartbeat_timeout").value)
        self.grace = float(self.get_parameter("startup_grace").value)

        self.limits = self._load_limits(self.get_parameter("limits_file").value)

        # Stare interna.
        self.t_start = time.monotonic()
        self.t_last_hb = None          # ultimul heartbeat primit (monotonic)
        self.tripped = False
        self.trip_reason = ""
        self.last_js = None

        # Comunicatie.
        self.sub_js = self.create_subscription(JointState, "/joint_states", self._on_js, 20)
        self.sub_hb = self.create_subscription(String, "/telerehab/heartbeat", self._on_hb, 20)
        self.sub_rst = self.create_subscription(Empty, "/safety/reset", self._on_reset, 1)
        self.pub_echo = self.create_publisher(String, "/telerehab/heartbeat_echo", 20)
        self.pub_cmd = self.create_publisher(String, "/exercise_cmd", 1)
        self.pub_status = self.create_publisher(String, "/safety/status", 1)
        self.pub_event = self.create_publisher(String, "/safety/event", 1)

        period = 1.0 / float(self.get_parameter("rate").value)
        self.timer = self.create_timer(period, self._watch)
        self.status_timer = self.create_timer(0.5, self._publish_status)

        hb_txt = (f"heartbeat ON (timeout {self.hb_timeout:.2f}s)"
                  if self.enable_hb else "heartbeat OFF (mod local)")
        self.get_logger().info(
            f"supervizor activ | stop='{self.stop_command}' | {hb_txt} | "
            f"limite pentru {len(self.limits)} articulatii")

    # ----------------------------------------------------------------- limite
    def _load_limits(self, path):
        limits = {j: dict(v) for j, v in DEFAULT_LIMITS.items()}
        if path and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = yaml.safe_load(f) or {}
                for j, v in (data.get("joints") or {}).items():
                    limits.setdefault(j, {})
                    limits[j].update({k: float(x) for k, x in v.items()})
                self.get_logger().info(f"limite incarcate din {path}")
            except Exception as e:  # YAML gresit nu trebuie sa doboare supervizorul
                self.get_logger().error(f"nu pot citi {path}: {e}; folosesc implicitele")
        elif path:
            self.get_logger().warning(f"{path} nu exista; folosesc limitele implicite")
        return limits

    # --------------------------------------------------------------- callback
    def _on_js(self, msg: JointState):
        self.last_js = msg

    def _on_hb(self, msg: String):
        self.t_last_hb = time.monotonic()
        # Echo imediat: operatorul masoara RTT pe perechea heartbeat/echo.
        self.pub_echo.publish(msg)

    def _on_reset(self, _msg: Empty):
        if self.tripped:
            self.tripped = False
            self.trip_reason = ""
            self.t_last_hb = None       # cerem un heartbeat proaspat dupa rearmare
            self.t_start = time.monotonic()  # noua perioada de gratie
            self.get_logger().warning("supervizor REARMAT de operator")

    # ------------------------------------------------------------ supraveghere
    def _trip(self, reason: str):
        if self.tripped:
            return
        self.tripped = True
        self.trip_reason = reason
        self.pub_cmd.publish(String(data=self.stop_command))
        self.pub_event.publish(String(data=reason))
        self.get_logger().error(f"FAILSAFE: {reason} -> '{self.stop_command}' pe /exercise_cmd")

    def _watch(self):
        if self.tripped:
            return
        if time.monotonic() - self.t_start < self.grace:
            return  # perioada de gratie: spawn-ul in Gazebo produce varfuri de effort

        # 1+2) limite de cuplu si viteza, pe baza /joint_states
        if self.last_js is not None:
            names = list(self.last_js.name)
            for j in LEG_JOINTS:
                if j not in names:
                    continue
                i = names.index(j)
                lim = self.limits.get(j, {})
                eff = self.last_js.effort[i] if i < len(self.last_js.effort) else 0.0
                vel = self.last_js.velocity[i] if i < len(self.last_js.velocity) else 0.0
                emax = lim.get("effort_max")
                vmax = lim.get("velocity_max")
                if emax is not None and abs(eff) > emax:
                    self._trip(f"cuplu depasit pe {j}: {eff:+.1f} Nm (limita {emax:.1f})")
                    return
                if vmax is not None and abs(vel) > vmax:
                    self._trip(f"viteza depasita pe {j}: {vel:+.2f} rad/s (limita {vmax:.2f})")
                    return

        # 3) legatura cu operatorul (doar in telereabilitare)
        if self.enable_hb:
            if self.t_last_hb is None:
                # nu am primit inca nimic: toleram pe durata gratiei extinse
                if time.monotonic() - self.t_start > max(self.grace, 3.0):
                    self._trip("niciun heartbeat primit de la operator")
            elif time.monotonic() - self.t_last_hb > self.hb_timeout:
                dt = time.monotonic() - self.t_last_hb
                self._trip(f"legatura cu operatorul pierduta de {dt:.2f}s")

    def _publish_status(self):
        txt = f"TRIPPED:{self.trip_reason}" if self.tripped else "OK"
        self.pub_status.publish(String(data=txt))


def main():
    rclpy.init()
    node = SafetySupervisor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
