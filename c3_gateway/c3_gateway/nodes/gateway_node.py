#!/usr/bin/env python3
"""gateway_node.py -- nodul gateway. SUBTIRE: I/O si apeluri in nucleul pur, atat.

REGULA CARE SE VERIFICA AUTOMAT (test/test_nodes_fara_politica.py): in nodes/ nu exista
niciun prag, nicio marja, niciun nume de transport hardcodat si nicio comparatie de politica.
Tot ce seamana a decizie sta in core/ (policy.py, switching.py). Daca cineva strecoara aici
un 'if L > 0.15', testul pica. Motivul nu e purismul: daca decizia e in doua locuri, nu se
mai poate spune care a produs un rezultat de campanie.

CE FACE
  - primeste mesajele aplicatiei de pe topicele configurate;
  - pentru FIECARE topic cere nucleului decizia pe (L, B, payload) -- decizia e PER-TOPIC,
    fiindca marimea mesajului e in cheia politicii (C2: la 64 KB castigatorul se schimba);
  - trimite mesajul pe canalul UDS al transportului ales;
  - tine o SONDA permanenta pe AMBELE cai (nu doar pe cea activa) si hraneste cu ea cate un
    estimator INDEPENDENT per cale;
  - scrie jurnalul per-esantion (c3_gateway/jurnal.py).

DE CE SONDA PE AMBELE CAI
C2 a aratat ca starea sesiunii minte: o cale nefolosita poate fi moarta exact cand ai nevoie
de ea (zenoh: 10/10 rulari fara niciun esantion livrat, in trei celule). Daca am sonda doar
calea activa, am comuta pe o cale despre care nu stim nimic. Estimarea caii candidate intra
in decizie prin switching.cale_utilizabila().
"""
import argparse
import os
import sys
import time

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
for _p in (os.path.join(PACHET, "ipc"), os.path.join(PACHET, "core"), PACHET):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import rclpy                                                        # noqa: E402
from rclpy.node import Node                                         # noqa: E402
from rclpy.qos import QoSProfile                                    # noqa: E402
from std_msgs.msg import String                                     # noqa: E402

import switching                                                    # noqa: E402
from channel import creeaza_canal                                   # noqa: E402
from estimator import EstimatorLink                                 # noqa: E402
from jurnal import Jurnal                                           # noqa: E402
from policy import Politica                                         # noqa: E402
from protocol import (TIP_APP, TIP_SONDA, despacheteaza,            # noqa: E402
                      impacheteaza)

ADANCIME_QOS = 50


class Cale(object):
    """O cale = un agent + canalul lui + estimatorul ei. Contorul de secvente e PER CALE:
    estimatorul are nevoie de un sir continuu ca sa deduca golurile."""

    def __init__(self, transport, canal, max_payload):
        self.transport = transport
        self.canal = creeaza_canal("uds", canal, "gazda", max_payload=max_payload)
        self.estimator = EstimatorLink()
        self.seq = 0
        self.in_zbor = {}
        self.n_trimise = self.n_ecouri = 0

    def urmatorul_seq(self):
        self.seq += 1
        return self.seq


class Gateway(Node):
    def __init__(self, a):
        Node.__init__(self, "c3_gateway")
        self.a = a
        self.politica = Politica.din_fisier(a.tabela or None)
        self.jurnal = Jurnal(a.jurnal, a.eticheta) if a.jurnal else None

        # Numele transporturilor NU sunt scrise aici: vin din cablajul de la lansare si
        # sunt validate fata de tabela de politica. Nodul nu are voie sa 'stie' ca exista
        # cyclonedds sau zenoh -- daca le-ar sti, ar avea o parere.
        cunoscute = self.politica.transporturi()
        self.cai = {}
        for transport, canal in a.cai:
            if transport not in cunoscute:
                raise SystemExit("EROARE: calea '%s' nu apare in tabela de politica (%s)"
                                 % (transport, ", ".join(sorted(cunoscute))))
            self.cai[transport] = Cale(transport, canal, a.max_payload)
        if len(self.cai) < 2:
            raise SystemExit("EROARE: gateway-ul are nevoie de cel putin doua cai (--cale)")
        self.get_logger().info("gateway: astept cei doi agenti")
        for c in self.cai.values():
            c.canal.conecteaza(timeout=a.timeout_conectare)
        self.get_logger().info("gateway: ambii agenti conectati")

        # cate un comutator PER TOPIC: decizia depinde de payload, deci nu poate fi globala
        self.topicuri = list(a.topicuri)
        self.comutatoare = {}
        for idx, (nume, payload) in enumerate(self.topicuri):
            self.comutatoare[idx] = switching.Comutator(self.politica, payload)
            self.create_subscription(
                String, nume, self._face_receptor(idx), QoSProfile(depth=ADANCIME_QOS))
            self.get_logger().info("gateway: topic %d = %s (payload nominal %d B)"
                                   % (idx, nume, payload))

        self.t_ultima_decizie = {}
        self.create_timer(0.002, self._citeste_ecouri)
        self.create_timer(1.0 / a.hz_sonda, self._trimite_sonda)
        self.n_sonda = 0

    # ------------------------------------------------------- intrare din aplicatie
    def _face_receptor(self, idx):
        def receptor(msg):
            self._trimite_aplicatie(idx, msg.data.encode("latin-1"))
        return receptor

    def _trimite_aplicatie(self, idx, util):
        """Singurul loc unde se alege calea -- si alegerea o face NUCLEUL."""
        acum = time.clock_gettime(time.CLOCK_MONOTONIC)
        com = self.comutatoare[idx]
        activ = com.transport
        est_activa = self.cai[activ].estimator.estimare()
        stari = {t: c.estimator.estimare() for t, c in self.cai.items()}

        ales, motiv = com.decide(est_activa, acum, stari)
        if ales != activ:
            self._noteaza_comutare(acum, activ, ales, motiv, idx)
        self.t_ultima_decizie[idx] = acum

        cale = self.cai[ales]
        seq = cale.urmatorul_seq()
        cadru = impacheteaza(TIP_APP, idx, util)
        try:
            cale.canal.send(cadru, seq)
        except Exception as e:
            self.get_logger().warn("nu am putut trimite pe %s: %s" % (ales, e))
            return
        cale.n_trimise += 1
        cale.in_zbor[seq] = (acum, len(cadru), "A", idx)

    # ------------------------------------------------------------------- sonda
    def _trimite_sonda(self):
        """PERMANENT pe AMBELE cai. Sonda e mica, dar nu gratuita: octetii ei se
        contabilizeaza separat in jurnal, ca overhead-ul sa fie o cifra, nu o impresie."""
        acum = time.clock_gettime(time.CLOCK_MONOTONIC)
        util = b"s" * self.a.payload_sonda
        for transport, cale in self.cai.items():
            seq = cale.urmatorul_seq()
            cadru = impacheteaza(TIP_SONDA, 0, util)
            try:
                cale.canal.send(cadru, seq)
            except Exception:
                continue
            cale.n_trimise += 1
            cale.in_zbor[seq] = (acum, len(cadru), "P", 0)
        self.n_sonda += 1

    # ------------------------------------------------------------------- ecouri
    def _citeste_ecouri(self):
        acum = time.clock_gettime(time.CLOCK_MONOTONIC)
        stari = {t: c.estimator.estimare() for t, c in self.cai.items()}
        for transport, cale in self.cai.items():
            for _ in range(128):
                m = cale.canal.recv(timeout=0.0)
                if m is None:
                    break
                cale.n_ecouri += 1
                # ecoul hraneste estimatorul CAII: golurile din seq sunt pierderile
                cale.estimator.observa(m.seq)
                trimis = cale.in_zbor.pop(m.seq, None)
                if trimis is None or self.jurnal is None:
                    continue
                t_trimis, octeti, tip, idx = trimis
                self.jurnal.esantion(acum, m.seq, transport, tip, idx, octeti, True,
                                     (acum - t_trimis) * 1000.0, stari)
        self._expira_in_zbor(acum, stari)

    def _expira_in_zbor(self, acum, stari):
        """Ce nu s-a intors intr-un timp rezonabil se scrie ca PIERDUT. Fara asta, jurnalul
        ar contine doar succese si livrarea ar iesi 100% din constructie."""
        for transport, cale in self.cai.items():
            expirate = [s for s, v in cale.in_zbor.items()
                        if acum - v[0] > self.a.timeout_ecou]
            for s in expirate:
                t_trimis, octeti, tip, idx = cale.in_zbor.pop(s)
                if self.jurnal is not None:
                    self.jurnal.esantion(acum, s, transport, tip, idx, octeti, False,
                                         None, stari)

    def _noteaza_comutare(self, acum, de_la, la, motiv, idx):
        self.get_logger().info("COMUTARE topic %d: %s -> %s (%s)" % (idx, de_la, la, motiv))
        if self.jurnal is not None:
            self.jurnal.eveniment(acum, "comutare", de_la, la, motiv, idx,
                                  self.topicuri[idx][1])

    # ------------------------------------------------------------------- inchidere
    def inchide(self):
        extra = {"hz_sonda": self.a.hz_sonda, "payload_sonda": self.a.payload_sonda,
                 "n_sonda_cicluri": self.n_sonda,
                 "transport_final": {i: c.transport for i, c in self.comutatoare.items()}}
        for t, c in self.cai.items():
            extra["trimise_%s" % t] = c.n_trimise
            extra["ecouri_%s" % t] = c.n_ecouri
        r = self.jurnal.inchide(extra) if self.jurnal else extra
        for c in self.cai.values():
            c.canal.close()
        return r


def construieste_argumente(argv):
    ap = argparse.ArgumentParser(description="Nodul gateway C3 (vezi docstringul).")
    ap.add_argument("--cale", action="append", default=None,
                    help="'transport:canal_uds', repetabil -- cablajul, nu politica")
    ap.add_argument("--topic", action="append", default=None,
                    help="'nume:payload_nominal', repetabil (decizie per topic)")
    ap.add_argument("--hz-sonda", type=float, default=5.0)
    ap.add_argument("--payload-sonda", type=int, default=32)
    ap.add_argument("--timeout-ecou", type=float, default=1.0)
    ap.add_argument("--max-payload", type=int, default=65536)
    ap.add_argument("--timeout-conectare", type=float, default=30.0)
    ap.add_argument("--jurnal", default=None, help="director pentru jurnalul rularii")
    ap.add_argument("--eticheta", default="rulare")
    ap.add_argument("--tabela", default=None, help="alta policy_table.json")
    a = ap.parse_args([x for x in argv if not x.startswith("--ros-args")])
    perechi = []
    for t in (a.topic or ["/c3/app:4096"]):
        nume, _, payload = t.partition(":")
        perechi.append((nume, int(payload or 4096)))
    a.topicuri = perechi
    cai = []
    for c in (a.cale or []):
        transport, _, canal = c.partition(":")
        if not transport or not canal:
            raise SystemExit("--cale asteapta 'transport:canal_uds', am primit %r" % c)
        cai.append((transport, canal))
    a.cai = cai
    return a


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    a = construieste_argumente(argv)
    rclpy.init()
    nod = None
    try:
        nod = Gateway(a)
        rclpy.spin(nod)
    except KeyboardInterrupt:
        pass
    finally:
        if nod is not None:
            r = nod.inchide()
            print("gateway: %s" % r, flush=True)
            nod.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
