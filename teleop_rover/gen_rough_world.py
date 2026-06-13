#!/usr/bin/env python3
"""gen_rough_world.py - genereaza worlds/teleop_rough.sdf + un teren MESH TEXTURAT
(.obj + .mtl + .png) DIN config: rover cu 4 ROTI skid-steer pe TEREN ACCIDENTAT,
COLORAT dupa inaltime (colormap terrain), cu CAMERA + LIDAR si tinte colorate.

DE CE MESH (nu heightmap): dartsim nu face coliziune din <heightmap> (roverul ar
cadea prin teren) si shaderul de heightmap ogre2 nu compileaza pe unele GPU-uri
(GUI crapa). Un mesh trimesh rezolva ambele.

CULOAREA: o textura PNG (inaltime -> colormap 'terrain') mapata pe mesh prin
coordonate UV; materialul (MTL) o leaga. Asa terenul arata ca in previzualizare
(albastru jos, verde, galben, maro, alb pe varfuri), nu maro uniform.

Dependinte: numpy + matplotlib (pentru textura). Validare XML aici.

  python3 gen_rough_world.py
"""
import os
import sys

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

TERR_XY = 40.0        # latura terenului [m]
TERR_Z = 0.8          # amplitudinea denivelarilor [m] (mai mare = mai accidentat, dar mai greu de condus)
TERR_N = 101          # vertecsi pe latura (~20000 triunghiuri; coliziune OK)
SPAWN_Z = 0.75        # roverul porneste putin peste teren si se aseaza
SEED = 7
TEX_RES = 512         # rezolutia texturii de culoare


def _upsample(grid, n):
    """Interpolare bilineara a unei grile mici la n x n (numpy, fara cv2)."""
    c = grid.shape[0]
    xs = np.linspace(0, c - 1, n)
    tmp = np.empty((c, n))
    for i in range(c):
        tmp[i] = np.interp(xs, np.arange(c), grid[i])
    out = np.empty((n, n))
    for j in range(n):
        out[:, j] = np.interp(xs, np.arange(c), tmp[:, j])
    return out


def value_noise(n=TERR_N, octaves=6, persistence=0.55, seed=SEED):
    """Zgomot fractal n x n in [0,1] cu MULTE denivelari (frecventa de baza
    ridicata, nu un singur deal), cu un disc central mic aplatizat (spawn)."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((n, n))
    amp = 1.0
    for o in range(octaves):
        cells = 2 ** (o + 2) + 1
        acc += amp * _upsample(rng.random((cells, cells)), n)
        amp *= persistence
    acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-9)
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - n / 2, yy - n / 2) / (n / 2)
    flat = np.clip(1.0 - r / 0.12, 0.0, 1.0)
    return acc * (1 - flat) + 0.5 * flat


def write_texture(png_path, h):
    """Inaltime -> imagine color (colormap terrain), salvata ca textura PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.cm as cm
    import matplotlib.pyplot as plt
    hi = np.clip(_upsample(h, TEX_RES), 0.0, 1.0)
    rgba = cm.terrain(hi)
    plt.imsave(png_path, rgba, origin="lower")


def write_terrain_obj(obj_path, mtl_path, tex_name, h):
    """Mesh texturat: vertecsi + UV + normale + fete (v/vt/vn), cu material MTL."""
    n = h.shape[0]
    xs = np.linspace(-TERR_XY / 2, TERR_XY / 2, n)
    ys = np.linspace(-TERR_XY / 2, TERR_XY / 2, n)
    Z = h * TERR_Z
    gy, gx = np.gradient(Z, ys, xs)
    with open(obj_path, "w") as f:
        f.write("# teleop_rough terrain mesh texturat\n")
        f.write(f"mtllib {os.path.basename(mtl_path)}\n")
        for j in range(n):
            for i in range(n):
                f.write(f"v {xs[i]:.4f} {ys[j]:.4f} {Z[j, i]:.4f}\n")
        for j in range(n):
            for i in range(n):
                f.write(f"vt {i / (n - 1):.4f} {j / (n - 1):.4f}\n")
        for j in range(n):
            for i in range(n):
                nx, ny, nz = -gx[j, i], -gy[j, i], 1.0
                ln = (nx * nx + ny * ny + nz * nz) ** 0.5
                f.write(f"vn {nx / ln:.4f} {ny / ln:.4f} {nz / ln:.4f}\n")
        f.write("usemtl terrain_mat\n")

        def k(i, j):
            return j * n + i + 1

        for j in range(n - 1):
            for i in range(n - 1):
                a, b, c, d = k(i, j), k(i + 1, j), k(i + 1, j + 1), k(i, j + 1)
                f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")
                f.write(f"f {a}/{a}/{a} {c}/{c}/{c} {d}/{d}/{d}\n")
    with open(mtl_path, "w") as m:
        m.write("newmtl terrain_mat\n")
        m.write("Ka 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\n")
        m.write(f"map_Kd {tex_name}\n")
    return n, 2 * (n - 1) * (n - 1)


def terrain_height_at(h, x, y):
    n = h.shape[0]
    i = min(max(int((x + TERR_XY / 2) / TERR_XY * (n - 1)), 0), n - 1)
    j = min(max(int((y + TERR_XY / 2) / TERR_XY * (n - 1)), 0), n - 1)
    return float(h[j, i] * TERR_Z)


def skid_wheel(name, xp, yp):
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


def camera_sensor():
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


def target_model(o, h):
    r, g, b = RGB[o["color"]]
    x, y = o["xy"]
    z = terrain_height_at(h, x, y) + 1.0
    return f"""
    <model name="{o['name']}"><static>true</static>
      <pose>{x:.2f} {y:.2f} {z:.2f} 0 0 0</pose>
      <link name="l">
        <visual name="v"><geometry><cylinder><radius>0.35</radius>
          <length>2.0</length></cylinder></geometry>
          <material><ambient>{r} {g} {b} 1</ambient>
          <diffuse>{r} {g} {b} 1</diffuse></material></visual>
        <collision name="c"><geometry><cylinder><radius>0.35</radius>
          <length>2.0</length></cylinder></geometry></collision></link>
    </model>"""


def gcs_station_model(h, x=-16.0, y=-16.0):
    """Statie GCS reprezentativa (container + catarg + varf rosu), asezata pe teren."""
    z = terrain_height_at(h, x, y)
    return f"""
    <model name="gcs_station"><static>true</static>
      <pose>{x:.2f} {y:.2f} {z:.2f} 0 0 0.6</pose>
      <link name="l">
        <visual name="box"><pose>0 0 0.45 0 0 0</pose>
          <geometry><box><size>1.4 1.0 0.9</size></box></geometry>
          <material><ambient>0.22 0.24 0.26 1</ambient>
          <diffuse>0.22 0.24 0.26 1</diffuse></material></visual>
        <collision name="cbox"><pose>0 0 0.45 0 0 0</pose>
          <geometry><box><size>1.4 1.0 0.9</size></box></geometry></collision>
        <visual name="mast"><pose>0.5 0 1.6 0 0 0</pose>
          <geometry><cylinder><radius>0.05</radius><length>2.2</length></cylinder></geometry>
          <material><ambient>0.7 0.7 0.7 1</ambient></material></visual>
        <visual name="tip"><pose>0.5 0 2.75 0 0 0</pose>
          <geometry><sphere><radius>0.12</radius></sphere></geometry>
          <material><ambient>0.85 0.1 0.1 1</ambient>
          <diffuse>0.85 0.1 0.1 1</diffuse></material></visual>
      </link>
    </model>"""


def main():
    os.makedirs("worlds", exist_ok=True)
    worlds_abs = os.path.abspath("worlds")
    obj_path = os.path.join(worlds_abs, "teleop_rough_terrain.obj")
    mtl_path = os.path.join(worlds_abs, "teleop_rough_terrain.mtl")
    tex_name = "teleop_rough_terrain.png"
    tex_path = os.path.join(worlds_abs, tex_name)

    h = value_noise()
    write_texture(tex_path, h)
    nverts, nfaces = write_terrain_obj(obj_path, mtl_path, tex_name, h)
    uri = "file://" + obj_path

    mesh = f"""<mesh><uri>{uri}</uri></mesh>"""
    targets = "".join(target_model(o, h) for o in OBJECTS)
    gcs = gcs_station_model(h)

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
        <collision name="c"><geometry>{mesh}</geometry></collision>
        <visual name="v"><geometry>{mesh}</geometry></visual>
      </link>
    </model>
    {targets}
    {gcs}

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
    print(f"[ok] {out} - XML valid, {len(sdf.splitlines())} linii; 4 roti, {len(OBJECTS)} tinte.")
    print(f"[ok] teren MESH TEXTURAT -> {obj_path}")
    print(f"     ({nverts}x{nverts} vertecsi, {nfaces} triunghiuri, "
          f"{TERR_XY}x{TERR_XY} m, amplitudine {TERR_Z} m)")
    print(f"[ok] textura -> {tex_path}  (+ {os.path.basename(mtl_path)})")


if __name__ == "__main__":
    main()
