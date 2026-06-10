from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'curs_ros2'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Adaugat:
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ubuntu',
    maintainer_email='ubuntu@todo.todo',
    description='Pachet de invatare ROS2',
    license='MIT',
    entry_points={
        'console_scripts': [
            'nod_simplu  = curs_ros2.m1_nod_simplu:main',
            'publisher   = curs_ros2.m1_publisher:main',
            'subscriber  = curs_ros2.m1_subscriber:main',
        ],
    },
)