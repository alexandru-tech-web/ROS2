#!/usr/bin/env python3
"""Porneste geamanul digital complet dintr-o singura comanda.

Componente:
  * simulatorul celor trei perechi;
  * filtrarea encoderelor si publicarea cinematicii;
  * Gazebo (GUI implicit, server-only cu ``gui:=false``);
  * bridge-ul ROS -> Gazebo si oglinda pozitiilor;
  * panoul operatorului cu slidere, ESTOP si grafice.

Gazebo este numai vizualizarea starii calculate de emulator. Inchiderea
Gazebo opreste intregul launch, inclusiv emulatorul.
"""
import os
import sys
from datetime import datetime, timezone

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, ExecuteProcess,
                            RegisterEventHandler)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_ENV = {"PYTHONDONTWRITEBYTECODE": "1"}


def python_node(script, *ros_arguments, condition=None):
    return ExecuteProcess(
        cmd=[sys.executable, os.path.join(PKG, "nodes", script),
             *ros_arguments],
        additional_env=PYTHON_ENV,
        condition=condition,
        output="screen",
    )


def generate_launch_description():
    gui = LaunchConfiguration("gui")
    hmi = LaunchConfiguration("hmi")
    adaptive = LaunchConfiguration("adaptive")
    rate_hz = LaunchConfiguration("rate_hz")
    state_hz = LaunchConfiguration("state_hz")
    reaction_mode = LaunchConfiguration("reaction_mode")
    contact_angle_deg = LaunchConfiguration("contact_angle_deg")
    data_dir = LaunchConfiguration("data_dir")
    session_id = LaunchConfiguration("session_id")

    emulator = python_node(
        "emulator_node.py",
        "--ros-args",
        "-p", ["adaptive:=", adaptive],
        "-p", ["rate_hz:=", rate_hz],
        "-p", ["state_hz:=", state_hz],
        "-p", ["reaction_mode:=", reaction_mode],
        "-p", ["contact_angle_deg:=", contact_angle_deg],
        "-p", ["data_dir:=", data_dir],
        "-p", ["session_id:=", session_id],
    )
    encoder = python_node("encoder_monitor_node.py", "--ros-args",
                          "-p", ["data_dir:=", data_dir],
                          "-p", ["session_id:=", session_id])
    mirror = python_node("gz_mirror_node.py")
    panel = python_node("operator_panel_node.py", "--ros-args",
                        "-p", ["data_dir:=", data_dir],
                        "-p", ["session_id:=", session_id],
                        condition=IfCondition(hmi))

    world = os.path.join(PKG, "gz", "joint_bench_world.sdf")
    gazebo_gui = ExecuteProcess(
        cmd=["gz", "sim", "-r", world],
        condition=IfCondition(gui),
        output="screen",
    )
    gazebo_server = ExecuteProcess(
        cmd=["gz", "sim", "-s", "-r", world],
        condition=UnlessCondition(gui),
        output="screen",
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="joint_gz_bridge",
        parameters=[{"config_file": os.path.join(PKG, "gz",
                                                   "bridge_bench.yaml")}],
        output="screen",
    )

    stop_on_gui_exit = RegisterEventHandler(OnProcessExit(
        target_action=gazebo_gui,
        on_exit=[EmitEvent(event=Shutdown(reason="Gazebo a fost inchis"))],
    ))
    stop_on_server_exit = RegisterEventHandler(OnProcessExit(
        target_action=gazebo_server,
        on_exit=[EmitEvent(event=Shutdown(reason="Gazebo server s-a oprit"))],
    ))

    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true",
                              description="Deschide fereastra Gazebo"),
        DeclareLaunchArgument("hmi", default_value="true",
                              description="Deschide panoul cu slidere si grafice"),
        DeclareLaunchArgument(
            "adaptive", default_value="true",
            description=("Foloseste impedanta adaptiva (recomandat cand "
                         "latenta este modificata din HMI)")),
        DeclareLaunchArgument("rate_hz", default_value="200.0"),
        DeclareLaunchArgument("state_hz", default_value="20.0"),
        DeclareLaunchArgument("reaction_mode", default_value="impedance",
                              description="impedance sau contact local"),
        DeclareLaunchArgument("contact_angle_deg", default_value="5.0",
                              description="Pragul bilateral al contactului SIM"),
        DeclareLaunchArgument("data_dir",
                              default_value="/home/ubuntu/Analiza_Teza/ViPRO/DATE",
                              description="Directorul pentru export si jurnale CSV"),
        DeclareLaunchArgument(
            "session_id",
            default_value=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
            description="Identificator comun pentru CSV si Excel"),
        gazebo_gui,
        gazebo_server,
        bridge,
        emulator,
        encoder,
        mirror,
        panel,
        stop_on_gui_exit,
        stop_on_server_exit,
    ])
