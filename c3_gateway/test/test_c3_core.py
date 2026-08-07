#!/usr/bin/env python3
"""test_c3_core.py -- suita nucleului C3. Ruleaza selftesturile fiecarui modul si adauga
testele de INTEGRARE, adica exact intrebarile la care un modul singur nu poate raspunde:

  I1. Lantul intreg (canal GE -> estimator -> politica -> comutator) alege transportul pe
      care il indica datele C2, pe celulele grilei.
  I2. ANTI-FLAPPING: un canal care oscileaza chiar pe granita pragului nu produce un numar
      nemarginit de comutari.
  I3. Politica NU comuta cand marja e sub incertitudinea estimarii -- testat cu sigma
      REALA, cea raportata de estimator dupa ce a mestecat canalul, nu cu una inventata.
  I4. Nucleul e PUR: niciun modul din core/ nu importa rclpy, socket sau os.environ.

Rulare: python3 test/test_c3_core.py
"""
import ast
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(os.path.dirname(AICI), "c3_gateway", "core")
sys.path.insert(0, CORE)

import canal_ge                                            # noqa: E402
import estimator                                          # noqa: E402
import policy                                             # noqa: E402
import switching                                          # noqa: E402
from canal_ge import CanalGE                               # noqa: E402
from estimator import EstimatorLink                       # noqa: E402
from policy import Politica                               # noqa: E402
from switching import Comutator, DWELL_MIN_S              # noqa: E402

# radacini de modul interzise in core/ (verificate pe AST, vezi I4)
INTERZISE = ("rclpy", "socket", "rosidl", "std_msgs", "rmw", "launch")


def ruleaza_selfteste():
    for m in (canal_ge, estimator, policy, switching):
        m._selftest()


def i1_lant_complet():
    """Canal GE pe o celula a grilei -> estimator -> politica -> comutator.
    Se verifica ca decizia coincide cu ce spune tabela derivata din C2 pentru acea celula,
    adica lantul chiar transporta informatia, nu doar ruleaza."""
    pol = Politica.din_fisier()
    for L, B in ((15, 8), (30, 3), (15, 3)):
        c = CanalGE.from_LB_pct(L, B, seed=2024)
        e = EstimatorLink(alpha_L=0.002, alpha_B=0.02)
        for s in c.secvente(200000):
            e.observa(s)
        est = e.estimare()
        asteptat = pol.decide(L, B, 4096)
        com = Comutator(pol, 4096, transport_initial="zenoh")
        t, motiv = com.decide(est, 1000.0)
        assert est.stable, ("estimare instabila pe celula grilei", L, B, est)
        # transportul ales trebuie sa fie cel din tabela (sau sa ramana pe loc daca
        # frana de marja/incertitudine a intervenit -- caz in care motivul o spune)
        if t != asteptat.transport:
            assert ("sub prag" in motiv or "incertitudine" in motiv), (L, B, t, motiv)
        else:
            assert asteptat.transport == t, (L, B, t, asteptat)
    return "I1 lant complet: 3 celule, decizia urmeaza tabela C2"


def i2_anti_flapping():
    """Canal care OSCILEAZA intre doua celule vecine, la fiecare 2 secunde de trafic.
    Un comutator fara franare ar comuta la fiecare oscilatie; cu dwell-time si histerezis
    numarul de comutari trebuie sa fie marginit de durata / dwell."""
    pol = Politica({
        "schema": "c3_policy_table/1", "default_transport": "cyclonedds",
        "default_motiv": "sintetic",
        "celule": [
            {"L": 5.0, "B": 8.0, "payload": 4096, "transport": "zenoh",
             "marja": 60.0, "covered": True, "sursa": "sintetic"},
            {"L": 30.0, "B": 8.0, "payload": 4096, "transport": "cyclonedds",
             "marja": 60.0, "covered": True, "sursa": "sintetic"},
        ]})
    # Doua comutatoare pe ACEEASI urma: unul cu frane, unul fara (dwell 0, praguri 0,
    # fara poarta de incertitudine). Simpla comparatie cu plafonul teoretic ar fi
    # tautologica -- plafonul rezulta aritmetic din dwell. Ce trebuie aratat e ca franele
    # SCHIMBA comportamentul fata de acelasi algoritm fara ele.
    cu_frane = Comutator(pol, 4096)
    fara_frane = Comutator(pol, 4096, dwell_min_s=0.0, prag_plecare=0.0,
                           prag_intoarcere=0.0, k_sigma=0.0)
    e = EstimatorLink(alpha_L=0.05, alpha_B=0.2)     # deliberat NERVOS, ca sa fie greu
    HZ, DURATA = 50.0, 120.0
    n = int(HZ * DURATA)
    canale = {5: CanalGE.from_LB_pct(5, 8, seed=11),
              30: CanalGE.from_LB_pct(30, 8, seed=12)}
    seq = 0
    for i in range(n):
        acum = i / HZ
        L_curent = 5 if int(acum // 2) % 2 == 0 else 30      # comuta la 2 s
        seq += 1
        if canale[L_curent].esantion():
            e.observa(seq)
        if i % 5 == 0:                                        # decide la 10 Hz
            est = e.estimare()
            cu_frane.decide(est, acum)
            fara_frane.decide(est, acum)
    plafon = int(DURATA / DWELL_MIN_S) + 1
    assert cu_frane.n_comutari <= plafon, (cu_frane.n_comutari, plafon)
    # si trebuie sa fi comutat MACAR o data, altfel testul ar trece si daca inghetam totul
    assert cu_frane.n_comutari >= 1, ("comutatorul nu a reactionat deloc la un canal care "
                                      "chiar isi schimba regimul")
    # franele trebuie sa TAIE flapping-ul, nu doar sa existe
    assert fara_frane.n_comutari > 3 * cu_frane.n_comutari, (fara_frane.n_comutari,
                                                             cu_frane.n_comutari)
    return ("I2 anti-flapping: %d comutari cu frane vs %d fara, in %.0f s "
            "(plafon teoretic %d, dwell %.1f s)"
            % (cu_frane.n_comutari, fara_frane.n_comutari, DURATA, plafon, DWELL_MIN_S))


def i3_marja_sub_incertitudine():
    """Celula reala 64 KB / L=15 / B=1: tabela zice zenoh, dar cu marja de 1.7 pp.
    Se foloseste sigma REALA raportata de estimator dupa ce a mestecat canalul."""
    pol = Politica.din_fisier()
    d = pol.decide(15.0, 1.0, 65536)
    assert d.transport == "zenoh" and d.marja < 5.0, d      # premisa testului

    c = CanalGE.from_LB_pct(15, 1, seed=77)
    e = EstimatorLink()
    for s in c.secvente(50000):
        e.observa(s)
    est = e.estimare()
    nevoie = switching.K_SIGMA * est.sigma_L * 100.0
    assert d.marja < nevoie, ("premisa: marja trebuie sa fie sub incertitudine", d.marja,
                              nevoie)

    com = Comutator(pol, 65536)
    t, motiv = com.decide(est, 1000.0)
    assert t == "cyclonedds" and com.n_comutari == 0, (t, motiv)
    return ("I3 marja %.1f pp < incertitudine %.1f pp -> NU se comuta (%s)"
            % (d.marja, nevoie, motiv.split("(")[0].strip()))


def i4_nucleu_pur():
    """Puritatea nu e o promisiune din README, e o proprietate verificabila.
    Verificarea se face pe ARBORELE SINTACTIC, nu pe text: cautarea prin sir de caractere
    da alarme false pe orice docstring care POMENESTE 'os.environ' (chiar cel care promite
    ca nu-l foloseste) si, mai rau, ar rata un import ascuns intr-o functie."""
    fisiere = [f for f in sorted(os.listdir(CORE)) if f.endswith(".py")]
    assert fisiere, "nu am gasit module in core/"
    for f in fisiere:
        arbore = ast.parse(open(os.path.join(CORE, f)).read(), filename=f)
        for nod in ast.walk(arbore):
            if isinstance(nod, ast.Import):
                for a in nod.names:
                    radacina = a.name.split(".")[0]
                    assert radacina not in INTERZISE, ("%s importa %s (linia %d)"
                                                       % (f, a.name, nod.lineno))
            elif isinstance(nod, ast.ImportFrom):
                radacina = (nod.module or "").split(".")[0]
                assert radacina not in INTERZISE, ("%s importa din %s (linia %d)"
                                                   % (f, nod.module, nod.lineno))
            elif isinstance(nod, ast.Attribute):
                # os.environ, chiar si citit o singura data
                if (nod.attr == "environ" and isinstance(nod.value, ast.Name)
                        and nod.value.id == "os"):
                    raise AssertionError("%s atinge os.environ (linia %d)"
                                         % (f, nod.lineno))
    return "I4 nucleu pur: %d module, verificate pe AST" % len(fisiere)


def main(argv):
    print("== selftesturile modulelor ==")
    ruleaza_selfteste()
    print("\n== teste de integrare ==")
    for t in (i1_lant_complet, i2_anti_flapping, i3_marja_sub_incertitudine,
              i4_nucleu_pur):
        print("  " + t())
    print("\nSUITA C3 (nucleu) OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
