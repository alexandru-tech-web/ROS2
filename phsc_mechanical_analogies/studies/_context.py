"""
_context.py
Face pachetul importabil si cand scripturile din studies/ sunt rulate direct
din sursa, fara `colcon build` + `source install/setup.bash`.

Se importa primul, inaintea modulelor pachetului:

    import _context  # noqa: F401
    from phsc_mechanical_analogies.cartpole_model import CartPoleModel

Daca pachetul e deja instalat, nu face nimic.
"""

import sys
from pathlib import Path

try:                                    # pachet instalat (dupa colcon build)
    import phsc_mechanical_analogies    # noqa: F401
except ImportError:                     # rulare directa din sursa
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
