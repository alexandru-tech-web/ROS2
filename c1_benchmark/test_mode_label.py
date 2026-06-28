#!/usr/bin/env python3
"""test_mode_label.py -- verificari pentru mode_label, env_label si flag-ul --mode (etichetare).

mode_label (sil/hil, compat) si env_label (sil/hil_wifi/hil_switch, matricea 2x2) sunt functii PURE
duplicate IDENTIC in analyze_campaign.py (canonic), campaign_stats.py si sil_vs_hil_table.py. Aceste
teste verifica eticheta corecta, inputul invalid si ca cele trei copii nu au divergat (pentru AMBELE).
Stil identic cu test_bench_core.py (script simplu; ruleaza cu python3)."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))

# In acest mediu matplotlib poate LIPSI, iar analyze_campaign il importa la nivel de modul. Il stub-uim
# DOAR ca sa putem importa modulele pentru a testa functiile PURE (mode_label/env_label nu deseneaza).
try:
    import matplotlib  # noqa: F401
except ImportError:
    import types
    _mpl = types.ModuleType("matplotlib")
    _mpl.use = lambda *a, **k: None
    sys.modules["matplotlib"] = _mpl
    sys.modules["matplotlib.pyplot"] = types.ModuleType("matplotlib.pyplot")

from analyze_campaign import mode_label as a_label, env_label as a_env     # noqa: E402
from campaign_stats import mode_label as cs_label, env_label as cs_env      # noqa: E402
from sil_vs_hil_table import mode_label as sh_label, env_label as sh_env     # noqa: E402

N = 0


def check(c, m):
    global N
    assert c, m
    N += 1
    print(f"  [ok] {m}")


check(a_label("sil") == "SIL (loopback)", "mode_label('sil') -> 'SIL (loopback)'")
check(a_label("hil") == "HIL (two-machine)", "mode_label('hil') -> 'HIL (two-machine)'")

try:
    a_label("bogus")
    raised = False
except ValueError:
    raised = True
check(raised, "mode_label respinge input invalid cu ValueError")

check(all(m("sil") == "SIL (loopback)" and m("hil") == "HIL (two-machine)"
          for m in (a_label, cs_label, sh_label)),
      "cele 3 copii mode_label (analyze_campaign / campaign_stats / sil_vs_hil_table) sunt IDENTICE")

# env_label: axa de MEDIU a matricei 2x2 (sil/hil_wifi/hil_switch); mode_label ramane pentru compat.
check(a_env("sil") == "SIL (loopback)", "env_label('sil') -> 'SIL (loopback)'")
check(a_env("hil_wifi") == "HIL (Wi-Fi)", "env_label('hil_wifi') -> 'HIL (Wi-Fi)'")
check(a_env("hil_switch") == "HIL (Gigabit switch)", "env_label('hil_switch') -> 'HIL (Gigabit switch)'")

try:
    a_env("bogus")
    raised_env = False
except ValueError:
    raised_env = True
check(raised_env, "env_label respinge input invalid cu ValueError")

check(all(m("sil") == "SIL (loopback)" and m("hil_wifi") == "HIL (Wi-Fi)"
          and m("hil_switch") == "HIL (Gigabit switch)" for m in (a_env, cs_env, sh_env)),
      "cele 3 copii env_label (analyze_campaign / campaign_stats / sil_vs_hil_table) sunt IDENTICE")

# flag-ul --mode pe CLI (testat pe campaign_stats, care importa matplotlib LENES -> ajunge la argparse
# chiar fara matplotlib): valoare necunoscuta respinsa; "hil" generic -> eroare blanda (ambiguu).
r_bogus = subprocess.run([sys.executable, "campaign_stats.py", "--demo", "--mode", "bogus"],
                         cwd=HERE, capture_output=True, text=True)
check(r_bogus.returncode != 0, "campaign_stats --mode bogus respins (cod != 0)")
r_hil = subprocess.run([sys.executable, "campaign_stats.py", "--demo", "--mode", "hil"],
                       cwd=HERE, capture_output=True, text=True)
check(r_hil.returncode != 0 and "ambiguu" in (r_hil.stderr + r_hil.stdout),
      "campaign_stats --mode hil (generic) -> eroare blanda care cere hil_wifi/hil_switch")

print(f"\nTOATE TESTELE MODE_LABEL AU TRECUT: {N} verificari.")
