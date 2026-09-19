#!/usr/bin/env python3
"""gen_bench_model.py -- geometrie SCHEMATICA a bancului, necalibrata.

Trei motoare A albastre stau in stanga, trei motoare B negre in dreapta.
Fiecare A/B impart un ax rigid cu doua flanse si sase suruburi ilustrative.
Dimensiunile nu sunt extrase din CAD sau masuratori ale standului real.

O SINGURA tabela de geometrie -> AMBELE fisiere:
    urdf/joint_bench.urdf        (RViz; culori INLINE per visual,
                                  fiindca RViz2 nu rezolva mereu
                                  materialele definite doar global)
    gz/joint_bench_world.sdf     (Gazebo; modelul e ANCORAT de lume cu
                                  un joint fix -- altfel, fara coliziuni,
                                  cadea prin podea si "disparea")
Ruleaza:  python3 tools/gen_bench_model.py
"""
import os
from math import cos, pi, sin

H = pi / 2
CUL = {"albastru": "0.13 0.32 0.65 1", "motor_a": "0.03 0.55 0.83 1",
       "negru": "0.10 0.10 0.10 1",
       "portocaliu": "0.91 0.35 0.05 1", "gri": "0.55 0.55 0.55 1",
       "gri_inchis": "0.30 0.30 0.30 1", "rosu": "0.95 0.01 0.01 1"}

BASE_H = 0.78
SHAFT_H = 0.90
ROW_Y = (-0.28, 0.0, 0.28)
# z-ul local al axului devine x-ul global: A in stanga, B in dreapta.
JRPY = (0, H, 0)
PAIRS = [(0, y, SHAFT_H) for y in ROW_Y]


def box(link, sz, xyz, rpy=(0, 0, 0), c="albastru"):
    return dict(link=link, kind="box", sz=sz, xyz=xyz, rpy=rpy, c=c)


def cyl(link, r, l, xyz, rpy=(0, 0, 0), c="albastru"):
    return dict(link=link, kind="cyl", r=r, l=l, xyz=xyz, rpy=rpy, c=c)


def geometrie():
    V = []
    B = "base_link"
    # Masa: cadru portocaliu si patru picioare.
    for sx in (-0.57, 0.57):
        V.append(box(B, (0.05, 0.94, 0.05), (sx, 0, BASE_H),
                     c="portocaliu"))
    for sy in (-0.45, 0.45):
        V.append(box(B, (1.19, 0.05, 0.05), (0, sy, BASE_H),
                     c="portocaliu"))
    for sx in (-0.55, 0.55):
        for sy in (-0.43, 0.43):
            V.append(box(B, (0.05, 0.05, BASE_H),
                         (sx, sy, BASE_H / 2), c="portocaliu"))

    # Trei perechi; fiecare rand are A in stanga si B in dreapta.
    for y in ROW_Y:
        for side, x, color in ((-1, -0.26, "motor_a"),
                               (1, 0.26, "negru")):
            V.append(box(B, (0.20, 0.14, 0.13), (x, y, SHAFT_H), c=color))
            V.append(box(B, (0.045, 0.07, 0.06),
                         (x + side * 0.11, y, SHAFT_H + 0.055), c=color))
            V.append(cyl(B, 0.012, 0.035,
                         (x + side * 0.11, y, SHAFT_H + 0.10), c="gri"))
            V.append(box(B, (0.18, 0.16, 0.025),
                         (x, y, SHAFT_H - 0.08), c="gri_inchis"))
        for x in (-0.12, 0.12):
            V.append(box(B, (0.04, 0.10, 0.045),
                         (x, y, SHAFT_H - 0.055), c="albastru"))

    # --- axele rotitoare: construite in frame-ul articulatiei (z = axa)
    for k in range(3):
        L = f"shaft{k}"
        V.append(cyl(L, 0.013, 0.36, (0, 0, 0), c="gri_inchis"))
        for face in (-1, 1):
            V.append(cyl(L, 0.048, 0.028, (0, 0, face * 0.014),
                         c="portocaliu"))
            V.append(cyl(L, 0.026, 0.014, (0, 0, face * 0.10), c="gri"))
        # Sase suruburi pe cercul de prindere, cu capete pe ambele fete.
        for j in range(6):
            ang = 2 * pi * j / 6
            px, py = 0.034 * cos(ang), 0.034 * sin(ang)
            V.append(cyl(L, 0.0035, 0.06, (px, py, 0), c="gri"))
            for face in (-1, 1):
                V.append(cyl(L, 0.006, 0.004,
                             (px, py, face * 0.032), c="gri"))
        # Reper rosu intre suruburi, pe cele doua fete ale flansei.
        for face in (-1, 1):
            ang = pi / 6
            V.append(box(L, (0.023, 0.006, 0.002),
                         (0.034 * cos(ang), 0.034 * sin(ang),
                          face * 0.0295), (0, 0, ang), c="rosu"))
    return V


def fmt(t):
    return " ".join(f"{x:g}" for x in t)


def geo_urdf(v):
    if v["kind"] == "box":
        return f'<box size="{fmt(v["sz"])}"/>'
    return f'<cylinder radius="{v["r"]:g}" length="{v["l"]:g}"/>'


def geo_sdf(v):
    if v["kind"] == "box":
        return f'<box><size>{fmt(v["sz"])}</size></box>'
    return (f'<cylinder><radius>{v["r"]:g}</radius>'
            f'<length>{v["l"]:g}</length></cylinder>')


def emit_urdf(V):
    links = {}
    for v in V:
        links.setdefault(v["link"], []).append(v)
    out = ['<?xml version="1.0"?>',
           "<!-- GENERAT de tools/gen_bench_model.py -- nu edita de mana -->",
           '<robot name="joint_bench">']
    for name in ["base_link", "shaft0", "shaft1", "shaft2"]:
        out.append(f'  <link name="{name}">')
        for v in links.get(name, []):
            out.append(
                f'    <visual><origin xyz="{fmt(v["xyz"])}" rpy="{fmt(v["rpy"])}"/>'
                f'<geometry>{geo_urdf(v)}</geometry>'
                f'<material name="{v["c"]}"><color rgba="{CUL[v["c"]]}"/>'
                f'</material></visual>')
        out.append("  </link>")
    for k, p in enumerate(PAIRS):
        out.append(
            f'  <joint name="pair{k}_joint" type="continuous">'
            f'<parent link="base_link"/><child link="shaft{k}"/>'
            f'<origin xyz="{fmt(p)}" rpy="{fmt(JRPY)}"/>'
            f'<axis xyz="0 0 1"/></joint>')
    out.append("</robot>")
    return "\n".join(out)


def emit_sdf(V):
    links = {}
    for v in V:
        links.setdefault(v["link"], []).append(v)

    def link_xml(name, pose, mass):
        s = [f'    <link name="{name}"><pose>{pose}</pose>',
             f'      <inertial><mass>{mass}</mass><inertia>'
             '<ixx>0.002</ixx><iyy>0.002</iyy><izz>0.002</izz>'
             '<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>']
        for i, v in enumerate(links.get(name, [])):
            s.append(
                f'      <visual name="v{i}"><pose>{fmt(v["xyz"])} {fmt(v["rpy"])}'
                f'</pose><geometry>{geo_sdf(v)}</geometry>'
                f'<material><diffuse>{CUL[v["c"]]}</diffuse></material></visual>')
        s.append("    </link>")
        return "\n".join(s)

    ctrl = "\n".join(
        f'      <plugin filename="gz-sim-joint-position-controller-system" '
        f'name="gz::sim::systems::JointPositionController">'
        f'<joint_name>pair{k}_joint</joint_name>'
        f'<topic>/bench/pair{k}_cmd_pos</topic>'
        f'<p_gain>15</p_gain><d_gain>0.3</d_gain></plugin>'
        for k in range(3))
    joints = "\n".join(
        f'    <joint name="pair{k}_joint" type="revolute">'
        f'<parent>base_link</parent><child>shaft{k}</child>'
        f'<axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower>'
        f'<upper>1e16</upper></limit></axis></joint>'
        for k in range(3))
    shafts = "\n".join(link_xml(f"shaft{k}",
                                f"{fmt(PAIRS[k])} {fmt(JRPY)}", 0.25)
                       for k in range(3))
    return f'''<?xml version="1.0"?>
<!-- GENERAT de tools/gen_bench_model.py -- nu edita de mana -->
<sdf version="1.9">
  <world name="bench_world">
    <gravity>0 0 -9.81</gravity>
    <light type="directional" name="sun"><pose>0 0 10 0 0.5 0.4</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse><cast_shadows>true</cast_shadows></light>
    <model name="ground"><static>true</static><link name="g">
      <collision name="c"><geometry><plane><normal>0 0 1</normal>
        <size>10 10</size></plane></geometry></collision>
      <visual name="v"><geometry><plane><normal>0 0 1</normal>
        <size>10 10</size></plane></geometry>
        <material><diffuse>0.75 0.7 0.6 1</diffuse></material></visual>
    </link></model>
    <model name="joint_bench">
      <pose>0 0 0 0 0 0</pose>
      <!-- ANCORA: fara coliziuni, modelul liber ar cadea prin podea -->
      <joint name="world_anchor" type="fixed">
        <parent>world</parent><child>base_link</child></joint>
{link_xml("base_link", "0 0 0 0 0 0", 80)}
{shafts}
{joints}
{ctrl}
    </model>
  </world>
</sdf>'''


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    V = geometrie()
    open(os.path.join(here, "urdf", "joint_bench.urdf"), "w").write(emit_urdf(V))
    open(os.path.join(here, "gz", "joint_bench_world.sdf"), "w").write(emit_sdf(V))
    print(f"[ok] {len(V)} elemente vizuale -> urdf/joint_bench.urdf + "
          "gz/joint_bench_world.sdf")
