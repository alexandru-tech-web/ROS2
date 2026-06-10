#!/usr/bin/env python3
"""launcher_core.py — logica PURA a meniului de misiune (fara Tk, fara ROS):
ce middleware-uri RMW sunt instalate si ce comanda exacta porneste misiunea
pentru fiecare combinatie (middleware x mod x scenariu x optiuni).

Folosit de sar_launcher.py (meniul grafic) si testat in
test_launcher_core.py. Separarea permite verificarea automata a tuturor
combinatiilor inainte de orice click.
"""
import os
import sys

# middleware-urile ROS 2 Tier-1/2 relevante pentru teza
RMW = {
    "CycloneDDS": "rmw_cyclonedds_cpp",   # implicitul ROS 2 Jazzy
    "Zenoh":      "rmw_zenoh_cpp",        # miezul tezei (cere routerul!)
    "FastDDS":    "rmw_fastrtps_cpp",     # al doilea DDS Tier-1
}
APT = {
    "CycloneDDS": "ros-jazzy-rmw-cyclonedds-cpp",
    "Zenoh":      "ros-jazzy-rmw-zenoh-cpp",
    "FastDDS":    "ros-jazzy-rmw-fastrtps-cpp",
}
MODES = ("sil", "ros", "gazebo")


def _default_roots():
    roots = [p for p in os.environ.get("AMENT_PREFIX_PATH", "").split(":") if p]
    roots.append("/opt/ros/jazzy")
    return roots


def rmw_available(name, roots=None):
    """True daca pachetul RMW e instalat (cauta share/<pachet> in radacini)."""
    pkg = RMW.get(name)
    if pkg is None:
        return False
    for r in (roots if roots is not None else _default_roots()):
        if os.path.isdir(os.path.join(r, "share", pkg)):
            return True
    return False


def build_plan(cfg, pkg_dir):
    """Traduce alegerile din meniu intr-un plan executabil.

    cfg: {mode, rmw, scenario, autostart, dashboard, regen_world}
    Intoarce: {"pre": [cmd...], "cmd": [...], "env": {...}, "router": bool}
    Ridica ValueError pentru combinatii invalide (meniul le afiseaza).
    """
    mode = cfg.get("mode")
    if mode not in MODES:
        raise ValueError(f"mod necunoscut: {mode!r}")
    scen = cfg.get("scenario") or "baseline.yaml"

    if mode == "sil":
        return {"pre": [],
                "cmd": [sys.executable, os.path.join(pkg_dir, "sil_run.py"),
                        os.path.join(pkg_dir, "scenarios", scen)],
                "env": {}, "router": False}

    rmw = cfg.get("rmw")
    if rmw not in RMW:
        raise ValueError(f"middleware necunoscut: {rmw!r} "
                         f"(alege dintre {sorted(RMW)})")
    launch = "sar_ros.launch.py" if mode == "ros" else "sar_gazebo.launch.py"
    cmd = ["ros2", "launch", os.path.join(pkg_dir, "launch", launch),
           f"scenario:={scen}",
           f"autostart:={'true' if cfg.get('autostart', True) else 'false'}",
           f"dashboard:={'true' if cfg.get('dashboard', True) else 'false'}"]
    pre = []
    if mode == "gazebo" and cfg.get("regen_world", True):
        pre.append([sys.executable, os.path.join(pkg_dir, "gen_world.py")])
    return {"pre": pre, "cmd": cmd,
            "env": {"RMW_IMPLEMENTATION": RMW[rmw]},
            "router": rmw == "Zenoh"}


ROUTER_CMD = ["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"]
