from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    # Broadcaster-ul publica transformarea world -> robot pe /tf la 20 Hz.
    # Il pornim primul, dar ordinea nu e critica aici: listener-ul stie sa astepte
    # (prinde TransformException si reincearca) pana cand transformarea apare.
    broadcaster = Node(
        package='curs_ros2',
        executable='m10_broadcaster',
        name='tf_broadcaster',
        output='screen'
    )

    # Listener-ul citeste din buffer cea mai recenta transformare si o logheaza o
    # data pe secunda. Daca inca nu a auzit-o, afiseaza ca asteapta (nu se opreste).
    listener = Node(
        package='curs_ros2',
        executable='m10_listener',
        name='tf_listener',
        output='screen'
    )

    return LaunchDescription([broadcaster, listener])
