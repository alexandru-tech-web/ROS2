#!/usr/bin/env python3
"""
demo_all.launch.py — Demonstratia completa dintr-o singura comanda:
robot_state_publisher + RViz + exercise_controller pornesc impreuna,
deci robotul apare direct in postura sezut si incepe exercitiul
(fara faza de link-uri albe care asteapta /joint_states).

    $ ros2 launch rehab_exo_description demo_all.launch.py
    $ ros2 launch rehab_exo_description demo_all.launch.py exercise:=ankle_pump reps:=4

Comutare live, din alt terminal:
    $ ros2 topic pub --once /exercise_cmd std_msgs/msg/String "data: alternating_march"
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    with open(os.path.join(pkg, "urdf", "rehab_exo.urdf"), "r") as f:
        robot_description = f.read()
    rviz_cfg = os.path.join(pkg, "rviz", "rehab.rviz")

    exercise_arg = DeclareLaunchArgument(
        "exercise", default_value="full_extension",
        description="knee_extension | hip_raise | ankle_pump | alternating_march | full_extension")
    reps_arg = DeclareLaunchArgument("reps", default_value="3")

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description}],
    )
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", rviz_cfg],
        output="screen",
    )
    controller = Node(
        package="rehab_exo_description",
        executable="exercise_controller.py",
        output="screen",
        parameters=[{
            "exercise": LaunchConfiguration("exercise"),
            "reps": ParameterValue(LaunchConfiguration("reps"), value_type=int),
        }],
    )
    return LaunchDescription([exercise_arg, reps_arg, rsp, rviz, controller])
