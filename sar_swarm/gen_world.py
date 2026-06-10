#!/usr/bin/env python3
"""gen_world.py — genereaza worlds/apocalypse.sdf DIN world_config.py
(sursa unica de adevar: ruinele din Gazebo = obstacolele A* ale dronelor).

Continut: teren 60x60, lumina joasa de amurg (vizibilitate variabila),
7 ruine inalte (no-fly), 3 coloane de fum semi-transparente, 5 victime
(cutii rosii), 6 bucati de moloz DINAMIC (impins la coliziune) si 4 drone
cu senzori (IMU, camera RGB, LiDAR gpu, NavSat cu zgomot = GPS degradat)
plus plugin-uri VelocityControl + OdometryPublisher per drona."""
import xml.dom.minidom
from world_config import WORLD, DRONES

H = 10.0  # inaltimea ruinelor (> altitudinea de zbor 6 m => no-fly real)
COL = {"d1": "0.18 0.45 0.80", "d2": "0.85 0.44 0.18",
       "d3": "0.18 0.55 0.34", "d4": "0.61 0.35 0.71"}
DEBRIS = [(18, 12), (35, 5), (5, 30), (48, 30), (25, 45), (58, 20)]

def ruin(i, r):
    x0, y0, x1, y1 = r
    sx, sy = x1 - x0 + 1, y1 - y0 + 1
    return f"""
    <model name="ruin_{i}"><static>true</static>
      <pose>{x0 + sx/2} {y0 + sy/2} {H/2} 0 0 0</pose>
      <link name="l">
        <collision name="c"><geometry><box><size>{sx} {sy} {H}</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>{sx} {sy} {H}</size></box></geometry>
          <material><ambient>0.32 0.27 0.24 1</ambient><diffuse>0.42 0.36 0.31 1</diffuse></material>
        </visual>
      </link>
    </model>"""

def smoke(i, s):
    x, y, r = s
    return f"""
    <model name="smoke_{i}"><static>true</static>
      <pose>{x} {y} 6 0 0 0</pose>
      <link name="l">
        <visual name="v"><transparency>0.6</transparency>
          <geometry><cylinder><radius>{r}</radius><length>12</length></cylinder></geometry>
          <material><ambient>0.5 0.5 0.5 1</ambient><diffuse>0.55 0.55 0.55 1</diffuse></material>
        </visual>
      </link>
    </model>"""

def victim(i, v):
    return f"""
    <model name="victim_{i}"><static>true</static>
      <pose>{v[0] + 0.5} {v[1] + 0.5} 0.3 0 0 0</pose>
      <link name="l">
        <collision name="c"><geometry><box><size>0.6 0.6 0.6</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>0.6 0.6 0.6</size></box></geometry>
          <material><ambient>0.8 0.1 0.1 1</ambient><diffuse>0.9 0.15 0.15 1</diffuse></material>
        </visual>
      </link>
    </model>"""

def debris(i, p):
    return f"""
    <model name="debris_{i}">
      <pose>{p[0]} {p[1]} 0.25 0.2 0.1 {0.7 * i}</pose>
      <link name="l">
        <inertial><mass>2.0</mass><inertia>
          <ixx>0.083</ixx><iyy>0.083</iyy><izz>0.083</izz>
          <ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <collision name="c"><geometry><box><size>0.7 0.5 0.4</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>0.7 0.5 0.4</size></box></geometry>
          <material><ambient>0.25 0.23 0.21 1</ambient><diffuse>0.33 0.3 0.27 1</diffuse></material>
        </visual>
      </link>
    </model>"""

def drone(did, cell):
    rotors = "".join(f"""
        <visual name="rotor_{k}"><pose>{rx} {ry} 0.07 0 0 0</pose>
          <geometry><cylinder><radius>0.1</radius><length>0.02</length></cylinder></geometry>
          <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.12 0.12 0.12 1</diffuse></material>
        </visual>"""
        for k, (rx, ry) in enumerate([(0.18, 0.18), (0.18, -0.18),
                                      (-0.18, 0.18), (-0.18, -0.18)]))
    return f"""
    <model name="{did}">
      <pose>{cell[0] + 0.5} {cell[1] + 0.5} 0.3 0 0 0</pose>
      <link name="base_link">
        <gravity>false</gravity>
        <inertial><mass>1.2</mass><inertia>
          <ixx>0.01</ixx><iyy>0.01</iyy><izz>0.02</izz>
          <ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <collision name="c"><geometry><box><size>0.4 0.4 0.12</size></box></geometry></collision>
        <visual name="body"><geometry><box><size>0.4 0.4 0.12</size></box></geometry>
          <material><ambient>{COL[did]} 1</ambient><diffuse>{COL[did]} 1</diffuse></material>
        </visual>{rotors}
        <sensor name="imu" type="imu">
          <update_rate>100</update_rate><topic>/model/{did}/imu</topic>
        </sensor>
        <sensor name="camera" type="camera">
          <update_rate>15</update_rate><topic>/model/{did}/camera</topic>
          <camera><horizontal_fov>1.25</horizontal_fov>
            <image><width>320</width><height>240</height></image>
            <clip><near>0.1</near><far>80</far></clip></camera>
        </sensor>
        <sensor name="lidar" type="gpu_lidar">
          <update_rate>10</update_rate><topic>/model/{did}/lidar</topic>
          <lidar><scan><horizontal><samples>360</samples><resolution>1</resolution>
            <min_angle>-3.1416</min_angle><max_angle>3.1416</max_angle></horizontal></scan>
          <range><min>0.2</min><max>30</max><resolution>0.05</resolution></range></lidar>
        </sensor>
        <sensor name="navsat" type="navsat">
          <update_rate>5</update_rate><topic>/model/{did}/navsat</topic>
          <navsat><position_sensing>
            <horizontal><noise type="gaussian"><mean>0</mean><stddev>1.5</stddev></noise></horizontal>
            <vertical><noise type="gaussian"><mean>0</mean><stddev>3.0</stddev></noise></vertical>
          </position_sensing></navsat>
        </sensor>
      </link>
      <plugin filename="gz-sim-velocity-control-system"
              name="gz::sim::systems::VelocityControl">
        <topic>/model/{did}/cmd_vel</topic>
      </plugin>
      <plugin filename="gz-sim-odometry-publisher-system"
              name="gz::sim::systems::OdometryPublisher">
        <odom_topic>/model/{did}/odometry</odom_topic>
        <odom_frame>{did}/odom</odom_frame>
        <robot_base_frame>{did}/base_link</robot_base_frame>
        <odom_publish_frequency>30</odom_publish_frequency>
        <dimensions>3</dimensions>
      </plugin>
    </model>"""

W = WORLD["w_cells"] * WORLD["cell"]
sdf = f"""<?xml version="1.0"?>
<sdf version="1.8">
  <world name="apocalypse">
    <physics name="default" type="ignored"><max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine></plugin>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-navsat-system" name="gz::sim::systems::NavSat"/>
    <spherical_coordinates><surface_model>EARTH_WGS84</surface_model>
      <latitude_deg>44.4268</latitude_deg><longitude_deg>26.1025</longitude_deg>
      <elevation>80</elevation><heading_deg>0</heading_deg></spherical_coordinates>
    <scene><ambient>0.28 0.26 0.24 1</ambient>
      <background>0.45 0.38 0.32 1</background><shadows>true</shadows></scene>
    <light type="directional" name="sun_dusk">
      <cast_shadows>true</cast_shadows><pose>0 0 60 0 0 0</pose>
      <diffuse>0.7 0.55 0.4 1</diffuse><specular>0.2 0.2 0.2 1</specular>
      <direction>-0.4 0.2 -0.5</direction>
    </light>
    <model name="ground"><static>true</static>
      <pose>{W/2} {W/2} 0 0 0 0</pose>
      <link name="l">
        <collision name="c"><geometry><plane><normal>0 0 1</normal>
          <size>{W} {W}</size></plane></geometry></collision>
        <visual name="v"><geometry><plane><normal>0 0 1</normal>
          <size>{W} {W}</size></plane></geometry>
          <material><ambient>0.36 0.33 0.29 1</ambient>
            <diffuse>0.4 0.37 0.33 1</diffuse></material>
        </visual>
      </link>
    </model>
{"".join(ruin(i, r) for i, r in enumerate(WORLD["ruins"]))}
{"".join(smoke(i, s) for i, s in enumerate(WORLD["smoke"]))}
{"".join(victim(i, v) for i, v in enumerate(WORLD["victims"]))}
{"".join(debris(i, p) for i, p in enumerate(DEBRIS))}
{"".join(drone(d, c) for d, c in sorted(DRONES.items()))}
  </world>
</sdf>
"""
open("worlds/apocalypse.sdf", "w").write(sdf)
xml.dom.minidom.parse("worlds/apocalypse.sdf")  # validare XML
n_models = sdf.count("<model name=")
print(f"[ok] worlds/apocalypse.sdf — XML valid, {n_models} modele, {len(sdf)} bytes")
