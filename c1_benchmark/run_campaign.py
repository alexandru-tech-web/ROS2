#!/usr/bin/env python3
"""run_campaign.py -- ORCHESTRATORUL campaniei C1: ruleaza intreaga matrice
RMW x conditie x repetitii, pe doua straturi de masurare, si organizeaza
rezultatele pentru analyze_campaign.py.

  stratul "transport": bench_echo_server + bench_client (RTT brut + rezumat)
  stratul "mission":   misiunea SAR reala (sar_swarm) cu scenario:=none.yaml
                       -- singura degradare e tc netem (REALA), deci
                       diferentele masurate apartin middleware-ului.

Mod SIL vs HIL (--mode):
  sil (implicit): tot pe o masina, prin loopback (--iface lo); ecoul/misiunea
                  sunt pornite local.
  hil           : ecoul/misiunea ruleaza pe a DOUA masina (PC + RPi); acest script
                  ruleaza doar clientul si aplica netem pe interfata reala. Schema de
                  date e IDENTICA -> analyze_campaign / selectorul ingera datele HIL
                  fara modificari de cod. Procedura completa: HIL_RUNBOOK.md.

Rulare SIL (pe o masina, prin lo):
  sudo -v && python3 run_campaign.py --mode sil --iface lo --reps 5
Rulare HIL (pe masina-client; ecoul pornit pe masina 2 -- vezi HIL_RUNBOOK.md):
  sudo -v && python3 run_campaign.py --mode hil --iface <interfata reala> --reps 5
Vezi planul fara sa rulezi nimic:
  python3 run_campaign.py --dry

Rezultate: results_c1/{rmw}/{conditie}/rep{N}/
  transport_p{P}.csv + _summary.json   (per dimensiune de sarcina utila)
  mission_metrics.csv, rtt_log.csv, op_commands.csv (recoltate din ~/sar_data)
La final (si la Ctrl+C) tc este CURATAT pe interfata.
"""
import argparse
import os
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, build_plan, netem_cmd, netem_clear_cmd

HERE = os.path.dirname(os.path.abspath(__file__))
PAYLOADS = [64, 4096, 65536]          # B: comanda / telemetrie / harta


def sh(cmd, dry, **kw):
    print(("[dry] " if dry else "$ ") + " ".join(map(str, cmd)))
    if not dry:
        return subprocess.run(cmd, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iface", default="lo")
    ap.add_argument("--mode", choices=["sil", "hil"], default="sil",
                    help="sil = tot pe o masina (loopback); "
                         "hil = ecoul/misiunea pe a doua masina (vezi HIL_RUNBOOK.md)")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--rmws", default="cyclonedds,zenoh")
    ap.add_argument("--conditions", default=None,
                    help="lista de conditii rulate (virgula); implicit toate")
    ap.add_argument("--layers", default="transport,mission")
    ap.add_argument("--duration", type=float, default=20.0,
                    help="durata unei rulari de transport per sarcina utila")
    ap.add_argument("--mission-timeout", type=float, default=170.0)
    ap.add_argument("--sar-dir", default=os.path.join(HERE, "..", "sar_swarm"))
    ap.add_argument("--out", default=os.path.join(HERE, "results_c1"))
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    rmws = [r.strip() for r in a.rmws.split(",") if r.strip()]
    layers = tuple(l.strip() for l in a.layers.split(","))
    if a.conditions:
        want = [c.strip() for c in a.conditions.split(",") if c.strip()]
        known = {c["name"] for c in CONDITIONS}
        bad = [c for c in want if c not in known]
        if bad:
            sys.exit(f"conditii necunoscute: {bad} (stiute: {sorted(known)})")
        conditions = [c for c in CONDITIONS if c["name"] in want]
    else:
        conditions = CONDITIONS
    # HIL: exclude conditiile de interferenta INGHETATE -- pe legatura fizica vrem comparatia
    # AUTORITARA memoryless + latenta. *_burst (corr) nu pastreaza media; gilbert_* fac parte din
    # suprafata RF inghetata (in afara drumului critic A1). Vezi NOTA_METODOLOGICA_C1.md / HIL_RUNBOOK.md.
    if a.mode == "hil":
        excluse = [c["name"] for c in conditions if c.get("type") == "gilbert" or "corr" in c]
        if excluse:
            conditions = [c for c in conditions if c.get("type") != "gilbert" and "corr" not in c]
            print(f"[hil] exclus (inghetat, interferenta corelata): {excluse}")
    plan = build_plan(rmws, conditions, a.reps, layers)
    print(f"plan: {len(plan)} rulari ({len(rmws)} RMW x {len(conditions)} "
          f"conditii x {a.reps} rep x {len(layers)} straturi)")
    loc = "loopback, o masina" if a.mode == "sil" else "doua masini -- ecoul/misiunea pe masina 2"
    print(f"mod: {a.mode.upper()}  iface: {a.iface}  ({loc})")
    if a.mode == "hil":
        print("[hil] ASIGURA-TE ca ecoul ruleaza pe masina a 2-a inainte sa pornesti "
              "(vezi HIL_RUNBOOK.md)")

    router = None
    cur_rmw = None

    def stop_router():
        nonlocal router
        if router and router.poll() is None:
            os.killpg(os.getpgid(router.pid), signal.SIGTERM)
        router = None

    try:
        for i, p in enumerate(plan, 1):
            env = {**os.environ, "RMW_IMPLEMENTATION": p["rmw_impl"],
                   "ZENOH_ROUTER_CHECK_ATTEMPTS": "10"}
            outdir = os.path.join(a.out, p["rmw"], p["condition"],
                                  f"rep{p['rep']}")
            print(f"\n=== [{i}/{len(plan)}] {p['rmw']} / {p['condition']} "
                  f"/ rep{p['rep']} / {p['layer']} ===")
            # WATCHDOG: doar SIL. Pe HIL routerul e gestionat extern (cu override).
            if (a.mode == "sil" and p["needs_router"] and router is not None
                    and router.poll() is not None):
                print("[!] routerul Zenoh a murit -- il repornesc")
                cur_rmw = None
            # routerul Zenoh: o singura instanta per bloc RMW
            if p["rmw"] != cur_rmw:
                stop_router()
                cur_rmw = p["rmw"]
                if p["needs_router"] and a.mode == "hil":
                    print("[hil] routerul Zenoh e gestionat EXTERN "
                          "(porneste-l manual cu ZENOH_CONFIG_OVERRIDE). "
                          "Campania NU porneste router pe HIL.")
                elif p["needs_router"] and not a.dry:
                    router = subprocess.Popen(
                        ["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"],
                        env=env, preexec_fn=os.setsid,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
                    time.sleep(2.0)
                elif p["needs_router"]:
                    print("[dry] pornesc routerul Zenoh (rmw_zenohd)")
            sh(["sudo", "bash", "-c", netem_cmd(a.iface, p["netem"])], a.dry)
            os.makedirs(outdir, exist_ok=True) if not a.dry else None

            if p["layer"] == "transport":
                for pay in PAYLOADS:
                    if a.dry:
                        srv = "echo local + " if a.mode == "sil" else "echo REMOTE (masina 2) + "
                        print(f"[dry] {srv}client payload={pay} "
                              f"durata={a.duration}s -> {outdir}")
                        continue
                    # SIL: pornim ecoul local. HIL: ecoul ruleaza pe masina 2.
                    echo = None
                    if a.mode == "sil":
                        echo = subprocess.Popen(
                            ["python3", os.path.join(HERE, "bench_echo_server.py")],
                            env=env, preexec_fn=os.setsid,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
                        time.sleep(1.5)
                    sh(["python3", os.path.join(HERE, "bench_client.py"),
                        "--payload", str(pay), "--duration", str(a.duration),
                        "--out", os.path.join(outdir,
                                              f"transport_p{pay}.csv")],
                       a.dry, env=env)
                    if echo is not None:
                        os.killpg(os.getpgid(echo.pid), signal.SIGTERM)
                        time.sleep(0.5)

            elif p["layer"] == "mission":
                if a.mode == "hil":
                    print("[hil] strat 'mission' distribuit pe doua masini -- ruleaza-l manual")
                    print("      conform HIL_RUNBOOK.md (recomandat: incepe cu --layers transport).")
                    continue
                launch = os.path.join(a.sar_dir, "launch",
                                      "sar_ros.launch.py")
                sh(["timeout", str(a.mission_timeout), "ros2", "launch",
                    launch, "scenario:=none.yaml", "autostart:=true",
                    "dashboard:=false"], a.dry, env=env)
                if not a.dry:
                    sar = os.path.expanduser("~/sar_data")
                    for f in ("mission_metrics.csv", "rtt_log.csv",
                              "op_commands.csv"):
                        src = os.path.join(sar, f)
                        if os.path.exists(src):
                            shutil.copy(src, os.path.join(outdir, f))
                    time.sleep(1.0)
    finally:
        stop_router()
        sh(["sudo", "bash", "-c", netem_clear_cmd(a.iface)], a.dry)
        print("\n[ok] tc curatat; rezultatele in", a.out)


if __name__ == "__main__":
    main()
