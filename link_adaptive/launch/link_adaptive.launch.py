#!/usr/bin/env python3
"""link_adaptive.launch.py - porneste stratul adaptiv (un singur nod).

Ruleaza in PARALEL cu roiul: masoara starea legaturii si publica politica pe
/link_adaptive/policy, pe care ceilalti noduri o consuma. Nu modifica nimic.

  ros2 launch link_adaptive link_adaptive.launch.py
  ros2 launch link_adaptive link_adaptive.launch.py \
      rtt_topic:=/operator/heartbeat telemetry_topic:=/sar/telemetry
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    rtt = LaunchConfiguration("rtt_topic")
    tele = LaunchConfiguration("telemetry_topic")
    return LaunchDescription([
        DeclareLaunchArgument("rtt_topic", default_value="/operator/heartbeat"),
        DeclareLaunchArgument("telemetry_topic", default_value="/sar/telemetry"),
        DeclareLaunchArgument("decide_hz", default_value="5.0"),
        DeclareLaunchArgument("min_dwell_s", default_value="2.0"),
        Node(package="link_adaptive", executable="link_adaptive_node",
             name="link_adaptive", output="screen",
             parameters=[{
                 "rtt_topic": ParameterValue(rtt, value_type=str),
                 "telemetry_topic": ParameterValue(tele, value_type=str),
                 "decide_hz": ParameterValue(LaunchConfiguration("decide_hz"), value_type=float),
                 "min_dwell_s": ParameterValue(LaunchConfiguration("min_dwell_s"), value_type=float),
             }]),
    ])
