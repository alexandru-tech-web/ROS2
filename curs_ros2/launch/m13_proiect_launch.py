from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Proiectul final M13: porneste senzorul si monitorul impreuna.

    Un singur "ros2 launch" ridica tot sistemul: senzor -> /senzor/temperatura
    -> monitor -> /senzor/alarma. Asa demonstram orchestrarea din M3 aplicata
    pe un sistem real cu doua noduri care colaboreaza.
    """

    # Senzorul SIMULAT. Ii dam parametri INLINE (dictionar) ca exemplu rapid:
    # amplitudine mai mare ca unda sa atinga si pragul CRITIC (50), nu doar ATENTIE.
    # Cu valoare_baza=25 si amplitudine=30, valoarea oscileaza intre -5 si 55.
    senzor = Node(
        package='curs_ros2',
        executable='m13_senzor',
        name='senzor_temperatura',
        output='screen',
        parameters=[{
            'rata': 2.0,
            'valoare_baza': 25.0,
            'amplitudine': 30.0,
        }]
    )

    # Monitorul. Setam pragurile INLINE ca sa aratam cum se configureaza la lansare.
    # prag_atentie poate fi schimbat ulterior LIVE prin serviciul /ajusteaza_prag.
    monitor = Node(
        package='curs_ros2',
        executable='m13_monitor',
        name='monitor_temperatura',
        output='screen',
        parameters=[{
            'prag_atentie': 30.0,
            'prag_critic': 50.0,
        }]
    )

    return LaunchDescription([senzor, monitor])
