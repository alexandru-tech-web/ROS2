#!/usr/bin/env python3
"""session_recorder.py -- fiecare sesiune de simulare lasa in urma date analizabile.

UN CSV per sesiune, in ~/DATE_TWIN/<AAAALLZZ_HHMMSS>_<exercitiu>/sesiune.csv.

DE CE UN DIRECTOR PROPRIU, si nu ~/DATE_CAMPANIE: acolo stau datele CANONICE de
campanie ale tezei, care sunt read-only si nu se amesteca niciodata cu date de
simulare. Un twin care scrie in arhiva de campanie ar contamina exact ce nu are voie.

Antetul poarta provenienta (vezi recorder_core), subsolul poarta contoarele. NaN se
scrie NaN. Inchiderea la Ctrl+C scrie subsolul si lasa fisierul valid.

    ros2 run rehab_exo_description session_recorder.py --ros-args \
        -p exercitiu:=knee_extension -p rata_hz:=50.0
"""
import json
import math
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import recorder_core as rc                                        # noqa: E402

PARTI = ("left", "right")
ARTIC = ("hip", "knee", "ankle")
CU_CUPLU = ("hip", "knee")
RADACINA = os.path.expanduser("~/DATE_TWIN")


def coloane():
    """Ordinea coloanelor, definita O SINGURA DATA si folosita si la scriere si la
    citire. Daca se schimba, se schimba pentru toata lumea deodata."""
    c = []
    for p in PARTI:
        for a in ARTIC:
            j = "%s_%s_joint" % (p, a)
            c += ["%s.pos" % j, "%s.vel" % j, "%s.cmd" % j]
    for p in PARTI:
        for a in CU_CUPLU:
            c.append("cuplu.%s_%s" % (p, a))
    for p in PARTI:
        for camp in ("force", "torque"):
            for ax in ("x", "y", "z"):
                c.append("f6d.%s.%s.%s" % (p, camp, ax))
    for p in PARTI:
        c.append("unghi_glezna.%s" % p)
    for p in PARTI:
        c.append("rigla.%s" % p)
    return c


def commit_scurt():
    """Commit-ul de la BUILD, citit din fisierul instalat. NU se incearca `git` aici:
    recorderul ruleaza din spatiul de install, care nu e repo, iar rezultatul era
    "NECUNOSCUT" in antetul fiecarui CSV; adica taman campul care leaga datele de cod.
    Se pastreaza si varianta din arbore, pentru rulari din sursa."""
    try:
        from ament_index_python.packages import get_package_share_directory
        cale = os.path.join(get_package_share_directory("rehab_exo_description"),
                            "COMMIT")
        if os.path.isfile(cale):
            v = open(cale).read().strip()
            if v:
                return v
    except Exception:
        pass
    try:
        r = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(__file__)),
                            "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "NECUNOSCUT"
    except Exception:
        return "NECUNOSCUT"


def main(argv=None):
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import WrenchStamped
    from sensor_msgs.msg import JointState
    from std_msgs.msg import Float64, String
    from control_msgs.msg import JointTrajectoryControllerState as CS

    COL = coloane()

    class Recorder(Node):
        def __init__(self):
            Node.__init__(self, "session_recorder")
            for nume, imp in (("exercitiu", "necunoscut"), ("postura", "culcat"),
                              ("sezut_max_deg", 25.0), ("viteza", 1.0),
                              ("castig", 1.0), ("rata_hz", 50.0),
                              ("conventie", "B1")):
                self.declare_parameter(nume, imp)
            g = lambda k: self.get_parameter(k).value
            self.rata = float(g("rata_hz"))
            self.val = {}
            self.contor = {}
            self.randuri = 0
            self.nan = {}
            self.t0_sim = None
            self.t0_perete = time.time()
            self.evenimente = 0

            stampila = time.strftime("%Y%m%d_%H%M%S")
            self.dir = os.path.join(RADACINA, "%s_%s" % (stampila, g("exercitiu")))
            os.makedirs(self.dir, exist_ok=True)
            self.cale = os.path.join(self.dir, "sesiune.csv")
            self.f = open(self.cale, "w")
            self.meta = {"data_ora": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "commit": commit_scurt(), "conventie": g("conventie"),
                         "exercitiu": g("exercitiu"), "postura": g("postura"),
                         "sezut_max_deg": g("sezut_max_deg"), "viteza": g("viteza"),
                         "castig": g("castig"), "rtf_mediu": "in curs",
                         "rata_hz": self.rata}
            for l in rc.antet(self.meta, ipoteze=(
                    "geometria NU e masurata pe dispozitiv (IPOTEZE.md)",
                    "inaltimea talpii 0.230 m: clasa INVARIANT, cea mai slaba",
                    "banda de sezut 0..25 grade: IPOTEZA-ANTROPO",
                    "senzorii sunt SINTETICI, model declarat in senzori_core")):
                self.f.write(l + "\n")
            self.f.write("t_sim," + ",".join(COL) + "\n")
            self.f.flush()

            self.create_subscription(JointState, "/joint_states", self._js, 50)
            self.create_subscription(
                CS, "/leg_trajectory_controller/controller_state", self._cs, 50)
            for p in PARTI:
                for a in CU_CUPLU:
                    self.create_subscription(
                        Float64, "/rehab/cuplu/%s_%s" % (p, a),
                        self._mk("cuplu.%s_%s" % (p, a)), 20)
                self.create_subscription(
                    Float64, "/rehab/unghi_glezna/%s" % p,
                    self._mk("unghi_glezna.%s" % p), 20)
                self.create_subscription(
                    Float64, "/rehab/rigla_gamba/%s" % p, self._mk("rigla.%s" % p), 20)
                self.create_subscription(
                    WrenchStamped, "/rehab/forta_6d/%s" % p, self._mk6(p), 20)
            self.create_subscription(String, "/rehab/supervizor/eveniment",
                                     self._ev, 20)
            self.create_timer(1.0 / self.rata, self._tic)
            self.get_logger().info("inregistrez in %s" % self.cale)

        def _numara(self, canal):
            self.contor[canal] = self.contor.get(canal, 0) + 1

        def _mk(self, canal):
            def cb(m):
                self.val[canal] = m.data
                self._numara(canal)
            return cb

        def _mk6(self, p):
            def cb(m):
                w = m.wrench
                for camp in ("force", "torque"):
                    for ax in ("x", "y", "z"):
                        self.val["f6d.%s.%s.%s" % (p, camp, ax)] = getattr(
                            getattr(w, camp), ax)
                self._numara("f6d.%s" % p)
            return cb

        def _js(self, m):
            for n, pos, vel in zip(m.name, m.position, m.velocity):
                self.val["%s.pos" % n] = pos
                self.val["%s.vel" % n] = vel
            self._numara("joint_states")

        def _cs(self, m):
            for n, r in zip(m.joint_names, m.reference.positions):
                self.val["%s.cmd" % n] = r
            self._numara("controller_state")

        def _ev(self, m):
            self.evenimente += 1
            self._numara("supervizor_eveniment")
            try:
                e = json.loads(m.data)
                self.f.write("# EVENIMENT t=%.3f %s=%.4f prag %s %.4f\n"
                             % (self._t(), e["articulatie"], e["valoare"],
                                e["capat"], e["prag"]))
            except Exception:
                self.f.write("# EVENIMENT (neparsabil): %s\n" % m.data[:120])

        def _t(self):
            t = self.get_clock().now().nanoseconds * 1e-9
            if self.t0_sim is None:
                self.t0_sim = t
            return t - self.t0_sim

        def _tic(self):
            if "joint_states" not in self.contor:
                return          # nu se scriu randuri inainte sa existe date
            for c in COL:
                v = self.val.get(c)
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    self.nan[c] = self.nan.get(c, 0) + 1
            self.f.write(rc.rand(self._t(), self.val, COL) + "\n")
            self.randuri += 1

        def inchide(self):
            durata = self._t() if self.t0_sim is not None else 0.0
            perete = time.time() - self.t0_perete
            rtf = (durata / perete) if perete > 0.5 else None
            self.f.write("# rtf_mediu: %s\n" % ("%.3f" % rtf if rtf else "NECUNOSCUT"))
            L, ok, rele = rc.subsol(self.contor, self.randuri, self.rata, durata,
                                    nan=self.nan)
            for l in L:
                self.f.write(l + "\n")
            self.f.flush()
            self.f.close()
            self.get_logger().info(
                "inchis: %d randuri, %.1f s, RTF %s, %d evenimente de supervizor"
                % (self.randuri, durata, "%.2f" % rtf if rtf else "?", self.evenimente))
            if not ok:
                for canal, n, motiv in rele:
                    self.get_logger().error("CANAL PROBLEMATIC %s: %s" % (canal, motiv))
            self.get_logger().info("fisier: %s" % self.cale)

    rclpy.init(args=argv)
    n = Recorder()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        n.inchide()
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
