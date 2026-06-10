#!/usr/bin/env python3
"""gen_rover_world.py — genereaza worlds/teleop_course.sdf DIN rover_core
(sursa unica: portile din Gazebo = traseul pilotului si al CTE-ului).
Rover diferential cu plugin gz DiffDrive (+ odometrie), porti din stalpi."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rover_core import COURSE

def post(x, y, name):
    return f"""
    <model name="{name}"><static>true</static>
      <pose>{x:.2f} {y:.2f} 0.6 0 0 0</pose>
      <link name="l"><visual name="v"><geometry><cylinder>
        <radius>0.06</radius><length>1.2</length></cylinder></geometry>
        <material><ambient>0.85 0.45 0.18 1</ambient>
        <diffuse>0.85 0.45 0.18 1</diffuse></material></visual>
      <collision name="c"><geometry><cylinder><radius>0.06</radius>
        <length>1.2</length></cylinder></geometry></collision></link>
    </model>"""

def wheel(name, ypos):
    return f"""
      <link name="{name}"><pose>0 {ypos} 0.12 -1.5708 0 0</pose>
        <inertial><mass>0.6</mass><inertia><ixx>0.002</ixx><iyy>0.002</iyy>
          <izz>0.004</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <visual name="v"><geometry><cylinder><radius>0.12</radius>
          <length>0.05</length></cylinder></geometry>
          <material><ambient>0.1 0.1 0.1 1</ambient></material></visual>
        <collision name="c"><geometry><cylinder><radius>0.12</radius>
          <length>0.05</length></cylinder></geometry>
          <surface><friction><ode><mu>1.1</mu><mu2>1.1</mu2></ode>
          </friction></surface></collision></link>
      <joint name="{name}_joint" type="revolute">
        <parent>chassis</parent><child>{name}</child>
        <axis><xyz>0 0 1</xyz></axis></joint>"""

parts = [post(gx, gy + dy, f"gate_{i}_{j}")
         for i, (gx, gy) in enumerate(COURSE)
         for j, dy in enumerate((+0.9, -0.9))]
sdf = f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="teleop_course">
    <physics name="p" type="ignored"><max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system"
            name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system"
            name="gz::sim::systems::SceneBroadcaster"/>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose><diffuse>0.9 0.85 0.8 1</diffuse>
      <direction>-0.4 0.2 -0.9</direction></light>
    <model name="ground"><static>true</static><link name="l">
      <collision name="c"><geometry><plane><normal>0 0 1</normal>
        <size>100 100</size></plane></geometry></collision>
      <visual name="v"><geometry><plane><normal>0 0 1</normal>
        <size>100 100</size></plane></geometry>
        <material><ambient>0.45 0.42 0.38 1</ambient>
        <diffuse>0.45 0.42 0.38 1</diffuse></material></visual></link></model>
    {''.join(parts)}
    <model name="rover">
      <pose>0 0 0.0 0 0 0</pose>
      <link name="chassis"><pose>0 0 0.18 0 0 0</pose>
        <inertial><mass>4.0</mass><inertia><ixx>0.05</ixx><iyy>0.09</iyy>
          <izz>0.12</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <visual name="v"><geometry><box><size>0.5 0.35 0.16</size></box>
          </geometry><material><ambient>0.18 0.45 0.8 1</ambient>
          <diffuse>0.18 0.45 0.8 1</diffuse></material></visual>
        <collision name="c"><geometry><box><size>0.5 0.35 0.16</size></box>
          </geometry></collision></link>
      {wheel('left_wheel', 0.21)}
      {wheel('right_wheel', -0.21)}
      <link name="caster"><pose>0.2 0 0.05 0 0 0</pose>
        <inertial><mass>0.2</mass><inertia><ixx>0.0004</ixx><iyy>0.0004</iyy>
          <izz>0.0004</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <visual name="v"><geometry><sphere><radius>0.05</radius></sphere>
          </geometry></visual>
        <collision name="c"><geometry><sphere><radius>0.05</radius></sphere>
          </geometry><surface><friction><ode><mu>0.0</mu><mu2>0.0</mu2>
          </ode></friction></surface></collision></link>
      <joint name="caster_joint" type="ball">
        <parent>chassis</parent><child>caster</child></joint>
      <plugin filename="gz-sim-diff-drive-system"
              name="gz::sim::systems::DiffDrive">
        <left_joint>left_wheel_joint</left_joint>
        <right_joint>right_wheel_joint</right_joint>
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
os.makedirs("worlds", exist_ok=True)
open("worlds/teleop_course.sdf", "w").write(sdf)
import xml.dom.minidom
xml.dom.minidom.parse("worlds/teleop_course.sdf")
print(f"[ok] worlds/teleop_course.sdf — XML valid, "
      f"{len(sdf.splitlines())} linii, {2*len(COURSE)} stalpi de poarta")
