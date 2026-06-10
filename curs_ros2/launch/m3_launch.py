from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction  # ← nou

def generate_launch_description():

    publisher = Node(
        package='curs_ros2',
        executable='publisher',
        name='publisher_temperatura',
        output='screen'
    )

    subscriber = TimerAction(
        period=3.0,  # ← delay 3 secunde
        actions=[
            Node(
                package='curs_ros2',
                executable='subscriber',
                name='subscriber_temperatura',
                output='screen'
            )
        ]
    )

    return LaunchDescription([publisher, subscriber])