from setuptools import find_packages, setup

package_name = 'phsc_teleop_mpc'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'numpy'],
    zip_safe=True,
    maintainer='phd_researcher',
    maintainer_email='researcher@university.edu',
    description='Predictive MPC and haptic shared control for teleoperation',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mpc_controller_node = phsc_teleop_mpc.mpc_controller_node:main',
            'shared_control_mixer = phsc_teleop_mpc.shared_control_mixer:main',
            'latency_estimator = phsc_teleop_mpc.latency_estimator:main',
            'latency_echo = phsc_teleop_mpc.latency_estimator:main_echo',
            'safety_watchdog = phsc_teleop_mpc.safety_watchdog:main',
        ],
    },
)
