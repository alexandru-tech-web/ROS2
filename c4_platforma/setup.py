from setuptools import find_packages, setup

PACHET = "c4_platforma"

setup(
    name=PACHET,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + PACHET]),
        ("share/" + PACHET, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Alexandru Gheorghita",
    maintainer_email="gheorghitaalexandruu@gmail.com",
    description="C4: roverul cu sonda la bord -- alpha si varsta informatiei fara ceasuri comune.",
    license="Apache-2.0",
    entry_points={"console_scripts": ["confidence_node = c4_platforma.confidence_node:main",
                                      "ecou_node = c4_platforma.ecou_node:main"]},
)
