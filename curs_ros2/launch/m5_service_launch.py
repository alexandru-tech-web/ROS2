from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction


def generate_launch_description():

    # Pornim intai serverul: el trebuie sa existe inainte ca clientul sa sune.
    server = Node(
        package='curs_ros2',
        executable='m5_server',
        name='server_adunare',
        output='screen'
    )

    # Pornim clientul dupa 2 secunde, ca serverul sa apuce sa fie gata.
    # Clientul oricum asteapta serviciul cu wait_for_service, dar acest delay
    # face demonstratia mai curata (vedem clar ordinea in log).
    # Argumentele 5 si 7 ajung in sys.argv al clientului.
    client = TimerAction(
        period=2.0,
        actions=[
            Node(
                package='curs_ros2',
                executable='m5_client',
                name='client_adunare',
                output='screen',
                arguments=['5', '7']
            )
        ]
    )

    return LaunchDescription([server, client])
