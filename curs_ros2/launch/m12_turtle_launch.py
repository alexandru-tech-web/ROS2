from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node


def generate_launch_description():

    # Pornim simularea turtlesim. Numele 'sim' e doar eticheta nodului in graf.
    # Acesta deschide fereastra cu broasca si publica /turtle1/pose, ascultand
    # comenzile pe /turtle1/cmd_vel.
    sim = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='sim',
        output='screen'
    )

    # Pornim nodul de control DUPA 2 secunde. DE CE intarziere? turtlesim are
    # nevoie de putin timp ca sa se initializeze si sa inceapa sa publice
    # /turtle1/pose. Daca am porni controlul instant, primele tic-uri n-ar avea
    # inca o pozitie de la care sa plece (am tratat si cazul pose=None in cod,
    # dar intarzierea face pornirea mai curata si mai usor de urmarit la curs).
    control_intarziat = TimerAction(
        period=2.0,
        actions=[
            Node(
                package='curs_ros2',
                executable='m12_control',
                output='screen'
            )
        ]
    )

    return LaunchDescription([sim, control_intarziat])
