#!/usr/bin/env python3
"""teleop_addons.launch.py — add-on-urile de teleoperare pentru rover.

Insereaza in lantul existent, FARA modificari de cod:
  garda:      /teleop/cmd  ->  [guard + /scan]  ->  /teleop/cmd_safe
  predictiv:  /teleop/pose + /teleop/cmd        ->  /teleop/pose_pred
  video:      /camera/image/compressed -> [link degradat] -> /teleop/video

Singura schimbare in sistemul tau: robot_node asculta /teleop/cmd_safe in
loc de /teleop/cmd (remapare in launch-ul lui sau parametrul de topic).

  ros2 launch teleop_addons.launch.py
  ros2 launch teleop_addons.launch.py d_stop:=0.8 guard_msg:=json
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration

HERE = os.path.dirname(os.path.abspath(__file__))


def generate_launch_description():
    d_stop = LaunchConfiguration("d_stop")
    d_slow = LaunchConfiguration("d_slow")
    guard_msg = LaunchConfiguration("guard_msg")
    linkstate = LaunchConfiguration("linkstate")

    def node(script, *extra):
        return ExecuteProcess(
            cmd=["python3", os.path.join(HERE, script), "--ros-args",
                 *extra],
            output="screen")

    return LaunchDescription([
        DeclareLaunchArgument("d_stop", default_value="0.6"),
        DeclareLaunchArgument("d_slow", default_value="1.5"),
        DeclareLaunchArgument("guard_msg", default_value="json"),
        DeclareLaunchArgument("linkstate",
                              default_value="/teleop/linkstate"),

        node("obstacle_guard_node.py",
             "-p", "in_topic:=/teleop/cmd",
             "-p", "out_topic:=/teleop/cmd_safe",
             "-p", "scan_topic:=/scan",
             "-p", ["msg:=", guard_msg],
             "-p", ["d_stop:=", d_stop],
             "-p", ["d_slow:=", d_slow]),

        node("predictive_display_node.py",
             "-p", "pose_topic:=/teleop/pose",
             "-p", "cmd_topic:=/teleop/cmd",
             "-p", "pred_topic:=/teleop/pose_pred"),

        node("video_link_node.py",
             "-p", "in_topic:=/camera/image/compressed",
             "-p", "out_topic:=/teleop/video",
             "-p", ["linkstate_topic:=", linkstate]),
    ])
