#!/usr/bin/env python3
"""
display.launch.py — Vizualizeaza robotul de recuperare in RViz (fara fizica).

Porneste:
  - robot_state_publisher  (incarca URDF-ul)
  - joint_state_publisher_gui  (glisiere pentru cele 6 articulatii)
  - rviz2  (cu o configuratie de baza)

Utilizare:
    ros2 launch rehab_exo_description display.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    urdf_path = os.path.join(pkg, "urdf", "rehab_exo.urdf")
    rviz_path = os.path.join(pkg, "rviz", "rehab.rviz")

    with open(urdf_path, "r") as f:
        robot_description = f.read()

    return LaunchDescription([
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description}],
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            name="joint_state_publisher_gui",
            output="screen",
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen",
            arguments=["-d", rviz_path],
        ),
    ])
