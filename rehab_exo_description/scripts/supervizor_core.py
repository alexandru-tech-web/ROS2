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

MARJA_IMPLICITA_RAD = math.radians(5.0)     # IPOTEZA: 5 grade sub opritorul mecanic
BANDA_ARMARE_RAD = math.radians(2.0)        # IPOTEZA: cat de adanc trebuie intrat

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


def praguri_electrice(limite, marja=MARJA_IMPLICITA_RAD):
    """{joint: (lo, hi)} mecanic -> {joint: (lo+marja, hi-marja)} electric.

    Marja se scade din AMBELE capete si se verifica: daca ce ramane nu mai e o
    fereastra utilizabila, e o eroare de configurare, nu ceva de rotunjit tacut.
    O articulatie cu prag electric egal cu cel mecanic nu protejeaza nimic."""
    if marja <= 0.0:
        raise ValueError("marja trebuie sa fie strict pozitiva: pragul electric "
                         "egal cu cel mecanic nu ofera nicio protectie")
    out = {}
    for j, (lo, hi) in limite.items():
        e_lo, e_hi = lo + marja, hi - marja
        if e_hi - e_lo < 2.0 * BANDA_ARMARE_RAD:
            raise ValueError(
                "%s: fereastra electrica %.4f..%.4f e prea ingusta pentru banda de "
                "armare (%.4f); marja %.4f e prea mare pentru limitele %.4f..%.4f"
                % (j, e_lo, e_hi, BANDA_ARMARE_RAD, marja, lo, hi))
        out[j] = (e_lo, e_hi)
    return out


def verdict_comutare(praguri_noi, q, banda=BANDA_ARMARE_RAD):
    """Se poate trece la noul set de limite din pozitia curenta?

    Se REFUZA daca vreo articulatie ar ajunge, prin simpla comutare, in afara noii
    ferestre. Motivul e ca altfel comutarea ar fi ea insasi o incalcare: dispozitivul
    nu s-a miscat, dar dintr-o data e in afara limitelor -- si atunci ori supervizorul
    declanseaza fara vina nimanui, ori (mai rau) nu declanseaza, fiindca articulatia
    nu se armeaza niciodata in noul set.

    Intoarce (permis, motiv). Motivul e text pentru om, cu numere in el."""
    rele = []
    for j, (lo, hi) in sorted(praguri_noi.items()):
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
                if v < lo:
                    self.stare[j] = DECLANSAT
                    evenimente.append(Eveniment(j, v, lo, "min"))
                elif v > hi:
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

    # 1. pragurile sunt STRICT inauntru, pe ambele capete
    for j, (lo, hi) in P.items():
        ok(lo > LIM[j][0] and hi < LIM[j][1], "%s: pragul electric trebuie sa fie strict inauntru" % j)
    ok(abs(P["hip"][0] - math.radians(5.0)) < 1e-9, "marja implicita = 5 grade")
    n[0] += 1

    # 2. marja nula sau negativa e EROARE, nu o configurare permisa
    for rea in (0.0, -0.1):
        try:
            praguri_electrice(LIM, marja=rea)
            ok(False, "marja %s trebuie respinsa" % rea)
        except ValueError:
            n[0] += 1
    # marja absurd de mare: fereastra dispare -> eroare, nu fereastra inversata
    try:
        praguri_electrice({"ankle": (-0.61087, 0.61087)}, marja=0.6)
        ok(False, "marja care inchide fereastra trebuie respinsa")
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

    # 3b. CONTROLUL NEGATIV AL ARMARII: fara armare (adica pornind direct din ARMAT),
    # acelasi boot declanseaza. Daca asta n-ar pica, armarea n-ar demonstra nimic.
    s_fara = Supervizor(P)
    s_fara.stare = {j: ARMAT for j in P}
    ok(len(s_fara.pas(boot)) == 2,
       "fara armare, boot-ul trebuie sa declanseze pe sold si genunchi")

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
    permis, motiv = verdict_comutare(P_SEZUT, {"hip": 0.8, "knee": 1.0, "ankle": 0.0})
    ok(permis, "din 0.8 rad comutarea la sezut e permisa")
    permis, motiv = verdict_comutare(P_SEZUT, {"hip": 0.2, "knee": 1.0, "ankle": 0.0})
    ok(not permis, "din 0.2 rad (sub minimul de sezut) comutarea trebuie REFUZATA")
    ok("0.2" in motiv and "hip" in motiv,
       "refuzul trebuie sa spuna CARE articulatie si LA CE valoare, nu doar 'nu'")
    permis, _ = verdict_comutare(P_SEZUT, {"knee": 1.0, "ankle": 0.0})
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
