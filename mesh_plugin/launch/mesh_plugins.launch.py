#!/usr/bin/env python3
"""mesh_plugins.launch.py - porneste stratul mesh peste roi.

Cate un mesh_node per drona (d1..dN) + unul pentru GCS (cu pozitie fixa, ca
sa-si emita beacon-ul si sa fie gasit ca sink). Ruleaza in PARALEL cu roiul
existent (drone_node, gcs_node) fara sa le modifice.

  ros2 launch mesh_plugin mesh_plugins.launch.py
  ros2 launch mesh_plugin mesh_plugins.launch.py path_loss_n:=3.5
  # cu transport de telemetrie prin mesh (integrare in roi):
  ros2 launch mesh_plugin mesh_plugins.launch.py ingest:=true \
      ingest_prefix:=/sar/telemetry/ egress_topic:=/sar/telemetry

Pentru a schimba numarul/numele dronelor, editeaza lista DRONES de mai jos.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# dronele din roi (acelasi set ca scenariile sar_swarm)
DRONES = ["d1", "d2", "d3", "d4"]
GCS_ID = "GCS"
POSE_PREFIX = "/sar/pose/"
INGEST_PREFIX = "/sar/telemetry/"


def _f(name):
    return ParameterValue(LaunchConfiguration(name), value_type=float)


def generate_launch_description():
    ingest = LaunchConfiguration("ingest")
    egress_topic = LaunchConfiguration("egress_topic")

    radio = {
        "gcs": GCS_ID,
        "tx_dbm": _f("tx_dbm"),
        "path_loss_n": _f("path_loss_n"),
        "sens_dbm": _f("sens_dbm"),
        "width_db": _f("width_db"),
        "pdr_min": _f("pdr_min"),
        "relay_ttl": ParameterValue(LaunchConfiguration("relay_ttl"), value_type=int),
    }

    nodes = []
    # un nod per drona
    for d in DRONES:
        params = dict(radio)
        params.update({
            "id": d,
            "pose_topic": POSE_PREFIX + d,
            "ingest": ParameterValue(ingest, value_type=bool),
            "ingest_topic": INGEST_PREFIX + d,
        })
        nodes.append(Node(package="mesh_plugin", executable="mesh_node",
                          name=f"mesh_{d}", output="screen", parameters=[params]))
    # nodul GCS: pozitie fixa, republica telemetria livrata pe egress_topic
    gcs_params = dict(radio)
    gcs_params.update({
        "id": GCS_ID,
        "static_x": _f("gcs_x"),
        "static_y": _f("gcs_y"),
        "egress_topic": ParameterValue(egress_topic, value_type=str),
    })
    nodes.append(Node(package="mesh_plugin", executable="mesh_node",
                      name="mesh_gcs", output="screen", parameters=[gcs_params]))

    return LaunchDescription([
        DeclareLaunchArgument("ingest", default_value="false",
                              description="true = transporta telemetria dronelor prin mesh"),
        DeclareLaunchArgument("egress_topic", default_value="/sar/telemetry",
                              description="unde republica GCS telemetria livrata"),
        DeclareLaunchArgument("gcs_x", default_value="0.0"),
        DeclareLaunchArgument("gcs_y", default_value="0.0"),
        DeclareLaunchArgument("tx_dbm", default_value="0.0"),
        DeclareLaunchArgument("path_loss_n", default_value="3.0"),
        DeclareLaunchArgument("sens_dbm", default_value="-40.0"),
        DeclareLaunchArgument("width_db", default_value="3.0"),
        DeclareLaunchArgument("pdr_min", default_value="0.10"),
        DeclareLaunchArgument("relay_ttl", default_value="8"),
        *nodes,
    ])
