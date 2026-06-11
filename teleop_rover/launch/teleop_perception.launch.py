#!/usr/bin/env python3
"""teleop_perception.launch.py — roverul cu 4 ROTI pe TEREN ACCIDENTAT in Gazebo,
cu CAMERA + recunoastere de obiecte + navigare go-to-goal, sub RMW la alegere
(Zenoh sau Cyclone). Metrica de teza: navigarea autonoma sub middleware degradat.

Lant:
  gz sim (lumea rough)
    -> ros_gz_bridge (cmd_vel, odometrie, lidar) + ros_gz_image (camera -> compressed)
    -> link_node (legatura degradata) -> robot_node (use_gazebo, SafetyGate, jurnal)
    -> detector_node (HSV -> /teleop/target) -> goto_node (drop-in operator -> /teleop/cmd)

Pregatire (o data):
    python3 gen_rough_world.py

Rulare:
    ros2 launch ./launch/teleop_perception.launch.py rmw:=zenoh \\
        goal_source:=object target_class:=red lat:=200 jit:=40
    # sau, tinta fixa:
    ros2 launch ./launch/teleop_perception.launch.py rmw:=cyclone \\
        goal_source:=waypoint goal_x:=8 goal_y:=3

Note:
  - rmw:=zenoh porneste si routerul `rmw_zenohd` (oprit automat la inchidere);
  - camera gz publica pe topicul "camera/image"; ros_gz_image image_bridge produce
    /camera/image (Image) si /camera/image/compressed (CompressedImage), pe care le
    consuma detector_node;
  - daca topicurile gz apar prefixate (/world/.../scan), verifica cu `gz topic -l`.
"""
import os

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            OpaqueFunction, TimerAction)
from launch.substitutions import LaunchConfiguration

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def setup(context, *a, **k):
    val = lambda n: LaunchConfiguration(n).perform(context)
    rmw = val("rmw")
    impl = "rmw_zenoh_cpp" if rmw == "zenoh" else "rmw_cyclonedds_cpp"
    env = {"RMW_IMPLEMENTATION": impl}
    world = os.path.join(PKG, "worlds", "teleop_rough.sdf")

    def ros(*cmd):
        return ExecuteProcess(cmd=list(cmd), output="screen", additional_env=env)

    early = []
    if rmw == "zenoh":                      # routerul TREBUIE inainte de noduri
        early.append(ros("ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"))
    early.append(ExecuteProcess(cmd=["gz", "sim", "-r", world], output="screen"))

    # bridge-uri + noduri, pornite dupa ce gz/routerul s-au asezat (3 s)
    delayed = TimerAction(period=3.0, actions=[
        ros("ros2", "run", "ros_gz_bridge", "parameter_bridge",
            "/model/rover/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
            "/model/rover/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan"),
        ros("ros2", "run", "ros_gz_image", "image_bridge", "camera/image"),
        ros("python3", os.path.join(PKG, "link_node.py"), "--ros-args",
            "-p", f"lat_ms:={val('lat')}", "-p", f"jit_ms:={val('jit')}",
            "-p", f"loss:={val('loss')}"),
        ros("python3", os.path.join(PKG, "robot_node.py"), "--ros-args",
            "-p", "use_gazebo:=true"),
        ros("python3", os.path.join(PKG, "detector_node.py"), "--ros-args",
            "-p", "scan_topic:=/scan", "-p", f"target_class:={val('target_class')}"),
        ros("python3", os.path.join(PKG, "goto_node.py"), "--ros-args",
            "-p", f"goal_source:={val('goal_source')}",
            "-p", f"goal_x:={val('goal_x')}", "-p", f"goal_y:={val('goal_y')}",
            "-p", f"target_class:={val('target_class')}"),
    ])
    return early + [delayed]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("rmw", default_value="cyclone",
                              description="cyclone | zenoh"),
        DeclareLaunchArgument("goal_source", default_value="object",
                              description="object | waypoint"),
        DeclareLaunchArgument("goal_x", default_value="8.0"),
        DeclareLaunchArgument("goal_y", default_value="3.0"),
        DeclareLaunchArgument("target_class", default_value="red"),
        DeclareLaunchArgument("lat", default_value="0.0"),
        DeclareLaunchArgument("jit", default_value="0.0"),
        DeclareLaunchArgument("loss", default_value="0.0"),
        OpaqueFunction(function=setup),
    ])
