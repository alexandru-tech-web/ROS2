#!/usr/bin/env python3
"""test_mode_label.py -- verificari pentru mode_label si flag-ul --mode (etichetarea SIL/HIL).

mode_label e o functie PURA duplicata IDENTIC in analyze_campaign.py (canonic), campaign_stats.py
si sil_vs_hil_table.py. Aceste teste verifica eticheta corecta, inputul invalid, si ca cele trei
copii nu au divergat. Stil identic cu test_bench_core.py (script simplu; ruleaza cu python3)."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
from analyze_campaign import mode_label as a_label     # noqa: E402
from campaign_stats import mode_label as cs_label       # noqa: E402
from sil_vs_hil_table import mode_label as sh_label      # noqa: E402

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

# flag-ul --mode respinge o valoare necunoscuta (argparse choices=sil/hil)
r = subprocess.run([sys.executable, "analyze_campaign.py", "--mode", "bogus"],
                   cwd=HERE, capture_output=True, text=True)
check(r.returncode != 0,
      "analyze_campaign.py --mode bogus respins (cod de iesire != 0)")

print(f"\nTOATE TESTELE MODE_LABEL AU TRECUT: {N} verificari.")
