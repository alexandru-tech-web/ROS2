#!/usr/bin/env python3
"""supervizor_electric.py -- stratul ELECTRIC de siguranta, pe bucla reala.

Emuleaza proximitatile [PDF p.7]: praguri de POZITIE strict inauntrul limitelor
mecanice. Vezi supervizor_core.py pentru cele trei straturi si pentru motivul
armarii cu histerezis.

LIMITELE NU SE RESCRIU AICI. Se citesc din URDF-ul instalat, adica din exact
artefactul pe care il foloseste si simularea. Singura valoare care NU poate fi citita
de acolo e minimul soldului in postura SEZUT: URDF-ul generat poarta doar postura
ACTIVA, deci cealalta nu exista in el. E parametru ROS, iar test/test_supervizor.py
aserteaza ca implicitul lui coincide cu proprietatea sold_sezut_min_deg din xacro --
o asertie in loc de o a doua copie.

ACTIUNEA LA DECLANSARE: se publica o traiectorie de UN SINGUR PUNCT la pozitia
curenta. Asta inlocuieste traiectoria in curs pe interfata de topic a lui
joint_trajectory_controller (care e calea folosita de exercise_controller) si o
opreste. Suplimentar se cere anularea oricarui goal de ACTIUNE activ, pentru cazul in
care cineva comanda pe acolo. E cea mai simpla actiune care opreste demonstrat
miscarea; nu e o oprire de siguranta certificata si nu pretinde sa fie.

Servicii si topicuri:
    /rehab/supervizor/postura   std_srvs/SetBool  true = sezut, false = culcat
                                raspunsul poarta MOTIVUL la refuz
    /rehab/supervizor/eveniment std_msgs/String   JSON la fiecare declansare
    /rehab/supervizor/stare     std_msgs/String   JSON, starea fiecarei articulatii
"""
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import supervizor_core as sc                                   # noqa: E402

ARTICULATII = ["left_hip_joint", "left_knee_joint", "left_ankle_joint",
               "right_hip_joint", "right_knee_joint", "right_ankle_joint"]


def limite_din_urdf(cale, articulatii=ARTICULATII):
    """{joint: (lower, upper)} citit din URDF. Pur: primeste o cale, nu cauta el."""
    r = ET.parse(cale).getroot()
    out = {}
    for j in r.findall("joint"):
        if j.get("name") in articulatii:
            lim = j.find("limit")
            if lim is not None:
                out[j.get("name")] = (float(lim.get("lower")), float(lim.get("upper")))
    lipsa = [a for a in articulatii if a not in out]
    if lipsa:
        raise ValueError("URDF-ul %s nu are limite pentru %s" % (cale, lipsa))
    return out


def limite_sezut(limite, sold_min_rad, sold_max_rad=None):
    """Setul SEZUT: inelul de oprire (reper 208) restrange cursa soldului. Restul
    articulatiilor raman neatinse; verificat in test_descriere.

    Banda are acum AMBELE capete, fiindca la flip-ul de conventie fereastra veche
    (un minim ridicat, cu maximul comun) s-a transportat intr-una care are si un
    maxim propriu. Daca sold_max_rad lipseste, se pastreaza maximul din culcat."""
    out = dict(limite)
    for j in out:
        if j.endswith("_hip_joint"):
            hi = out[j][1] if sold_max_rad is None else sold_max_rad
            out[j] = (sold_min_rad, hi)
    return out


def main(argv=None):
    import rclpy
    from rclpy.node import Node
    from ament_index_python.packages import get_package_share_directory
    from builtin_interfaces.msg import Duration
    from sensor_msgs.msg import JointState
    from std_msgs.msg import String
    from std_srvs.srv import SetBool
    from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

    class SupervizorElectric(Node):
        def __init__(self):
            Node.__init__(self, "rehab_supervizor_electric")
            self.declare_parameter("marja_deg", math.degrees(sc.MARJA_IMPLICITA_RAD))
            # RE-JUSTIFICATA (nu convertita) pe 22 aug: 0..25 grade in B-prim.
            # Derivarea in urdf/IPOTEZE_LIMITE.md; clasa IPOTEZA-ANTROPO.
            self.declare_parameter("sold_sezut_min_deg", 0.0)
            self.declare_parameter("sold_sezut_max_deg", 25.0)
            self.declare_parameter("postura", "culcat")
            self.declare_parameter("hz", 20.0)

            marja = math.radians(float(self.get_parameter("marja_deg").value))
            self.sezut_min = math.radians(
                float(self.get_parameter("sold_sezut_min_deg").value))
            self.sezut_max = math.radians(
                float(self.get_parameter("sold_sezut_max_deg").value))
            urdf = os.path.join(get_package_share_directory("rehab_exo_description"),
                                "urdf", "rehab_exo.urdf")
            self.lim_culcat = limite_din_urdf(urdf)
            self.lim_sezut = limite_sezut(self.lim_culcat, self.sezut_min,
                                          self.sezut_max)
            self.marja = marja
            self.postura = self.get_parameter("postura").value
            self.sup = sc.Supervizor(self._praguri(self.postura))

            self.q = {}
            self.create_subscription(JointState, "/joint_states", self._js, 20)
            self.p_ev = self.create_publisher(String, "/rehab/supervizor/eveniment", 10)
            self.p_st = self.create_publisher(String, "/rehab/supervizor/stare", 10)
            self.p_traj = self.create_publisher(
                JointTrajectory, "/leg_trajectory_controller/joint_trajectory", 10)
            self.create_service(SetBool, "/rehab/supervizor/postura", self._postura)
            self.create_timer(1.0 / float(self.get_parameter("hz").value), self._tic)
            self.create_timer(1.0, self._publica_stare)

            p = self.sup.praguri
            self.get_logger().info(
                "supervizor ELECTRIC activ, postura '%s', marja %.2f grade. "
                "Praguri: %s" % (self.postura, math.degrees(marja),
                                 ", ".join("%s %.3f..%.3f" % (j.replace("_joint", ""),
                                                              p[j][0], p[j][1])
                                           for j in sorted(p))))
            self.get_logger().info(
                "IPOTEZA: pragurile electrice sunt derivate din cele mecanice printr-o "
                "marja aleasa; proximitatile reale nu au fost inca masurate.")

        def _praguri(self, postura):
            lim = self.lim_sezut if postura == "sezut" else self.lim_culcat
            return sc.praguri_electrice(lim, self.marja)

        def _js(self, m):
            for n, p in zip(m.name, m.position):
                self.q[n] = p

        def _tic(self):
            for ev in self.sup.pas(self.q):
                self.get_logger().error(str(ev))
                self.p_ev.publish(String(data=json.dumps({
                    "articulatie": ev.articulatie, "valoare": ev.valoare,
                    "prag": ev.prag, "capat": ev.capat, "postura": self.postura})))
                self._opreste()

        def _opreste(self):
            """Inlocuieste traiectoria in curs cu una de un punct, la pozitia
            curenta. Simplu si demonstrabil: JTC preia ultimul mesaj primit."""
            nume = [j for j in ARTICULATII if j in self.q]
            if not nume:
                self.get_logger().error("NU pot opri: nu am nicio pozitie masurata")
                return
            t = JointTrajectory()
            t.joint_names = nume
            pt = JointTrajectoryPoint()
            pt.positions = [self.q[j] for j in nume]
            pt.time_from_start = Duration(sec=0, nanosec=100000000)
            t.points = [pt]
            for _ in range(3):
                self.p_traj.publish(t)
            self.get_logger().error("OPRIT: mentin pozitia curenta.")

        def _postura(self, cerere, raspuns):
            noua = "sezut" if cerere.data else "culcat"
            praguri = self._praguri(noua)
            # verificarea se face pe limitele MECANICE ale posturii-tinta, nu pe
            # praguri; vezi verdict_comutare pentru de ce
            mecanice = self.lim_sezut if noua == "sezut" else self.lim_culcat
            permis, motiv = sc.verdict_comutare(mecanice, self.q)
            if not permis:
                raspuns.success = False
                raspuns.message = motiv
                self.get_logger().warn("postura '%s': %s" % (noua, motiv))
                return raspuns
            self.postura = noua
            self.sup.schimba_praguri(praguri)
            raspuns.success = True
            raspuns.message = ("postura '%s'; praguri sold %.4f..%.4f rad; armarea "
                               "s-a resetat" % (noua, praguri["left_hip_joint"][0],
                                                praguri["left_hip_joint"][1]))
            self.get_logger().info(raspuns.message)
            return raspuns

        def _publica_stare(self):
            self.p_st.publish(String(data=json.dumps({
                "postura": self.postura,
                "declansat": self.sup.declansat(),
                "stari": dict(self.sup.stare)})))

    rclpy.init(args=argv)
    n = SupervizorElectric()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
