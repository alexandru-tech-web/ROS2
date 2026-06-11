#!/usr/bin/env python3
"""patch_world_sensors.py — injecteaza senzori in lumea Gazebo existenta.

Ia worlds/teleop_course.sdf (sau orice SDF) si adauga, fara sa-l editezi
manual:
  - la nivel de <world>: pluginul de randare a senzorilor
      gz::sim::systems::Sensors (obligatoriu pt. gpu_lidar/camera)
    si, optional, gz::sim::systems::Imu / gz::sim::systems::NavSat
    (+ <spherical_coordinates> pentru NavSat);
  - in link-ul ales al modelului ales: senzorul gpu_lidar (360 de raze,
    0.12-12 m, 10 Hz, topic "scan"), optional imu si navsat.

Idempotent: daca senzorul/pluginul exista deja, nu il dubleaza.

Folosire (pe masina ta cu Jazzy + Gazebo Harmonic):
  python3 patch_world_sensors.py worlds/teleop_course.sdf \
      worlds/teleop_course_sensors.sdf --model rover --link chassis \
      --lidar --imu
  gz sim worlds/teleop_course_sensors.sdf
  ros2 run ros_gz_bridge parameter_bridge --ros-args \
      -p config_file:=bridge_rover.yaml
"""
import argparse
import sys
import xml.etree.ElementTree as ET

LIDAR_XML = """<sensor name="front_lidar" type="gpu_lidar">
  <pose>0.25 0 0.25 0 0 0</pose>
  <topic>scan</topic>
  <update_rate>10</update_rate>
  <always_on>1</always_on>
  <visualize>true</visualize>
  <lidar>
    <scan>
      <horizontal>
        <samples>360</samples>
        <resolution>1</resolution>
        <min_angle>-3.14159</min_angle>
        <max_angle>3.14159</max_angle>
      </horizontal>
    </scan>
    <range>
      <min>0.12</min>
      <max>12.0</max>
      <resolution>0.01</resolution>
    </range>
  </lidar>
</sensor>"""

IMU_XML = """<sensor name="imu_sensor" type="imu">
  <topic>imu</topic>
  <update_rate>100</update_rate>
  <always_on>1</always_on>
</sensor>"""

NAVSAT_XML = """<sensor name="navsat_sensor" type="navsat">
  <topic>navsat</topic>
  <update_rate>10</update_rate>
  <always_on>1</always_on>
</sensor>"""

SPHERICAL_XML = """<spherical_coordinates>
  <surface_model>EARTH_WGS84</surface_model>
  <world_frame_orientation>ENU</world_frame_orientation>
  <latitude_deg>44.4396</latitude_deg>
  <longitude_deg>26.0963</longitude_deg>
  <elevation>80</elevation>
  <heading_deg>0</heading_deg>
</spherical_coordinates>"""

WORLD_PLUGINS = {
    "sensors": ('gz-sim-sensors-system', 'gz::sim::systems::Sensors',
                '<render_engine>ogre2</render_engine>'),
    "imu": ('gz-sim-imu-system', 'gz::sim::systems::Imu', ''),
    "navsat": ('gz-sim-navsat-system', 'gz::sim::systems::NavSat', ''),
}


def has_plugin(world, name):
    return any(p.get("name") == name for p in world.findall("plugin"))


def add_world_plugin(world, key):
    fname, name, inner = WORLD_PLUGINS[key]
    if has_plugin(world, name):
        return False
    el = ET.fromstring(f'<plugin filename="{fname}" name="{name}">'
                       f'{inner}</plugin>')
    world.insert(0, el)
    return True


def find_link(root, model_name, link_name):
    for model in root.iter("model"):
        if model.get("name") == model_name:
            for link in model.findall("link"):
                if link.get("name") == link_name:
                    return link
            avail = [ln.get("name") for ln in model.findall("link")]
            sys.exit(f"[eroare] modelul '{model_name}' nu are link-ul "
                     f"'{link_name}'; disponibile: {avail}")
    sys.exit(f"[eroare] nu am gasit modelul '{model_name}' in lume")


def add_sensor(link, xml_text):
    sensor = ET.fromstring(xml_text)
    name = sensor.get("name")
    if any(s.get("name") == name for s in link.findall("sensor")):
        return False
    link.append(sensor)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--model", default="rover")
    ap.add_argument("--link", default="chassis")
    ap.add_argument("--lidar", action="store_true")
    ap.add_argument("--imu", action="store_true")
    ap.add_argument("--navsat", action="store_true")
    args = ap.parse_args()

    tree = ET.parse(args.input)
    root = tree.getroot()
    world = root.find("world")
    if world is None:
        sys.exit("[eroare] fisierul nu contine <world>")

    changed = []
    link = find_link(root, args.model, args.link)
    if args.lidar:
        if add_world_plugin(world, "sensors"):
            changed.append("plugin Sensors (world)")
        if add_sensor(link, LIDAR_XML):
            changed.append("gpu_lidar -> topic gz 'scan'")
    if args.imu:
        if add_world_plugin(world, "imu"):
            changed.append("plugin Imu (world)")
        if add_sensor(link, IMU_XML):
            changed.append("imu -> topic gz 'imu'")
    if args.navsat:
        if add_world_plugin(world, "navsat"):
            changed.append("plugin NavSat (world)")
        if world.find("spherical_coordinates") is None:
            world.insert(0, ET.fromstring(SPHERICAL_XML))
            changed.append("spherical_coordinates (Bucuresti)")
        if add_sensor(link, NAVSAT_XML):
            changed.append("navsat -> topic gz 'navsat'")

    ET.indent(tree, space="  ")
    tree.write(args.output, encoding="unicode", xml_declaration=True)
    print(f"[ok] scris {args.output}")
    for c in changed:
        print(f"  + {c}")
    if not changed:
        print("  (nimic de adaugat — totul exista deja)")


if __name__ == "__main__":
    main()
