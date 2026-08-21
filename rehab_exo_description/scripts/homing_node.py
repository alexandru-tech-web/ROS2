#!/usr/bin/env python3
"""homing_node.py -- secventa de pornire, nod SUBTIRE peste transmisie_core.

Ce face si de ce, din document [PDF p.10]: encoderele de sold si genunchi sunt
ABSOLUTE, pe RS485 (REALWETECH RS485-RTU), si PASTREAZA unghiul la cadere de tensiune.
Deci pornirea dispozitivului real nu are cursa de referinta: unghiul se afla CITIND
encoderele. Twin-ul reproduce secventa, nu doar rezultatul.

Emularea: 'citirea encoderului' e primul /joint_states primit de la simulare, trecut
prin lantul de transmisie (transmisie_core: articulatie -> encoder -> articulatie).
Drumul dus-intors pare redundant, dar e chiar ce trebuie exercitat -- daca raportul
19:25 al genunchiului ar fi gresit undeva, aici s-ar vedea.

Iesire:
  - publica pe /rehab/homing un std_msgs/String cu starea (json-like, citibil in log);
  - IESE CU 0 cand homing-ul e gata, si cu 4 la timeout. Codul de iesire e contractul
    cu launch-ul: controllerele de miscare se lanseaza pe OnProcessExit al acestui nod,
    deci o pornire fara pozitie cunoscuta NU poate ajunge la o comanda de traiectorie.

Coduri de iesire distincte, dupa lectia din F0 (o clasa de esec pe cod):
  0 homing gata | 4 timeout fara toate encoderele | 5 argumente invalide
"""
import argparse
import json
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
if AICI not in sys.path:
    sys.path.insert(0, AICI)

from transmisie_core import (ARE_ENCODER, Homing, familie,          # noqa: E402
                            unghi_encoder_rad)

COD_OK = 0
COD_TIMEOUT = 4
COD_ARGUMENTE = 5


def construieste(argv):
    ap = argparse.ArgumentParser(description="Secventa de homing (vezi docstringul).")
    ap.add_argument("--articulatii", default=None,
                    help="lista separata prin virgula; implicit cele 6 revolute")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--topic", default="/joint_states")
    from rclpy.utilities import remove_ros_args
    return ap.parse_args(remove_ros_args(args=["homing_node.py"] + list(argv))[1:])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    a = construieste(argv)
    articulatii = ([x.strip() for x in a.articulatii.split(",") if x.strip()]
                   if a.articulatii else
                   ["left_hip_joint", "left_knee_joint", "left_ankle_joint",
                    "right_hip_joint", "right_knee_joint", "right_ankle_joint"])
    if not articulatii:
        print("homing: lista de articulatii goala", file=sys.stderr)
        return COD_ARGUMENTE

    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from std_msgs.msg import String

    class NodHoming(Node):
        def __init__(self):
            Node.__init__(self, "rehab_homing")
            self.h = Homing(articulatii)
            self.pub = self.create_publisher(String, "/rehab/homing", 10)
            self.create_subscription(JointState, a.topic, self._js, 10)
            self.gata = False
            self.get_logger().info(
                "HOMING: astept citirea encoderelor ABSOLUTE pe %d articulatii (%s). "
                "Cele fara encoder (%s) nu blocheaza."
                % (len(self.h.cere_encoder()), ", ".join(self.h.cere_encoder()),
                   ", ".join(self.h.raport()["fara_encoder"]) or "niciuna"))

        def _js(self, msg):
            if self.gata:
                return
            for nume, poz in zip(msg.name, msg.position):
                if nume not in articulatii or not ARE_ENCODER[familie(nume)]:
                    continue
                # emuleaza citirea: articulatie -> encoder -> inapoi
                self.h.citeste(nume, unghi_encoder_rad(familie(nume), poz))
            r = self.h.raport()
            self.pub.publish(String(data=json.dumps(r, sort_keys=True)))
            if r["gata"]:
                self.gata = True
                self.get_logger().info(
                    "HOMING GATA: %d encodere citite, unghiuri recuperate: %s"
                    % (len(r["citite"]),
                       ", ".join("%s=%.4f" % (j, self.h.unghi[j])
                                 for j in sorted(self.h.unghi))))

    rclpy.init()
    nod = NodHoming()
    cod = COD_TIMEOUT
    try:
        t0 = nod.get_clock().now()
        while rclpy.ok():
            rclpy.spin_once(nod, timeout_sec=0.1)
            if nod.gata:
                cod = COD_OK
                break
            if (nod.get_clock().now() - t0).nanoseconds > a.timeout * 1e9:
                nod.get_logger().error(
                    "HOMING ESUAT dupa %.0f s: lipsesc %s. Controllerele de miscare NU "
                    "pornesc -- o comanda de traiectorie pe pozitie necunoscuta nu are "
                    "voie sa existe." % (a.timeout, nod.h.raport()["lipsa"]))
                break
    except KeyboardInterrupt:
        pass
    finally:
        nod.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass
    return cod


if __name__ == "__main__":
    sys.exit(main())
