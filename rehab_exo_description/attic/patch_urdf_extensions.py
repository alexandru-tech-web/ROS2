#!/usr/bin/env python3
"""
patch_urdf_extensions.py — Insereaza in rehab_exo.urdf extensiile Gazebo necesare
modelului de pacient si senzorilor inertiali, fara a atinge restul fisierului.

Ce adauga (inainte de </robot>):
  1. cate un plugin gz::sim::systems::ApplyJointForce pentru fiecare dintre cele
     6 articulatii motorizate — canalul prin care patient_model.py aplica
     cuplurile de rezistenta/tremor (topice gz:
     /model/rehab_exo/joint/<joint>/cmd_force);
  2. trei senzori IMU (base_link, left_foot, right_foot) la 100 Hz — baza pentru
     analiza de mers; necesita lumea worlds/rehab_world.sdf, care incarca
     sistemul gz-sim-imu-system.

Proprietati:
  * idempotent — al doilea apel detecteaza markerul si nu dubleaza nimic;
  * face backup (.bak) inainte de modificare;
  * valideaza ca XML-ul ramane well-formed dupa inserare.

Utilizare:
    python3 patch_urdf_extensions.py ~/ros2_ws/src/rehab_exo_description/urdf/rehab_exo.urdf
"""

import sys
import shutil
import xml.etree.ElementTree as ET

MARKER = "<!-- REHAB_EXT v1: ApplyJointForce + IMU (generat de patch_urdf_extensions.py) -->"

LEG_JOINTS = [
    "left_hip_joint", "left_knee_joint", "left_ankle_joint",
    "right_hip_joint", "right_knee_joint", "right_ankle_joint",
]
IMU_LINKS = ["base_link", "left_foot", "right_foot"]


def apply_joint_force_blocks():
    out = []
    for j in LEG_JOINTS:
        out.append(
            "  <gazebo>\n"
            "    <plugin filename=\"gz-sim-apply-joint-force-system\"\n"
            "            name=\"gz::sim::systems::ApplyJointForce\">\n"
            f"      <joint_name>{j}</joint_name>\n"
            "    </plugin>\n"
            "  </gazebo>\n")
    return "".join(out)


def imu_blocks():
    out = []
    for link in IMU_LINKS:
        out.append(
            f"  <gazebo reference=\"{link}\">\n"
            f"    <sensor name=\"imu_{link}\" type=\"imu\">\n"
            "      <always_on>1</always_on>\n"
            "      <update_rate>100</update_rate>\n"
            f"      <topic>rehab/imu/{link}</topic>\n"
            "    </sensor>\n"
            "  </gazebo>\n")
    return "".join(out)


def main():
    if len(sys.argv) != 2:
        sys.exit(f"utilizare: {sys.argv[0]} <cale/catre/rehab_exo.urdf>")
    path = sys.argv[1]

    with open(path, "r") as f:
        src = f.read()

    if MARKER in src:
        print("extensiile sunt deja prezente (marker gasit) — nu modific nimic")
        return
    if "</robot>" not in src:
        sys.exit("fisierul nu contine </robot> — nu pare un URDF valid")

    # verificari de coerenta: articulatiile si link-urile chiar exista in model
    missing = [j for j in LEG_JOINTS if f'name="{j}"' not in src]
    if missing:
        sys.exit(f"articulatii absente din URDF: {missing} — verifica numele")
    for link in IMU_LINKS:
        if f'name="{link}"' not in src:
            sys.exit(f"link-ul '{link}' lipseste din URDF — verifica numele")

    block = ("\n" + "  " + MARKER + "\n"
             + apply_joint_force_blocks()
             + imu_blocks())
    patched = src.replace("</robot>", block + "</robot>", 1)

    # validare XML inainte de a scrie ceva pe disc
    ET.fromstring(patched)

    shutil.copyfile(path, path + ".bak")
    with open(path, "w") as f:
        f.write(patched)

    print(f"OK: {len(LEG_JOINTS)} pluginuri ApplyJointForce + {len(IMU_LINKS)} senzori IMU")
    print(f"backup: {path}.bak")
    print("nota: pentru IMU porniti Gazebo cu worlds/rehab_world.sdf "
          "(incarca gz-sim-imu-system)")


if __name__ == "__main__":
    main()
