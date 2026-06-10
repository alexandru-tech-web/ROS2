#!/usr/bin/env python3
"""
operator.launch.py — Statia de OPERATOR pe RViz (fara Gazebo):
robot + RViz + controlerul exercitiilor + inregistratorul de senzori +
panoul grafic de operator. Totul dintr-o singura comanda:

    $ ros2 launch rehab_exo_description operator.launch.py

Operatorul comanda din panou: exercitii/sesiuni, ajustarea la pacient
(scaun + extensii telescopice) si inregistrarea datelor (~/rehab_data/).
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    with open(os.path.join(pkg, "urdf", "rehab_exo.urdf"), "r") as f:
        robot_description = f.read()
    rviz_cfg = os.path.join(pkg, "rviz", "rehab.rviz")

    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher",
               output="screen", parameters=[{"robot_description": robot_description}])
    rviz = Node(package="rviz2", executable="rviz2",
                arguments=["-d", rviz_cfg], output="screen")
    controller = Node(package="rehab_exo_description",
                      executable="exercise_controller.py", output="screen",
                      parameters=[{"backend": "joint_states",
                                   "exercise": "neutral"}])
    recorder = Node(package="rehab_exo_description",
                    executable="sensor_recorder.py", output="screen")
    panel = Node(package="rehab_exo_description",
                 executable="operator_panel.py", output="screen")
    return LaunchDescription([rsp, rviz, controller, recorder, panel])
