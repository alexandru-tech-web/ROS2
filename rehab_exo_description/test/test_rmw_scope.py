#!/usr/bin/env python3
"""test_rmw_scope.py -- grupul de pinuire RMW NU are voie sa fie scoped.

DE CE EXISTA TESTUL ASTA
Pe 21 aug 2026 s-a dovedit ca un GroupAction scoped isi scoate mediul inainte ca
actiunile amanate (RegisterEventHandler / on_exit) sa porneasca. In gazebo.launch.py
asta punea simulatorul pe rmw_cyclonedds_cpp si spawnerele pe rmw_fastrtps_cpp.
Fiindca cele doua interopereaza pe pub/sub dar nu pe servicii, simptomul arata ca un
defect de ros2_control: serviciile controller_manager-ului existau si nu raspundeau.

Regresia e periculoasa exact fiindca e tacuta: daca cineva pune la loc scoped=True,
NIMIC nu cade la build, launch-ul porneste, topicurile apar, si abia spawnerele dau
timeout dupa 60 s. De aceea alegerea e asertata aici, nu doar comentata.

Rulare: python3 test/test_rmw_scope.py
"""
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
sys.path.insert(0, os.path.join(PACHET, "launch"))
sys.path.insert(0, os.path.join(PACHET, "scripts"))

from launch import LaunchContext                               # noqa: E402
from launch.actions import GroupAction, LogInfo                # noqa: E402

from rmw_common import cu_rmw                                  # noqa: E402


def _grup(**kw):
    """Executa OpaqueFunction-ul si intoarce GroupAction-ul rezultat."""
    ctx = LaunchContext()
    ctx.launch_configurations["rmw"] = "cyclonedds"
    actiuni = cu_rmw([LogInfo(msg="martor")], "test", cu_gardian=False,
                     **kw).execute(ctx)
    grupuri = [a for a in actiuni if isinstance(a, GroupAction)]
    assert len(grupuri) == 1, "cu_rmw trebuie sa produca exact un GroupAction"
    return grupuri[0]


def _este_scoped(grup):
    """GroupAction tine flagul intr-un atribut privat; numele e name-mangled."""
    for nume in ("_GroupAction__scoped", "_GroupAction__scoped_"):
        if hasattr(grup, nume):
            return getattr(grup, nume)
    raise AssertionError("nu gasesc flagul de scope pe GroupAction; API-ul launch "
                         "s-a schimbat, testul trebuie actualizat, NU sters")


def main(argv):
    n = 0

    # 1. AFIRMATIA CENTRALA: implicit NEscopat, ca mediul sa ajunga si la actiunile
    # pornite din event handlers.
    g = _grup()
    assert _este_scoped(g) is False, "grupul RMW e scoped -- vezi antetul acestui test"
    n += 1

    # 2. CONTROL NEGATIV: butonul e real, nu ignorat. Daca scoped=True nu s-ar
    # propaga, testul 1 ar trece din motivul gresit (un GroupAction care e
    # nescopat orice i-ai cere).
    g2 = _grup(scoped=True)
    assert _este_scoped(g2) is True, "scoped=True nu se propaga; testul 1 nu dovedeste nimic"
    n += 1

    # 3. Mediul chiar e setat inauntru, si la valoarea NORMALIZATA (alias -> nume
    # complet). Daca ar ajunge 'cyclonedds' in variabila, rclpy ar cadea pe implicit.
    ctx = LaunchContext()
    ctx.launch_configurations["rmw"] = "cyclonedds"
    interior = cu_rmw([LogInfo(msg="martor")], "test",
                      cu_gardian=False).execute(ctx)[0].get_sub_entities()
    setari = [a for a in interior if type(a).__name__ == "SetEnvironmentVariable"]
    assert len(setari) == 1, "trebuie exact un SetEnvironmentVariable"
    valoare = "".join(s.perform(ctx) for s in setari[0].value)
    assert valoare == "rmw_cyclonedds_cpp", valoare
    n += 2

    # 4. Martorul din interior supravietuieste invelirii (nu se pierde actiuni).
    def _text(a):
        return "".join(x.perform(ctx) for x in a.msg)
    assert any(type(a).__name__ == "LogInfo" and "martor" in _text(a)
               for a in interior), "actiunea invelita s-a pierdut"
    n += 1

    print("test_rmw_scope: %d verificari OK (nescopat implicit, control negativ, "
          "valoare normalizata)." % n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
