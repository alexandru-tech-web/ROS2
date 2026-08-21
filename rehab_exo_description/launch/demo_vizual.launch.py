#!/usr/bin/env python3
"""demo_vizual.launch.py -- modelul STATIC, cu slidere, pentru inspectie cu ochiul.

    ros2 launch rehab_exo_description demo_vizual.launch.py

Porneste DOAR robot_state_publisher + joint_state_publisher_gui + RViz. Fara Gazebo,
fara controlere, fara exercitii: nimic nu se misca decat daca tragi de un slider.
E modul in care se verifica GEOMETRIA, separat de dinamica; daca ceva arata gresit
aici, nu are rost sa se caute in fizica.

    postura:=culcat|sezut   ce set de limite au sliderele

ATENTIE la postura:=sezut. Banda ei e inca cea TRANSPORTATA mecanic din conventia
veche si cade integral sub orizontala (DECIZII.md, corectia 3). Modelul va arata
gresit acolo, DELIBERAT, pana la rejustificarea de la punctul 5. Pentru inspectia
geometriei, foloseste culcat.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rmw_common import argument_rmw, cu_rmw          # noqa: E402


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    xacro_src = os.path.join(pkg, "urdf", "rehab_exo.urdf.xacro")
    descriere = ParameterValue(
        Command(["xacro ", xacro_src,
                 " postura:=", LaunchConfiguration("postura"),
                 " controllers:=", os.path.join(pkg, "config", "controllers.yaml")]),
        value_type=str)

    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher",
               output="screen", parameters=[{"robot_description": descriere}])
    # POZA DE PORNIRE = postura de LUCRU, nu toate zerourile. La zero, genunchiul e
    # complet intins, deci piciorul iese orizontal in fata pe toata lungimea lui si
    # modelul arata sprawled, desi e o configuratie perfect legala. Cine deschide
    # fereastra ca sa verifice geometria trebuie sa vada intai postura in care
    # dispozitivul chiar sta: coapsa orizontala, gamba verticala, talpa pe suport.
    # Sold ramane 0 fiindca ZERO CHIAR E repausul in conventia B-prim.
    jsp = Node(package="joint_state_publisher_gui",
               executable="joint_state_publisher_gui", output="screen",
               parameters=[{"zeros.left_knee_joint": 1.5708,
                            "zeros.right_knee_joint": 1.5708}])
    rviz = Node(package="rviz2", executable="rviz2", output="screen",
                condition=IfCondition(LaunchConfiguration("rviz")),
                arguments=["-d", os.path.join(pkg, "rviz", "rehab.rviz")])

    return LaunchDescription([
        DeclareLaunchArgument("postura", default_value="culcat",
                              description="setul de limite al sliderelor"),
        DeclareLaunchArgument("rviz", default_value="true"),
        argument_rmw(),
        cu_rmw([rsp, jsp, rviz], "vizual", cu_gardian=False),
    ])
