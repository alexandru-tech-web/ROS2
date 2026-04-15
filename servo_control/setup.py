from setuptools import find_packages, setup
import os

package_name = "servo_control"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"),
            ["launch/servo_launch.py"]),
        (os.path.join("share", package_name, "worlds"),
            ["worlds/lab_world.sdf"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ubuntu",
    maintainer_email="ubuntu@todo.todo",
    description="Servo motor control package",
    license="MIT",
    entry_points={
        "console_scripts": [
            "servo_teleop = servo_control.servo_teleop:main",
        ],
    },
)
