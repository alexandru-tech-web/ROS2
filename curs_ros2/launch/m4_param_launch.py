import os

from launch import LaunchDescription
from launch_ros.actions import Node
# get_package_share_directory ne da calea catre folderul "share" al pachetului
# (acolo unde colcon copiaza fisierele instalate, inclusiv config/*.yaml).
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    # Construim calea ABSOLUTA catre fisierul YAML din folderul instalat "share".
    # Atentie: folosim copia din "share", nu cea din "src" (de aceea trebuie
    # ca YAML-ul sa fie instalat de setup.py prin data_files).
    cale_yaml = os.path.join(
        get_package_share_directory('curs_ros2'),
        'config',
        'm4_params.yaml'
    )

    nod = Node(
        package='curs_ros2',
        executable='m4_param',
        name='nod_parametri',
        output='screen',
        # parameters accepta o lista; un element string este interpretat ca o cale
        # catre un fisier YAML cu parametri. Asa pornim nodul direct configurat.
        parameters=[cale_yaml]
    )

    # === Alternativa: parametri INLINE (decomentati ca sa o folositi) ===
    # In loc de fisier, putem da un dictionar direct in launch. E util pentru
    # valori rapide sau override-uri. Daca vrei sa testezi varianta inline,
    # comenteaza linia "parameters=[cale_yaml]" de mai sus si foloseste:
    #
    # nod = Node(
    #     package='curs_ros2',
    #     executable='m4_param',
    #     name='nod_parametri',
    #     output='screen',
    #     parameters=[{'rata': 5.0}]  # 5 Hz; "mesaj" ramane valoarea implicita
    # )

    return LaunchDescription([nod])
