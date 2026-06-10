#!/usr/bin/env python3
"""teleop.launch.py — teleoperare FARA Gazebo (roverul integreaza cinematica
intern). Bancul de comparatie RMW pe metrici de aplicatie:
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp   # sau rmw_zenoh_cpp
  ros2 launch ./launch/teleop.launch.py lat:=200 jit:=40 loss:=0.1 mode:=pilot
"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_launch_description():
    lat, jit = LaunchConfiguration("lat"), LaunchConfiguration("jit")
    loss, mode = LaunchConfiguration("loss"), LaunchConfiguration("mode")
    return LaunchDescription([
        DeclareLaunchArgument("lat", default_value="0.0"),
        DeclareLaunchArgument("jit", default_value="0.0"),
        DeclareLaunchArgument("loss", default_value="0.0"),
        DeclareLaunchArgument("mode", default_value="pilot"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "link_node.py"),
                            "--ros-args", "-p", ["lat_ms:=", lat],
                            "-p", ["jit_ms:=", jit], "-p", ["loss:=", loss]],
                       output="screen"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "robot_node.py"),
                            "--ros-args", "-p", "use_gazebo:=false"],
                       output="screen"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "operator_node.py"),
                            "--ros-args", "-p", ["mode:=", mode]],
                       output="screen"),
    ])
