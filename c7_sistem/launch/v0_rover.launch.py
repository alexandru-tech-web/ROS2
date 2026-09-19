"""v0_rover.launch.py -- ROLUL ROVER (P0-HIL): nodul de rover + filtrul C6 + semnalele C4 (confidence_node: /network_confidence, /network_age).
Ruleaza pe masina roverului (in octombrie: Pi). Nimic hardcodat pe 'aceeasi masina': descoperirea e DDS (cyclonedds, multicast/unicast pe
ROS_DOMAIN_ID); `pereche:=` e adresa operatorului (folosita in log si, pentru unicast fara multicast, de CYCLONEDDS_URI din checklist).
  ros2 launch c7_sistem v0_rover.launch.py rol:=rover pereche:=192.0.2.1 domain:=76 c6_outputs:=<dir> jurnal_c4:=<csv>
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

VENV = os.path.expanduser("~/ros2_ws/.venv_c6/bin/python")


def generate_launch_description():
    L = LaunchConfiguration
    return LaunchDescription([
        DeclareLaunchArgument("rol", default_value="rover"),
        DeclareLaunchArgument("pereche", default_value="127.0.0.1"),
        DeclareLaunchArgument("domain", default_value="76"),
        DeclareLaunchArgument("c6_outputs", default_value="/tmp/v0_rover_c6"),
        DeclareLaunchArgument("jurnal_c4", default_value=""),
        DeclareLaunchArgument("mod_dt", default_value="max"),
        SetEnvironmentVariable("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp"),
        SetEnvironmentVariable("ROS_DOMAIN_ID", L("domain")),
        LogInfo(msg=["ROL=", L("rol"), " pereche(operator)=", L("pereche"), " domain=", L("domain")]),
        Node(package="c4_platforma", executable="confidence_node", name="c4_confidence_rover", output="screen",
             parameters=[{"T_dead": 0.25, "W": 20, "hz": 10.0, "jurnal": L("jurnal_c4")}]),
        Node(package="c6_safety", executable="rover_node", name="c6_rover", output="screen", prefix=[VENV, " "],
             parameters=[{"brat": "A2", "scenariu": "traversare", "v_o_max": 0.5, "seed": 1, "react": False,
                          "outputs": L("c6_outputs"), "eticheta": "rover_A2", "qos": "reliable", "mod_dt": L("mod_dt")}]),
    ])
