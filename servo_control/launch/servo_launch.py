import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node

WORLD = os.path.expanduser('~/.gz/worlds/lab_world.sdf')
TOPIC = '/model/servo1/joint/shaft_joint/cmd_vel'

def generate_launch_description():

    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', WORLD],
        output='screen'
    )

    bridge = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                name='servo_bridge',
                arguments=[TOPIC + '@std_msgs/msg/Float64]gz.msgs.Double'],
                output='screen'
            )
        ]
    )

    teleop = TimerAction(
        period=6.0,
        actions=[
            Node(
                package='servo_control',
                executable='servo_teleop',
                name='servo_teleop',
                output='screen',
                prefix='xterm -e'
            )
        ]
    )

    return LaunchDescription([gazebo, bridge, teleop])