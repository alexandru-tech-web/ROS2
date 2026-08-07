#!/usr/bin/env python3
"""test_integrare_offline.py -- lantul INTREG, local: gateway + doi agenti + doua ecouri.

FARA netem si FARA a doua masina. Pierderea vine dintr-un canal GE sintetic, iar dupa
corectia de la etapa 3.5 ea se aplica acolo unde s-ar aplica si netem: pe drumul SONDEI DE
CANAL, adica in reflector. Asta nu e un detaliu de montaj -- e chiar proprietatea testata.
Decizia gateway-ului se ia acum pe (L,B) masurate de sonda transport-neutra, deci un test
care ar injecta pierderea doar in agent ar lasa estimatorul sa vada un canal curat si nu ar
mai exercita lantul real.

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
  V5. SONDA DE CANAL VEDE CE S-A INJECTAT: rapoartele din sonda_canal.csv trebuie sa dea
      un L apropiat de cel injectat in reflector. E validarea de instrument pentru C3, si
      se face cu tools/valideaza_instrument_c3.py -- adica exact pe drumul pe care se va
      face si pe datele de campanie, nu cu o citire ad-hoc scrisa doar pentru test.
  V6. ESTIMAREA NU MAI DEPINDE DE TRANSPORTUL ACTIV: jurnalul nu are voie sa contina
      coloane de (L,B) per cale. Daca reapar, cineva a reintrodus estimarea prin transport.

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
SONDA = os.path.join(PACHET, "c3_gateway", "sonda", "sonda_canal.py")
VALIDATOR = os.path.join(PACHET, "tools", "valideaza_instrument_c3.py")
PORT_SONDA = 47399                  # port propriu, sa nu dea peste o rulare reala
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

    def __init__(self, dir_lucru, marja, pierdere_canal, durata, eticheta="integrare"):
        self.dir = dir_lucru
        self.marja = marja
        self.pierdere_canal = pierdere_canal
        self.durata = durata
        self.eticheta = eticheta
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

        # 0. reflectorul sondei de canal: tine locul masinii a doua. Pierderea sintetica
        # se aplica AICI, la receptie -- unde ar aplica-o si netem pe HIL.
        cmd_sonda = [PY, SONDA, "--rol", "reflector", "--port", str(PORT_SONDA)]
        if self.pierdere_canal:
            cmd_sonda += ["--pierdere", self.pierdere_canal, "--seed", "5"]
        self._porneste("reflector", cmd_sonda, "rmw_cyclonedds_cpp")
        time.sleep(0.5)
        # 1. router Zenoh (calea zenoh nu exista fara el)
        self._porneste("router", ["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"],
                       "rmw_zenoh_cpp")
        time.sleep(4.0)
        # 2. ecourile (tin locul masinii a doua), unul per RMW
        for transport, rmw in CAI:
            self._porneste("ecou_%s" % transport, [PY, ECOU, transport], rmw)
        time.sleep(2.0)
        # 3. agentii: amandoi curati. Pierderea e pe canal (in reflector), nu in agent --
        # exact ca in HIL, unde netem degradeaza linkul, nu un anume transport.
        for transport, rmw in CAI:
            cmd = [PY, AGENT, "--canal", "it_%s" % transport, "--rmw-asteptat", rmw,
                   "--nume-nod", "c3_agent_%s" % transport]
            self._porneste("agent_%s" % transport, cmd, rmw)
        time.sleep(1.0)
        # 4. gateway-ul (pe RMW-ul primei cai; traficul lui ROS e local si nu se masoara)
        self._porneste("gateway", [PY, GATEWAY,
                                   "--cale", "cyclonedds:it_cyclonedds",
                                   "--cale", "zenoh:it_zenoh",
                                   "--topic", "/c3/app:4096",
                                   "--tabela", cale_tabela,
                                   "--jurnal", jurnal,
                                   "--eticheta", self.eticheta,
                                   "--reflector", "127.0.0.1",
                                   "--port-sonda", str(PORT_SONDA)],
                       "rmw_cyclonedds_cpp")
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


def scenariu(dir_baza, nume, marja, pierdere, durata, eticheta="integrare"):
    d = os.path.join(dir_baza, nume)
    os.makedirs(d)
    r = Rulare(d, marja, pierdere, durata, eticheta)
    jurnal = r.ruleaza()
    esantioane, evenimente, rezumat = citeste_jurnal(jurnal)
    r.jurnal = jurnal
    return r, esantioane, evenimente, rezumat


def main(argv):
    pastreaza = "--pastreaza" in argv
    baza = tempfile.mkdtemp(prefix="c3_integrare_")
    probleme = []
    try:
        print("== V1: marja mare (60 pp) + pierdere 30/8 pe CANAL -> TREBUIE sa comute ==")
        # 70 s, nu 40: validarea de instrument (V5) cere rapoarte cu estimatorul convers
        # (n >= 500 esantioane), iar la 20 Hz cu 30% pierdere asta se atinge abia dupa ~36 s
        r1, es1, ev1, rez1 = scenariu(baza, "v1_comuta", 60.0, "30,8", 70.0, "ge_30_8")
        comutari1 = [e for e in ev1 if e["eveniment"] == "comutare"]
        print("   esantioane=%d comutari=%d" % (len(es1), len(comutari1)))
        for e in comutari1[:3]:
            print("     t=%s %s -> %s (%s)" % (e["t_mono"], e["de_la"], e["la"], e["motiv"]))
        if not comutari1:
            probleme.append("V1: nu a comutat desi marja e 60 pp si calea activa pierde 30%")
        elif comutari1[0]["la"] != "zenoh":
            probleme.append("V1: a comutat pe %s, nu pe zenoh" % comutari1[0]["la"])

        print("\n== V2: acelasi scenariu, marja 2 pp -> NU are voie sa comute ==")
        r2, es2, ev2, rez2 = scenariu(baza, "v2_nu_comuta", 2.0, "30,8", 40.0, "ge_30_8")
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
            o = rez1.get("overhead", {})
            print("   sonde de canal trimise=%s, rapoarte primite=%s, decizii fara raport=%s"
                  % (rez1.get("sonde_canal_trimise"), rez1.get("rapoarte_canal_primite"),
                     rez1.get("decizii_fara_raport_canal")))
            print("   overhead sonde: %.2f%% in OCTETI, %.2f%% in PACHETE"
                  % (o.get("overhead_octeti_pct", 0.0), o.get("overhead_pachete_pct", 0.0)))
            print("   numitor: %s" % o.get("numitor"))
            # Nu e destul ca rapoartele sa EXISTE: trebuie sa vina la ritmul promis.
            # Prima versiune a reflectorului trimitea 3 rapoarte in 40 s in loc de ~80, si
            # testul trecea oricum, fiindca cele 3 erau aproximativ corecte. Un instrument
            # care raspunde de 25 de ori mai rar decat crezi nu e un instrument bun 'in
            # medie', e unul pe care nu-l cunosti.
            asteptate = 2.0 * rez1.get("durata_s", 0.0) * 0.5      # 2 Hz, marja generoasa
            primite = rez1.get("rapoarte_canal_primite", 0)
            if primite < asteptate:
                probleme.append("V3: doar %d rapoarte de canal in %.0f s (asteptat cel "
                                "putin %.0f la 2 Hz) -- sonda nu tine ritmul"
                                % (primite, rez1.get("durata_s", 0.0), asteptate))
            fara = rez1.get("decizii_fara_raport_canal", 0)
            n_app = rez1.get("n_app", 1) or 1
            if fara > 0.2 * n_app:
                probleme.append("V3: %d decizii din %d luate fara raport proaspat de canal "
                                "-- gateway-ul a fost orb mai tot timpul" % (fara, n_app))

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

        print("\n== V5: sonda de canal vede ce s-a injectat (validare de instrument) ==")
        p = subprocess.run([PY, VALIDATOR, r1.jurnal], capture_output=True, text=True)
        for linie in p.stdout.strip().splitlines():
            print("   " + linie)
        if p.returncode != 0:
            probleme.append("V5: validatorul nu a gasit nicio rulare comparabila -- "
                            "jurnalul nu permite comparatia masurat vs injectat")
        else:
            # abaterea nu trebuie sa fie zero (canalul e stochastic), dar nici de ordinul
            # regimului: o sonda care ar rata complet 30% de pierdere nu masoara canalul
            import re as _re
            # Ce se verifica AICI e mecanismul, nu acuratetea: o singura rulare nu poate
            # valida instrumentul (la B=8 informatia vine per rafala, deci estimarea
            # variaza mult intre rulari). Acuratetea se stabileste pe repetitiile
            # campaniei. Ce trebuie sa fie adevarat deja e ca sonda VEDE regimul injectat
            # si ca exista destule rapoarte converse ca sa se poata compara offline.
            m = _re.search(r"(\d+) \((\d+) converse\)", p.stdout)
            mL = _re.search(r"masurat.*\n.*\n\S+\s+\S+\s+\S+ / \S+\s+([0-9.]+) /",
                            p.stdout)
            if not m or int(m.group(2)) < 10:
                probleme.append("V5: prea putine rapoarte converse (%s) -- rularea nu "
                                "ajunge pentru validarea offline"
                                % (m.group(2) if m else "?"))
            if not mL:
                probleme.append("V5: nu am putut citi L masurat din iesirea validatorului")
            elif float(mL.group(1)) < 10.0:
                probleme.append("V5: sonda raporteaza L=%s%% pe un canal cu 30%% injectat "
                                "-- nu vede regimul, deci nu masoara canalul" % mL.group(1))

        print("\n== V6: nicio coloana de (L,B) per cale in jurnal ==")
        coloane = list(es1[0].keys()) if es1 else []
        gresite = [c for c in coloane
                   if (c.startswith("L_") or c.startswith("B_"))
                   and c not in ("L_canal", "B_canal")]
        print("   coloane de stare: %s" % [c for c in coloane
                                           if c.startswith(("L_", "B_", "viab_"))])
        if gresite:
            probleme.append("V6: jurnalul are (L,B) per cale (%s) -- estimarea prin "
                            "transport a revenit" % ", ".join(gresite))

        print("\n" + "=" * 70)
        if probleme:
            print("TEST DE INTEGRARE PICAT:")
            for p in probleme:
                print("  - %s" % p)
            print("\nlogurile raman in %s" % baza)
            return 1
        print("TEST DE INTEGRARE OFFLINE OK (V1 comuta, V2 nu, V3 sonde pe ambele cai, "
              "V4 fara scurgere de RMW, V5 sonda vede ce s-a injectat, V6 nicio estimare "
              "per cale).")
        return 0
    finally:
        if pastreaza:
            print("(loguri pastrate in %s)" % baza)
        elif not probleme:
            shutil.rmtree(baza, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
