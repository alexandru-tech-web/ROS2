from setuptools import find_packages, setup

PACHET = "c7_sistem"

setup(
    name=PACHET,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + PACHET]),
        ("share/" + PACHET, ["package.xml"]),
        ("share/" + PACHET + "/launch", ["launch/v0_sistem.launch.py", "launch/v0_rover.launch.py", "launch/v0_operator.launch.py"]),
        ("share/" + PACHET + "/tools", ["tools/v0_smoke.sh", "tools/split_smoke.sh"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Alexandru Gheorghita",
    maintainer_email="gheorghitaalexandruu@gmail.com",
    description="C7: launch-uri de sistem peste pachetele existente + substitut C4.",
    license="Apache-2.0",
    entry_points={"console_scripts": ["substitut_c4_node = c7_sistem.substitut_c4_node:main",
                                      "punte_telemetrie = c7_sistem.punte_telemetrie:main"]},
)
