#!/usr/bin/env python3
"""netem.py — aplica/curata/arata conditia de retea REALA (tc netem).
  sudo python3 netem.py apply --iface lo --name loss_30      # din CONDITIONS
  sudo python3 netem.py apply --iface lo --lat 200 --jit 50 --loss 0.15
  sudo python3 netem.py clear --iface lo
  python3 netem.py show  --iface lo
Cu --dry doar afiseaza comanda (folosit si de teste/repetitia generala)."""
import argparse, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, netem_cmd, netem_clear_cmd

def run(cmd, dry):
    print(("[dry] " if dry else "$ ") + cmd)
    if not dry:
        subprocess.run(cmd.split(), check=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["apply", "clear", "show"])
    ap.add_argument("--iface", default="lo")
    ap.add_argument("--name", default=None)
    ap.add_argument("--lat", type=float, default=0.0)
    ap.add_argument("--jit", type=float, default=0.0)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if a.action == "show":
        run(f"tc qdisc show dev {a.iface}", a.dry)
        return
    if a.action == "clear":
        run(netem_clear_cmd(a.iface), a.dry)
        return
    c = next((c for c in CONDITIONS if c["name"] == a.name), None) if a.name \
        else dict(base_ms=a.lat, jitter_ms=a.jit, loss=a.loss)
    if c is None:
        sys.exit(f"conditie necunoscuta: {a.name} "
                 f"(stiute: {[x['name'] for x in CONDITIONS]})")
    run(netem_cmd(a.iface, c), a.dry)

if __name__ == "__main__": main()
