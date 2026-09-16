#!/usr/bin/env python3
"""models.py -- modelele de vehicul, cu aceeasi interfata.

RoverModel: step(state, cmd, dt) -> state. Unicycle deleaga la rover_core, care e
deja testat; SkidSteerAdapter imprumuta SkidSteer4W din teleop_rover (READ-ONLY,
prin sys.path) ca sa putem compara doua cinematici pe acelasi scenariu.
"""
import os
import sys

try:
    from typing import Protocol
except ImportError:
    Protocol = object

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)
import rover_core                                            # noqa: E402


class RoverModel(Protocol):
    def step(self, state, cmd, dt):
        ...


class Unicycle(object):
    nume = "unicycle"

    def step(self, state, cmd, dt):
        return rover_core.step(state, cmd, dt)


class SkidSteerAdapter(object):
    """SkidSteer4W din teleop_rover/nav_core.py, adus la interfata noastra.

    teleop_rover e pachet INGHETAT: importul e read-only, prin sys.path, fara
    nicio modificare acolo."""
    nume = "skidsteer4w"

    def __init__(self):
        cale = os.path.expanduser("~/ros2_ws/src/teleop_rover")
        # COLIZIUNE DE NUME: teleop_rover are PROPRIUL rover_core.py (cu V_MAX,
        # W_MAX), iar al nostru se cheama la fel. Fara izolare, nav_core il
        # importa pe al nostru si cade cu ImportError: W_MAX. Deci: punem calea
        # lui primul, scoatem din cache modulele cu nume comun cat tine importul,
        # si le punem inapoi. Pachetul inghetat NU se atinge.
        salvate = {k: sys.modules.pop(k, None) for k in ("rover_core", "nav_core")}
        sys.path.insert(0, cale)
        try:
            import nav_core                                   # noqa: E402
            self._m = nav_core.SkidSteer4W()
        finally:
            sys.path.remove(cale)
            for k in ("rover_core", "nav_core"):
                sys.modules.pop(k, None)
                if salvate[k] is not None:
                    sys.modules[k] = salvate[k]

    def step(self, state, cmd, dt):
        self._m.x, self._m.y = state.x, state.y
        self._m.theta = state.theta
        self._m.step(float(cmd[0]), float(cmd[1]), dt)
        v = getattr(self._m, "_v", cmd[0])
        return rover_core.Stare(x=self._m.x, y=self._m.y, theta=self._m.theta,
                                v=v, omega=float(cmd[1]))


def incearca_skidsteer():
    """(model, None) sau (None, motiv). Adaptorul se SARE daca importul cere ROS
    sau esueaza: nu oprim S1 pentru un pachet inghetat."""
    try:
        return SkidSteerAdapter(), None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
