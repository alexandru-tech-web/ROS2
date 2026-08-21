#!/usr/bin/env python3
"""
gazebo.launch.py -- Simuleaza robotul de recuperare in Gazebo (gz) cu ros2_control.

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


# --- pinuirea RMW (F0): o singura sursa, launch/rmw_common.py ---
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rmw_common import argument_rmw, cu_rmw          # noqa: E402


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
        parameters=[{"robot_description": robot_description,
                     "use_sim_time": True}],
    )

    # Podul de ceas: nodurile ROS primesc timpul simularii (/clock) din Gazebo.
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )

    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "robot_description", "-name", "rehab_exo", "-z", "0.0"],
        output="screen",
    )

    # HOMING (M3): citeste encoderele ABSOLUTE si iese cu 0 abia cand toate au
    # raspuns. Controllerele de MISCARE se lanseaza pe OnProcessExit al lui, deci o
    # pornire fara pozitie cunoscuta nu poate ajunge la o comanda de traiectorie
    # [secventa reala, PDF p.10].
    homing = Node(
        package="rehab_exo_description", executable="homing_node.py",
        name="rehab_homing", output="screen",
        parameters=[{"use_sim_time": True}],
    )

    jsb = Node(
        package="controller_manager", executable="spawner",
        arguments=["joint_state_broadcaster",
                   "--controller-manager-timeout", "60"], output="screen",
    )
    traj = Node(
        package="controller_manager", executable="spawner",
        arguments=["leg_trajectory_controller",
                   "--controller-manager-timeout", "60"], output="screen",
    )
    adjust = Node(
        package="controller_manager", executable="spawner",
        arguments=["adjust_position_controller",
                   "--controller-manager-timeout", "60"], output="screen",
    )

    # v3: controlerul de exercitii (backend trajectory) + inregistratorul de senzori
    exercise = Node(
        package="rehab_exo_description", executable="exercise_controller.py",
        output="screen",
        parameters=[{"backend": "trajectory", "exercise": "neutral",
                     "use_sim_time": True}],
    )
    recorder = Node(
        package="rehab_exo_description", executable="sensor_recorder.py",
        output="screen", parameters=[{"use_sim_time": True}],
    )

    # Lant: spawn -> joint_state_broadcaster -> leg_trajectory -> adjust
    #       -> (controler exercitii + inregistrator)
    after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn, on_exit=[jsb]))
    # joint_state_broadcaster are voie INAINTE de homing: doar publica starea, nu
    # comanda nimic. Fara el, homing-ul nici nu ar avea ce citi.
    after_jsb = RegisterEventHandler(
        OnProcessExit(target_action=jsb, on_exit=[homing]))
    after_homing = RegisterEventHandler(
        OnProcessExit(target_action=homing, on_exit=[traj]))
    after_traj = RegisterEventHandler(
        OnProcessExit(target_action=traj, on_exit=[adjust]))
    after_adjust = RegisterEventHandler(
        OnProcessExit(target_action=adjust, on_exit=[exercise, recorder]))

    return LaunchDescription([argument_rmw(), cu_rmw(
        [gz_sim, rsp, clock_bridge, spawn,
         after_spawn, after_jsb, after_homing, after_traj, after_adjust],
        "gazebo")])
