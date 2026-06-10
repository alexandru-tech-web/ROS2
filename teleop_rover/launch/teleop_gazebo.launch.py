#!/usr/bin/env python3
"""teleop_gazebo.launch.py — aceeasi teleoperare, cu roverul in Gazebo:
  python3 gen_rover_world.py
  ros2 launch ./launch/teleop_gazebo.launch.py lat:=500 jit:=100 mode:=manual
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
        DeclareLaunchArgument("mode", default_value="manual"),
        ExecuteProcess(cmd=["gz", "sim", "-r",
                            os.path.join(PKG, "worlds", "teleop_course.sdf")],
                       output="screen"),
        ExecuteProcess(cmd=["ros2", "run", "ros_gz_bridge", "parameter_bridge",
                            "/model/rover/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
                            "/model/rover/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry"],
                       output="screen"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "link_node.py"),
                            "--ros-args", "-p", ["lat_ms:=", lat],
                            "-p", ["jit_ms:=", jit], "-p", ["loss:=", loss]],
                       output="screen"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "robot_node.py"),
                            "--ros-args", "-p", "use_gazebo:=true"],
                       output="screen"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "operator_node.py"),
                            "--ros-args", "-p", ["mode:=", mode]],
                       output="screen"),
    ])
