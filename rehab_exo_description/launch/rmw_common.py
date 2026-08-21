"""rmw_common.py -- pinuirea RMW-ului, o singura data, pentru toate launch-urile.

Tiparul e cel VALIDAT la C3 etapa 1c si masurat atunci cu un martor in afara
grupurilor: SetEnvironmentVariable in interiorul unui GroupAction scoped. Fiecare
proces din grup primeste exact RMW-ul grupului, iar valoarea nu se scurge afara.

Trei lucruri se intampla aici, nu unul:
  1. se DECLARA argumentul rmw:= (implicit cyclonedds -- decizia din registrul de
     pe 18 aug: demonstratorul isi alege stiva care nu colapseaza, iar zenoh
     ramane optiune de prima clasa, nu accident de environment);
  2. se APLICA, prin variabila de mediu, in grup scoped;
  3. se VERIFICA la runtime, cu rmw_guard.py, care iese nenul daca implementarea
     efectiv incarcata difera de cea ceruta. Pasul 3 nu e redundant fata de 2:
     daca RMW-ul cerut nu e instalat, rclpy cade linistit pe implicit si pinuirea
     devine o promisiune nerespectata in tacere.

Tabela de aliasuri si functia de verdict NU se dubleaza aici: se importa din
rmw_guard.py, care e instalat si in launch/ tocmai ca sa existe o singura sursa.
"""
import os
import sys

from launch.actions import (DeclareLaunchArgument, GroupAction, LogInfo,
                            OpaqueFunction, SetEnvironmentVariable)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# O SINGURA sursa pentru rmw_guard.py, cautata in cele doua locuri unde poate sta:
# instalat (share/<pkg>/launch/) sau in arborele sursa (../scripts/). NU se copiaza --
# doua copii ale aceleiasi tabele de aliasuri ar fi exact anti-tiparul pe care F1a il
# elimina din descriere.
_AICI = os.path.dirname(os.path.abspath(__file__))
for _c in (_AICI, os.path.join(os.path.dirname(_AICI), "scripts")):
    if os.path.isfile(os.path.join(_c, "rmw_guard.py")):
        sys.path.insert(0, _c)
        break
else:
    raise RuntimeError("rmw_guard.py nu a fost gasit nici in %s, nici in ../scripts" % _AICI)
from rmw_guard import IMPLICIT, normalizeaza          # noqa: E402

PACHET = "rehab_exo_description"


def argument_rmw():
    """Argumentul de launch. Se declara O SINGURA DATA per launch de nivel inalt."""
    return DeclareLaunchArgument(
        "rmw", default_value=IMPLICIT,
        description=("implementarea RMW: cyclonedds (implicit) | zenoh | fastrtps, "
                     "sau un identificator complet rmw_*_cpp"))


def cu_rmw(actiuni, eticheta="rehab", cu_gardian=True):
    """Inveleste `actiuni` intr-un GroupAction scoped cu RMW-ul pinuit.

    `actiuni` poate fi o lista, sau o functie context -> lista (cand actiunile au
    nevoie de valori rezolvate). Intoarce un OpaqueFunction, fiindca aliasul
    ('cyclonedds') trebuie rezolvat la numele complet INAINTE de a ajunge in
    variabila de mediu -- substitutiile nu pot face maparea singure."""
    def _construieste(context, *_a, **_k):
        cerut = LaunchConfiguration("rmw").perform(context)
        plin = normalizeaza(cerut)
        interior = actiuni(context) if callable(actiuni) else list(actiuni)
        continut = [
            SetEnvironmentVariable("RMW_IMPLEMENTATION", plin),
            LogInfo(msg="[%s] RMW pinuit: %s (cerut: '%s')" % (eticheta, plin, cerut)),
        ]
        if cu_gardian:
            continut.append(Node(
                package=PACHET, executable="rmw_guard.py",
                name="rmw_guard_%s" % eticheta,
                arguments=["--rmw-asteptat", plin, "--eticheta",
                           "rmw_guard_%s" % eticheta],
                output="screen"))
        return [GroupAction(continut + interior)]
    return OpaqueFunction(function=_construieste)
