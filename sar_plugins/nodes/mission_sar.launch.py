#!/usr/bin/env python3
"""mission_sar.launch.py — etajul de misiune cuplat la GENERATIA NOUA a
roiului (sar_swarm, topicuri /sar/*).

Telemetria intra de pe /sar/telemetry; linkstate-ul iese pe /sar/linkstate.
ATENTIE: /sar/linkstate trebuie sa aiba UN SINGUR publisher — porneste
acest launch DOAR cand vrei degradare dependenta de distanta, in locul
scenariilor statice (sau cu scenariul "baseline" in sar_launcher).

  ros2 launch mission_sar.launch.py profile:=urban_rubble seed:=42
"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration

HERE = os.path.dirname(os.path.abspath(__file__))


def generate_launch_description():
    profile = LaunchConfiguration("profile")
    seed = LaunchConfiguration("seed")
    n_vict = LaunchConfiguration("n_victims")
    sensor_r = LaunchConfiguration("sensor_r")

    def node(script, *params):
        cmd = ["python3", os.path.join(HERE, script), "--ros-args"]
        for p in params:
            cmd += ["-p", p]
        return ExecuteProcess(cmd=cmd, output="screen")

    return LaunchDescription([
        DeclareLaunchArgument("profile", default_value="open_field"),
        DeclareLaunchArgument("seed", default_value="42"),
        DeclareLaunchArgument("n_victims", default_value="6"),
        DeclareLaunchArgument("sensor_r", default_value="6.0"),

        node("radio_link_node.py",
             ["profile:=", profile], ["seed:=", seed],
             "pose_topic:=/sar/telemetry",
             "linkstate_topic:=/sar/linkstate"),

        node("coverage_node.py",
             "xmin:=-5.0", "xmax:=65.0", "ymin:=-5.0", "ymax:=65.0",
             ["sensor_r:=", sensor_r],
             "pose_topic:=/sar/telemetry"),

        node("victim_node.py",
             ["n:=", n_vict], ["seed:=", seed],
             "xmin:=0.0", "xmax:=60.0", "ymin:=0.0", "ymax:=60.0",
             ["sensor_r:=", sensor_r],
             "pose_topic:=/sar/telemetry"),

        node("battery_node.py",
             "pose_topic:=/sar/telemetry",
             "state_topic:=/sar/battery",
             "failsafe_cmd_topic:=/sar/failsafe",
             'failsafe_template:={"id":"%ID%","action":"%STATE%"}'),
    ])
