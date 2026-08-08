#!/usr/bin/env python3
"""
cartpole_sim.launch.py
Launch file pentru simulare cart-pole in Gazebo Harmonic cu MPC + delay variabil.

Porneste:
  NOTA: in starea actuala porneste DOAR nodurile ROS (vezi comentariile din cod).
  Urmatoarele NU sunt implementate inca:
  1. Gazebo Harmonic cu world gol
  2. Model cart-pole (URDF)
  3. VariableDelayPlugin
  4. MPC Controller Node
  5. Shared Control Mixer (optional)
  6. RViz2 (optional)

Autor: PhD Research - Predictive Haptic Shared Control
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Cai pachete
    bringup_dir = get_package_share_directory('phsc_bringup')

    # Argumente
    # Fara default= aici: valoarea implicita vine din DeclareLaunchArgument
    # de mai jos (altfel ai doua surse de default care se contrazic).
    use_rviz = LaunchConfiguration('use_rviz')
    use_mixer = LaunchConfiguration('use_mixer')
    # delay_profile e declarat mai jos, dar deocamdata INERT: nimic din
    # workspace nu citeste profilul de delay (plugin-ul isi ia valorile din SDF).

    # Config files
    mpc_config = os.path.join(bringup_dir, 'config', 'mpc_tuning.yaml')
    # delay_profiles.yaml NU e in format de parametri ROS (nu are cheie de nod
    # + ros__parameters) si nu e citit de nimic in workspace. Nu il incarcam:
    # a fi pasat in parameters= ar opri lansarea. Ramane doar referinta pentru
    # plugin-ul Gazebo, care isi ia valorile din SDF, nu din acest fisier.

    # 1. Gazebo Harmonic -- NU este pornit de acest launch file.
    # Nu exista niciun URDF/SDF de cart-pole in workspace si VariableDelayPlugin
    # nu e instantiat de nimeni. Ce porneste efectiv fisierul: nodurile ROS.
    # Pentru simulare reala e nevoie de: world SDF + model cart-pole +
    # ros_gz_sim/gz_sim.launch.py + ros_gz_bridge. Vezi raportul.

    # 2. MPC Controller Node
    # ATENTIE: numele nodului TREBUIE sa fie 'mpc_controller_node', identic cu
    # cheia de nivel superior din mpc_tuning.yaml. Cu name='mpc_controller'
    # (varianta anterioara) rclpy nu potrivea nicio cheie si TOT fisierul de
    # tuning era ignorat in silentiu -- nu se observa doar pentru ca valorile
    # din YAML erau identice cu default-urile din cod.
    mpc_node = Node(
        package='phsc_teleop_mpc',
        executable='mpc_controller_node',
        name='mpc_controller_node',
        output='screen',
        parameters=[mpc_config]
    )

    # 3. Shared Control Mixer (optional)
    mixer_node = Node(
        package='phsc_teleop_mpc',
        executable='shared_control_mixer',
        name='shared_control_mixer',
        output='screen',
        parameters=[{
            'alpha': 0.5,
            'alpha_mode': 'fixed'
        }],
        condition=IfCondition(use_mixer)
    )

    # 4. RViz2
    # Nu exista config/phsc.rviz in pachet, deci NU pasam '-d' (rviz2 ar porni
    # cu eroare de fisier lipsa). Default use_rviz=false: fara model/URDF si
    # fara TF nu e nimic de afisat.
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(use_rviz)
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='false',
                              description='Porneste RViz2 (fara config dedicat)'),
        DeclareLaunchArgument('use_mixer', default_value='false',
                              description='Porneste Shared Control Mixer'),
        DeclareLaunchArgument('delay_profile', default_value='sine',
                              description='Profil delay: constant, sine, burst'),

        mpc_node,
        mixer_node,
        rviz_node,
    ])
