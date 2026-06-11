#!/usr/bin/env python3
"""viz_rviz.launch.py — vizualizarea bancului in RViz:
robot_state_publisher (URDF) + podul /joint/state -> /joint_states + RViz.
Porneste SEPARAT emulatorul (nodes/emulator_node.py).
    ros2 launch launch/viz_rviz.launch.py
"""
import os

from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_launch_description():
    urdf = open(os.path.join(PKG, "urdf", "joint_bench.urdf")).read()
    return LaunchDescription([
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": urdf}]),
        ExecuteProcess(cmd=["python3",
                            os.path.join(PKG, "nodes", "state_to_jointstate_node.py")],
                       output="screen"),
        Node(package="rviz2", executable="rviz2",
             arguments=["-d", os.path.join(PKG, "rviz", "joint_bench.rviz")]),
    ])
