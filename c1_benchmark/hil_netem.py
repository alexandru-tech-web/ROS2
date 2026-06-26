#!/usr/bin/env python3
"""hil_netem.py -- aplica/curata regula tc netem a UNEI conditii pe o interfata, pentru a OGLINDI
SIMETRIC pe M2 (RPi) exact regula pe care run_campaign.py o aplica pe M1 (PC). Reutilizeaza
bench_core.netem_cmd (SURSA UNICA a regulii) -> M1 si M2 aplica regula IDENTICA per conditie,
deci pierderea round-trip ~ 1-(1-p)^2 si RTT ~ 2x one-way raman coerente cu SIL.

Folosire pe M2 (RPi), conditie cu conditie:
  sudo python3 hil_netem.py <iface> <conditie>     # ex: sudo python3 hil_netem.py eth0 loss_15
  sudo python3 hil_netem.py <iface> --clear        # curata netem la finalul conditiei
  python3 hil_netem.py <iface> <conditie> --dry    # arata comanda, NU o executa

Conditiile *_burst / gilbert_* sunt INGHETATE pe HIL (corelate; in afara drumului critic A1) ->
refuzate aici, la fel ca in run_campaign.py --mode hil."""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, netem_cmd, netem_clear_cmd


def main():
    ap = argparse.ArgumentParser(description="Aplica/curata netem simetric pe M2 (vezi HIL_RUNBOOK.md).")
    ap.add_argument("iface", help="interfata reala (ex. eth0, wlan0)")
    ap.add_argument("condition", nargs="?", default=None, help="numele conditiei din bench_core.CONDITIONS")
    ap.add_argument("--clear", action="store_true", help="curata netem pe iface (in loc sa aplice o conditie)")
    ap.add_argument("--dry", action="store_true", help="arata comanda, NU o executa")
    a = ap.parse_args()

    if a.clear or a.condition is None:
        cmd = netem_clear_cmd(a.iface)
    else:
        by_name = {c["name"]: c for c in CONDITIONS}
        c = by_name.get(a.condition)
        if c is None:
            sys.exit("conditie necunoscuta: %s (stiute: %s)" % (a.condition, sorted(by_name)))
        if c.get("type") == "gilbert" or "corr" in c:
            sys.exit("conditie INGHETATA pe HIL (interferenta corelata): %s. "
                     "Pe legatura fizica ruleaza doar loss_* + lat200_*." % a.condition)
        cmd = netem_cmd(a.iface, c)

    print(cmd)
    if a.dry:
        return
    subprocess.run(["sudo", "bash", "-c", cmd], check=False)


if __name__ == "__main__":
    main()
