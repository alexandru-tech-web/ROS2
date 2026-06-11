#!/usr/bin/env python3
"""gen_bench_model.py — generatorul GEOMETRIEI bancului, construita dupa
pozele standului real: piedestal albastru cu picioare evazate si talpi
disc (perechea din fata), doua coloane albastre inalte (perechile din
spate, nivelul de sus), suporti U albastri cu cuplaj portocaliu vizibil,
motoare negre cu cutii de conectori, cadru portocaliu de jur imprejur.

O SINGURA tabela de geometrie -> AMBELE fisiere:
    urdf/joint_bench.urdf        (RViz; culori INLINE per visual,
                                  fiindca RViz2 nu rezolva mereu
                                  materialele definite doar global)
    gz/joint_bench_world.sdf     (Gazebo; modelul e ANCORAT de lume cu
                                  un joint fix — altfel, fara coliziuni,
                                  cadea prin podea si "disparea")
Ruleaza:  python3 tools/gen_bench_model.py
"""
import os
from math import pi

H = pi / 2
CUL = {"albastru": "0.13 0.32 0.65 1", "negru": "0.10 0.10 0.10 1",
       "portocaliu": "0.91 0.35 0.05 1", "gri": "0.55 0.55 0.55 1",
       "gri_inchis": "0.30 0.30 0.30 1"}

# panoul inclinat: coordonate de PANOU (xp=latime, yp=normala, zp=sus)
# rotite in lume despre axa X cu TILT si ridicate la BASE_H
import math as _m
TILT = 1.5708                     # panoul rotit la orizontala = blatul mesei
_CA, _SA = _m.cos(TILT), _m.sin(TILT)
BASE_H = 0.78


def T(xp, yp, zp):
    return (xp, _CA * yp - _SA * zp, _SA * yp + _CA * zp + BASE_H)


JRPY = (TILT, 0, 0)               # orientarea articulatiilor (rpy)
# 3 coloane = 3 perechi cuplate VERTICAL; cuplajul la mijlocul coloanei
PAIRS = [T(-0.40, 0, 0), T(0.0, 0, 0), T(0.40, 0, 0)]


def box(link, sz, xyz, rpy=(0, 0, 0), c="albastru"):
    return dict(link=link, kind="box", sz=sz, xyz=xyz, rpy=rpy, c=c)


def cyl(link, r, l, xyz, rpy=(0, 0, 0), c="albastru"):
    return dict(link=link, kind="cyl", r=r, l=l, xyz=xyz, rpy=rpy, c=c)


def geometrie():
    V = []
    B = "base_link"
    # --- cadrul portocaliu inclinat (dreptunghiul panoului)
    for sx in (-0.62, 0.62):                       # montantii (zp)
        V.append(box(B, (0.05, 0.05, 0.92), T(sx, 0, 0), (TILT, 0, 0),
                     c="portocaliu"))
    for sz in (-0.45, 0.45):                       # barele orizontale (xp)
        V.append(box(B, (1.29, 0.05, 0.05), T(0, 0, sz), (TILT, 0, 0),
                     c="portocaliu"))
    # --- 4 picioare verticale, ca la o masa obisnuita
    for sx in (-0.60, 0.60):
        for sy in (-0.42, 0.42):
            V.append(box(B, (0.05, 0.05, BASE_H), (sx, sy, BASE_H / 2),
                         c="portocaliu"))
    # --- 3 coloane: motor sus + suport U + motor jos (forma pastrata)
    for xc, _, _ in [(-0.40, 0, 0), (0.0, 0, 0), (0.40, 0, 0)]:
        for sz in (-1, 1):                          # cele doua motoare
            V.append(box(B, (0.145, 0.145, 0.22), T(xc, 0, sz * 0.23),
                         (TILT, 0, 0), c="negru"))
            V.append(box(B, (0.10, 0.05, 0.09),    # cutia de conectori
                         T(xc - 0.01, 0.095, sz * 0.29), (TILT, 0, 0),
                         c="negru"))
            V.append(cyl(B, 0.013, 0.05,           # conectorul argintiu
                         T(xc - 0.01, 0.145, sz * 0.29),
                         (TILT + H, 0, 0), c="gri"))
        V.append(box(B, (0.02, 0.14, 0.12), T(xc - 0.085, 0, 0),
                     (TILT, 0, 0)))                 # obraz U stanga
        V.append(box(B, (0.02, 0.14, 0.12), T(xc + 0.085, 0, 0),
                     (TILT, 0, 0)))                 # obraz U dreapta
        V.append(box(B, (0.15, 0.02, 0.10), T(xc, -0.075, 0),
                     (TILT, 0, 0)))                 # spatele U (pe panou)
    # --- axele rotitoare: construite in frame-ul articulatiei (z = axa)
    for k in range(3):
        L = f"shaft{k}"
        V.append(cyl(L, 0.016, 0.24, (0, 0, 0), c="gri_inchis"))
        V.append(cyl(L, 0.050, 0.050, (0, 0, 0), c="portocaliu"))
        V.append(cyl(L, 0.032, 0.015, (0, 0, 0.06), c="gri"))
        V.append(cyl(L, 0.032, 0.015, (0, 0, -0.06), c="gri"))
        V.append(box(L, (0.08, 0.016, 0.016), (0.06, 0, 0), c="portocaliu"))
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
           "<!-- GENERAT de tools/gen_bench_model.py — nu edita de mana -->",
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
<!-- GENERAT de tools/gen_bench_model.py — nu edita de mana -->
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
