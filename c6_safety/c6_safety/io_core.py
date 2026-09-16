#!/usr/bin/env python3
"""io_core.py -- scrie trace CSV si metrics JSON intr-un dir dat. Fara ROS."""
import csv
import json
import os

COLOANE = ("t", "x", "y", "theta", "v", "omega", "v_op", "omega_op", "AoI_cmd", "h")


def scrie(dir_iesire, metrics, trace, eticheta="episod"):
    os.makedirs(dir_iesire, exist_ok=True)
    pc = os.path.join(dir_iesire, "%s_trace.csv" % eticheta)
    with open(pc, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLOANE)
        w.writeheader()
        for p in trace:
            w.writerow({k: ("" if p.get(k) is None else p.get(k)) for k in COLOANE})
    pj = os.path.join(dir_iesire, "%s_metrics.json" % eticheta)
    with open(pj, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)
        f.write("\n")
    return pc, pj
