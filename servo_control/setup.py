# Copyright 2026 Alexandru Gheorghita
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
"""Package configuration for servo_control."""

from glob import glob
import os

from setuptools import find_packages
from setuptools import setup


package_name = 'servo_control'


setup(
    name=package_name,
    version='1.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        (
            os.path.join('share', package_name),
            [
                'package.xml',
                'LICENSE',
                'README.md',
                'DOCUMENTATIE_UTILIZARE.md',
            ],
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.py'),
        ),
        (
            os.path.join('share', package_name, 'worlds'),
            glob('worlds/*.sdf'),
        ),
        (
            os.path.join('share', package_name, 'models', 'Servomotor'),
            glob('models/Servomotor/*.sdf')
            + glob('models/Servomotor/*.config'),
        ),
        (
            os.path.join(
                'share',
                package_name,
                'models',
                'Servomotor',
                'meshes',
            ),
            glob('models/Servomotor/meshes/*'),
        ),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=False,
    maintainer='Alexandru Gheorghita',
    maintainer_email='alexandrugheorghita.tehnic@yahoo.com',
    description='Fail-safe keyboard teleoperation for a Gazebo servo joint',
    license='MIT',
    entry_points={
        'console_scripts': [
            'servo_teleop = servo_control.servo_teleop:main',
        ],
    },
)
