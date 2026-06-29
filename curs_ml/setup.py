from setuptools import find_packages, setup

package_name = "curs_ml"

setup(
    name=package_name,
    version="0.1.0",
    # Pachetul intern curs_ml (date_sar, utils) + eventualele subpachete cu __init__.py.
    # Folderele de modul mXX_* sunt continut educational rulat din sursa cu `python3`
    # (nu pachete instalate); nodul ROS din M22 isi importa nucleul cu sys.path.insert.
    packages=find_packages(exclude=["tests", "tests.*"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Alexandru",
    maintainer_email="gheorghitaalexandruu@gmail.com",
    description="Curs academic de Machine Learning ca pachet ROS 2 (M00-M22).",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            # Nodurile ROS demo se adauga pe masura ce sunt construite modulele.
            # M22 capstone: 'link_predictor_node = curs_ml.m22_capstone_link_predictor.link_predictor_node:main'
        ],
    },
)
