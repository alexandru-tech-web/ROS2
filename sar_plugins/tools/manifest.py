#!/usr/bin/env python3
"""manifest.py — manifestul de reproductibilitate al unei rulari.

Fiecare experiment din articol trebuie sa poata fi refacut exact: ce RMW,
ce scenariu, ce seed, ce versiune de cod. Scriptul scrie un manifest JSON
langa bag-ul rosbag2 cu toate aceste informatii.

Folosire (de obicei prin run_experiment.sh, dar merge si direct):
  python3 manifest.py --out ~/sar_data/bags/run_01/manifest.json \
      --scenario loss_30 --rmw rmw_zenoh_cpp --seed 1 \
      --extra '{"note":"prima rulare pe masina noua"}'
"""
import argparse
import datetime
import json
import os
import platform
import subprocess
import sys


def git_rev(cwd=None):
    """Revizia git a codului, daca exista un depozit; altfel None."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=cwd, capture_output=True, text=True,
                             timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def build_manifest(scenario, rmw=None, seed=None, extra=None, cwd=None):
    m = {
        "datetime_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "rmw_implementation": rmw or os.environ.get(
            "RMW_IMPLEMENTATION", "(implicit)"),
        "ros_distro": os.environ.get("ROS_DISTRO"),
        "scenario": scenario,
        "seed": seed,
        "git_rev": git_rev(cwd),
    }
    if extra:
        m.update(extra)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--rmw", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--extra", default=None,
                    help="JSON cu campuri suplimentare")
    args = ap.parse_args()
    # --extra accepta JSON ('{"durata_s":120}') sau perechi 'cheie=valoare'
    extra = None
    if args.extra:
        try:
            extra = json.loads(args.extra)
        except json.JSONDecodeError:
            extra = {}
            for tok in args.extra.replace(",", " ").split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    try:
                        v = json.loads(v)  # numere/bool daca se poate
                    except json.JSONDecodeError:
                        pass
                    extra[k] = v
    m = build_manifest(args.scenario, rmw=args.rmw, seed=args.seed,
                       extra=extra)
    out = os.path.expanduser(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(m, f, indent=2)
    print(f"[ok] manifest scris: {out}")
    for k, v in m.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
