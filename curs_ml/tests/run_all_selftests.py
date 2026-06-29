#!/usr/bin/env python3
"""run_all_selftests.py -- agregator: ruleaza toate _selftest()-urile din curs_ml.

Gaseste utils.py, date_sar.py si fiecare <topic>_core.py de modul, le ruleaza ca
subprocese (fiecare are propriul `if __name__ == '__main__': _selftest()`) si
raporteaza verde/rosu. Iesire 0 daca toate trec.

Rulare (din venv-ul ML):
  ~/ros2_ws/.venv_ml/bin/python tests/run_all_selftests.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(os.path.dirname(HERE), "curs_ml")


def collect():
    targets = [os.path.join(PKG, "utils.py"), os.path.join(PKG, "date_sar.py")]
    for root, _dirs, files in os.walk(PKG):
        for f in sorted(files):
            if f.endswith("_core.py"):
                targets.append(os.path.join(root, f))
    return [t for t in targets if os.path.exists(t)]


def main():
    fails = []
    targets = collect()
    for t in targets:
        rel = os.path.relpath(t, PKG)
        r = subprocess.run([sys.executable, t], capture_output=True, text=True)
        if r.returncode == 0:
            print("  [verde] %s" % rel)
        else:
            print("  [ROSU]  %s -- selftest PICAT" % rel)
            fails.append(rel)
    print("\n%d/%d selfteste verzi." % (len(targets) - len(fails), len(targets)))
    if fails:
        print("AU PICAT: " + ", ".join(fails))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
