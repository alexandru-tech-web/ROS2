from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'curs_ros2'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Instaleaza fisierele de launch, config si documentatia cursului,
        # ca sa fie gasite de "ros2 launch" si de get_package_share_directory.
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'docs'), glob('docs/*.md')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alexandru',
    maintainer_email='gheorghitaalexandruu@gmail.com',
    description='Curs complet ROS 2 Jazzy (rclpy): noduri, topice, launch, parametri, '
                'servicii, actiuni, interfete custom, QoS, executors, TF2, lifecycle, '
                'turtlesim si un proiect final integrator.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            # --- M1: noduri ---
            'nod_simplu       = curs_ros2.m1_nod_simplu:main',
            # --- M2: topice ---
            'publisher        = curs_ros2.m1_publisher:main',
            'subscriber       = curs_ros2.m1_subscriber:main',
            # --- M4: parametri ---
            'm4_param         = curs_ros2.m4_param_node:main',
            # --- M5: servicii ---
            'm5_server        = curs_ros2.m5_service_server:main',
            'm5_client        = curs_ros2.m5_service_client:main',
            # --- M6: actiuni ---
            'm6_action_server = curs_ros2.m6_action_server:main',
            'm6_action_client = curs_ros2.m6_action_client:main',
            # --- M7: interfete custom ---
            'm7_pub           = curs_ros2.m7_pub_custom:main',
            'm7_sub           = curs_ros2.m7_sub_custom:main',
            # --- M8: QoS ---
            'm8_pub           = curs_ros2.m8_qos_publisher:main',
            'm8_sub           = curs_ros2.m8_qos_subscriber:main',
            # --- M9: executors ---
            'm9_executor      = curs_ros2.m9_executor_demo:main',
            # --- M10: TF2 ---
            'm10_broadcaster  = curs_ros2.m10_tf_broadcaster:main',
            'm10_listener     = curs_ros2.m10_tf_listener:main',
            # --- M11: lifecycle ---
            'm11_lifecycle    = curs_ros2.m11_lifecycle_node:main',
            # --- M12: turtlesim ---
            'm12_patrat       = curs_ros2.m12_turtle_patrat:main',
            'm12_control      = curs_ros2.m12_turtle_control:main',
            # --- M13: proiect final ---
            'm13_senzor       = curs_ros2.m13_senzor:main',
            'm13_monitor      = curs_ros2.m13_monitor:main',
        ],
    },
)
