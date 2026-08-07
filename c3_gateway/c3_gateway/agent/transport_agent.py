#!/usr/bin/env python3
"""transport_agent.py -- agentul de transport. UN SINGUR fisier, rulat de DOUA ori, cu
RMW_IMPLEMENTATION diferit (mecanismul dovedit la etapa 1c: SetEnvironmentVariable in
GroupAction izoleaza mediul per proces).

CE FACE, exact:
  canal UDS (de la gateway)  ->  publica pe topicul ROS prin RMW-ul LUI
  ecoul de pe topicul ROS    ->  raporteaza inapoi pe UDS (acelasi seq)

CE NU FACE, deliberat:
  - nu ia NICIO decizie (nu stie ce e o politica, un prag sau o marja);
  - nu stie ca exista un al doilea agent;
  - nu se uita niciodata la ce transport 'ar fi mai bun'.
Tot ce stie e: octetii astia, pe topicul asta, prin RMW-ul cu care am fost pornit. Daca
agentul ar sti mai mult, experimentul ar avea doua creiere si n-am mai putea spune care a
luat decizia.

VERIFICAREA DE PORNIRE: agentul primeste --rmw-asteptat si compara cu ce raporteaza
rclpy.get_rmw_implementation_identifier(). Daca nu se potriveste, IESE ZGOMOTOS, cu cod
nenul. Nu logheaza un avertisment si merge mai departe: un agent care ruleaza pe alt
transport decat crede lansatorul ar strica toata campania in tacere.

Nodul e SUBTIRE: I/O si atat. Canalul GE sintetic (--pierdere L,B) exista doar pentru
testul de integrare offline si aplica pierderea INAINTE de publicare, ca sa se poata
provoca o schimbare de regim fara netem si fara a doua masina.
"""
import argparse
import os
import sys
import time

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
for _p in (os.path.join(PACHET, "ipc"), os.path.join(PACHET, "core")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import rclpy                                                        # noqa: E402
from rclpy.node import Node                                         # noqa: E402
from rclpy.qos import QoSProfile                                    # noqa: E402
from std_msgs.msg import String                                     # noqa: E402

from channel import creeaza_canal                                   # noqa: E402
from protocol import TIP_ECOU, despacheteaza, impacheteaza          # noqa: E402

ADANCIME_QOS = 50               # aceeasi ca in C1/C2 (bench_client), ca sa fie comparabil


class AgentTransport(Node):
    def __init__(self, a):
        Node.__init__(self, a.nume_nod)
        self.a = a
        self.rmw = rclpy.get_rmw_implementation_identifier()
        self._verifica_rmw()

        qos = QoSProfile(depth=ADANCIME_QOS)
        self.pub = self.create_publisher(String, a.topic_iesire, qos)
        self.create_subscription(String, a.topic_ecou, self._din_ros, qos)

        self.canal = creeaza_canal("uds", a.canal, "oaspete", max_payload=a.max_payload)
        self.get_logger().info("agent %s: astept gateway-ul pe canalul '%s'"
                               % (self.rmw, a.canal))
        self.canal.conecteaza(timeout=a.timeout_conectare)
        self.get_logger().info("agent %s: conectat, public pe %s, ascult ecoul pe %s"
                               % (self.rmw, a.topic_iesire, a.topic_ecou))

        self.pierdere = None
        if a.pierdere:
            from canal_ge import CanalGE          # nucleul pur, acelasi canal ca in teste
            L, B = [float(x) for x in a.pierdere.split(",")]
            self.pierdere = CanalGE.from_LB_pct(L, B, seed=a.seed)
            self.get_logger().warn("agent %s: canal GE SINTETIC activ (%s) -- doar pentru "
                                   "testul offline" % (self.rmw, a.pierdere))

        self.n_primite = self.n_publicate = self.n_ecouri = 0
        # 500 Hz: la trafic de 55 Hz adauga cel mult 2 ms de asteptare, si e mult
        # sub costul unei masuratori (handoff-ul UDS e ~0.09 ms)
        self.create_timer(0.002, self._din_uds)

    # ------------------------------------------------------------------- verificari
    def _verifica_rmw(self):
        astept = self.a.rmw_asteptat
        if astept and self.rmw != astept:
            mesaj = ("EROARE FATALA: agentul '%s' ruleaza pe %s dar lansatorul astepta %s. "
                     "Ies acum: un agent pe alt transport decat cel asteptat ar falsifica "
                     "toata campania, in tacere." % (self.a.nume_nod, self.rmw, astept))
            self.get_logger().fatal(mesaj)
            print(mesaj, file=sys.stderr, flush=True)
            raise SystemExit(2)
        self.get_logger().info("agent %s: rmw confirmat" % self.rmw)

    # ------------------------------------------------------------------- fluxuri
    def _din_uds(self):
        """Tot ce a venit de la gateway se publica pe ROS. Bucla goleste canalul, ca sa nu
        ramana mesaje in urma cand ritmul creste."""
        for _ in range(64):
            m = self.canal.recv(timeout=0.0)
            if m is None:
                break
            self.n_primite += 1
            try:
                tip, topic, util = despacheteaza(m.payload)
            except ValueError as e:
                self.get_logger().error("cadru invalid de la gateway: %s" % e)
                continue
            if self.pierdere is not None and not self.pierdere.esantion():
                continue                       # 'pierdut pe link' (doar in testul offline)
            msg = String()
            # seq-ul calatoreste in mesajul ROS: ecoul trebuie sa poata fi legat de cerere
            msg.data = "%d|%s|%d|%s" % (m.seq, tip.decode(), topic,
                                        util.decode("latin-1"))
            self.pub.publish(msg)
            self.n_publicate += 1

    def _din_ros(self, msg):
        """Ecoul se intoarce la gateway cu ACELASI seq. Agentul nu interpreteaza nimic."""
        try:
            seq_s, tip_s, topic_s, _ = msg.data.split("|", 3)
            seq, topic = int(seq_s), int(topic_s)
        except (ValueError, AttributeError):
            return
        try:
            self.canal.send(impacheteaza(TIP_ECOU, topic, tip_s.encode()), seq)
            self.n_ecouri += 1
        except Exception as e:                 # canal inchis / pereche moarta
            self.get_logger().warn("nu am putut raporta ecoul: %s" % e)

    def raport(self):
        return ("agent %s: primite=%d publicate=%d ecouri=%d"
                % (self.rmw, self.n_primite, self.n_publicate, self.n_ecouri))


def construieste_argumente(argv):
    ap = argparse.ArgumentParser(description="Agent de transport C3 (vezi docstringul).")
    ap.add_argument("--canal", required=True, help="numele canalului UDS catre gateway")
    ap.add_argument("--nume-nod", default=None)
    ap.add_argument("--topic-iesire", default="/c3/tx")
    ap.add_argument("--topic-ecou", default="/c3/rx")
    ap.add_argument("--rmw-asteptat", default=None,
                    help="daca difera de cel efectiv, agentul IESE cu cod nenul")
    ap.add_argument("--max-payload", type=int, default=65536)
    ap.add_argument("--timeout-conectare", type=float, default=30.0)
    ap.add_argument("--pierdere", default=None,
                    help="canal GE sintetic 'L,B' (procente, pachete) -- DOAR pentru "
                         "testul offline; in campanie pierderea vine de la netem")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args([x for x in argv if not x.startswith("--ros-args")])
    if a.nume_nod is None:
        a.nume_nod = "c3_agent_%s" % a.canal.replace("-", "_")
    return a


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    a = construieste_argumente(argv)
    rclpy.init()
    nod = None
    try:
        nod = AgentTransport(a)
        rclpy.spin(nod)
    except KeyboardInterrupt:
        pass
    finally:
        if nod is not None:
            print(nod.raport(), flush=True)
            nod.canal.close()
            nod.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
