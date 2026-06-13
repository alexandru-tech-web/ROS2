import os
from glob import glob
from setuptools import setup

package_name = "mesh_plugin"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "docs"), glob("docs/*.png")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Alexandru",
    maintainer_email="alexandru@example.ro",
    description="Retea mesh multi-hop intre drone pentru ROS 2 (SAR).",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mesh_node = mesh_plugin.mesh_node:main",
            "sil_mesh = mesh_plugin.sil_mesh:main",
            "sil_mesh_mission = mesh_plugin.sil_mesh_mission:main",
        ],
    },
)
