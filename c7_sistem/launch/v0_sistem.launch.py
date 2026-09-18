"""v0_sistem.launch.py -- V0 (C7): toate piesele existente in ACELASI grafic ROS 2, loopback, fara degradare.

Ordinea pornirii (fiecare bloc = pachetele existente, neatinse; doar procese, remapari, parametri):
  0. rmw_zenohd (routerul zenoh; fara el calea zenoh a gateway-ului e moarta: c3_gateway/docs/SMOKE_TRAFIC_2026-09-02.md)
  1. c3_gateway: 2 agenti (cdds, zenoh, fiecare in RMW-ul lui) + reflectorul sondei (local) + gateway (procesele din
     c3_gateway.launch.py, replicate fara handler-ele lui OnProcessExit fara tinta) + un ecou per RMW (test/echo_node.py)
     + trafic de aplicatie pe /c3/app (test/app_pub.py, 50 Hz, 4096 B)
  2. c4: SUBSTITUT (c7_sistem/substitut_c4_node: /network_confidence = 1.0, /network_age = 0.0 constante) -- P0 e dupa 28.09
  3. c6_safety: operator_node + rover_node (A2, traversare, react=False), sub .venv_c6 (osqp); FARA handler-ul de Shutdown
     din c6_smoke.launch.py (rover_node iese singur la T_G ~16 s; graficul continua)
  4. sar_swarm (fara Gazebo): 4 drone (use_gazebo:=false) + GCS + injector (scenario none) + latency_probe
  5. mesh_plugin: mesh_plugins.launch.py ingest:=true (4 noduri mesh + GCS)
  6. teleop_rover (fara Gazebo): link_node + robot_node (use_gazebo:=false) + operator_node (mode pilot)
RMW pentru tot graficul (in afara agentului zenoh al gateway-ului): rmw_cyclonedds_cpp, setat GLOBAL; ROS_DOMAIN_ID=76 (izolare).
Interpretorul: /usr/bin/python3 (cel cu rclpy); pachetele-script folosesc 'python3' in launch-urile lor, care aici ar fi Anaconda.

  ros2 launch c7_sistem v0_sistem.launch.py jurnal:=<dir> [c6_outputs:=<dir>] [durata_app:=60]
"""
import os

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, GroupAction, IncludeLaunchDescription,
                            LogInfo, SetEnvironmentVariable, TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PY = "/usr/bin/python3"
SRC = os.path.expanduser("~/ros2_ws/src")
VENV = os.path.expanduser("~/ros2_ws/.venv_c6/bin/python")
C3 = os.path.join(SRC, "c3_gateway")
SAR = os.path.join(SRC, "sar_swarm")
TEL = os.path.join(SRC, "teleop_rover")
MESH_LAUNCH = os.path.join(SRC, "mesh_plugin", "launch", "mesh_plugins.launch.py")
C3_LAUNCH = os.path.join(C3, "launch", "c3_gateway.launch.py")
DRONES = {"d1": (3.5, 3.5), "d2": (3.5, 6.5), "d3": (6.5, 3.5), "d4": (6.5, 6.5)}   # sar_ros.launch.py:17


def generate_launch_description():
    L = LaunchConfiguration
    jurnal, c6_out, durata = L("jurnal"), L("c6_outputs"), L("durata_app")
    A = [DeclareLaunchArgument("jurnal", default_value="/tmp/v0_jurnal"),
         DeclareLaunchArgument("c6_outputs", default_value="/tmp/v0_c6"),
         DeclareLaunchArgument("durata_app", default_value="60"),
         DeclareLaunchArgument("mod_dt", default_value="max"),          # V0.1: "pas" | "max" (vezi cbf_core)
         SetEnvironmentVariable("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp"),
         # izolare: pe masina ruleaza si alte noduri (ex. /joint/*, /bench/*) in domain 0; V0 sta in domain 76
         SetEnvironmentVariable("ROS_DOMAIN_ID", "76"),
         LogInfo(msg="V0: graficul comun, loopback, fara degradare, rmw_cyclonedds_cpp global")]
    # 0. routerul zenoh
    A.append(ExecuteProcess(cmd=["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"], name="rmw_zenohd", output="screen"))
    # 1. c3_gateway: ACELEASI procese ca in c3_gateway.launch.py (agent per RMW, reflector local, gateway), replicate aici
    #    pentru ca launch-ul lui are handler-e OnProcessExit FARA tinta ("un agent a iesit -> opresc TOTUL"), care intr-un
    #    grafic comun se declanseaza la iesirea normala a oricarui alt proces (V0 smoke 1: rover_node C6 a iesit la T_G=14.6 s
    #    si a stins tot). Pachetul c3_gateway nu se modifica.
    GATEWAY = os.path.join(C3, "c3_gateway", "nodes", "gateway_node.py")
    AGENT = os.path.join(C3, "c3_gateway", "agent", "transport_agent.py")
    SONDA = os.path.join(C3, "c3_gateway", "sonda", "sonda_canal.py")
    c3 = []
    for transport, rmw, canal in (("cyclonedds", "rmw_cyclonedds_cpp", "agent_cdds"), ("zenoh", "rmw_zenoh_cpp", "agent_zenoh")):
        c3.append(GroupAction([SetEnvironmentVariable("RMW_IMPLEMENTATION", rmw),
                               ExecuteProcess(cmd=[PY, AGENT, "--canal", canal, "--rmw-asteptat", rmw, "--nume-nod", "c3_agent_%s" % transport],
                                              name="c3_agent_%s" % transport, output="screen")]))
    c3.append(ExecuteProcess(cmd=[PY, SONDA, "--rol", "reflector", "--port", "47311"], name="c3_sonda_reflector", output="screen"))
    c3.append(ExecuteProcess(cmd=[PY, GATEWAY, "--cale", "cyclonedds:agent_cdds", "--cale", "zenoh:agent_zenoh", "--topic", "/c3/app:4096",
                                  "--jurnal", jurnal, "--eticheta", "v0", "--reflector", "127.0.0.1", "--port-sonda", "47311"],
                             name="c3_gateway", output="screen"))
    for rmw, et in (("rmw_cyclonedds_cpp", "cdds"), ("rmw_zenoh_cpp", "zenoh")):
        c3.append(GroupAction([SetEnvironmentVariable("RMW_IMPLEMENTATION", rmw),
                               ExecuteProcess(cmd=[PY, os.path.join(C3, "test", "echo_node.py"), et], name="c3_echo_%s" % et, output="screen")]))
    c3.append(TimerAction(period=8.0, actions=[ExecuteProcess(cmd=[PY, os.path.join(C3, "test", "app_pub.py"), "50", "4096", durata],
                                                               name="c3_app_pub", output="screen")]))
    A.append(TimerAction(period=3.0, actions=c3))
    # 2. C4 SUBSTITUT
    A.append(Node(package="c7_sistem", executable="substitut_c4_node", name="c4_SUBSTITUT_nu_masuratoare", output="screen"))
    # 3. c6_safety (aceleasi doua noduri ca in c6_smoke.launch.py, fara Shutdown la iesirea roverului)
    pref = [VENV, " "]
    F = lambda k, v: ParameterValue(v, value_type=k)                      # noqa: E731
    A.append(Node(package="c6_safety", executable="rover_node", name="c6_rover", output="screen", prefix=pref,
                  parameters=[{"brat": "A2", "scenariu": "traversare", "v_o_max": 0.5, "seed": 1, "react": False,
                               "outputs": c6_out, "eticheta": "v0_A2", "qos": "reliable", "mod_dt": L("mod_dt")}]))
    A.append(Node(package="c6_safety", executable="operator_node", name="c6_operator", output="screen", prefix=pref,
                  parameters=[{"scenariu": "traversare", "v_o_max": 0.5, "react": False, "f_haz": 5.0, "qos": "reliable"}]))
    # 4. sar_swarm fara Gazebo (ca sar_ros.launch.py, dar cu interpretorul ROS)
    for d, (x, y) in DRONES.items():
        A.append(ExecuteProcess(cmd=[PY, os.path.join(SAR, "drone_node.py"), "--ros-args", "-p", "id:=%s" % d, "-p", "x0:=%s" % x,
                                     "-p", "y0:=%s" % y, "-p", "use_gazebo:=false"], name="sar_drone_%s" % d, output="screen"))
    A.append(ExecuteProcess(cmd=[PY, os.path.join(SAR, "gcs_node_ros.py"), "--ros-args", "-p", "autostart:=true"], name="sar_gcs", output="screen"))
    A.append(ExecuteProcess(cmd=[PY, os.path.join(SAR, "fault_injector_node.py"), "--ros-args", "-p", "scenario:=none"], name="sar_injector", output="screen"))
    A.append(ExecuteProcess(cmd=[PY, os.path.join(SAR, "latency_probe.py")], name="sar_probe", output="screen"))
    # 5. mesh_plugin (launch-ul lui, neatins) + puntea de telemetrie (V0.1): /sar/telemetry -> /sar/telemetry/<id> (ingest per drona);
    #    egress-ul mesh-ului merge pe /sar/telemetry_mesh, altfel GCS-ul mesh ar republica pe /sar/telemetry si puntea ar face bucla
    A.append(Node(package="c7_sistem", executable="punte_telemetrie", name="punte_telemetrie", output="screen"))
    A.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(MESH_LAUNCH),
                                      launch_arguments={"ingest": "true", "egress_topic": "/sar/telemetry_mesh"}.items()))
    # 6. teleop_rover fara Gazebo (ca teleop.launch.py, cu interpretorul ROS)
    A.append(ExecuteProcess(cmd=[PY, os.path.join(TEL, "link_node.py"), "--ros-args", "-p", "lat_ms:=0.0", "-p", "jit_ms:=0.0", "-p", "loss:=0.0"],
                            name="teleop_link", output="screen"))
    A.append(ExecuteProcess(cmd=[PY, os.path.join(TEL, "robot_node.py"), "--ros-args", "-p", "use_gazebo:=false"], name="teleop_robot", output="screen"))
    A.append(ExecuteProcess(cmd=[PY, os.path.join(TEL, "operator_node.py"), "--ros-args", "-p", "mode:=pilot"], name="teleop_operator", output="screen"))
    return LaunchDescription(A)
