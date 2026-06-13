#!/usr/bin/env python3
"""link_adaptive_loop.launch.py - bucla C3 completa: decizie + aplicare.

Porneste impreuna:
  - link_adaptive_node  : masoara legatura (RTT + pierdere) si publica /link_adaptive/policy;
  - policy_adapter_node : sta in calea telemetriei (in_topic -> out_topic) si aplica politica.

Ruleaza in PARALEL cu roiul. Atasare fara cod nou: remapeaza iesirea de
telemetrie a dronelor catre in_topic (raw), iar GCS citeste out_topic ca inainte:
  drone_node ... -r /sar/telemetry:=/sar/telemetry/raw

  ros2 launch link_adaptive link_adaptive_loop.launch.py
  ros2 launch link_adaptive link_adaptive_loop.launch.py \
      rtt_topic:=/operator/heartbeat in_topic:=/sar/telemetry/raw out_topic:=/sar/telemetry
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    rtt = LaunchConfiguration("rtt_topic")
    in_t = LaunchConfiguration("in_topic")
    out_t = LaunchConfiguration("out_topic")
    stamp = LaunchConfiguration("stamp_field")
    s = lambda v: ParameterValue(v, value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument("rtt_topic", default_value="/operator/heartbeat"),
        DeclareLaunchArgument("in_topic", default_value="/sar/telemetry/raw"),
        DeclareLaunchArgument("out_topic", default_value="/sar/telemetry"),
        DeclareLaunchArgument("stamp_field", default_value="",
                              description="camp de timestamp (ceas perete) pt aruncarea pe vechime; gol = dezactivat"),
        # decide: monitorizeaza RTT + pierderea pe fluxul brut produs de drone
        Node(package="link_adaptive", executable="link_adaptive_node",
             name="link_adaptive", output="screen",
             parameters=[{"rtt_topic": s(rtt), "telemetry_topic": s(in_t)}]),
        # aplica: throttle + staleness + payload + QoS pe calea telemetriei
        Node(package="link_adaptive", executable="policy_adapter_node",
             name="policy_adapter", output="screen",
             parameters=[{"in_topic": s(in_t), "out_topic": s(out_t),
                          "policy_topic": "/link_adaptive/policy",
                          "stamp_field": s(stamp)}]),
    ])
