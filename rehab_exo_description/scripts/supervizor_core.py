#!/usr/bin/env python3
"""supervizor_core.py -- stratul ELECTRIC de siguranta. NUCLEU PUR.

CELE TREI STRATURI, ca sa nu fie confundate niciodata
  1. MECANIC   opritoarele fizice; in model, <limit> din URDF. Ultimul cuvant.
  2. ELECTRIC  proximitatile [PDF p.7]; acest fisier le EMULEAZA. Praguri de
               POZITIE, strict inauntrul celor mecanice cu o marja.
  3. SOFTWARE  safety_limits.yaml + safety_supervisor.py: cuplu, viteza, heartbeat.
Straturile nu se sincronizeaza intre ele si nu se inlocuiesc: fiecare prinde alta
clasa de esec. Cel electric prinde POZITIA, adica exact cazul in care software-ul a
comandat ceva legal si mecanica ar fi lovita oricum.

DE CE ARMARE CU HISTEREZIS, si de ce nu e o rafinare optionala
La spawn, toate articulatiile pornesc la 0.0 rad. Iar limitele mecanice ipotezate au
sold_min = 0 si genunchi_min = 0. Deci in clipa pornirii sold si genunchi stau EXACT
pe limita lor inferioara, adica DINCOLO de pragul electric, care e cu o marja mai
inauntru. Un supervizor naiv ar declansa la fiecare pornire, inainte ca robotul sa
fi facut ceva -- si un supervizor care striga mereu se dezactiveaza, adica devine
mai rau decat niciunul.

Solutia: fiecare articulatie se ARMEAZA separat, si abia dupa ce a fost vazuta o data
BINE inauntru (cu o banda de histerezis peste prag). Pana atunci e observata, nu
supravegheata. Consecinta acceptata si scrisa aici ca sa nu fie descoperita mai
tarziu: o articulatie care nu intra niciodata in zona sigura nu se armeaza niciodata,
deci nu poate declansa. Asta e corect pentru pornire, dar inseamna ca armarea trebuie
sa se poata CITI din afara -- de aceea starea fiecarei articulatii e publicata.

MARJA e o IPOTEZA, nu o masuratoare. Proximitatile reale nu au fost inca vazute pe
dispozitiv; pana atunci pragurile electrice sunt derivate din cele mecanice printr-o
marja aleasa. Statut: acelasi cu al maselor.

Rulare: python3 scripts/supervizor_core.py --selftest
"""
import math
import sys

# MARJE PER CAPAT, nu simetrice (decizia D2, 22 aug 2026). Vezi DECIZII.md.
# Jos zero, sus 5 grade. Argumentul e de coerenta interna, nu de gust: repausul la
# sold 0 e FAPT documentat (postura de sezut, chiar ancora conventiei B-prim), iar un
# strat electric a carui zona interzisa CONTINE starea de repaus documentata e
# auto-contradictoriu -- pe dispozitivul real proximity-ul de jos e prin necesitate
# la sau sub repaus, altfel robotul s-ar autodeclansa stand.
# Versiunea simetrica de dinainte a produs exact asta: 4 declansari pe capatul min si
# trei exercitii tinute de propriul supervizor. Vezi README, sectiunea de smoke.
MARJA_JOS_RAD = 0.0                         # IPOTEZA: repausul NU e zona interzisa
MARJA_SUS_RAD = math.radians(5.0)           # IPOTEZA: 5 grade sub opritorul de sus
BANDA_ARMARE_RAD = math.radians(2.0)        # IPOTEZA: cat de adanc trebuie intrat

# TOLERANTA NUMERICA, si NU o marja de siguranta. Distinctia e toata substanta:
# marja (D2) e o alegere despre unde incepe zona interzisa; asta e o corectie pentru
# felul in care solverul de fizica aseaza o articulatie care se odihneste PE limita.
# Masurat pe 22 aug: cu marja de jos zero, soldul in repaus raporta -0.0000 rad, adica
# o fractiune sub pragul de 0.0000, si declansa la fiecare pornire.
# 1e-4 rad inseamna 0.0057 grade: de 350 de ori mai mica decat banda de armare, deci
# nu poate fi confundata cu o marja si nici nu ascunde vreo depasire reala. Selftestul
# aserteaza raportul, ca nimeni sa nu o creasca pe furis pana devine una.
TOLERANTA_NUMERICA_RAD = 1e-4

NEARMAT, ARMAT, DECLANSAT = "NEARMAT", "ARMAT", "DECLANSAT"


class Eveniment(object):
    """Ce s-a intamplat, cu numere, ca sa poata fi publicat si citit fara ghicit."""

    __slots__ = ("articulatie", "valoare", "prag", "capat")

    def __init__(self, articulatie, valoare, prag, capat):
        self.articulatie = articulatie
        self.valoare = valoare
        self.prag = prag
        self.capat = capat          # "min" sau "max"

    def __repr__(self):
        return ("DECLANSARE %s: %.4f rad a depasit pragul %s de %.4f rad"
                % (self.articulatie, self.valoare, self.capat, self.prag))


def praguri_electrice(limite, marja_jos=MARJA_JOS_RAD, marja_sus=MARJA_SUS_RAD):
    """{joint: (lo, hi)} mecanic -> {joint: (lo+marja_jos, hi-marja_sus)} electric.

    Marjele sunt SEPARATE pe capete. Una dintre ele are voie sa fie zero -- si chiar
    e, jos -- dar nu amandoua: un strat care nu ingusteaza nimic la niciun capat nu
    protejeaza nimic si mai bine lipseste decat sa dea impresia ca exista.
    Marjele negative raman interzise: ar LARGI fereastra peste cea mecanica."""
    if marja_jos < 0.0 or marja_sus < 0.0:
        raise ValueError("marjele nu pot fi negative: ar largi fereastra electrica "
                         "peste cea mecanica")
    if marja_jos == 0.0 and marja_sus == 0.0:
        raise ValueError("ambele marje zero: stratul electric coincide cu cel "
                         "mecanic si nu protejeaza nimic")
    out = {}
    for j, (lo, hi) in limite.items():
        e_lo, e_hi = lo + marja_jos, hi - marja_sus
        if e_hi - e_lo < 2.0 * BANDA_ARMARE_RAD:
            raise ValueError(
                "%s: fereastra electrica %.4f..%.4f e prea ingusta pentru banda de "
                "armare (%.4f); marjele %.4f/%.4f sunt prea mari pentru limitele "
                "%.4f..%.4f" % (j, e_lo, e_hi, BANDA_ARMARE_RAD, marja_jos,
                                marja_sus, lo, hi))
        out[j] = (e_lo, e_hi)
    return out


def verdict_comutare(limite_noi, q, banda=BANDA_ARMARE_RAD):
    """Se poate trece la noul set de limite din pozitia curenta?

    `limite_noi` sunt limitele MECANICE ale posturii-tinta, nu pragurile electrice.
    Distinctia a fost gasita printr-o proba numerica pe 22 aug si conteaza: intrebarea
    "pot trece la postura asta" e despre LEGALITATEA pozitiei curente in noul set, nu
    despre marja de siguranta. Cu praguri electrice, comutarea era refuzata chiar din
    POSTURA_INITIALA (sold 0, adica exact capatul benzii de sezut), fiindca zero e sub
    pragul electric de 5 grade -- adica serviciul devenea inutilizabil taman din
    pozitia in care dispozitivul chiar sta.
    Dupa comutare, o articulatie aflata intre limita mecanica si pragul electric ramane
    pur si simplu NEARMATA, ceea ce e comportamentul deja proiectat pentru pornire.

    Se REFUZA daca vreo articulatie ar ajunge, prin simpla comutare, in afara noii
    ferestre. Motivul e ca altfel comutarea ar fi ea insasi o incalcare: dispozitivul
    nu s-a miscat, dar dintr-o data e in afara limitelor -- si atunci ori supervizorul
    declanseaza fara vina nimanui, ori (mai rau) nu declanseaza, fiindca articulatia
    nu se armeaza niciodata in noul set.

    Intoarce (permis, motiv). Motivul e text pentru om, cu numere in el."""
    rele = []
    for j, (lo, hi) in sorted(limite_noi.items()):
        v = q.get(j)
        if v is None:
            rele.append("%s: pozitie necunoscuta" % j)
        elif not (lo <= v <= hi):
            rele.append("%s la %.4f, in afara noii ferestre %.4f..%.4f" % (j, v, lo, hi))
    if rele:
        return (False, "comutare REFUZATA: " + "; ".join(rele))
    return (True, "comutare permisa: toate articulatiile sunt in noua fereastra")


class Supervizor(object):
    """Masina de stare per articulatie. Nu stie nimic despre ROS."""

    def __init__(self, praguri, banda=BANDA_ARMARE_RAD):
        self.praguri = dict(praguri)
        self.banda = float(banda)
        self.stare = {j: NEARMAT for j in self.praguri}

    def pas(self, q):
        """Un ciclu. Intoarce lista de evenimente NOI (de obicei goala)."""
        evenimente = []
        for j, (lo, hi) in self.praguri.items():
            v = q.get(j)
            if v is None:
                continue
            st = self.stare[j]
            if st == NEARMAT:
                if lo + self.banda <= v <= hi - self.banda:
                    self.stare[j] = ARMAT
            elif st == ARMAT:
                if v < lo - TOLERANTA_NUMERICA_RAD:
                    self.stare[j] = DECLANSAT
                    evenimente.append(Eveniment(j, v, lo, "min"))
                elif v > hi + TOLERANTA_NUMERICA_RAD:
                    self.stare[j] = DECLANSAT
                    evenimente.append(Eveniment(j, v, hi, "max"))
            # DECLANSAT e LATCH: nu se stinge singur. Se iese doar prin rearmeaza(),
            # adica printr-o decizie explicita, nu fiindca articulatia s-a intors.
        return evenimente

    def declansat(self):
        return any(s == DECLANSAT for s in self.stare.values())

    def rearmeaza(self):
        """Dupa o interventie. Totul redevine NEARMAT: nu se presupune ca ce era
        armat inainte mai e valabil dupa ce cineva a atins dispozitivul."""
        for j in self.stare:
            self.stare[j] = NEARMAT

    def schimba_praguri(self, praguri_noi):
        """Comutarea setului. Starile se reseteaza: un ARMAT castigat in vechea
        fereastra nu are niciun inteles in cea noua."""
        self.praguri = dict(praguri_noi)
        self.stare = {j: NEARMAT for j in self.praguri}


def _selftest():
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    LIM = {"hip": (0.0, 1.5708), "knee": (0.0, 2.44346), "ankle": (-0.61087, 0.61087)}
    P = praguri_electrice(LIM)

    # 1. MARJE PER CAPAT (D2). Jos pragul COINCIDE cu limita mecanica -- deliberat,
    # fiindca repausul e acolo -- iar sus e strict inauntru.
    for j, (lo, hi) in P.items():
        ok(abs(lo - LIM[j][0]) < 1e-12,
           "%s: jos pragul trebuie sa COINCIDA cu limita mecanica (marja zero)" % j)
        ok(hi < LIM[j][1], "%s: sus pragul trebuie sa fie strict inauntru" % j)
    ok(abs(LIM["hip"][1] - P["hip"][1] - math.radians(5.0)) < 1e-9,
       "marja de sus implicita = 5 grade")
    n[0] += 1

    # 1b. AFIRMATIA CENTRALA A LUI D2: repausul (capatul de jos) NU e in zona
    # interzisa. Cu marje simetrice era, si de acolo veneau declansarile false.
    s_rep = Supervizor(P)
    repaus = {j: LIM[j][0] for j in LIM}
    for _ in range(50):
        ok(not s_rep.pas(repaus),
           "repausul, adica exact limita mecanica de jos, NU are voie sa declanseze")
    # ... si nici dupa ce articulatia s-a armat si se INTOARCE la repaus, care e
    # scenariul care a picat la smoke-ul din 22 aug.
    s_rep.pas({j: (LIM[j][0] + LIM[j][1]) / 2.0 for j in LIM})
    ok(all(v == ARMAT for v in s_rep.stare.values()), "premisa: toate s-au armat")
    ok(not s_rep.pas(repaus),
       "REVENIREA la repaus dupa armare nu are voie sa declanseze; cu marje "
       "simetrice declansa, si supervizorul tinea articulatia tot restul sesiunii")
    n[0] += 2

    # 2. marjele NEGATIVE raman interzise: ar largi fereastra peste cea mecanica.
    for jos, sus in ((-0.1, 0.087), (0.0, -0.1)):
        try:
            praguri_electrice(LIM, jos, sus)
            ok(False, "marja negativa (%s, %s) trebuie respinsa" % (jos, sus))
        except ValueError as e:
            ok("negative" in str(e), "mesajul trebuie sa spuna de ce")
    # AMBELE zero inseamna un strat care nu face nimic: respins.
    try:
        praguri_electrice(LIM, 0.0, 0.0)
        ok(False, "ambele marje zero trebuie respinse")
    except ValueError as e:
        ok("nu protejeaza nimic" in str(e), "mesajul trebuie sa spuna ce e degeaba")
    # ... dar UNA zero e perfect valida, si asta e chiar configuratia aleasa.
    ok(praguri_electrice(LIM, 0.0, math.radians(5.0)) is not None,
       "o singura marja zero trebuie ACCEPTATA; e configuratia din D2")
    # marja absurd de mare: fereastra dispare -> eroare, nu fereastra inversata
    try:
        praguri_electrice({"ankle": (-0.61087, 0.61087)}, 0.6, 0.6)
        ok(False, "marjele care inchid fereastra trebuie respinse")
    except ValueError as e:
        ok("prea ingusta" in str(e), "mesajul trebuie sa spuna CE e in neregula")

    # 3. SCENARIUL 'BOOT PE MARGINE', motivul pentru care exista armarea.
    # Toate articulatiile la 0.0, exact limita inferioara mecanica a soldului si a
    # genunchiului. NIMIC nu are voie sa declanseze.
    s = Supervizor(P)
    boot = {"hip": 0.0, "knee": 0.0, "ankle": 0.0}
    for _ in range(50):
        ok(not s.pas(boot), "boot pe margine NU are voie sa declanseze")
    ok(s.stare["hip"] == NEARMAT, "soldul ramane NEARMAT la boot pe margine")
    ok(s.stare["ankle"] == ARMAT, "glezna, care porneste bine inauntru, SE armeaza")

    # 3b. CONTROLUL NEGATIV AL ARMARII, MUTAT PE CAPATUL DE SUS dupa D2.
    # Cu marja de jos zero, pornirea la limita inferioara nu mai e in zona interzisa,
    # deci nu mai poate servi drept control: nici cu armare, nici fara. Capatul care
    # ramane periculos e cel de SUS, unde marja e 5 grade. O pornire acolo (de pilda
    # dupa o interventie care a lasat articulatia la maxim mecanic) ar declansa daca
    # supervizorul ar fi armat din start.
    sus = {j: LIM[j][1] for j in LIM}
    s_sus = Supervizor(P)
    for _ in range(30):
        ok(not s_sus.pas(sus), "pornirea la limita de SUS nu declanseaza (nearmat)")
    ok(all(v == NEARMAT for v in s_sus.stare.values()),
       "la limita de sus articulatiile raman NEARMATE")
    s_fara = Supervizor(P)
    s_fara.stare = {j: ARMAT for j in P}
    ok(len(s_fara.pas(sus)) == len(LIM),
       "fara armare, pornirea la limita de SUS trebuie sa declanseze pe toate")

    # 3c. TOLERANTA NUMERICA: o articulatie care se odihneste PE limita si e
    # raportata cu o fractiune dedesubt nu declanseaza. Cazul real din 22 aug.
    s_tol = Supervizor(P)
    s_tol.pas({j: (LIM[j][0] + LIM[j][1]) / 2.0 for j in LIM})       # se armeaza
    ok(not s_tol.pas({j: LIM[j][0] - 1e-7 for j in LIM}),
       "zgomotul solverului sub limita (1e-7 rad) NU are voie sa declanseze")
    # ... dar o depasire REALA, chiar mica, tot declanseaza
    ok(len(s_tol.pas({j: LIM[j][0] - 0.01 for j in LIM})) == len(LIM),
       "o depasire reala de 0.01 rad trebuie sa declanseze")
    # ... si toleranta e de un alt ordin de marime fata de banda de armare, ca sa nu
    # poata fi confundata cu o marja de siguranta
    ok(TOLERANTA_NUMERICA_RAD < BANDA_ARMARE_RAD / 100.0,
       "toleranta numerica (%.1e) trebuie sa fie cu ordine de marime sub banda de "
       "armare (%.4f); altfel a devenit o marja pe furis"
       % (TOLERANTA_NUMERICA_RAD, BANDA_ARMARE_RAD))
    n[0] += 1

    # 4. ciclul complet: intra inauntru -> se armeaza -> depaseste -> declanseaza
    s = Supervizor(P)
    s.pas({"hip": 0.6, "knee": 1.0, "ankle": 0.0})
    ok(all(v == ARMAT for v in s.stare.values()), "toate se armeaza in zona sigura")
    ev = s.pas({"hip": 1.60, "knee": 1.0, "ankle": 0.0})
    ok(len(ev) == 1 and ev[0].articulatie == "hip", "declansare pe sold")
    ok(ev[0].capat == "max" and abs(ev[0].prag - P["hip"][1]) < 1e-12,
       "evenimentul poarta pragul si capatul corecte")
    ok(abs(ev[0].valoare - 1.60) < 1e-12, "evenimentul poarta valoarea masurata")
    ok(s.declansat(), "supervizorul raporteaza starea declansata")

    # 4b. LATCH: intoarcerea in zona sigura NU stinge declansarea de la sine
    s.pas({"hip": 0.6, "knee": 1.0, "ankle": 0.0})
    ok(s.stare["hip"] == DECLANSAT, "declansarea e LATCH, nu se stinge singura")
    ok(not s.pas({"hip": 1.60}), "o articulatie deja declansata nu re-emite evenimente")
    s.rearmeaza()
    ok(s.stare["hip"] == NEARMAT, "rearmarea readuce in NEARMAT, nu in ARMAT")

    # 5. HISTEREZISUL e real: exact PE prag nu armeaza, cu banda inauntru armeaza.
    s = Supervizor(P)
    s.pas({"hip": P["hip"][0]})
    ok(s.stare["hip"] == NEARMAT, "exact pe prag nu se armeaza (asta e histerezisul)")
    s.pas({"hip": P["hip"][0] + BANDA_ARMARE_RAD})
    ok(s.stare["hip"] == ARMAT, "la exact banda inauntru se armeaza")

    # 6. COMUTAREA DE POSTURA. Sezut ridica minimul soldului la 25 grade.
    LIM_SEZUT = dict(LIM); LIM_SEZUT["hip"] = (math.radians(25.0), 1.5708)
    P_SEZUT = praguri_electrice(LIM_SEZUT)
    ok(P_SEZUT["hip"][0] > P["hip"][0], "sezut trebuie sa ridice pragul inferior")
    permis, motiv = verdict_comutare(LIM_SEZUT, {"hip": 0.8, "knee": 1.0, "ankle": 0.0})
    ok(permis, "din 0.8 rad comutarea la sezut e permisa")
    permis, motiv = verdict_comutare(LIM_SEZUT, {"hip": 0.2, "knee": 1.0, "ankle": 0.0})
    ok(not permis, "din 0.2 rad (sub minimul mecanic de sezut) comutarea trebuie REFUZATA")

    # Verificarea se face pe limitele MECANICE, nu pe praguri: o pozitie aflata intre
    # limita mecanica si pragul electric e LEGALA, doar nearmata. Daca s-ar verifica
    # pe praguri, comutarea ar fi refuzata chiar din pozitia de repaus.
    # Dupa D2 distinctia se vede la capatul de SUS: acolo marja e 5 grade, deci o
    # pozitie intre pragul electric si limita mecanica e LEGALA dar nearmata. Jos cele
    # doua coincid, si tocmai de aceea repausul nu mai e o problema.
    chiar_sub_max = {"hip": LIM_SEZUT["hip"][1] - math.radians(1.0),
                     "knee": 1.0, "ankle": 0.0}
    ok(verdict_comutare(LIM_SEZUT, chiar_sub_max)[0],
       "la un grad sub limita mecanica de sus comutarea trebuie PERMISA")
    ok(not verdict_comutare(P_SEZUT, chiar_sub_max)[0],
       "control: pe PRAGURI aceeasi pozitie ar fi refuzata; de aceea nu se folosesc")
    ok(verdict_comutare(LIM_SEZUT, {"hip": LIM_SEZUT["hip"][0], "knee": 1.0,
                                    "ankle": 0.0})[0],
       "exact pe limita de jos, adica in repaus, comutarea trebuie PERMISA")
    permis, motiv = verdict_comutare(LIM_SEZUT, {"hip": 0.2, "knee": 1.0, "ankle": 0.0})
    ok("0.2" in motiv and "hip" in motiv,
       "refuzul trebuie sa spuna CARE articulatie si LA CE valoare, nu doar 'nu'")
    permis, _ = verdict_comutare(LIM_SEZUT, {"knee": 1.0, "ankle": 0.0})
    ok(not permis, "pozitie necunoscuta = refuz, nu presupunere optimista")

    # 6b. CONTROLUL NEGATIV AL COMUTARII: comutarea fara verificare lasa o
    # articulatie in afara ferestrei, si atunci ea nu se mai armeaza NICIODATA --
    # adica supervizorul tace exact acolo unde ar trebui sa vada.
    s = Supervizor(P)
    s.pas({"hip": 0.2, "knee": 1.0, "ankle": 0.0})
    s.schimba_praguri(P_SEZUT)
    for _ in range(50):
        s.pas({"hip": 0.2, "knee": 1.0, "ankle": 0.0})
    ok(s.stare["hip"] == NEARMAT,
       "dovada ca refuzul e necesar: comutata fortat, articulatia ramane oarba")
    ok(not s.declansat(), "si nu declanseaza, desi e in afara noii ferestre")

    # 7. comutarea reseteaza armarea: ce era castigat in vechea fereastra nu se muta
    s = Supervizor(P)
    s.pas({"hip": 0.6, "knee": 1.0, "ankle": 0.0})
    ok(s.stare["knee"] == ARMAT, "premisa")
    s.schimba_praguri(P_SEZUT)
    ok(all(v == NEARMAT for v in s.stare.values()), "comutarea reseteaza starile")

    print("SELFTEST supervizor_core OK (%d verificari: boot pe margine, histerezis, "
          "latch, comutare cu refuz, toate cu control negativ)." % n[0])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
