# Copyright 2026 Alexandru Gheorghita
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
"""Launch the packaged Gazebo world and the ROS-Gazebo command bridge."""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import OpaqueFunction
from launch.actions import SetEnvironmentVariable
from launch.actions import UnsetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


DEFAULT_TOPIC = '/model/servo1/joint/shaft_joint/cmd_vel'
SNAP_GUI_ENVIRONMENT = (
    'GDK_PIXBUF_MODULEDIR',
    'GDK_PIXBUF_MODULE_FILE',
    'GIO_MODULE_DIR',
    'GSETTINGS_SCHEMA_DIR',
    'GTK_EXE_PREFIX',
    'GTK_IM_MODULE_FILE',
    'GTK_PATH',
    'LOCPATH',
)


def sanitize_snap_environment(context):
    """Prevent Snap GUI libraries from leaking into the host Gazebo process."""
    environment = context.environment
    if 'SNAP' not in environment:
        return []

    names_to_unset = set(SNAP_GUI_ENVIRONMENT)
    names_to_unset.update(
        name
        for name in environment
        if name == 'SNAP' or name.startswith('SNAP_')
    )

    actions = [
        UnsetEnvironmentVariable(name)
        for name in sorted(names_to_unset)
    ]

    xdg_data_home = environment.get('XDG_DATA_HOME', '')
    if '/snap/' in xdg_data_home:
        actions.append(UnsetEnvironmentVariable('XDG_DATA_HOME'))

    xdg_data_dirs = environment.get('XDG_DATA_DIRS', '')
    if xdg_data_dirs:
        host_data_dirs = os.pathsep.join(
            path
            for path in xdg_data_dirs.split(os.pathsep)
            if '/snap/' not in path
        )
        if host_data_dirs != xdg_data_dirs:
            actions.append(
                SetEnvironmentVariable('XDG_DATA_DIRS', host_data_dirs)
            )

    return actions


def generate_launch_description():
    """Create the Gazebo and bridge launch description."""
    world = LaunchConfiguration('world')
    command_topic = LaunchConfiguration('command_topic')

    default_world = PathJoinSubstitution(
        [FindPackageShare('servo_control'), 'worlds', 'lab_world.sdf']
    )
    gazebo_launch = PathJoinSubstitution(
        [FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py']
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gazebo_launch),
        launch_arguments={
            'gz_args': ['-r ', world],
            'on_exit_shutdown': 'true',
        }.items(),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='servo_bridge',
        arguments=[
            [command_topic, '@std_msgs/msg/Float64]gz.msgs.Double'],
        ],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world',
            default_value=default_world,
            description='Absolute path to the Gazebo SDF world.',
        ),
        DeclareLaunchArgument(
            'command_topic',
            default_value=DEFAULT_TOPIC,
            description='ROS/Gazebo joint velocity command topic.',
        ),
        OpaqueFunction(function=sanitize_snap_environment),
        gazebo,
        bridge,
    ])
