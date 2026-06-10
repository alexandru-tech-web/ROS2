#!/usr/bin/env python3
"""
exercitii_combinat.launch.py — Sesiunea COMBINATA: val coordonat + mars + extensie completa (61 s)
Ruleaza intreaga sesiune (RViz + controler) dintr-o singura comanda:
    $ ros2 launch rehab_exo_description exercitii_combinat.launch.py
    $ ros2 launch rehab_exo_description exercitii_combinat.launch.py reps:=2   # repeta sesiunea de 2 ori
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    demo = os.path.join(pkg, "launch", "demo_all.launch.py")
    reps_arg = DeclareLaunchArgument("reps", default_value="1",
                                     description="De cate ori se repeta sesiunea")
    return LaunchDescription([
        reps_arg,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(demo),
            launch_arguments={
                "exercise": "combined_session",
                "reps": LaunchConfiguration("reps"),
            }.items(),
        ),
    ])
