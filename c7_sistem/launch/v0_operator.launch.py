"""v0_operator.launch.py -- ROLUL OPERATOR (P0-HIL): operator_node (C6) + agentul sondei C4 (ecou_node) + gateway-ul C3
(2 agenti + reflectorul sondei de canal + gateway). Ruleaza la statie (laptop). `pereche:=` = adresa roverului (reflectorul
sondei de canal C3 ruleaza AICI local in aceasta unitate; pe HIL el sta pe rover si `pereche` devine --reflector al gateway-ului).
`deviatie_s:=` injecteaza software o deviatie de ceas pe marcajele ecoului (experimentul de ceasuri); ceasul de sistem nu se atinge.
  ros2 launch c7_sistem v0_operator.launch.py rol:=operator pereche:=192.0.2.2 domain:=76 jurnal:=<dir> deviatie_s:=0.0
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, GroupAction, LogInfo, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PY = "/usr/bin/python3"
VENV = os.path.expanduser("~/ros2_ws/.venv_c6/bin/python")
C3 = os.path.expanduser("~/ros2_ws/src/c3_gateway")


def generate_launch_description():
    L = LaunchConfiguration
    A = [DeclareLaunchArgument("rol", default_value="operator"),
         DeclareLaunchArgument("pereche", default_value="127.0.0.1"),
         DeclareLaunchArgument("domain", default_value="76"),
         DeclareLaunchArgument("jurnal", default_value="/tmp/v0_operator_c3"),
         DeclareLaunchArgument("deviatie_s", default_value="0.0"),
         DeclareLaunchArgument("cu_gateway", default_value="true"),
         SetEnvironmentVariable("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp"),
         SetEnvironmentVariable("ROS_DOMAIN_ID", L("domain")),
         LogInfo(msg=["ROL=", L("rol"), " pereche(rover)=", L("pereche"), " domain=", L("domain")]),
         Node(package="c4_platforma", executable="ecou_node", name="c4_ecou_operator", output="screen",
              parameters=[{"deviatie_s": ParameterValue(L("deviatie_s"), value_type=float)}]),
         Node(package="c6_safety", executable="operator_node", name="c6_operator", output="screen", prefix=[VENV, " "],
              parameters=[{"scenariu": "traversare", "v_o_max": 0.5, "react": False, "f_haz": 5.0, "qos": "reliable"}])]
    GATEWAY = os.path.join(C3, "c3_gateway", "nodes", "gateway_node.py")
    AGENT = os.path.join(C3, "c3_gateway", "agent", "transport_agent.py")
    SONDA = os.path.join(C3, "c3_gateway", "sonda", "sonda_canal.py")
    from launch.conditions import IfCondition
    g = []
    g.append(ExecuteProcess(cmd=["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"], name="rmw_zenohd", output="screen"))
    for transport, rmw, canal in (("cyclonedds", "rmw_cyclonedds_cpp", "agent_cdds"), ("zenoh", "rmw_zenoh_cpp", "agent_zenoh")):
        g.append(GroupAction([SetEnvironmentVariable("RMW_IMPLEMENTATION", rmw),
                              ExecuteProcess(cmd=[PY, AGENT, "--canal", canal, "--rmw-asteptat", rmw, "--nume-nod", "c3_agent_%s" % transport],
                                             name="c3_agent_%s" % transport, output="screen")]))
    g.append(ExecuteProcess(cmd=[PY, SONDA, "--rol", "reflector", "--port", "47311"], name="c3_sonda_reflector", output="screen"))
    g.append(ExecuteProcess(cmd=[PY, GATEWAY, "--cale", "cyclonedds:agent_cdds", "--cale", "zenoh:agent_zenoh", "--topic", "/c3/app:4096",
                                 "--jurnal", L("jurnal"), "--eticheta", "operator", "--reflector", "127.0.0.1", "--port-sonda", "47311"],
                            name="c3_gateway", output="screen"))
    A.append(GroupAction(g, condition=IfCondition(L("cu_gateway"))))
    return LaunchDescription(A)
