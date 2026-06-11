#!/usr/bin/env python3
"""
telerehab.launch.py — Porneste extensiile peste simularea existenta (rehab_exo).

NU porneste Gazebo: rulati intai gazebo.launch.py (neschimbat), apoi:

    ros2 launch rehab_exo_description telerehab.launch.py

Argumente (toate optionale):
  telerehab:=true      activeaza watchdog-ul de heartbeat in supervizor
                       (porniti operator_heartbeat.py pe statia operatorului!)
  with_patient:=true   porneste modelul de pacient + puntea ros_gz
                       (necesita URDF-ul patch-uit cu ApplyJointForce)
  profile:=<cale.yaml> profilul de pacient (implicit config/patient_demo.yaml)
  stop_command:=<txt>  comanda publicata pe /exercise_cmd la failsafe
                       (implicit "neutral" — calea STOP existenta)

Exemple:
  # doar supervizorul de siguranta, mod local:
  ros2 launch rehab_exo_description telerehab.launch.py

  # telereabilitare completa, cu pacient simulat:
  ros2 launch rehab_exo_description telerehab.launch.py \
      telerehab:=true with_patient:=true
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    limits_default = os.path.join(pkg, "config", "safety_limits.yaml")
    profile_default = os.path.join(pkg, "config", "patient_demo.yaml")
    bridge_cfg = os.path.join(pkg, "config", "gz_patient_bridge.yaml")

    telerehab = LaunchConfiguration("telerehab")
    with_patient = LaunchConfiguration("with_patient")

    args = [
        DeclareLaunchArgument("telerehab", default_value="false",
                              description="watchdog heartbeat operator pornit"),
        DeclareLaunchArgument("with_patient", default_value="false",
                              description="model pacient + punte ros_gz pornite"),
        DeclareLaunchArgument("profile", default_value=profile_default,
                              description="profil YAML de pacient"),
        DeclareLaunchArgument("limits", default_value=limits_default,
                              description="limite YAML de siguranta"),
        DeclareLaunchArgument("stop_command", default_value="neutral",
                              description="comanda de STOP pe /exercise_cmd"),
    ]

    supervisor = Node(
        package="rehab_exo_description",
        executable="safety_supervisor.py",
        output="screen",
        parameters=[{
            "limits_file": LaunchConfiguration("limits"),
            "stop_command": LaunchConfiguration("stop_command"),
            "enable_heartbeat": ParameterValue(telerehab, value_type=bool),
        }],
    )

    patient = Node(
        package="rehab_exo_description",
        executable="patient_model.py",
        output="screen",
        condition=IfCondition(with_patient),
        parameters=[{"profile_file": LaunchConfiguration("profile")}],
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        condition=IfCondition(with_patient),
        parameters=[{"config_file": bridge_cfg}],
    )

    return LaunchDescription(args + [supervisor, patient, bridge])
