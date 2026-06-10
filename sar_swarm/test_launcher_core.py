#!/usr/bin/env python3
"""test_launcher_core.py — verificari pentru logica meniului de misiune."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launcher_core import RMW, rmw_available, build_plan

N = 0
def check(c, m):
    global N; assert c, m; N += 1; print(f"  [ok] {m}")

# rmw_available pe radacini controlate
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "share", "rmw_zenoh_cpp"))
check(rmw_available("Zenoh", roots=[tmp]), "detecteaza RMW instalat")
check(not rmw_available("FastDDS", roots=[tmp]), "raporteaza RMW lipsa")
check(not rmw_available("Inexistent", roots=[tmp]), "nume necunoscut -> False")

p = build_plan(dict(mode="sil", scenario="loss_30.yaml"), "/pkg")
check(p["cmd"][1].endswith("sil_run.py") and p["cmd"][2].endswith("scenarios/loss_30.yaml")
      and p["env"] == {} and not p["router"] and p["pre"] == [],
      "SIL: sil_run + scenariu, fara RMW/router")

p = build_plan(dict(mode="ros", rmw="Zenoh", scenario="baseline.yaml",
                    autostart=False, dashboard=True), "/pkg")
check(p["env"] == {"RMW_IMPLEMENTATION": "rmw_zenoh_cpp"} and p["router"],
      "ROS+Zenoh: env corect si router pornit")
check("scenario:=baseline.yaml" in p["cmd"] and "autostart:=false" in p["cmd"]
      and "dashboard:=true" in p["cmd"] and p["cmd"][2].endswith("sar_ros.launch.py"),
      "ROS: launch + argumentele traduse corect")

p = build_plan(dict(mode="gazebo", rmw="CycloneDDS", scenario="none.yaml",
                    regen_world=True), "/pkg")
check(p["cmd"][2].endswith("sar_gazebo.launch.py") and len(p["pre"]) == 1
      and p["pre"][0][1].endswith("gen_world.py") and not p["router"],
      "Gazebo: gen_world inainte + launch-ul corect")
p = build_plan(dict(mode="gazebo", rmw="FastDDS", regen_world=False), "/pkg")
check(p["pre"] == [] and p["env"]["RMW_IMPLEMENTATION"] == "rmw_fastrtps_cpp",
      "Gazebo fara regenerare; FastDDS mapat corect")

for bad in (dict(mode="zbor"), dict(mode="ros", rmw="MQTT"),
            dict(mode="gazebo", rmw=None)):
    try:
        build_plan(bad, "/pkg"); ok = False
    except ValueError:
        ok = True
    check(ok, f"combinatie invalida respinsa: {bad}")

print(f"\nTOATE TESTELE LAUNCHER AU TRECUT: {N} verificari.")
