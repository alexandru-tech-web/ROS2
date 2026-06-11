#!/usr/bin/env python3
"""mission_plugins.launch.py — etajul de misiune pentru roi.

Porneste impreuna: link radio pe distanta + acoperire + victime + baterie,
toate ascultand telemetria existenta a roiului (implicit /swarm/telemetry).
Nodurile tale (coordonator, GCS, drone_sim) NU se modifica — doar ruleaza
acest launch in paralel.

  ros2 launch mission_plugins.launch.py
  ros2 launch mission_plugins.launch.py profile:=urban_rubble seed:=7 \
      area:=40.0 pose_topic:=/swarm/telemetry
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration

HERE = os.path.dirname(os.path.abspath(__file__))


def generate_launch_description():
    area = LaunchConfiguration("area")            # semi-latura ariei [m]
    pose_topic = LaunchConfiguration("pose_topic")
    profile = LaunchConfiguration("profile")
    seed = LaunchConfiguration("seed")
    sensor_r = LaunchConfiguration("sensor_r")

    def node(script, *extra):
        return ExecuteProcess(
            cmd=["python3", os.path.join(HERE, script), "--ros-args",
                 *extra],
            output="screen")

    return LaunchDescription([
        DeclareLaunchArgument("area", default_value="30.0"),
        DeclareLaunchArgument("pose_topic", default_value="/swarm/telemetry"),
        DeclareLaunchArgument("profile", default_value="open_field"),
        DeclareLaunchArgument("seed", default_value="1"),
        DeclareLaunchArgument("sensor_r", default_value="6.0"),

        node("radio_link_node.py",
             "-p", ["pose_topic:=", pose_topic],
             "-p", ["profile:=", profile],
             "-p", ["seed:=", seed],
             "-p", "linkstate_topic:=/swarm/linkstate"),

        node("coverage_node.py",
             "-p", ["pose_topic:=", pose_topic],
             "-p", ["sensor_r:=", sensor_r],
             "-p", ["xmin:=-", area], "-p", ["xmax:=", area],
             "-p", ["ymin:=-", area], "-p", ["ymax:=", area]),

        node("victim_node.py",
             "-p", ["pose_topic:=", pose_topic],
             "-p", ["sensor_r:=", sensor_r],
             "-p", ["seed:=", seed],
             "-p", ["xmin:=-", area], "-p", ["xmax:=", area],
             "-p", ["ymin:=-", area], "-p", ["ymax:=", area]),

        node("battery_node.py",
             "-p", ["pose_topic:=", pose_topic],
             "-p", "state_topic:=/swarm/battery"),
    ])
