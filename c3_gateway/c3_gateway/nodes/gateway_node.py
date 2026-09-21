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
  - tine sonde permanente si scrie jurnalul per-esantion (c3_gateway/jurnal.py).

DOUA SONDE, DOUA INTREBARI DIFERITE (corectie etapa 3.5)
Pana la 3.5 exista o singura sonda care facea doua treburi deodata si le facea pe amandoua
prost. Acum sunt separate, fiindca intrebarile chiar sunt diferite:

  SONDA DE CANAL (sonda/sonda_canal.py) -- 'ce a injectat netem in canal?'
  UDP brut, in afara ROS, transport-neutra. Alimenteaza SINGURUL estimator (L,B), cel cu
  care se cauta in tabela de politica. Trebuie sa fie transport-neutra tocmai fiindca
  tabela e indexata pe pierderea INJECTATA: masurata prin transport, aceeasi pierdere iese
  alta (CycloneDDS repara o parte, Zenoh amplifica), deci cheia de cautare ar depinde de
  raspunsul cautat.

  SONDE DE VIABILITATE -- 'calea asta mai e vie?'
  Cate una prin fiecare transport, la rata mica. Raspunsul lor e BINAR si merge exclusiv in
  vetoul switching.cale_utilizabila(). Nu produc (L,B) si nu au voie sa produca: C2 a
  aratat ca starea sesiunii minte (zenoh: 10/10 rulari fara niciun esantion livrat, in trei
  celule), deci calea de rezerva trebuie verificata -- dar pentru 'e vie?' nu e nevoie de o
  estimare, ci de un raspuns.

Castigul: un singur estimator fin in loc de doua estimari partinitoare, si dispare punctul
orb de 34 s de pe calea inactiva (unde aceleasi 171 de esantioane de asezare veneau la 5 Hz).
"""
import argparse
import collections
import os
import queue
import sys
import threading
import time

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
for _p in (os.path.join(PACHET, "ipc"), os.path.join(PACHET, "core"),
           os.path.join(PACHET, "sonda"), PACHET):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import rclpy                                                        # noqa: E402
from rclpy.node import Node                                         # noqa: E402
from rclpy.qos import QoSProfile                                    # noqa: E402
from std_msgs.msg import String                                     # noqa: E402

import switching                                                    # noqa: E402
from channel import creeaza_canal                                   # noqa: E402
from jurnal import Jurnal                                           # noqa: E402
from policy import Politica                                         # noqa: E402
from protocol import (TIP_APP, TIP_SONDA, despacheteaza,            # noqa: E402
                      impacheteaza)
import sonda_canal                                                  # noqa: E402
from sonda_canal import ClientSondaCanal                            # noqa: E402

ADANCIME_QOS = 50


class Cale(object):
    """O cale = un agent + canalul lui + o FEREASTRA de viabilitate.

    Fereastra tine ultimele rezultate ale sondei de viabilitate (True = s-a intors) si atat.
    Nu mai exista un estimator per cale: ce masura el -- pierderea vazuta prin transport --
    nu e marimea pe care e indexata tabela, iar pentru 'calea e vie?' o fereastra glisanta
    de bifat e suficienta si raspunde imediat, nu dupa 171 de esantioane."""

    def __init__(self, transport, canal, max_payload, fereastra):
        self.transport = transport
        self.canal = creeaza_canal("uds", canal, "gazda", max_payload=max_payload)
        self.seq = 0
        self.in_zbor = {}
        self.n_trimise = self.n_ecouri = 0
        self.fereastra = collections.deque(maxlen=int(fereastra))

    def urmatorul_seq(self):
        self.seq += 1
        return self.seq

    def noteaza_sonda(self, s_a_intors):
        self.fereastra.append(1 if s_a_intors else 0)

    def viabilitate(self):
        return switching.Viabilitate(len(self.fereastra), sum(self.fereastra))


class Gateway(Node):
    def __init__(self, a):
        Node.__init__(self, "c3_gateway")
        self.a = a
        self.politica = Politica.din_fisier(a.tabela or None)
        self.jurnal = (Jurnal(a.jurnal, a.eticheta, [t for t, _ in a.cai])
                       if a.jurnal else None)

        # Numele transporturilor NU sunt scrise aici: vin din cablajul de la lansare si
        # sunt validate fata de tabela de politica. Nodul nu are voie sa 'stie' ca exista
        # cyclonedds sau zenoh -- daca le-ar sti, ar avea o parere.
        cunoscute = self.politica.transporturi()
        self.cai = {}
        for transport, canal in a.cai:
            if transport not in cunoscute:
                raise SystemExit("EROARE: calea '%s' nu apare in tabela de politica (%s)"
                                 % (transport, ", ".join(sorted(cunoscute))))
            self.cai[transport] = Cale(transport, canal, a.max_payload, a.fereastra_sonda)
        if len(self.cai) < 2:
            raise SystemExit("EROARE: gateway-ul are nevoie de cel putin doua cai (--cale)")
        if a.transport_initial and a.transport_initial not in self.cai:
            raise SystemExit("EROARE: --transport-initial %r nu e una din cai (%s)"
                             % (a.transport_initial, ", ".join(sorted(self.cai))))
        self.get_logger().info("gateway: astept cei doi agenti")
        for c in self.cai.values():
            c.canal.conecteaza(timeout=a.timeout_conectare)
        self.get_logger().info("gateway: ambii agenti conectati")

        # cate un comutator PER TOPIC: decizia depinde de payload, deci nu poate fi globala
        self.topicuri = list(a.topicuri)
        self.comutatoare = {}
        for idx, (nume, payload) in enumerate(self.topicuri):
            # V1.1: calea de start e un factor FIXAT al campaniei (--transport-initial); implicit = cel din tabela
            self.comutatoare[idx] = switching.Comutator(self.politica, payload, transport_initial=a.transport_initial)
            self.create_subscription(
                String, nume, self._face_receptor(idx), QoSProfile(depth=ADANCIME_QOS))
            self.get_logger().info("gateway: topic %d = %s (payload nominal %d B)"
                                   % (idx, nume, payload))

        # sonda de CANAL: singura care hraneste estimatorul (L,B) folosit la lookup
        self.sonda_canal = ClientSondaCanal(a.reflector, a.port_sonda)
        self.get_logger().info("gateway: sonda de canal -> %s:%d la %.1f Hz (dwell %.2f s)"
                               % (a.reflector, a.port_sonda, a.hz_canal,
                                  switching.DWELL_MIN_S))

        self.t_ultima_decizie = {}
        # V1.1: ecourile nu se mai citesc prin timer la 500 Hz (masurat ~50% dintr-un nucleu, asteptare activa):
        # un fir per cale citeste BLOCANT (recv cu timeout 0.1 s), pune (transport, mesaj) in coada si trezeste
        # executorul prin guard condition; _citeste_ecouri goleste coada in firul executorului (starea nodului
        # ramane atinsa dintr-un singur fir). Expirarea celor in zbor: timer la 50 ms (timeout-ul e 1 s).
        self._coada = queue.Queue()
        self._gc = self.create_guard_condition(self._citeste_ecouri)
        self._fire = [threading.Thread(target=self._citeste_cale, args=(t, c), daemon=True) for t, c in self.cai.items()]
        for f in self._fire:
            f.start()
        self.create_timer(0.05, self._expira)
        self.create_timer(1.0 / a.hz_sonda, self._trimite_sonda)
        self.create_timer(1.0 / a.hz_canal, self._bate_sonda_canal)
        self.n_sonda = 0
        self.n_canal_fara_raport = 0

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
        est_canal = self.sonda_canal.estimare(varsta_maxima=self.a.varsta_maxima_raport)
        viab = {t: c.viabilitate() for t, c in self.cai.items()}

        if est_canal is None:
            # Fara o masuratoare proaspata a canalului nu exista cheie de cautare in tabela.
            # Se ramane pe transportul curent; NU se cade pe ultima valoare stiuta, fiindca
            # exact asta ar face gateway-ul sa para sanatos cand linkul a murit.
            self.n_canal_fara_raport += 1
            ales, motiv = activ, "fara raport proaspat de la sonda de canal"
        else:
            ales, motiv = com.decide(est_canal, acum, viab)
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

    # ------------------------------------------------------ sonda de canal (L,B)
    def _bate_sonda_canal(self):
        """Un pachet UDP brut spre reflector, plus consumarea rapoartelor intoarse.
        Nu blocheaza: socketul e neblocant si citirea e marginita."""
        self.sonda_canal.trimite()
        if self.sonda_canal.citeste() and self.jurnal is not None:
            r = self.sonda_canal.ultim
            self.jurnal.raport_canal(time.clock_gettime(time.CLOCK_MONOTONIC), r)

    # --------------------------------------------------- sonde de viabilitate
    def _trimite_sonda(self):
        """PERMANENT pe AMBELE cai, si pe cea inactiva. Raspund la o singura intrebare --
        calea e vie? -- si merg exclusiv in veto. Sunt mici, dar nu gratuite: octetii si
        pachetele lor se contabilizeaza separat in jurnal, ca overhead-ul sa fie o cifra."""
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
    def _citeste_cale(self, transport, cale):
        while rclpy.ok():
            try:
                m = cale.canal.recv(timeout=0.1)
            except Exception:
                m = None
            if m is None:
                if not cale.canal.stare().viu:
                    time.sleep(0.1)
                continue
            self._coada.put((transport, m))
            self._gc.trigger()

    def _expira(self):
        acum = time.clock_gettime(time.CLOCK_MONOTONIC)
        self._expira_in_zbor(acum, self._stare_curenta())

    def _citeste_ecouri(self):
        acum = time.clock_gettime(time.CLOCK_MONOTONIC)
        stare = self._stare_curenta()
        while True:
            try:
                transport, m = self._coada.get_nowait()
            except queue.Empty:
                break
            cale = self.cai[transport]
            cale.n_ecouri += 1
            trimis = cale.in_zbor.pop(m.seq, None)
            if trimis is None:
                continue
            t_trimis, octeti, tip, idx = trimis
            if tip == TIP_SONDA.decode("ascii"):
                # ATAT: sonda de viabilitate bifeaza 's-a intors' si se opreste aici.
                # Nu hraneste niciun estimator -- vezi docstringul modulului.
                cale.noteaza_sonda(True)
            if self.jurnal is None:
                continue
            self.jurnal.esantion(acum, m.seq, transport, tip, idx, octeti, True,
                                 (acum - t_trimis) * 1000.0, stare)

    def _expira_in_zbor(self, acum, stare):
        """Ce nu s-a intors intr-un timp rezonabil se scrie ca PIERDUT. Fara asta, jurnalul
        ar contine doar succese si livrarea ar iesi 100% din constructie -- iar fereastra de
        viabilitate nu ar afla niciodata ca o cale a murit (mortii nu raspund)."""
        for transport, cale in self.cai.items():
            expirate = [s for s, v in cale.in_zbor.items()
                        if acum - v[0] > self.a.timeout_ecou]
            for s in expirate:
                t_trimis, octeti, tip, idx = cale.in_zbor.pop(s)
                if tip == TIP_SONDA.decode("ascii"):
                    cale.noteaza_sonda(False)
                if self.jurnal is not None:
                    self.jurnal.esantion(acum, s, transport, tip, idx, octeti, False,
                                         None, stare)

    def _stare_curenta(self):
        """Ce stie gateway-ul in clipa asta: estimarea CANALULUI (una singura) plus
        viabilitatea fiecarei cai. Se scrie la fiecare esantion din jurnal."""
        return (self.sonda_canal.estimare(varsta_maxima=self.a.varsta_maxima_raport),
                {t: c.viabilitate() for t, c in self.cai.items()})

    def _noteaza_comutare(self, acum, de_la, la, motiv, idx):
        self.get_logger().info("COMUTARE topic %d: %s -> %s (%s)" % (idx, de_la, la, motiv))
        if self.jurnal is not None:
            self.jurnal.eveniment(acum, "comutare", de_la, la, motiv, idx,
                                  self.topicuri[idx][1])

    # ------------------------------------------------------------------- inchidere
    def inchide(self):
        # Tot ce trebuie ca overhead-ul sa poata fi recalculat offline, cu numitorul lui:
        # ratele, payload-urile si numarul de pachete -- nu doar procentul final.
        extra = {"hz_sonda_viabilitate": self.a.hz_sonda,
                 "payload_sonda_viabilitate": self.a.payload_sonda,
                 "hz_sonda_canal": self.a.hz_canal,
                 "payload_sonda_canal": self.sonda_canal.octeti_sonda(),
                 "dwell_min_s": switching.DWELL_MIN_S,
                 "n_sonda_cicluri": self.n_sonda,
                 "sonde_canal_trimise": self.sonda_canal.n_trimise,
                 "rapoarte_canal_primite": self.sonda_canal.n_rapoarte,
                 "decizii_fara_raport_canal": self.n_canal_fara_raport,
                 "transport_final": {i: c.transport for i, c in self.comutatoare.items()}}
        for t, c in self.cai.items():
            extra["trimise_%s" % t] = c.n_trimise
            extra["ecouri_%s" % t] = c.n_ecouri
            extra["viabilitate_%s" % t] = repr(c.viabilitate())
        r = self.jurnal.inchide(extra) if self.jurnal else extra
        for c in self.cai.values():
            c.canal.close()
        self.sonda_canal.close()
        return r


def construieste_argumente(argv):
    ap = argparse.ArgumentParser(description="Nodul gateway C3 (vezi docstringul).")
    ap.add_argument("--cale", action="append", default=None,
                    help="'transport:canal_uds', repetabil -- cablajul, nu politica")
    ap.add_argument("--topic", action="append", default=None,
                    help="'nume:payload_nominal', repetabil (decizie per topic)")
    ap.add_argument("--hz-sonda", type=float, default=5.0,
                    help="rata sondelor de VIABILITATE (raspuns binar, doar veto)")
    ap.add_argument("--payload-sonda", type=int, default=32)
    ap.add_argument("--fereastra-sonda", type=int, default=50,
                    help="cate sonde de viabilitate intra in fereastra glisanta")
    ap.add_argument("--reflector", default="127.0.0.1",
                    help="gazda pe care ruleaza reflectorul sondei de canal")
    ap.add_argument("--port-sonda", type=int, default=sonda_canal.PORT_IMPLICIT)
    ap.add_argument("--hz-canal", type=float, default=switching.HZ_SONDA_CANAL,
                    help="rata sondei de canal -- fixeaza dwell-ul, vezi sonda_canal.py")
    ap.add_argument("--varsta-maxima-raport", type=float, default=5.0,
                    help="peste atatea secunde, ultimul raport de canal nu mai e o "
                         "masuratoare si decizia se abtine")
    ap.add_argument("--timeout-ecou", type=float, default=1.0)
    ap.add_argument("--max-payload", type=int, default=65536)
    ap.add_argument("--timeout-conectare", type=float, default=30.0)
    ap.add_argument("--jurnal", default=None, help="director pentru jurnalul rularii")
    ap.add_argument("--eticheta", default="rulare")
    ap.add_argument("--tabela", default=None, help="alta policy_table.json")
    ap.add_argument("--transport-initial", default=None,
                    help="calea pe care porneste gateway-ul (V1.1: 'zenoh' in campania Etapei A); implicit cel din tabela")
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
