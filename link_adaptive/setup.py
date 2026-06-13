import os
from glob import glob
from setuptools import setup

package_name = "link_adaptive"

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
    description="Strat aplicativ adaptiv la starea legaturii pentru ROS 2 (C3).",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "link_adaptive_node = link_adaptive.link_adaptive_node:main",
            "policy_adapter_node = link_adaptive.policy_adapter_node:main",
            "sil_link_adaptive = link_adaptive.sil_link_adaptive:main",
            "sil_policy_loop = link_adaptive.sil_policy_loop:main",
        ],
    },
)
