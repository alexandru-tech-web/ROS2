#!/usr/bin/env python3
"""gen_bench_model.py -- geometrie vizuala a bancului, necalibrata.

Carcasa motorului provine din modelul STL arhivat anterior in servo_control;
ea este folosita numai vizual. Trei motoare albastre stau in stanga si trei
motoare rosii in dreapta.
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
       "motor_b": "0.82 0.20 0.12 1", "eticheta": "0.08 0.08 0.08 1",
       "alb": "0.96 0.96 0.96 1",
       "portocaliu": "0.91 0.35 0.05 1", "gri": "0.55 0.55 0.55 1",
       "gri_inchis": "0.30 0.30 0.30 1", "rosu": "0.95 0.01 0.01 1",
       "cabinet": "0.24 0.27 0.30 1", "usa": "0.38 0.41 0.44 1",
       "cablu_date": "0.08 0.72 0.42 1", "galben": "0.95 0.75 0.05 1"}

BASE_H = 0.78
SHAFT_H = 0.90
ROW_Y = (-0.28, 0.0, 0.28)
# z-ul local al axului devine x-ul global: A in stanga, B in dreapta.
JRPY = (0, H, 0)
PAIRS = [(0, y, SHAFT_H) for y in ROW_Y]

# Centrul gaurii de iesire, masurat direct in STL (metri, coordonate locale).
# Fata arborelui este planul local y=max. Dupa rotatia Rz(yaw)*Ry(90 deg),
# acest punct trebuie sa coincida exact cu capatul axului ViPRO.
MOTOR_HOLE_LOCAL_M = (-0.01692325, 0.15230010, 0.00299565)
MOTOR_INTERFACE_X = 0.18


def motor_pose(side, row_y):
    """Pozitia mesh-ului care suprapune centrul gaurii peste axul comun."""
    if side not in (-1, 1):
        raise ValueError("side trebuie sa fie -1 (stanga) sau 1 (dreapta)")
    lx, ly, lz = MOTOR_HOLE_LOCAL_M
    yaw = -H if side < 0 else H
    # Rz(yaw) * Ry(90 deg) aplicat centrului local al gaurii.
    rotated_hole = ((ly, -lz, -lx) if side < 0
                    else (-ly, lz, -lx))
    target = (side * MOTOR_INTERFACE_X, row_y, SHAFT_H)
    xyz = tuple(target[i] - rotated_hole[i] for i in range(3))
    return xyz, yaw


def box(link, sz, xyz, rpy=(0, 0, 0), c="albastru"):
    return dict(link=link, kind="box", sz=sz, xyz=xyz, rpy=rpy, c=c)


def cyl(link, r, l, xyz, rpy=(0, 0, 0), c="albastru"):
    return dict(link=link, kind="cyl", r=r, l=l, xyz=xyz, rpy=rpy, c=c)


def mesh(link, uri, scale, xyz, rpy=(0, 0, 0), c="albastru"):
    return dict(link=link, kind="mesh", uri=uri, scale=scale,
                xyz=xyz, rpy=rpy, c=c)


FONT = {
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
}


def label_shapes(link, text, center, tag, yaw=0.0):
    """Return robust raised-pixel labels; no Gazebo font dependency."""
    px, gap = 0.006, 0.0015
    glyph_w = 3 * px + 2 * gap
    text_w = len(text) * glyph_w + max(0, len(text) - 1) * gap
    x0 = center[0] - text_w / 2 + px / 2
    y0 = center[1] + (5 * px + 4 * gap) / 2 - px / 2
    result = []
    for n, char in enumerate(text):
        for row, bits in enumerate(FONT[char]):
            for col, active in enumerate(bits):
                if active == "1":
                    raw_x = x0 + n * (glyph_w + gap) + col * (px + gap)
                    raw_y = y0 - row * (px + gap)
                    dx, dy = raw_x - center[0], raw_y - center[1]
                    xyz = (center[0] + cos(yaw) * dx - sin(yaw) * dy,
                           center[1] + sin(yaw) * dx + cos(yaw) * dy,
                           center[2])
                    item = box(link, (px, px, 0.003), xyz,
                               (0, 0, yaw), c="alb")
                    item["label"] = tag
                    result.append(item)
    return result


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

    # Cabinet schematic alaturat in dreapta mesei. Este parte din geometria
    # ancorata si nu reprezinta un inventar electric confirmat al bancului.
    cabinet_x = 1.15
    cabinet = box(B, (0.42, 0.78, 1.15),
                  (cabinet_x, 0, 0.575), c="cabinet")
    cabinet["cabinet"] = True
    V.append(cabinet)
    V.append(box(B, (0.018, 0.70, 0.98),
                 (cabinet_x - 0.219, 0, 0.61), c="usa"))
    V.append(box(B, (0.022, 0.22, 0.15),
                 (cabinet_x - 0.231, 0, 0.88), c="eticheta"))
    for y, color in ((-0.055, "rosu"), (0, "galben"), (0.055, "cablu_date")):
        V.append(cyl(B, 0.012, 0.025, (cabinet_x - 0.245, y, 0.90),
                     (0, H, 0), c=color))
    V.append(box(B, (0.026, 0.08, 0.18),
                 (cabinet_x - 0.244, 0.27, 0.58), c="gri_inchis"))

    # Trei perechi. Mesh-ul este recentrat/orientat spre axul comun si nu are
    # coliziune ori inertie proprie: matematica PairSim ramane neschimbata.
    left_labels = ("A", "B", "C")
    right_labels = ("A1", "B1", "C1")
    for row, y in enumerate(ROW_Y):
        for side, color, label in (
                (-1, "motor_a", left_labels[row]),
                (1, "motor_b", right_labels[row])):
            # Pitch-ul local este rotatia de 90 deg in jurul axului motorului;
            # yaw-ul pastreaza iesirea axului orientata spre flansa comuna.
            motor_xyz, yaw = motor_pose(side, y)
            item = mesh(B, "servo_body.stl", (0.001, 0.001, 0.001),
                        motor_xyz,
                        (0, H, yaw), c=color)
            item["motor_side"] = "left" if side < 0 else "right"
            item["label"] = label
            item["shaft_interface"] = (side * MOTOR_INTERFACE_X, y, SHAFT_H)
            V.append(item)
            V.append(box(B, (0.18, 0.16, 0.025),
                         (-0.23 if side < 0 else 0.23, y,
                          SHAFT_H - 0.08), c="gri_inchis"))
            # Centrul aproximativ al carcasei rotite, pentru modul si eticheta.
            plate_x = -0.254 if side < 0 else 0.254
            plate_y = y + (0.0094 if side < 0 else -0.0094)
            daisy = box(B, (0.10, 0.065, 0.025),
                        (plate_x, plate_y, SHAFT_H + 0.055), c="eticheta")
            daisy["daisy_chain"] = True
            daisy["label"] = label
            V.append(daisy)
            V.append(box(B, (0.075, 0.055, 0.004),
                         (plate_x, plate_y, SHAFT_H + 0.069),
                         (0, 0, H), c="eticheta"))
            V.extend(label_shapes(B, label,
                                  (plate_x, plate_y, SHAFT_H + 0.073),
                                  label, H))
        for x in (-0.12, 0.12):
            V.append(box(B, (0.04, 0.10, 0.045),
                         (x, y, SHAFT_H - 0.055), c="albastru"))

    # --- axele rotitoare: construite in frame-ul articulatiei (z = axa)
    for k in range(3):
        L = f"shaft{k}"
        # Arbore vizual Ø12 mm, apropiat de geometria STL (aprox. Ø10 mm).
        # Lungimea de 390 mm depaseste cu 15 mm fiecare fata de motor, astfel
        # incat imbinarea sa fie vizibila fara gol. PairSim nu foloseste aceste
        # dimensiuni in ecuatiile sale.
        shaft = cyl(L, 0.006, 0.39, (0, 0, 0), c="gri_inchis")
        shaft["main_shaft"] = True
        V.append(shaft)
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
    if v["kind"] == "cyl":
        return f'<cylinder radius="{v["r"]:g}" length="{v["l"]:g}"/>'
    return (f'<mesh filename="../gz/meshes/{v["uri"]}" '
            f'scale="{fmt(v["scale"])}"/>')


def geo_sdf(v):
    if v["kind"] == "box":
        return f'<box><size>{fmt(v["sz"])}</size></box>'
    if v["kind"] == "cyl":
        return (f'<cylinder><radius>{v["r"]:g}</radius>'
                f'<length>{v["l"]:g}</length></cylinder>')
    return (f'<mesh><uri>meshes/{v["uri"]}</uri>'
            f'<scale>{fmt(v["scale"])}</scale></mesh>')


def emit_urdf(V):
    links = {}
    for v in V:
        links.setdefault(v["link"], []).append(v)
    out = ['<?xml version="1.0"?>',
           "<!-- GENERAT de tools/gen_bench_model.py; nu edita de mana -->",
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
<!-- GENERAT de tools/gen_bench_model.py; nu edita de mana -->
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
