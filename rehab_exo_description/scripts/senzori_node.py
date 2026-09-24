#!/usr/bin/python3
"""senzori_node.py -- nod SUBTIRE peste senzori_core. Publica familia documentata.

Toate valorile sunt SINTETICE, cu model declarat in senzori_core.py, si fara nicio
pretentie de fidelitate fizica. Eticheta apare si pe fir: fiecare topic are un
frame_id sau un mesaj insotitor care o poarta, ca cineva care asculta topicul fara sa
citeasca sursa sa nu creada ca sunt masuratori.

TOPICURI (rata implicita 100 Hz, parametru --hz; unghiul gleznei si rigla la rate
proprii, tot parametri):

  /rehab/cuplu/<parte>_<articulatie>   std_msgs/Float64   [Nm]   sold + genunchi x2
  /rehab/forta_6d/<parte>              geometry_msgs/WrenchStamped  cele 3 marimi
                                       numite in document; restul componentelor NaN
  /rehab/unghi_glezna/<parte>          std_msgs/Float64   [rad]  senzor DEDICAT
  /rehab/rigla_gamba/<parte>           std_msgs/Float64   [m]    lungime MASURATA
  /rehab/senzori/eticheta              std_msgs/String    eticheta, la 1 Hz

De ce NaN si nu zero pe componentele nemasurate: senzorul real numeste TREI marimi
[PDF p.11]. Zero ar afirma "masurat si e nul"; NaN spune "nu se masoara". Diferenta
conteaza pentru orice consumator care nu a citit documentul.
"""
import argparse
import math
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
if AICI not in sys.path:
    sys.path.insert(0, AICI)

from senzori_core import (ETICHETA, MAPARE_6D, NEMASURATE,          # noqa: E402
                         cuplu_sintetic, forta_6d_sintetica,
                         rigla_gamba_sintetica, unghi_glezna_sintetic, OFFSET_MONTAJ_GLEZNA)

PARTI = ("left", "right")
CU_CUPLU = ("hip", "knee")


def construieste(argv):
    ap = argparse.ArgumentParser(description="Senzori sintetici (vezi docstringul).")
    ap.add_argument("--hz", type=float, default=100.0, help="rata cuplu si forta 6D")
    ap.add_argument("--hz-unghi", type=float, default=100.0)
    ap.add_argument("--hz-rigla", type=float, default=10.0,
                    help="rigla e o masura lenta de lungime, nu un semnal de bucla")
    ap.add_argument("--incarcare-n", type=float, default=300.0,
                    help="apasarea de referinta pe pedala [N], parametru")
    from rclpy.utilities import remove_ros_args
    return ap.parse_args(remove_ros_args(args=["senzori_node.py"] + list(argv))[1:])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    a = construieste(argv)

    import rclpy
    from geometry_msgs.msg import WrenchStamped
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from std_msgs.msg import Float64, String

    class Senzori(Node):
        def __init__(self):
            Node.__init__(self, "rehab_senzori")
            self.q = {}
            self.dq = {}
            self.create_subscription(JointState, "/joint_states", self._js, 10)
            self.p_cuplu = {}
            for p in PARTI:
                for art in CU_CUPLU:
                    self.p_cuplu[(p, art)] = self.create_publisher(
                        Float64, "/rehab/cuplu/%s_%s" % (p, art), 10)
            self.p_6d = {p: self.create_publisher(
                WrenchStamped, "/rehab/forta_6d/%s" % p, 10) for p in PARTI}
            self.p_ung = {p: self.create_publisher(
                Float64, "/rehab/unghi_glezna/%s" % p, 10) for p in PARTI}
            self.p_rig = {p: self.create_publisher(
                Float64, "/rehab/rigla_gamba/%s" % p, 10) for p in PARTI}
            self.p_et = self.create_publisher(String, "/rehab/senzori/eticheta", 1)
            self.create_timer(1.0 / a.hz, self._tic_rapid)
            self.create_timer(1.0 / a.hz_unghi, self._tic_unghi)
            self.create_timer(1.0 / a.hz_rigla, self._tic_rigla)
            self.create_timer(1.0, self._tic_eticheta)
            self.get_logger().info(
                "senzori: cuplu+forta la %.0f Hz, unghi la %.0f Hz, rigla la %.0f Hz. "
                "TOATE valorile sunt %s." % (a.hz, a.hz_unghi, a.hz_rigla, ETICHETA))

        def _js(self, msg):
            for n, p in zip(msg.name, msg.position):
                self.q[n] = p
            if msg.velocity and len(msg.velocity) == len(msg.name):
                for n, v in zip(msg.name, msg.velocity):
                    self.dq[n] = v

        def _t(self):
            return self.get_clock().now().nanoseconds * 1e-9

        def _tic_rapid(self):
            t = self._t()
            for i, p in enumerate(PARTI):
                for j, art in enumerate(CU_CUPLU):
                    nume = "%s_%s_joint" % (p, art)
                    self.p_cuplu[(p, art)].publish(Float64(data=cuplu_sintetic(
                        self.q.get(nume, 0.0), self.dq.get(nume, 0.0), t,
                        faza=0.7 * (2 * i + j))))
                g = self.q.get("%s_ankle_joint" % p, 0.0)
                f = forta_6d_sintetica(g, a.incarcare_n, t)
                m = WrenchStamped()
                m.header.stamp = self.get_clock().now().to_msg()
                # frame_id poarta eticheta pe fir, nu doar in sursa
                m.header.frame_id = "%s_foot__SINTETIC" % p
                for cheie, (grup, camp, _) in MAPARE_6D.items():
                    setattr(getattr(m.wrench, grup), camp, float(f[cheie]))
                for grup, camp in NEMASURATE:
                    setattr(getattr(m.wrench, grup), camp, float("nan"))
                self.p_6d[p].publish(m)

        def _tic_unghi(self):
            t = self._t()
            for p in PARTI:
                self.p_ung[p].publish(Float64(data=unghi_glezna_sintetic(
                    self.q.get("%s_ankle_joint" % p, 0.0), t,
                    offset_rad=OFFSET_MONTAJ_GLEZNA[p])))

        def _tic_rigla(self):
            t = self._t()
            for p in PARTI:
                com = self.q.get("%s_shank_ext_joint" % p, 0.0)
                self.p_rig[p].publish(Float64(data=rigla_gamba_sintetica(
                    com, t, intarziere_m=0.0015)))

        def _tic_eticheta(self):
            self.p_et.publish(String(data=ETICHETA))

    rclpy.init()
    nod = Senzori()
    try:
        rclpy.spin(nod)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            nod.destroy_node()
        except KeyboardInterrupt:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except (Exception, KeyboardInterrupt):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
