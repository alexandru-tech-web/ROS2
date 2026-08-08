#!/usr/bin/env python3
"""
ur3_teleop.launch.py
Launch file pentru teleoperare UR3 real cu MPC.

Porneste:
  1. Driver UR3 (ros2_control sau driver specific)
  2. MPC Controller Node cu parametri UR3
  3. Shared Control Mixer
  4. (Fara Gazebo - hardware real)

Autor: PhD Research - Predictive Haptic Shared Control
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_mixer = LaunchConfiguration('use_mixer', default='true')

    mpc_node = Node(
        package='phsc_teleop_mpc',
        executable='mpc_controller_node',
        name='mpc_controller_ur3',
        output='screen',
        parameters=[{
            'N': 20,
            'dt': 0.05,
            'u_max': 50.0,
            'tau_est': 0.08,
            'Q_diag': [10.0, 1.0, 100.0, 1.0],
            'R': 0.01,
            'P_diag': [50.0, 5.0, 500.0, 5.0],
        }]
    )

    mixer_node = Node(
        package='phsc_teleop_mpc',
        executable='shared_control_mixer',
        name='shared_control_mixer',
        output='screen',
        parameters=[{
            'alpha': 0.6,
            'alpha_mode': 'fixed'
        }]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_mixer', default_value='true'),
        mpc_node,
        mixer_node,
    ])
