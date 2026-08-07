"""c3_gateway.launch.py -- gateway + doi agenti, fiecare pe RMW-ul lui.

TIPARUL e cel VALIDAT la etapa 1c: SetEnvironmentVariable in interiorul unui GroupAction.
Masurat atunci, cu un martor in afara grupurilor: fiecare proces primeste exact RMW-ul
grupului lui, iar valoarea nu se scurge nici intre grupuri, nici in afara.

ESECUL E ZGOMOTOS, in doua straturi:
  1. fiecare agent primeste --rmw-asteptat si IESE cu cod nenul daca
     rclpy.get_rmw_implementation_identifier() nu se potriveste;
  2. aici, OnProcessExit opreste TOT daca vreun agent moare -- inclusiv la pornire.
Un agent care ruleaza pe alt transport decat crede lansatorul ar falsifica toata campania
fara sa scoata un sunet; de aceea nu exista varianta 'logam un avertisment si continuam'.

Cablajul (ce transport merge pe ce canal UDS) se da AICI, nu in nod: nodul isi valideaza
caile fata de tabela de politica si nu are voie sa stie ce transporturi exista.

Uz:
  ros2 launch c3_gateway c3_gateway.launch.py jurnal:=/tmp/rulare1 eticheta:=ge_15_8
"""
import os

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, ExecuteProcess, GroupAction,
                            LogInfo, RegisterEventHandler, SetEnvironmentVariable)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration

PACHET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(PACHET, "c3_gateway", "agent", "transport_agent.py")
GATEWAY = os.path.join(PACHET, "c3_gateway", "nodes", "gateway_node.py")
PY = "/usr/bin/python3"          # interpretorul ROS (3.12); 'python3' e Anaconda si nu are rclpy

CAI = (("cyclonedds", "rmw_cyclonedds_cpp", "agent_cdds"),
       ("zenoh", "rmw_zenoh_cpp", "agent_zenoh"))


def _agent(transport, rmw, canal):
    """Un agent, in grupul lui, cu mediul lui. GroupAction e scoped implicit.
    Topicurile sunt ACELEASI pentru ambii agenti (implicitele /c3/tx si /c3/rx):
    izolarea nu vine din nume diferite, ci din RMW-uri diferite -- si asa se poate
    si VERIFICA, fiindca o scurgere ar aparea imediat ca mesaje in plus la ecou."""
    return GroupAction([
        SetEnvironmentVariable("RMW_IMPLEMENTATION", rmw),
        ExecuteProcess(
            cmd=[PY, AGENT,
                 "--canal", canal,
                 "--rmw-asteptat", rmw,
                 "--nume-nod", "c3_agent_%s" % transport],
            name="agent_%s" % transport, output="screen"),
    ])


def generate_launch_description():
    jurnal = LaunchConfiguration("jurnal")
    eticheta = LaunchConfiguration("eticheta")
    topic = LaunchConfiguration("topic")

    gateway = ExecuteProcess(
        cmd=[PY, GATEWAY,
             "--cale", "%s:%s" % (CAI[0][0], CAI[0][2]),
             "--cale", "%s:%s" % (CAI[1][0], CAI[1][2]),
             "--topic", topic,
             "--jurnal", jurnal,
             "--eticheta", eticheta],
        name="c3_gateway", output="screen")

    actiuni = [
        DeclareLaunchArgument("jurnal", default_value="/tmp/c3_rulare",
                              description="director pentru jurnalul per-esantion"),
        DeclareLaunchArgument("eticheta", default_value="rulare",
                              description="eticheta rularii (ex. numele conditiei netem)"),
        DeclareLaunchArgument("topic", default_value="/c3/app:4096",
                              description="'nume:payload_nominal' -- decizia e per topic"),
        LogInfo(msg="C3: pornesc gateway + 2 agenti (cyclonedds, zenoh)"),
    ]
    actiuni += [_agent(*c) for c in CAI]
    actiuni.append(gateway)

    # daca ORICE proces moare, cade tot: o rulare cu un singur agent ar produce date care
    # arata valid dar nu sunt (calea 'de rezerva' nu ar exista, iar sonda ar tacea)
    for transport, _, _ in CAI:
        actiuni.append(RegisterEventHandler(OnProcessExit(
            on_exit=[LogInfo(msg="EROARE: agentul %s a iesit -- opresc TOTUL, rularea "
                                 "nu mai e valida" % transport),
                     EmitEvent(event=Shutdown(reason="agent %s a iesit" % transport))])))
    return LaunchDescription(actiuni)
