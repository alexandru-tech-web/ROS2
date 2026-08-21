#!/usr/bin/env python3
"""test_rmw_mutant.py -- MUTANTUL NUMIT: bugul de RMW, reconstruit si omorat.

CE DOVEDESTE
Ruleaza fixture-ul test/fixtures/mutant_rmw_scoped.launch.py, care reconstruieste
deliberat mecanica veche: SetEnvironmentVariable intr-un GroupAction scoped, plus un
nod pornit din RegisterEventHandler. Doi gardieni IDENTICI stau in doua pozitii:

    in_grup      pozitia gardianului din Valul 1 (in procesul launch-ului)
    din_handler  pozitia gardianului v2 (pe acelasi drum ca spawnerele)

Afirmatia centrala nu e 'gardianul prinde bugul'. E mai ascutita: ACELASI gardian,
pe ACELASI sistem stricat, da verdicte OPUSE dupa pozitie. Deci ce s-a reparat in v2
nu e logica verdictului, ci LOCUL din care se pune intrebarea. De aceea testul
aserteaza si ca pozitia veche raporteaza VERDE -- controlul negativ al controlului
negativ. Daca vreodata pozitia veche incepe sa pice, fixture-ul nu mai reproduce
bugul si testul nu mai dovedeste nimic; atunci trebuie reparat el, nu asertia.

CAPCANA DE MEDIU, tratata explicit
Daca mediul in care ruleaza testul are deja RMW_IMPLEMENTATION=rmw_cyclonedds_cpp,
nodul nascut din handler ar mosteni valoarea CORECTA din intamplare, mutantul nu ar
mai devia si testul ar TRECE DIN MOTIVUL GRESIT. De aceea subprocesul primeste
explicit un RMW ambiant DIFERIT de cel cerut de grup, si faptul asta e asertat.

Rulare: python3 test/test_rmw_mutant.py
"""
import os
import subprocess
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(AICI, "fixtures", "mutant_rmw_scoped.launch.py")

RMW_GRUP = "rmw_cyclonedds_cpp"      # ce cere grupul din fixture
RMW_AMBIANT = "rmw_fastrtps_cpp"     # ce gaseste un nod care NU primeste mediul grupului
COD_NEPOTRIVIRE = 3                  # tinut sincron cu rmw_guard.COD_NEPOTRIVIRE


def _ruleaza(scoped):
    env = dict(os.environ)
    env["RMW_IMPLEMENTATION"] = RMW_AMBIANT
    env["ROS_DOMAIN_ID"] = "181"
    p = subprocess.run(["ros2", "launch", FIXTURE, "scoped:=%s" % scoped],
                       capture_output=True, text=True, timeout=120, env=env)
    return p.stdout + p.stderr


def _verdict(iesire, eticheta):
    """(confirmat, a_murit_cu_cod) pentru gardianul cu eticheta data."""
    confirmat = ("[%s]: RMW confirmat" % eticheta) in iesire
    nepotrivire = ("[%s]: NEPOTRIVIRE RMW" % eticheta) in iesire
    return confirmat, nepotrivire


def main(argv):
    n = [0]

    def ok(cond, mesaj):
        if not cond:
            print("ESEC: %s" % mesaj)
            raise SystemExit(1)
        n[0] += 1

    # 0. sanatatea premisei: cele doua RMW-uri trebuie sa fie diferite, altfel
    # fixture-ul nu poate devia si tot testul e decorativ.
    ok(RMW_AMBIANT != RMW_GRUP,
       "RMW ambiant si RMW de grup trebuie sa difere, altfel mutantul nu deviaza")

    # 1. MUTANTUL VIU: grup scoped. Bugul TREBUIE sa se manifeste.
    out_bug = _ruleaza("true")
    conf_grup, nep_grup = _verdict(out_bug, "in_grup")
    conf_hand, nep_hand = _verdict(out_bug, "din_handler")

    ok(conf_grup and not nep_grup,
       "pozitia VECHE trebuie sa raporteze verde pe sistemul stricat; daca pica, "
       "fixture-ul nu mai reproduce bugul si testul nu mai dovedeste nimic")
    ok(nep_hand and not conf_hand,
       "pozitia din handler trebuie sa PRINDA nepotrivirea")
    ok("ruleaza '%s'" % RMW_AMBIANT in out_bug,
       "mesajul trebuie sa numeasca RMW-ul EFECTIV gasit, nu doar sa spuna ca difera")
    ok("exit code %d" % COD_NEPOTRIVIRE in out_bug,
       "gardianul din handler trebuie sa moara cu codul de NEPOTRIVIRE (%d), nu cu "
       "altul: altfel a fost prins din motivul gresit" % COD_NEPOTRIVIRE)
    ok("exit code 2" not in out_bug,
       "codul 2 ar insemna eroare de argparse, adica gardianul a murit inainte sa "
       "verifice ceva")

    # 2. FIXUL: acelasi fixture, grup nescopat. AMBELE pozitii trebuie sa treaca.
    out_fix = _ruleaza("false")
    conf_grup2, nep_grup2 = _verdict(out_fix, "in_grup")
    conf_hand2, nep_hand2 = _verdict(out_fix, "din_handler")
    ok(conf_grup2 and not nep_grup2, "cu grup nescopat, pozitia din grup trece")
    ok(conf_hand2 and not nep_hand2,
       "cu grup nescopat, nodul din handler mosteneste acelasi RMW -- asta E fixul")
    ok("NEPOTRIVIRE" not in out_fix, "fixul nu are voie sa lase nicio nepotrivire")

    # 3. Contrastul, spus o data explicit: acelasi gardian, aceeasi tinta, verdicte
    # opuse dupa pozitie. Asta e afirmatia pe care se sprijina mutarea gardianului.
    ok(nep_hand and not nep_hand2,
       "acelasi gardian trebuie sa pice cu grup scoped si sa treaca fara -- daca nu, "
       "nu pozitia era problema")

    print("test_rmw_mutant: %d verificari OK." % n[0])
    print("  mutant viu (scoped)  : in_grup=VERDE, din_handler=NEPOTRIVIRE cod %d"
          % COD_NEPOTRIVIRE)
    print("  fix       (nescopat) : in_grup=VERDE, din_handler=VERDE")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
