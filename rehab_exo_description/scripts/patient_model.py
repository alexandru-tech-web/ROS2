#!/usr/bin/env python3
"""
patient_model.py — Simularea pacientului ca sarcina dinamica pe articulatii (rehab_exo).

Pana acum robotul misca picioare "goale"; nodul acesta adauga in Gazebo ceea ce
ar simti motoarele cu un pacient real in dispozitiv: rezistenta elastica si
vascoasa a membrelor (model arc-amortizor) si, optional, tremor (4-6 Hz, tipic
parkinsonian). Cuplurile rezultate sunt aplicate articulatiilor prin plugin-ul
standard gz::sim::systems::ApplyJointForce (inserat in URDF de
patch_urdf_extensions.py) prin intermediul lui ros_gz_bridge.

Pentru fiecare articulatie motorizata:

    tau = -k * (q - q_rest)  -  b * q_punct  +  tremor(t)        [Nm]
    tau = clamp(tau * scale, -tau_max, +tau_max)

Lantul de date:
    /joint_states --> patient_model --> /rehab/patient_force/<joint> (Float64)
        --(ros_gz_bridge, config/gz_patient_bridge.yaml)-->
    /model/rehab_exo/joint/<joint>/cmd_force (gz.msgs.Double) --> ApplyJointForce

Astfel senzorii de cuplu din ros2_control masoara in sfarsit o sarcina reala,
iar exercitiile pot fi evaluate "cu pacient" vs "fara pacient".

Parametri:
  profile_file   YAML cu profilul pacientului (vezi config/patient_demo.yaml)
  rate           frecventa de calcul/publicare, Hz (implicit 100)
  scale          factor global 0..1 aplicat peste profil (0 = pacient "absent")

Topicuri auxiliare:
  sub /patient_model/scale  std_msgs/Float64  — modificare live a factorului
                                                (ex. crestere progresiva a sarcinii)
"""

import math
import os
import time

import rclpy
import yaml
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

LEG_JOINTS = [
    "left_hip_joint", "left_knee_joint", "left_ankle_joint",
    "right_hip_joint", "right_knee_joint", "right_ankle_joint",
]

# Profil implicit prudent: rezistenta usoara, fara tremor.
DEFAULT_PROFILE = {
    "tau_max": 15.0,
    "joints": {j: {"k": 4.0, "b": 1.0, "q_rest": 0.0} for j in LEG_JOINTS},
    "tremor": {"amp": 0.0, "freq": 5.0, "joints": []},
}


class PatientModel(Node):
    def __init__(self):
        super().__init__("patient_model")

        self.declare_parameter("profile_file", "")
        self.declare_parameter("rate", 100.0)
        self.declare_parameter("scale", 1.0)

        self.scale = float(self.get_parameter("scale").value)
        self.profile = self._load_profile(self.get_parameter("profile_file").value)
        self.tau_max = float(self.profile.get("tau_max", 15.0))

        self.q = {j: 0.0 for j in LEG_JOINTS}
        self.qd = {j: 0.0 for j in LEG_JOINTS}
        self.have_js = False
        self.t0 = time.monotonic()

        self.pubs = {
            j: self.create_publisher(Float64, f"/rehab/patient_force/{j}", 10)
            for j in LEG_JOINTS
        }
        self.create_subscription(JointState, "/joint_states", self._on_js, 20)
        self.create_subscription(Float64, "/patient_model/scale", self._on_scale, 1)

        period = 1.0 / float(self.get_parameter("rate").value)
        self.create_timer(period, self._step)

        trem = self.profile.get("tremor", {})
        self.get_logger().info(
            f"model pacient activ | scale={self.scale:.2f} | tau_max={self.tau_max:.1f} Nm | "
            f"tremor amp={float(trem.get('amp', 0.0)):.2f} Nm @ {float(trem.get('freq', 0.0)):.1f} Hz "
            f"pe {trem.get('joints', [])}")

    # ----------------------------------------------------------------- profil
    def _load_profile(self, path):
        prof = {
            "tau_max": DEFAULT_PROFILE["tau_max"],
            "joints": {j: dict(v) for j, v in DEFAULT_PROFILE["joints"].items()},
            "tremor": dict(DEFAULT_PROFILE["tremor"]),
        }
        if path and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = yaml.safe_load(f) or {}
                if "tau_max" in data:
                    prof["tau_max"] = float(data["tau_max"])
                for j, v in (data.get("joints") or {}).items():
                    prof["joints"].setdefault(j, {"k": 0.0, "b": 0.0, "q_rest": 0.0})
                    prof["joints"][j].update({k: float(x) for k, x in v.items()})
                if "tremor" in data and data["tremor"]:
                    prof["tremor"].update(data["tremor"])
                self.get_logger().info(f"profil pacient incarcat din {path}")
            except Exception as e:
                self.get_logger().error(f"nu pot citi {path}: {e}; folosesc profilul implicit")
        elif path:
            self.get_logger().warning(f"{path} nu exista; folosesc profilul implicit")
        return prof

    # --------------------------------------------------------------- callback
    def _on_js(self, msg: JointState):
        names = list(msg.name)
        for j in LEG_JOINTS:
            if j in names:
                i = names.index(j)
                if i < len(msg.position):
                    self.q[j] = msg.position[i]
                if i < len(msg.velocity):
                    self.qd[j] = msg.velocity[i]
        self.have_js = True

    def _on_scale(self, msg: Float64):
        self.scale = max(0.0, min(2.0, float(msg.data)))
        self.get_logger().info(f"scale pacient -> {self.scale:.2f}")

    # ------------------------------------------------------------------ pas
    def _step(self):
        if not self.have_js:
            return  # fara stare articulara nu aplicam nimic (pornire sigura)
        t = time.monotonic() - self.t0
        trem = self.profile.get("tremor", {})
        trem_amp = float(trem.get("amp", 0.0))
        trem_w = 2.0 * math.pi * float(trem.get("freq", 5.0))
        trem_joints = set(trem.get("joints", []))

        for j in LEG_JOINTS:
            p = self.profile["joints"].get(j, {})
            k = float(p.get("k", 0.0))
            b = float(p.get("b", 0.0))
            q_rest = float(p.get("q_rest", 0.0))
            tau = -k * (self.q[j] - q_rest) - b * self.qd[j]
            if j in trem_joints and trem_amp > 0.0:
                # faza decalata pe dreapta, ca tremorul sa nu fie perfect simetric
                phase = 0.0 if j.startswith("left") else math.pi / 3.0
                tau += trem_amp * math.sin(trem_w * t + phase)
            tau = max(-self.tau_max, min(self.tau_max, tau * self.scale))
            self.pubs[j].publish(Float64(data=tau))


def main():
    rclpy.init()
    node = PatientModel()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # La oprire trimitem 0 Nm, ca Gazebo sa nu ramana cu ultimul cuplu aplicat.
        try:
            for pub in node.pubs.values():
                pub.publish(Float64(data=0.0))
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
