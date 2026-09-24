#!/usr/bin/python3
"""monitor_senzori.py -- tabloul LIVE al demonstratiei, in terminal, la 2 Hz.

De ce in terminal si nu o fereastra: pe masina asta procesele grafice pornite din
terminalul VSCode mor cu 'symbol lookup error' pe biblioteci scurse din snap (e
exact ce omora GUI-ul Gazebo). Un tablou de text merge peste ssh, se poate copia
intr-un jurnal si nu are nevoie de nimic instalat. telemetry_display.py, cu
grafice, ramane pentru cand se ruleaza dintr-un terminal normal.

Ce arata, pe fiecare din cele 6 articulatii: pozitia CERUTA (referinta lui JTC),
pozitia MASURATA (/joint_states), eroarea de urmarire cu bara, si cuplul. Dedesubt,
senzorii sintetici, cu cele trei verdicte din monitor_core.

Tot ce vine de la senzori e SINTETIC. Eticheta se citeste de la sursa, din
/rehab/senzori/eticheta, si se afiseaza la fiecare cadru -- nu se scrie aici, ca sa
nu existe doua versiuni ale ei care pot ajunge sa nu mai coincida.

Rulare:  ros2 run rehab_exo_description monitor_senzori.py
         ros2 run rehab_exo_description monitor_senzori.py --ros-args -p hz:=1.0
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import monitor_core as mc                                          # noqa: E402
import senzori_core as sc                                          # noqa: E402
import spec_derivate as sd                                        # noqa: E402

# Limitele nominale de viteza NU se scriu aici: se deriva, o singura data, din
# reductor + motor, in spec_derivate. Sunt aceleasi cifre care ajung si in xacro.
RO = {"hip": "sold", "knee": "genunchi", "ankle": "glezna"}
LIMITE_VITEZA = {en: sd.viteza_nominala_rad_s(ro) for en, ro in RO.items()}


def main(argv=None):
    import rclpy
    from rclpy.node import Node
    from control_msgs.msg import JointTrajectoryControllerState as CS
    from geometry_msgs.msg import WrenchStamped
    from sensor_msgs.msg import JointState
    from std_msgs.msg import Float64, String

    class Monitor(Node):
        def __init__(self):
            Node.__init__(self, "rehab_monitor")
            self.declare_parameter("hz", 2.0)
            self.declare_parameter("parte_6d", "left")
            self.parte6 = self.get_parameter("parte_6d").value
            self.masurat, self.cerut, self.cupluri = {}, {}, {}
            self.viteze = {}
            self.unghi, self.w6 = {}, {}
            self.eticheta = "(eticheta senzorilor inca nu a sosit)"
            self.t0 = None
            self.perete0 = None

            self.create_subscription(JointState, "/joint_states", self._js, 10)
            self.create_subscription(
                CS, "/leg_trajectory_controller/controller_state", self._cs, 10)
            for p in mc.PARTI:
                for a in ("hip", "knee"):
                    self.create_subscription(
                        Float64, "/rehab/cuplu/%s_%s" % (p, a),
                        self._mk_cuplu(p, a), 10)
                self.create_subscription(
                    Float64, "/rehab/unghi_glezna/%s" % p, self._mk_unghi(p), 10)
                self.create_subscription(
                    WrenchStamped, "/rehab/forta_6d/%s" % p, self._mk_w6(p), 10)
            self.create_subscription(
                String, "/rehab/senzori/eticheta", self._et, 1)
            self.create_timer(1.0 / float(self.get_parameter("hz").value), self._tic)

        def _js(self, m):
            if self.t0 is None:
                self.t0 = self.get_clock().now().nanoseconds * 1e-9
                self.perete0 = time.time()
            for n, p in zip(m.name, m.position):
                self.masurat[n] = p
            for n, v in zip(m.name, m.velocity):
                self.viteze[n] = v

        def _cs(self, m):
            for n, p in zip(m.joint_names, m.reference.positions):
                self.cerut[n] = p

        def _mk_cuplu(self, p, a):
            return lambda m: self.cupluri.__setitem__((p, a), m.data)

        def _mk_unghi(self, p):
            return lambda m: self.unghi.__setitem__(p, m.data)

        def _mk_w6(self, p):
            def cb(m):
                if p != self.parte6:
                    return
                w = m.wrench
                self.w6 = {(c, a): getattr(getattr(w, c), a)
                           for c in ("force", "torque") for a in ("x", "y", "z")}
            return cb

        def _et(self, m):
            self.eticheta = m.data

        def _tic(self):
            t = 0.0 if self.t0 is None else (
                self.get_clock().now().nanoseconds * 1e-9 - self.t0)
            # RTF: nodul are use_sim_time, deci get_clock() e timpul SIMULAT, iar
            # time.time() e cel de perete. Raportul lor e ce cauta oricine compara
            # o rata masurata aici cu alta rulare sau cu hardware-ul.
            factor = None if self.perete0 is None else mc.rtf(
                t, time.time() - self.perete0)
            linii = mc.tabel(t, self.cerut, self.masurat, self.cupluri,
                             self.unghi, self.w6, sc.NEMASURATE, self.eticheta,
                             sc.OFFSET_MONTAJ_GLEZNA, self.viteze, LIMITE_VITEZA,
                             factor)
            # ecran curat, ca sa se citeasca de la distanta la o demonstratie
            sys.stdout.write("\033[H\033[2J" if sys.stdout.isatty() else "\n")
            sys.stdout.write("\n".join(linii) + "\n")
            sys.stdout.flush()

    rclpy.init(args=argv)
    n = Monitor()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            n.destroy_node()
        except KeyboardInterrupt:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
