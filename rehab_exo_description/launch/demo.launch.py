#!/usr/bin/env python3
"""
demo.launch.py — Demonstratia controlului: robot_state_publisher + RViz,
FARA joint_state_publisher_gui (glisierele ar intra in conflict cu
exercise_controller pe /joint_states — un singur emitator de pozitii!).

Terminal 1:  $ ros2 launch rehab_exo_description demo.launch.py
Terminal 2:  $ python3 ~/ros2_ws/src/rehab_exo_description/scripts/exercise_controller.py \
                 --ros-args -p exercise:=full_extension -p reps:=3
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    urdf_path = os.path.join(pkg, "urdf", "rehab_exo.urdf")
    with open(urdf_path, "r") as f:
        robot_description = f.read()
    rviz_cfg = os.path.join(pkg, "rviz", "rehab.rviz")

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
    return LaunchDescription([rsp, rviz])
