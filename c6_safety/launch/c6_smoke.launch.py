"""c6_smoke.launch.py -- operator_node + rover_node pe lo, rmw_cyclonedds_cpp. S3.

  ros2 launch c6_safety c6_smoke.launch.py brat:=A2 seed:=1 outputs:=/dir eticheta:=x

Cele doua noduri ruleaza sub python-ul dat de `python:=` (implicit ~/ros2_ws/.venv_c6,
unde e osqp; pe /usr/bin/python3 nu e). RMW se seteaza GLOBAL (nu in GroupAction:
CLAUDE.md sec. 6). Launch-ul se OPRESTE cand rover_node iese (a scris fisierele).
"""
import os

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, RegisterEventHandler,
                            SetEnvironmentVariable)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

VENV = os.path.expanduser("~/ros2_ws/.venv_c6/bin/python")


def generate_launch_description():
    L = LaunchConfiguration
    arg = [DeclareLaunchArgument(k, default_value=v) for k, v in (
        ("brat", "A2"), ("scenariu", "traversare"), ("v_o_max", "0.5"), ("seed", "1"),
        ("react", "false"), ("f_haz", "5.0"), ("outputs", ""), ("eticheta", "s3"),
        ("rmw", "rmw_cyclonedds_cpp"), ("qos", "reliable"), ("mod_dt", "plafon"), ("dt_max_admis", "0.15"),
        ("python", VENV if os.path.exists(VENV) else ""))]
    prefix = [L("python"), " "]
    F = lambda k: ParameterValue(L(k), value_type=float)                  # noqa: E731
    B = lambda k: ParameterValue(L(k), value_type=bool)                   # noqa: E731
    op = Node(package="c6_safety", executable="operator_node", name="c6_operator", output="screen",
              prefix=prefix,
              parameters=[{"scenariu": L("scenariu"), "v_o_max": F("v_o_max"),
                           "react": B("react"), "f_haz": F("f_haz"), "qos": L("qos")}])
    rv = Node(package="c6_safety", executable="rover_node", name="c6_rover", output="screen",
              prefix=prefix,
              parameters=[{"brat": L("brat"), "scenariu": L("scenariu"), "v_o_max": F("v_o_max"),
                           "seed": ParameterValue(L("seed"), value_type=int), "react": B("react"),
                           "outputs": L("outputs"),
                           "eticheta": L("eticheta"), "qos": L("qos"), "mod_dt": L("mod_dt"),
                           "dt_max_admis": F("dt_max_admis")}])
    stop = RegisterEventHandler(OnProcessExit(target_action=rv, on_exit=[EmitEvent(event=Shutdown())]))
    return LaunchDescription(arg + [SetEnvironmentVariable("RMW_IMPLEMENTATION", L("rmw")), rv, op, stop])
