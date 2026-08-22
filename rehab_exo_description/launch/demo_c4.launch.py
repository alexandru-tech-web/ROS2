#!/usr/bin/env python3
"""demo_c4.launch.py -- demonstratia C4 intr-o singura comanda.

    ros2 launch rehab_exo_description demo_c4.launch.py
    ros2 launch rehab_exo_description demo_c4.launch.py exercitiu:=knee_extension viteza:=1.5

Porneste, in ordinea in care dependentele o cer:
  Gazebo headless -> robot_state_publisher -> spawn -> joint_state_broadcaster ->
  homing -> leg_trajectory_controller -> adjust_position_controller ->
  senzori sintetici + playerul de exercitii + tabloul de monitorizare la 2 Hz.

DE CE HEADLESS: 'gz sim gui' moare pe masina asta cu symbol lookup error pe
biblioteci scurse din snap-ul VSCode, si ia serverul cu el. Fizica ruleaza si fara
GUI; ce se vede e tabloul din terminal, cu pozitia ceruta, cea masurata si eroarea
de urmarire pe fiecare articulatie. gui:=true merge dintr-un terminal normal.

CE E REAL SI CE NU, ca sa nu se creada altceva la o demonstratie:
  REAL      -- cinematica, limitele articulare, lantul ros2_control, urmarirea de
               traiectorie masurata in Gazebo.
  SINTETIC  -- toti senzorii (cuplu, forta 6D, unghi de glezna, rigla de gamba).
               Vin din senzori_core cu model declarat; eticheta lor circula pe
               /rehab/senzori/eticheta si apare in fiecare cadru al tabloului.
  PLACEHOLDER -- masele si inertiile. Deci NICIO concluzie dinamica.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch.substitutions import (Command, LaunchConfiguration,
                                  PathJoinSubstitution, PythonExpression)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rmw_common import argument_rmw, cu_rmw, gardian_in_lant   # noqa: E402


def generate_launch_description():
    pkg = get_package_share_directory("rehab_exo_description")
    urdf_path = os.path.join(pkg, "urdf", "rehab_exo.urdf")
    robot_description = ParameterValue(Command(["xacro ", urdf_path]), value_type=str)

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"),
                                  "launch", "gz_sim.launch.py"])]),
        launch_arguments={"gz_args": PythonExpression(
            ["'-r empty.sdf' if '", LaunchConfiguration("gui"),
             "'.lower() in ('true', '1') else '-s -r empty.sdf'"])}.items(),
    )

    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher",
               output="screen",
               parameters=[{"robot_description": robot_description,
                            "use_sim_time": True}])

    clock_bridge = Node(package="ros_gz_bridge", executable="parameter_bridge",
                        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
                        output="screen")

    spawn = Node(package="ros_gz_sim", executable="create", output="screen",
                 # -z: robotul se ridica de la podea. Fara asta talpile intra in
                 # planul solului si contactul tine genunchiul flectat peste tinta,
                 # cu o eroare care NU raspunde la castig (masurat: 0.153 rad
                 # identic la castig 15 si la 100) si cu ~69 Nm de cuplu inutil.
                 arguments=["-topic", "robot_description", "-name", "rehab_exo",
                            "-z", LaunchConfiguration("inaltime")],
                 parameters=[{"use_sim_time": True}])

    def spawner(nume):
        return Node(package="controller_manager", executable="spawner",
                    output="screen",
                    arguments=[nume, "--controller-manager-timeout", "60"])

    jsb, traj, adjust = spawner("joint_state_broadcaster"), \
        spawner("leg_trajectory_controller"), spawner("adjust_position_controller")

    homing = Node(package="rehab_exo_description", executable="homing_node.py",
                  output="screen", parameters=[{"use_sim_time": True}])

    senzori = Node(package="rehab_exo_description", executable="senzori_node.py",
                   output="screen", parameters=[{"use_sim_time": True}])

    exercitiu = Node(
        package="rehab_exo_description", executable="exercise_controller.py",
        output="screen",
        parameters=[{"backend": "trajectory",
                     "exercise": LaunchConfiguration("exercitiu"),
                     "viteza": LaunchConfiguration("viteza"),
                     "reps": LaunchConfiguration("repetari"),
                     "use_sim_time": True}])

    # Stratul ELECTRIC de siguranta: praguri de POZITIE sub cele mecanice, cu armare
    # per articulatie. Porneste implicit; supervizor:=false doar pentru a ARATA ce se
    # intampla fara el (controlul negativ din raportul zilei 3).
    supervizor = Node(
        package="rehab_exo_description", executable="supervizor_electric.py",
        output="screen", condition=IfCondition(LaunchConfiguration("supervizor")),
        parameters=[{"marja_jos_deg": LaunchConfiguration("marja_jos_deg"),
                     "marja_sus_deg": LaunchConfiguration("marja_sus_deg"),
                     "postura": LaunchConfiguration("postura"),
                     "use_sim_time": True}])

    # Inregistratorul de sesiune. Implicit OPRIT: o demonstratie nu trebuie sa lase
    # fisiere in urma decat daca cineva a cerut-o. Scrie in ~/DATE_TWIN, niciodata in
    # ~/DATE_CAMPANIE, care e arhiva canonica a tezei si ramane read-only.
    recorder = Node(
        package="rehab_exo_description", executable="session_recorder.py",
        output="screen", condition=IfCondition(LaunchConfiguration("inregistrare")),
        parameters=[{"exercitiu": LaunchConfiguration("exercitiu"),
                     "postura": LaunchConfiguration("postura"),
                     "viteza": LaunchConfiguration("viteza"),
                     "marja_sus_deg": LaunchConfiguration("marja_sus_deg"),
                     "use_sim_time": True}])

    # Tabloul iese pe ecran; are nevoie de terminalul curat, deci porneste ultimul.
    monitor = Node(package="rehab_exo_description", executable="monitor_senzori.py",
                   output="screen", parameters=[{"hz": 2.0, "use_sim_time": True}])

    # Gardianul e PRIMA veriga dupa spawn, si e o POARTA: restul lantului porneste
    # doar daca el iese cu 0. Sta aici, si nu in procesul launch-ului, fiindca de aici
    # vede acelasi mediu ca spawnerele. Proba activa cere ca serviciul CM sa raspunda
    # -- exact clasa care moare la nepotrivire de RMW, in timp ce topicurile trec.
    gardian = gardian_in_lant("demo_c4", [jsb],
                              serviciu="/controller_manager/list_controllers",
                              asteapta=30.0)

    lant = [
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=gardian)),
        RegisterEventHandler(OnProcessExit(target_action=jsb, on_exit=[homing])),
        RegisterEventHandler(OnProcessExit(target_action=homing, on_exit=[traj])),
        RegisterEventHandler(OnProcessExit(target_action=traj, on_exit=[adjust])),
        RegisterEventHandler(OnProcessExit(target_action=adjust,
                                           on_exit=[senzori, supervizor, recorder,
                                                    exercitiu, monitor])),
    ]

    argumente = [
        DeclareLaunchArgument("exercitiu", default_value="knee_extension",
                              description="numele exercitiului din exercise_core.EXERCISES"),
        DeclareLaunchArgument("viteza", default_value="1.0",
                              description="factor pe axa timpului, 0.1 .. 3.0"),
        DeclareLaunchArgument("repetari", default_value="3",
                              description="numarul de repetari"),
        DeclareLaunchArgument("inaltime", default_value="1.2",
                              description="inaltimea de aparitie [m]; tine talpile "
                                          "deasupra solului"),
        DeclareLaunchArgument("inregistrare", default_value="false",
                              description="scrie un CSV de sesiune in ~/DATE_TWIN"),
        DeclareLaunchArgument("supervizor", default_value="true",
                              description="stratul electric de siguranta (M5). "
                                          "supervizor:=false e PORTITA DE DEPANARE, "
                                          "nu un mod de demonstratie"),
        DeclareLaunchArgument("marja_jos_deg", default_value="0.0",
                              description="marja electrica la capatul de JOS [grade]; "
                                          "zero fiindca repausul e acolo (D2)"),
        DeclareLaunchArgument("marja_sus_deg", default_value="5.0",
                              description="marja electrica la capatul de SUS [grade]; "
                                          "IPOTEZA, inchisa de proximity-uri"),
        DeclareLaunchArgument("postura", default_value="culcat",
                              description="setul de limite supravegheat: culcat|sezut"),
        DeclareLaunchArgument("gui", default_value="false",
                              description="porneste si GUI-ul Gazebo (vezi antetul)"),
    ]
    return LaunchDescription(argumente + [argument_rmw(), cu_rmw(
        [gz_sim, rsp, clock_bridge, spawn] + lant, "demo_c4", cu_gardian=False)])
