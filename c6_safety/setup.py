from setuptools import find_packages, setup

PACHET = "c6_safety"

setup(
    name=PACHET,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + PACHET]),
        ("share/" + PACHET, ["package.xml"]),
        ("share/" + PACHET + "/launch", ["launch/c6_smoke.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Alexandru Gheorghita",
    maintainer_email="gheorghitaalexandruu@gmail.com",
    description="C6: nucleu pur pentru garda de siguranta a roverului teleoperat.",
    license="Apache-2.0",
    # S3: doua noduri SUBTIRI peste core; toata logica ramane in modulele fara ROS.
    entry_points={"console_scripts": [
        "operator_node = c6_safety.operator_node:main",
        "rover_node = c6_safety.rover_node:main",
    ]},
)
