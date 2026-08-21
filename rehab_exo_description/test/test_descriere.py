#!/usr/bin/env python3
"""test_descriere.py -- selftestul DESCRIERII, echivalentul lui validate.py.

Genereaza URDF-ul din sursa canonica (urdf/rehab_exo.urdf.xacro) si il interogheaza.
Nu verifica fisierul livrat: verifica ARTEFACTUL, adica exact ce ajunge la
robot_state_publisher si la Gazebo.

DE CE EXISTA. Pana la F1a pachetul avea trei surse de adevar (URDF editat manual,
un xacro care descria alt robot, si un script care mutata URDF-ul in loc) si ZERO
teste. Un pachet de descriere fara test e o descriere pe cuvant.

CIFRELE DE AICI SUNT CELE ACTUALE, NU CELE DIN SPEC. Cursele 65,89 / 100,27 / 68,75
grade sunt IPOTEZE LOCALE (GAP 4 din SPEC_LLR_twin_din_PDF.md) si se redefinesc la
F1b, impreuna cu zeroul anatomic. Testul le fixeaza ca sa prinda schimbari
NEINTENTIONATE, nu ca sa pretinda ca sunt corecte.
"""
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
XACRO_SRC = os.path.join(PACHET, "urdf", "rehab_exo.urdf.xacro")

ACTIVE = ("revolute", "continuous", "prismatic")
REVOLUTE = ("left_hip_joint", "left_knee_joint", "left_ankle_joint",
            "right_hip_joint", "right_knee_joint", "right_ankle_joint")
PRISMATICE = ("seat_lift_joint", "left_thigh_ext_joint", "right_thigh_ext_joint",
              "left_shank_ext_joint", "right_shank_ext_joint")
# Conventie ANATOMICA (M1). Cursele TOTALE sunt documentate [PDF Tabel 3.1];
# impartirea min/max ramane IPOTEZA LOCALA (GAP 4), motivata in urdf/IPOTEZE_LIMITE.md.
import math as _m
LIMITE = {"hip": (0.0, _m.radians(90)), "knee": (0.0, _m.radians(140)),
          "ankle": (_m.radians(-35), _m.radians(35))}
ROM_DOCUMENTAT = {"hip": 90.0, "knee": 140.0, "ankle": 70.0}

_V = [0]


def ok(cond, mesaj):
    assert cond, mesaj
    _V[0] += 1


def genereaza(*argumente):
    """xacro -> URDF, intr-un fisier temporar. Ridica RuntimeError cu stderr-ul real."""
    f = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    f.close()
    p = subprocess.run(["xacro", XACRO_SRC] + list(argumente) + ["-o", f.name],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("xacro a picat pe %s:\n%s" % (list(argumente), p.stderr[:400]))
    return f.name


def _plugin_si_senzori(r):
    pl = [p.get("filename") or "" for g in r.findall("gazebo") for p in g.findall("plugin")]
    se = [s.get("name") for g in r.findall("gazebo") for s in g.findall("sensor")]
    return sum(1 for x in pl if "apply-joint-force" in x), len(se)


def main(argv=None):
    print("== selftestul descrierii (sursa: %s) ==" % os.path.basename(XACRO_SRC))

    # --- 1. se genereaza si e URDF valid
    f = genereaza()
    p = subprocess.run(["check_urdf", f], capture_output=True, text=True)
    ok(p.returncode == 0, "check_urdf a picat:\n%s" % p.stdout[-300:])
    r = ET.parse(f).getroot()

    # --- 2. topologia
    linkuri = [x.get("name") for x in r.findall("link")]
    jointuri = {x.get("name"): x.get("type") for x in r.findall("joint")}
    ok(len(linkuri) == 15, "linkuri: %d, se cer 15" % len(linkuri))
    ok(len(jointuri) == 14, "jointuri: %d, se cer 14" % len(jointuri))
    active = [n for n, t in jointuri.items() if t in ACTIVE]
    ok(len(active) == 11, "DOF active: %d, se cer 11" % len(active))
    rev = [n for n, t in jointuri.items() if t == "revolute"]
    pri = [n for n, t in jointuri.items() if t == "prismatic"]
    ok(sorted(rev) == sorted(REVOLUTE), "revolute: %s" % sorted(rev))
    ok(sorted(pri) == sorted(PRISMATICE), "prismatice: %s" % sorted(pri))

    # --- 3. limitele (IPOTEZE LOCALE, GAP 4)
    for j in r.findall("joint"):
        n = j.get("name")
        if n not in REVOLUTE:
            continue
        cheie = "hip" if "hip" in n else ("knee" if "knee" in n else "ankle")
        lo, hi = LIMITE[cheie]
        lim = j.find("limit")
        ok(lim is not None, "%s fara <limit>" % n)
        ok(abs(float(lim.get("lower")) - lo) < 1e-9
           and abs(float(lim.get("upper")) - hi) < 1e-9,
           "%s: limite %s..%s, se cer %.5f..%.5f (ipoteza locala GAP 4)"
           % (n, lim.get("lower"), lim.get("upper"), lo, hi))
        # cursa TOTALA trebuie sa fie cea DOCUMENTATA, oricare ar fi impartirea
        cursa = math.degrees(float(lim.get("upper")) - float(lim.get("lower")))
        ok(abs(cursa - ROM_DOCUMENTAT[cheie]) < 1e-6,
           "%s: cursa %.3f grade, documentat %.0f [PDF Tabel 3.1]"
           % (n, cursa, ROM_DOCUMENTAT[cheie]))

    # --- 4. SIMETRIA stanga-dreapta, joint cu joint. Fara asta, un macro stricat pe
    # o singura parte ar trece neobservat -- si tocmai simetria e ce justifica macroul.
    def prop(n):
        j = [x for x in r.findall("joint") if x.get("name") == n][0]
        lim, ax, o = j.find("limit"), j.find("axis"), j.find("origin")
        return (j.get("type"),
                None if lim is None else tuple(round(float(lim.get(k)), 9)
                                               for k in ("lower", "upper", "effort", "velocity")),
                None if ax is None else ax.get("xyz"),
                None if o is None else tuple(round(float(v), 9) for v in o.get("xyz").split()))
    for n in REVOLUTE + PRISMATICE:
        if not n.startswith("left_"):
            continue
        d = "right_" + n[len("left_"):]
        ok(d in jointuri, "lipseste perechea %s" % d)
        ts, ls, axs, os_ = prop(n)
        td, ld, axd, od = prop(d)
        ok(ts == td, "%s/%s: tipuri diferite" % (n, d))
        ok(ls == ld, "%s/%s: limite diferite (%s vs %s)" % (n, d, ls, ld))
        ok(axs == axd, "%s/%s: axe diferite (%s vs %s) -- axele NU se oglindesc"
           % (n, d, axs, axd))
        # originile difera EXACT prin semnul lui Y
        ok(os_[0] == od[0] and os_[2] == od[2] and abs(os_[1] + od[1]) < 1e-9,
           "%s/%s: originile nu sunt oglindite pe Y (%s vs %s)" % (n, d, os_, od))

    # --- 5. FLAGURI, cu CONTROL NEGATIV. Un test care verifica doar prezenta ar trece
    # si daca flagul nu ar functiona deloc.
    ajf, imu = _plugin_si_senzori(r)
    ok(ajf == 6 and imu == 3, "implicit: ApplyJointForce=%d IMU=%d, se cer 6 si 3" % (ajf, imu))
    for arg, a_ajf, a_imu in (("gazebo:=false", 0, 3), ("senzori:=false", 6, 0)):
        r2 = ET.parse(genereaza(arg)).getroot()
        g, i = _plugin_si_senzori(r2)
        ok(g == a_ajf and i == a_imu,
           "%s: ApplyJointForce=%d IMU=%d, se cer %d si %d" % (arg, g, i, a_ajf, a_imu))
        ok(len(r2.findall("link")) == 15 and len(r2.findall("joint")) == 14,
           "%s nu are voie sa schimbe topologia" % arg)

    # --- 6. ros2_control: cele 11 jointuri, o singura data fiecare
    rc = r.find("ros2_control")
    ok(rc is not None, "lipseste blocul ros2_control")
    rcj = [x.get("name") for x in rc.findall("joint")]
    ok(len(rcj) == len(set(rcj)) == 11,
       "ros2_control: %d intrari, %d unice, se cer 11 si 11" % (len(rcj), len(set(rcj))))
    ok(sorted(rcj) == sorted(active), "ros2_control nu acopera exact DOF-urile active")

    # --- 7. cursele, in grade, ca cifra sa fie citibila in raport
    for n, cheie in (("left_hip_joint", "hip"), ("left_knee_joint", "knee"),
                     ("left_ankle_joint", "ankle")):
        lo, hi = LIMITE[cheie]
        print("   %-18s %7.1f .. %7.1f grade  (cursa %.0f, DOCUMENTATA; split GAP 4)"
              % (n, math.degrees(lo), math.degrees(hi), math.degrees(hi - lo)))

    print("SELFTEST descriere OK (%d verificari)." % _V[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
