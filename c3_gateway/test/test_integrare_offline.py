#!/usr/bin/env python3
"""test_integrare_offline.py -- lantul INTREG, local: gateway + doi agenti + doua ecouri.

FARA netem si FARA a doua masina. Pierderea vine dintr-un canal GE sintetic aplicat IN
AGENT (--pierdere L,B), deci regimul e cunoscut exact si testul e repetabil pe orice masina.

CE VERIFICA (cerinta 7):
  V1. COMUTAREA ARE LOC cand regimul se schimba: calea activa capata pierdere mare, tabela
      (sintetica, scrisa de test) indica cealalta cale cu marja mare -> gateway-ul comuta.
  V2. NU COMUTA cand marja e sub prag/incertitudine: exact acelasi scenariu, dar cu o
      tabela in care marja e mica. Perechea V1/V2 e esentiala -- un test care doar arata
      ca 'a comutat' nu deosebeste o decizie de un reflex.
  V3. CALEA INACTIVA RAMANE SONDATA: in jurnal exista esantioane de tip 'P' pe AMBELE cai,
      pe tot parcursul, nu doar pe cea activa.
  V4. NICIO SCURGERE DE RMW: ambii agenti publica pe ACELASI nume de topic; daca RMW-urile
      s-ar vedea intre ele, ecoul unui transport ar numara si mesajele celuilalt.

Rulare: python3 test/test_integrare_offline.py [--pastreaza]
Cere ROS 2 sourced si /usr/bin/python3 (Anaconda nu are rclpy).
"""
import csv
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
PY = "/usr/bin/python3"
AGENT = os.path.join(PACHET, "c3_gateway", "agent", "transport_agent.py")
GATEWAY = os.path.join(PACHET, "c3_gateway", "nodes", "gateway_node.py")
ECOU = os.path.join(AICI, "echo_node.py")
APP = os.path.join(AICI, "app_pub.py")
DOMENIU = "88"                      # domeniu propriu, sa nu atinga nimic din campanii
CAI = (("cyclonedds", "rmw_cyclonedds_cpp"), ("zenoh", "rmw_zenoh_cpp"))


def _mediu(rmw):
    e = dict(os.environ)
    e["ROS_DOMAIN_ID"] = DOMENIU
    e["RMW_IMPLEMENTATION"] = rmw
    e["RUST_LOG"] = "warn"
    return e


def tabela(marja):
    """Tabela de politica SINTETICA. Testul nu foloseste tabela reala: acolo cyclonedds
    castiga 12/13 celule, deci nu s-ar putea provoca o comutare la 4 KB. Aici avem nevoie
    de un regim in care cealalta cale sa fie clar mai buna, ca sa putem verifica MECANISMUL.
    Marja e parametru: cu 60 pp trebuie sa comute, cu 2 pp nu are voie."""
    return {
        "schema": "c3_policy_table/1",
        "default_transport": "cyclonedds",
        "default_motiv": "sintetic (test de integrare)",
        "celule": [
            {"L": 0.0, "B": 1.0, "payload": 4096, "transport": "cyclonedds",
             "marja": 0.0, "covered": True, "sursa": "test", "conditie": "ideal"},
            {"L": 30.0, "B": 8.0, "payload": 4096, "transport": "zenoh",
             "marja": marja, "covered": True, "sursa": "test", "conditie": "ge_30_8"},
        ],
    }


class Rulare(object):
    """Porneste, supravegheaza si opreste toate procesele unei rulari."""

    def __init__(self, dir_lucru, marja, pierdere_cdds, durata):
        self.dir = dir_lucru
        self.marja = marja
        self.pierdere_cdds = pierdere_cdds
        self.durata = durata
        self.proc = []
        self.iesiri = {}

    def _porneste(self, nume, cmd, rmw):
        f = open(os.path.join(self.dir, "%s.log" % nume), "w")
        p = subprocess.Popen(cmd, env=_mediu(rmw), stdout=f, stderr=subprocess.STDOUT)
        self.proc.append((nume, p, f))
        return p

    def ruleaza(self):
        cale_tabela = os.path.join(self.dir, "tabela.json")
        with open(cale_tabela, "w") as f:
            json.dump(tabela(self.marja), f)
        jurnal = os.path.join(self.dir, "jurnal")

        # 1. router Zenoh (calea zenoh nu exista fara el)
        self._porneste("router", ["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"],
                       "rmw_zenoh_cpp")
        time.sleep(4.0)
        # 2. ecourile (tin locul masinii a doua), unul per RMW
        for transport, rmw in CAI:
            self._porneste("ecou_%s" % transport, [PY, ECOU, transport], rmw)
        time.sleep(2.0)
        # 3. agentii: cdds primeste canalul GE sintetic, zenoh ramane curat
        for transport, rmw in CAI:
            cmd = [PY, AGENT, "--canal", "it_%s" % transport, "--rmw-asteptat", rmw,
                   "--nume-nod", "c3_agent_%s" % transport]
            if transport == "cyclonedds" and self.pierdere_cdds:
                cmd += ["--pierdere", self.pierdere_cdds, "--seed", "5"]
            self._porneste("agent_%s" % transport, cmd, rmw)
        time.sleep(1.0)
        # 4. gateway-ul (pe RMW-ul primei cai; traficul lui ROS e local si nu se masoara)
        self._porneste("gateway", [PY, GATEWAY,
                                   "--cale", "cyclonedds:it_cyclonedds",
                                   "--cale", "zenoh:it_zenoh",
                                   "--topic", "/c3/app:4096",
                                   "--tabela", cale_tabela,
                                   "--jurnal", jurnal,
                                   "--eticheta", "integrare"], "rmw_cyclonedds_cpp")
        time.sleep(3.0)
        # 5. aplicatia
        self._porneste("app", [PY, APP, "50", "4096", str(self.durata)],
                       "rmw_cyclonedds_cpp")
        time.sleep(self.durata + 3.0)
        self.opreste()
        return jurnal

    def opreste(self):
        for nume, p, f in reversed(self.proc):
            if p.poll() is None:
                p.send_signal(signal.SIGINT)
        time.sleep(2.0)
        for nume, p, f in reversed(self.proc):
            if p.poll() is None:
                p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
            f.close()
            with open(os.path.join(self.dir, "%s.log" % nume)) as g:
                self.iesiri[nume] = g.read()


def citeste_jurnal(dir_jurnal):
    with open(os.path.join(dir_jurnal, "esantioane.csv")) as f:
        esantioane = list(csv.DictReader(f))
    with open(os.path.join(dir_jurnal, "evenimente.csv")) as f:
        evenimente = list(csv.DictReader(f))
    rez = {}
    cale_rez = os.path.join(dir_jurnal, "rezumat.json")
    if os.path.isfile(cale_rez):
        with open(cale_rez) as f:
            rez = json.load(f)
    return esantioane, evenimente, rez


def _numar_ecou(text):
    for linie in text.splitlines():
        if linie.startswith("ECOU "):
            for bucata in linie.split():
                if bucata.startswith("primite="):
                    return int(bucata.split("=")[1])
    return None


def scenariu(dir_baza, nume, marja, pierdere, durata):
    d = os.path.join(dir_baza, nume)
    os.makedirs(d)
    r = Rulare(d, marja, pierdere, durata)
    jurnal = r.ruleaza()
    esantioane, evenimente, rezumat = citeste_jurnal(jurnal)
    return r, esantioane, evenimente, rezumat


def main(argv):
    pastreaza = "--pastreaza" in argv
    baza = tempfile.mkdtemp(prefix="c3_integrare_")
    probleme = []
    try:
        print("== V1: marja mare (60 pp) + pierdere pe calea activa -> TREBUIE sa comute ==")
        r1, es1, ev1, rez1 = scenariu(baza, "v1_comuta", 60.0, "30,8", 25.0)
        comutari1 = [e for e in ev1 if e["eveniment"] == "comutare"]
        print("   esantioane=%d comutari=%d" % (len(es1), len(comutari1)))
        for e in comutari1[:3]:
            print("     t=%s %s -> %s (%s)" % (e["t_mono"], e["de_la"], e["la"], e["motiv"]))
        if not comutari1:
            probleme.append("V1: nu a comutat desi marja e 60 pp si calea activa pierde 30%")
        elif comutari1[0]["la"] != "zenoh":
            probleme.append("V1: a comutat pe %s, nu pe zenoh" % comutari1[0]["la"])

        print("\n== V2: acelasi scenariu, marja 2 pp -> NU are voie sa comute ==")
        r2, es2, ev2, rez2 = scenariu(baza, "v2_nu_comuta", 2.0, "30,8", 25.0)
        comutari2 = [e for e in ev2 if e["eveniment"] == "comutare"]
        print("   esantioane=%d comutari=%d" % (len(es2), len(comutari2)))
        if comutari2:
            probleme.append("V2: a comutat (%d ori) desi marja de 2 pp e sub prag"
                            % len(comutari2))

        print("\n== V3: calea inactiva ramane sondata ==")
        sonde = {}
        for e in es1:
            if e["tip"] == "P":
                sonde[e["cale"]] = sonde.get(e["cale"], 0) + 1
        print("   esantioane de sonda per cale: %s" % sonde)
        for transport, _ in CAI:
            if sonde.get(transport, 0) == 0:
                probleme.append("V3: calea %s nu a fost sondata deloc" % transport)
        if rez1:
            print("   overhead sonda: %s octeti/s (%.3f%% din trafic)"
                  % (rez1.get("octeti_s_sonda"), rez1.get("overhead_sonda_pct", 0.0)))

        print("\n== V4: nicio scurgere de RMW intre procese ==")
        for transport, _ in CAI:
            text = r1.iesiri.get("ecou_%s" % transport, "")
            n_ecou = _numar_ecou(text)
            publicate = None
            for linie in r1.iesiri.get("agent_%s" % transport, "").splitlines():
                if linie.startswith("agent ") and "publicate=" in linie:
                    publicate = int(linie.split("publicate=")[1].split()[0])
            print("   %-11s ecoul a primit %s, agentul a publicat %s"
                  % (transport, n_ecou, publicate))
            if n_ecou is None or publicate is None:
                probleme.append("V4: nu am putut citi contoarele pentru %s" % transport)
            elif n_ecou > publicate:
                probleme.append("V4: ecoul %s a primit %d > %d publicate de agentul lui "
                                "-- SCURGERE de RMW" % (transport, n_ecou, publicate))

        print("\n" + "=" * 70)
        if probleme:
            print("TEST DE INTEGRARE PICAT:")
            for p in probleme:
                print("  - %s" % p)
            print("\nlogurile raman in %s" % baza)
            return 1
        print("TEST DE INTEGRARE OFFLINE OK (V1 comuta, V2 nu, V3 sonda pe ambele cai, "
              "V4 fara scurgere de RMW).")
        return 0
    finally:
        if pastreaza:
            print("(loguri pastrate in %s)" % baza)
        elif not probleme:
            shutil.rmtree(baza, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
