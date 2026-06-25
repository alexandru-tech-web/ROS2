#!/usr/bin/env python3
"""sar_gazebo.launch.py -- Misiunea SAR completa in Gazebo:
lumea apocaliptica + bridge-uri gz<->ROS per drona + 4 drone (use_gazebo)
+ GCS + injectorul de defecte (scenariul ales) + sonda de latenta + ecranul
cu date. Zero-build: nodurile ruleaza direct cu python3.

  ros2 launch sar_swarm/launch/sar_gazebo.launch.py scenario:=partition_2v2.yaml
"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRONES = {"d1": (3.5, 3.5), "d2": (3.5, 6.5), "d3": (6.5, 3.5), "d4": (6.5, 6.5)}


def generate_launch_description():
    scenario = LaunchConfiguration("scenario")
    autostart = LaunchConfiguration("autostart")
    dash = LaunchConfiguration("dashboard")
    acts = [
        DeclareLaunchArgument("autostart", default_value="true"),
        DeclareLaunchArgument("scenario", default_value="baseline.yaml",
                              description="fisier din sar_swarm/scenarios/"),
        DeclareLaunchArgument("dashboard", default_value="true"),
        ExecuteProcess(cmd=["gz", "sim", "-r",
                            os.path.join(PKG, "worlds", "apocalypse.sdf")],
                       output="screen"),
    ]
    bridge_args = ["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"]
    for d in DRONES:
        bridge_args += [
            f"/model/{d}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
            f"/model/{d}/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
        ]
    acts.append(Node(package="ros_gz_bridge", executable="parameter_bridge",
                     arguments=bridge_args, output="screen"))
    for d, (x, y) in DRONES.items():
        acts.append(ExecuteProcess(
            cmd=["python3", os.path.join(PKG, "drone_node.py"), "--ros-args",
                 "-p", f"id:={d}", "-p", f"x0:={x}", "-p", f"y0:={y}",
                 "-p", "use_gazebo:=true"],
            output="screen"))
    acts += [
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "gcs_node_ros.py"), "--ros-args",
                            "-p", ["autostart:=", autostart]],
                       output="screen"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "fault_injector_node.py"),
                            "--ros-args", "-p",
                            ["scenario:=" + os.path.join(PKG, "scenarios") + "/",
                             scenario]],
                       output="screen"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "latency_probe.py")],
                       output="screen"),
        ExecuteProcess(cmd=["python3", os.path.join(PKG, "dashboard_node.py")],
                       condition=IfCondition(dash), output="screen"),
    ]
    return LaunchDescription(acts)
