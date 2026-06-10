#!/usr/bin/env python3
"""
gazebo.launch.py — Simuleaza robotul de recuperare in Gazebo (gz) cu ros2_control.

Porneste:
  - Gazebo (gz sim) cu o lume goala
  - robot_state_publisher (din xacro, cu plugin gz_ros2_control)
  - spawn al robotului in simulare
  - joint_state_broadcaster + leg_trajectory_controller

Utilizare:
    ros2 launch rehab_exo_description gazebo.launch.py

Necesita: ros_gz_sim, gz_ros2_control, controller_manager, ros2_controllers.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    urdf_path = os.path.join(pkg, "urdf", "rehab_exo.urdf")

    # Procesam xacro la lansare -> robot_description (rezolva plugin-ul gz).
    robot_description = ParameterValue(
        Command(["xacro ", urdf_path]), value_type=str)

    # Gazebo (gz) cu lume goala
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"),
                                  "launch", "gz_sim.launch.py"])
        ]),
        launch_arguments={"gz_args": "-r empty.sdf"}.items(),
    )

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description}],
    )

    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "robot_description", "-name", "rehab_exo", "-z", "0.0"],
        output="screen",
    )

    jsb = Node(
        package="controller_manager", executable="spawner",
        arguments=["joint_state_broadcaster"], output="screen",
    )
    traj = Node(
        package="controller_manager", executable="spawner",
        arguments=["leg_trajectory_controller"], output="screen",
    )

    # Pornim controllerele dupa ce robotul a fost creat in simulare.
    after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn, on_exit=[jsb, traj]))

    return LaunchDescription([gz_sim, rsp, spawn, after_spawn])
