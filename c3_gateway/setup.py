from setuptools import find_packages, setup

package_name = "c3_gateway"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test", "gate", "tools"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    # tabela de politica e DATA, nu cod: se genereaza cu tools/derive_policy.py din
    # tabelele canonice C2 si trebuie sa mearga alaturi de modul
    package_data={package_name + ".core": ["policy_table.json"]},
    include_package_data=True,
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Alexandru",
    maintainer_email="gheorghitaalexandruu@gmail.com",
    description="C3: gateway de selectie a transportului condus de starea linkului "
                "(etapa 1: nucleu pur, fara ROS).",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        # ETAPA 1: NICIUN nod. Nodurile subtiri peste nucleu vin in etapa 2.
        "console_scripts": [],
    },
)
