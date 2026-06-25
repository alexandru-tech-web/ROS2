#!/usr/bin/env python3
"""sar_ros.launch.py -- Aceeasi misiune SAR FARA Gazebo (dronele integreaza
cinematica intern): demo intr-un minut pe orice masina cu ROS 2 si bancul
ideal pentru comparatia middleware (C1): aceleasi noduri, acelasi trafic,
rulate o data cu CycloneDDS si o data cu rmw_zenoh:

  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp   # sau rmw_zenoh_cpp
  ros2 launch sar_swarm/launch/sar_ros.launch.py scenario:=loss_30.yaml
"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRONES = {"d1": (3.5, 3.5), "d2": (3.5, 6.5), "d3": (6.5, 3.5), "d4": (6.5, 6.5)}


def generate_launch_description():
    scenario = LaunchConfiguration("scenario")
    autostart = LaunchConfiguration("autostart")
    dash = LaunchConfiguration("dashboard")
    acts = [
        DeclareLaunchArgument("autostart", default_value="true"),
        DeclareLaunchArgument("scenario", default_value="baseline.yaml"),
        DeclareLaunchArgument("dashboard", default_value="true"),
    ]
    for d, (x, y) in DRONES.items():
        acts.append(ExecuteProcess(
            cmd=["python3", os.path.join(PKG, "drone_node.py"), "--ros-args",
                 "-p", f"id:={d}", "-p", f"x0:={x}", "-p", f"y0:={y}",
                 "-p", "use_gazebo:=false"],
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
