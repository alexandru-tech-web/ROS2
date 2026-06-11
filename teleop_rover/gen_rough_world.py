#!/usr/bin/env python3
"""gen_rough_world.py — genereaza worlds/teleop_rough.sdf (+ heightmap PNG) DIN
config: un rover cu 4 ROTI skid-steer pe TEREN ACCIDENTAT, cu CAMERA + LIDAR si
tinte COLORATE la coordonate cunoscute (adevarul-teren pentru analizor).

Sursa unica, ca la gen_rover_world.py: lista OBJECTS (coordonatele tintelor)
e folosita atat aici (modelele colorate din Gazebo) cat si de analyze_perception
(eroarea de localizare a detectorului fata de adevar).

Filosofie: lumea e GENERATA din config; validata XML aici (xml.dom.minidom).
Randarea senzorilor (camera/gpu_lidar) cere ogre2/GPU -> prima rulare la tine.

Capcane heightmap (respectate mai jos):
  - imaginea TREBUIE patrata si de dimensiune 2^k+1 (aici 129);
  - <uri> e cale ABSOLUTA file:// (cwd nu e de incredere la incarcare);
  - heightmap apare in COLLISION (fizica) SI in VISUAL (camera) — altfel roverul
    cade prin teren sau camera nu vede nimic;
  - <size> = "X Y Zscale" [m]; Zscale mic (1.0 m) ca skid-steer-ul sa il poata urca;
  - motor ogre2 + pluginul Sensors sunt obligatorii pentru camera/lidar.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- config: tintele colorate (adevarul-teren) ---
OBJECTS = [
    {"name": "target_red",   "color": "red",   "xy": (8.0, 3.0)},
    {"name": "target_green", "color": "green", "xy": (-6.0, 5.0)},
    {"name": "target_blue",  "color": "blue",  "xy": (5.0, -7.0)},
]
RGB = {"red": (0.80, 0.10, 0.10), "green": (0.12, 0.70, 0.18),
       "blue": (0.15, 0.32, 0.85), "yellow": (0.85, 0.80, 0.10)}

HMAP_N = 129          # 2^7 + 1 (OBLIGATORIU 2^k+1)
TERR_XY = 40.0        # latura terenului [m]
TERR_Z = 1.0          # amplitudinea maxima [m] (mic = traversabil)
SPAWN_Z = 0.85        # roverul porneste putin peste teren si se aseaza


def value_noise(n=HMAP_N, octaves=4, seed=7):
    """Zgomot fractal (value-noise) n x n in [0,1], cu un disc central aplatizat
    pentru o zona de pornire mai linistita a roverului."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((n, n), np.float64)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = 2 ** (o + 1) + 1
        grid = rng.random((cells, cells))
        up = cv2.resize(grid, (n, n), interpolation=cv2.INTER_CUBIC)
        acc += amp * up
        total += amp
        amp *= 0.5
    acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-9)
    # aplatizeaza un disc central spre o valoare medie (zona de spawn)
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - n / 2, yy - n / 2) / (n / 2)
    flat = np.clip(1.0 - r / 0.25, 0.0, 1.0)        # 1 in centru -> 0 la r=0.25
    acc = acc * (1 - flat) + 0.4 * flat
    return acc


def write_heightmap(path):
    arr = (value_noise() * 255).astype(np.uint8)
    cv2.imwrite(path, arr)                            # PNG grayscale 1 canal
    return arr


def skid_wheel(name, xp, yp):
    """O roata motoare (cilindru), joint revolute. 4 instante (skid-steer)."""
    return f"""
      <link name="{name}"><pose>{xp} {yp} 0.12 -1.5708 0 0</pose>
        <inertial><mass>0.7</mass><inertia><ixx>0.003</ixx><iyy>0.003</iyy>
          <izz>0.005</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <visual name="v"><geometry><cylinder><radius>0.12</radius>
          <length>0.06</length></cylinder></geometry>
          <material><ambient>0.08 0.08 0.08 1</ambient></material></visual>
        <collision name="c"><geometry><cylinder><radius>0.12</radius>
          <length>0.06</length></cylinder></geometry>
          <surface><friction><ode><mu>1.4</mu><mu2>1.2</mu2></ode>
          </friction></surface></collision></link>
      <joint name="{name}_joint" type="revolute">
        <parent>chassis</parent><child>{name}</child>
        <axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis>
      </joint>"""


def target_model(obj):
    """Tinta colorata: un stalp (cilindru) vizibil peste teren, la (x,y) cunoscut."""
    x, y = obj["xy"]
    rr, gg, bb = RGB[obj["color"]]
    return f"""
    <model name="{obj['name']}"><static>true</static>
      <pose>{x:.2f} {y:.2f} 1.0 0 0 0</pose>
      <link name="l">
        <visual name="v"><geometry><cylinder><radius>0.35</radius>
          <length>2.0</length></cylinder></geometry>
          <material><ambient>{rr} {gg} {bb} 1</ambient>
          <diffuse>{rr} {gg} {bb} 1</diffuse></material></visual>
        <collision name="c"><geometry><cylinder><radius>0.35</radius>
          <length>2.0</length></cylinder></geometry></collision></link>
    </model>"""


def camera_sensor():
    """Camera frontala, usor inclinata in jos ca sa vada tintele pe teren."""
    return """
        <sensor name="front_camera" type="camera">
          <pose>0.34 0 0.18 0 0.2 0</pose>
          <topic>camera/image</topic>
          <update_rate>15</update_rate>
          <always_on>1</always_on>
          <visualize>true</visualize>
          <camera>
            <horizontal_fov>1.0472</horizontal_fov>
            <image><width>320</width><height>240</height><format>R8G8B8</format></image>
            <clip><near>0.05</near><far>60</far></clip>
          </camera>
        </sensor>"""


def lidar_sensor():
    return """
        <sensor name="front_lidar" type="gpu_lidar">
          <pose>0.3 0 0.2 0 0 0</pose>
          <topic>scan</topic>
          <update_rate>10</update_rate>
          <always_on>1</always_on>
          <lidar><scan><horizontal><samples>360</samples><resolution>1</resolution>
            <min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle></horizontal></scan>
            <range><min>0.12</min><max>12.0</max><resolution>0.01</resolution></range>
          </lidar>
        </sensor>"""


def main():
    os.makedirs("worlds", exist_ok=True)
    worlds_abs = os.path.abspath("worlds")
    png_path = os.path.join(worlds_abs, "teleop_rough_height.png")
    write_heightmap(png_path)
    uri = "file://" + png_path

    heightmap = f"""<heightmap>
        <uri>{uri}</uri>
        <size>{TERR_XY} {TERR_XY} {TERR_Z}</size>
        <pos>0 0 0</pos>
      </heightmap>"""

    targets = "".join(target_model(o) for o in OBJECTS)

    sdf = f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="teleop_rough">
    <physics name="p" type="ignored"><max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system"
            name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system"
            name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose><diffuse>0.95 0.92 0.86 1</diffuse>
      <direction>-0.4 0.2 -0.9</direction></light>

    <model name="terrain"><static>true</static>
      <link name="l">
        <collision name="c"><geometry>{heightmap}</geometry></collision>
        <visual name="v"><geometry>{heightmap}</geometry>
          <material><ambient>0.50 0.45 0.36 1</ambient>
          <diffuse>0.52 0.47 0.38 1</diffuse></material></visual>
      </link>
    </model>
    {targets}

    <model name="rover">
      <pose>0 0 {SPAWN_Z} 0 0 0</pose>
      <link name="chassis"><pose>0 0 0.18 0 0 0</pose>
        <inertial><mass>5.0</mass><inertia><ixx>0.07</ixx><iyy>0.12</iyy>
          <izz>0.16</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <visual name="v"><geometry><box><size>0.6 0.4 0.18</size></box>
          </geometry><material><ambient>0.18 0.45 0.8 1</ambient>
          <diffuse>0.18 0.45 0.8 1</diffuse></material></visual>
        <collision name="c"><geometry><box><size>0.6 0.4 0.18</size></box>
          </geometry></collision>
        {camera_sensor()}
        {lidar_sensor()}
      </link>
      {skid_wheel('fl_wheel', 0.2, 0.21)}
      {skid_wheel('rl_wheel', -0.2, 0.21)}
      {skid_wheel('fr_wheel', 0.2, -0.21)}
      {skid_wheel('rr_wheel', -0.2, -0.21)}
      <plugin filename="gz-sim-diff-drive-system"
              name="gz::sim::systems::DiffDrive">
        <left_joint>fl_wheel_joint</left_joint>
        <left_joint>rl_wheel_joint</left_joint>
        <right_joint>fr_wheel_joint</right_joint>
        <right_joint>rr_wheel_joint</right_joint>
        <wheel_separation>0.42</wheel_separation>
        <wheel_radius>0.12</wheel_radius>
        <odom_publish_frequency>30</odom_publish_frequency>
        <topic>/model/rover/cmd_vel</topic>
        <odom_topic>/model/rover/odometry</odom_topic>
      </plugin>
    </model>
  </world>
</sdf>
"""
    out = "worlds/teleop_rough.sdf"
    open(out, "w").write(sdf)
    import xml.dom.minidom
    xml.dom.minidom.parse(out)
    print(f"[ok] {out} — XML valid, {len(sdf.splitlines())} linii; "
          f"4 roti skid-steer, {len(OBJECTS)} tinte, "
          f"heightmap {HMAP_N}x{HMAP_N} ({TERR_XY}x{TERR_XY}x{TERR_Z} m) -> {png_path}")


if __name__ == "__main__":
    main()
