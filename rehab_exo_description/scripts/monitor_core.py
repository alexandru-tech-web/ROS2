#!/usr/bin/env python3
"""monitor_core.py -- formatarea si VERDICTELE tabloului de monitorizare. NUCLEU PUR.

De ce un nucleu separat pentru un afisaj: fiindca afisajul nu e doar afisaj. Trei
lucruri de aici sunt afirmatii care pot fi GRESITE, si atunci demonstratia ar minti
linistit in fata coordonatorului:

  1. NaN inseamna NEMASURAT, si trebuie SA SE VADA ca NaN. Un canal nemasurat afisat
     ca 0.000 e cea mai proasta varianta posibila: arata ca o masuratoare valida de
     valoare zero. Componentele senzorului 6D pe care documentul nu le da (Fy, Mx,
     Mz) sunt NaN prin constructie in senzori_core, si aici raman NaN pe ecran.
  2. Eroarea de urmarire e diferenta dintre CE S-A CERUT si CE S-A MASURAT. Daca
     sursele se incurca intre ele, tabloul arata verde pe o simulare care nu misca.
  3. Coerenta: unghiul raportat de senzorul de glezna trebuie sa fie acelasi lucru
     cu unghiul articulatiei din /joint_states. Daca cele doua se despart, ori
     senzorul sintetic s-a rupt, ori citim alt picior. E un control incrucisat
     ieftin care prinde exact clasa de greseli pe care ochiul nu o vede.

Rulare: python3 scripts/monitor_core.py --selftest
"""
import math
import sys

# Ce se afiseaza si in ce ordine. Numele scurte sunt pentru latimea terminalului.
ARTICULATII = ("hip", "knee", "ankle")
PARTI = ("left", "right")
SCURT = {"hip": "sold", "knee": "genunchi", "ankle": "glezna"}

# Sub aceste praguri tabloul spune OK. Nu sunt cerinte clinice, sunt praguri de
# DEMONSTRATIE, alese dupa ce s-a masurat urmarirea reala (0.002 .. 0.042 rad).
PRAG_URMARIRE_RAD = 0.10

# Pragul de coerenta NU e o cifra rotunda aleasa de mine: e suma marimilor pe care
# modelul senzorului le DECLARA ca abateri legitime. Prima versiune a acestui modul
# folosea 1e-3 si a strigat 'ATENTIE' pe o simulare perfect sanatoasa, fiindca
# ignora offsetul de montaj de +-0.012 rad pe care senzorul il aplica intentionat.
# Un tablou care da alarme false e mai rau decat niciun tablou.
#   2 * zgomot   -- semnalul si referinta pot fi in extremele opuse ale sinusoidei
#   viteza*skew  -- senzorul si /joint_states nu sunt esantionate in aceeasi clipa
SKEW_MAX_S = 0.05
ZGOMOT_UNGHI_RAD = 0.0015          # valoarea canonica vine din senzori_core

# Termenul de viteza din pragul de coerenta se PLAFONEAZA. Motivul e o capcana in
# care am si cazut: glezna oscila in saturatie de viteza, iar pragul, largit chiar
# de viteza aia, ajunsese 0.155 rad -- de cincizeci de ori zgomotul. Verificarea
# trecea, dar din motivul gresit: devenise vida exact cand era mai multa nevoie de
# ea. Un prag care creste nelimitat cu marimea pe care ar trebui s-o supravegheze
# nu mai supravegheaza nimic.
VITEZA_MAX_PRAG_RAD_S = 0.5

# Peste ce fractie din limita nominala o articulatie se considera SATURATA.
PRAG_SATURATIE = 0.98


def fmt(v, latime=8, zecimale=3):
    """Un numar, sau NaN scris ca NaN. Niciodata NaN transformat in 0."""
    if v is None:
        return "-".rjust(latime)
    if isinstance(v, float) and math.isnan(v):
        return "NaN".rjust(latime)
    return ("%+.*f" % (zecimale, v)).rjust(latime)


def eroare_urmarire(cerut, masurat):
    """Eroarea pe articulatie. None acolo unde lipseste oricare din cele doua --
    NU zero, fiindca 'nu stiu' si 'exact la tinta' sunt lucruri diferite."""
    out = {}
    for j in set(cerut) | set(masurat):
        c, m = cerut.get(j), masurat.get(j)
        out[j] = None if (c is None or m is None) else m - c
    return out


def verdict_urmarire(erori, prag=PRAG_URMARIRE_RAD):
    """(ok, cea_mai_mare_eroare, articulatia). Articulatiile fara date NU trec
    automat: daca nu stim nimic, verdictul e None, nu OK."""
    perechi = [(abs(e), j) for j, e in erori.items() if e is not None]
    if not perechi:
        return (None, None, None)
    e_max, j_max = max(perechi)
    return (e_max <= prag, e_max, j_max)


def prag_coerenta(viteza, zgomot=ZGOMOT_UNGHI_RAD, skew=SKEW_MAX_S):
    """Cat are voie sa difere senzorul de articulatie, la viteza data. Termenul de
    viteza e plafonat -- vezi VITEZA_MAX_PRAG_RAD_S."""
    v = min(abs(viteza or 0.0), VITEZA_MAX_PRAG_RAD_S)
    return 2.0 * zgomot + v * skew


def articulatia(nume_joint):
    """'left_ankle_joint' -> 'ankle'. None daca numele nu are forma asteptata."""
    p = nume_joint.split("_")
    return p[1] if len(p) >= 3 else None


def verdict_saturatie(viteze, limite, prag=PRAG_SATURATIE):
    """Ce articulatii isi ating limita nominala de viteza. O articulatie saturata
    poate parea NEMISCATA in pozitie si sa bata totusi intre extreme la viteza
    maxima; in pozitie nu se vede, in viteza da. Pentru un dispozitiv care se pune
    pe piciorul unui om, asta trebuie sa fie pe ecran, nu ascuns.
    `limite` e {articulatie: rad/s} si vine din spec_derivate, nu de aici."""
    sat = []
    for j, v in sorted(viteze.items()):
        lim = limite.get(articulatia(j) or "")
        if lim and v is not None and abs(v) >= prag * lim:
            sat.append((j, v, lim))
    return (not sat, sat)


def verdict_coerenta(unghi_senzor, q_masurat, offset, viteze=None,
                     zgomot=ZGOMOT_UNGHI_RAD, skew=SKEW_MAX_S):
    """Senzorul de glezna vs articulatia de glezna, pe fiecare picior, DUPA scaderea
    offsetului de montaj declarat. Ce ramane e abaterea neexplicata: daca ea creste,
    ori senzorul sintetic s-a rupt, ori se citeste alt picior.

    `offset` e {parte: rad} si vine din senzori_core.OFFSET_MONTAJ_GLEZNA -- NU se
    scrie a doua oara aici. `viteze` e {nume_joint: rad/s} si largeste pragul cat
    trebuie ca miscarea sa nu produca alarme false.
    Intoarce (ok, detalii) unde detalii e {parte: abatere neexplicata sau None}."""
    viteze = viteze or {}
    det, praguri = {}, {}
    for p in PARTI:
        s_ = unghi_senzor.get(p)
        j = "%s_ankle_joint" % p
        q = q_masurat.get(j)
        if s_ is None or q is None:
            det[p] = None
            continue
        det[p] = abs((s_ - offset.get(p, 0.0)) - q)
        praguri[p] = prag_coerenta(viteze.get(j), zgomot, skew)
    valori = [(det[p], praguri[p]) for p in PARTI if det[p] is not None]
    if not valori:
        return (None, det)
    return (all(d <= pr for d, pr in valori), det)


def verdict_nemasurate(w6, nemasurate):
    """Componentele nemasurate TREBUIE sa fie NaN, cele numite TREBUIE sa nu fie.
    Afirmatia inversa e la fel de importanta: un canal numit care devine NaN
    inseamna senzor rupt, si tabloul trebuie s-o spuna, nu s-o ascunda."""
    rele = []
    for (camp, ax), v in w6.items():
        nan = isinstance(v, float) and math.isnan(v)
        trebuie_nan = (camp, ax) in nemasurate
        if nan != trebuie_nan:
            rele.append(("%s.%s" % (camp, ax),
                         "NaN dar e canal masurat" if nan else "numar dar e canal nemasurat"))
    return (not rele, rele)


def _bara(e, prag, latime=12):
    """Bara de eroare, ca sa se vada dintr-o privire de la doi metri."""
    if e is None:
        return " " * latime
    n = min(latime, int(round(latime * min(1.0, abs(e) / prag))))
    return ("#" * n).ljust(latime)


def tabel(t, cerut, masurat, cupluri, unghi_senzor, w6, nemasurate, eticheta,
          offset=None, viteze=None, limite=None):
    """Tabloul complet, ca lista de linii. Pur: nimic nu se citeste din lume aici."""
    offset = offset or {}
    er = eroare_urmarire(cerut, masurat)
    ok_u, e_max, j_max = verdict_urmarire(er)
    ok_c, det_c = verdict_coerenta(unghi_senzor, masurat, offset, viteze)
    ok_n, rele = verdict_nemasurate(w6, nemasurate)
    ok_s, sat = verdict_saturatie(viteze or {}, limite or {})

    L = []
    L.append("t = %6.1f s   %s" % (t, eticheta))
    L.append("")
    L.append("  articulatie      cerut   masurat    eroare  " + "urmarire".ljust(12) + "  cuplu[Nm]")
    for p in PARTI:
        for a in ARTICULATII:
            j = "%s_%s_joint" % (p, a)
            L.append("  %-14s %s %s %s  %s  %s"
                     % ("%s %s" % (p, SCURT[a]), fmt(cerut.get(j)), fmt(masurat.get(j)),
                        fmt(er.get(j)), _bara(er.get(j), PRAG_URMARIRE_RAD),
                        fmt(cupluri.get((p, a)))))
    L.append("")
    L.append("  senzor 6D (o talpa):  " + "  ".join(
        "%s.%s=%s" % (c, a, fmt(v, latime=7)) for (c, a), v in sorted(w6.items())))
    L.append("  unghi glezna senzor:  " + "  ".join(
        "%s=%s" % (p, fmt(unghi_senzor.get(p))) for p in PARTI))
    L.append("")
    L.append("  URMARIRE  : %s (max %s rad la %s, prag %.3f)"
             % (_eticheta(ok_u), fmt(e_max, latime=6), j_max or "-", PRAG_URMARIRE_RAD))
    L.append("  COERENTA  : %s (abatere NEEXPLICATA, dupa scaderea offsetului de "
             "montaj: %s)"
             % (_eticheta(ok_c), ", ".join("%s=%s" % (p, fmt(det_c[p], latime=7))
                                           for p in PARTI)))
    L.append("  CANALE    : %s%s"
             % (_eticheta(ok_n),
                "" if ok_n else " -- " + "; ".join("%s: %s" % r for r in rele)))
    L.append("  VITEZA    : %s%s"
             % (_eticheta(ok_s),
                " (nicio articulatie in saturatie)" if ok_s else
                " -- SATURATE: " + ", ".join("%s %+.3f din %.3f rad/s" % r for r in sat)))
    return L


def _eticheta(ok):
    return "necunoscut" if ok is None else ("OK  " if ok else "ATENTIE")


def _selftest():
    n = 0
    # 1. NaN se vede ca NaN, si niciodata ca 0. Afirmatia centrala a modulului.
    assert fmt(float("nan")).strip() == "NaN"
    assert fmt(0.0).strip() == "+0.000"
    assert fmt(None).strip() == "-"
    assert "0.000" not in fmt(float("nan"))
    n += 4

    # 2. eroarea: lipsa unei surse NU devine zero
    er = eroare_urmarire({"a": 1.0, "b": 2.0}, {"a": 1.25})
    assert abs(er["a"] - 0.25) < 1e-12, er
    assert er["b"] is None, er
    n += 2

    # 3. verdictul de urmarire, cu control negativ pe ambele sensuri
    assert verdict_urmarire({"a": 0.01, "b": -0.02})[0] is True
    assert verdict_urmarire({"a": 0.5})[0] is False
    assert verdict_urmarire({"a": None})[0] is None, "fara date verdictul NU e OK"
    _, e, j = verdict_urmarire({"a": 0.01, "b": -0.3})
    assert j == "b" and abs(e - 0.3) < 1e-12, (e, j)
    n += 4

    # 4. exact la prag = trece; un pic peste = nu. Granita e afirmata, nu presupusa.
    assert verdict_urmarire({"a": PRAG_URMARIRE_RAD})[0] is True
    assert verdict_urmarire({"a": PRAG_URMARIRE_RAD * 1.0001})[0] is False
    n += 2

    # 5. coerenta senzor-articulatie. OFF e offsetul de montaj declarat; senzorul
    # citeste articulatia PLUS offsetul, deci scaderea lui trebuie sa dea zero.
    OFF = {"left": +0.012, "right": -0.012}
    senzor = {"left": 0.10 + OFF["left"], "right": -0.05 + OFF["right"]}
    art = {"left_ankle_joint": 0.10, "right_ankle_joint": -0.05}
    ok, det = verdict_coerenta(senzor, art, OFF)
    assert ok is True, det
    assert det["left"] < 1e-12 and det["right"] < 1e-12, det
    n += 3

    # 5b. REGRESIA CARE A DAT ALARMA FALSA: fara compensarea offsetului, exact
    # aceleasi date sanatoase pica. Testul asta exista ca sa nu se mai 'simplifice'
    # compensarea inapoi afara.
    ok_fara, _ = verdict_coerenta(senzor, art, {})
    assert ok_fara is False, ("fara offset ar trebui sa pice; daca trece, "
                             "pragul e prea larg si verificarea nu mai vede nimic")
    n += 1

    # 5c. o desincronizare REALA se prinde, si la viteza zero, si in miscare
    rupt = {"left": 0.30 + OFF["left"], "right": -0.05 + OFF["right"]}
    assert verdict_coerenta(rupt, art, OFF)[0] is False
    assert verdict_coerenta(rupt, art, OFF, {"left_ankle_joint": 0.5})[0] is False, \
        "viteza nu are voie sa largeasca pragul destul cat sa ascunda 0.2 rad"
    n += 2

    # 5d. pragul creste cu viteza, dar pleaca de la zgomot si SE PLAFONEAZA
    assert prag_coerenta(0.0) == 2.0 * ZGOMOT_UNGHI_RAD
    assert prag_coerenta(0.1) > prag_coerenta(0.0)
    assert prag_coerenta(None) == prag_coerenta(0.0)
    # regresia care conteaza: o viteza absurda NU are voie sa umfle pragul
    assert prag_coerenta(50.0) == prag_coerenta(VITEZA_MAX_PRAG_RAD_S), \
        "prag neplafonat: o articulatie in saturatie ar face verificarea vida"
    assert prag_coerenta(50.0) < 0.03
    n += 5

    # 5e. SATURATIA. Cifrele sunt cele reale ale gleznei, masurate pe 21 aug 2026:
    # pozitia parea nemiscata (+-0.02 rad) iar viteza statea fixata pe limita.
    LIM = {"hip": 1.5786, "knee": 1.9732, "ankle": 3.0369}
    assert articulatia("left_ankle_joint") == "ankle"
    assert articulatia("seat_lift_joint") == "lift"
    assert articulatia("ciudat") is None
    ok_s, sat = verdict_saturatie({"left_ankle_joint": -3.0369,
                                   "left_hip_joint": 0.02}, LIM)
    assert ok_s is False and len(sat) == 1 and sat[0][0] == "left_ankle_joint", sat
    assert verdict_saturatie({"left_ankle_joint": 0.5}, LIM)[0] is True
    # un nume necunoscut NU declanseaza si NU crapa
    assert verdict_saturatie({"nimic": 99.0}, LIM)[0] is True
    # limita se ia pe ARTICULATIE, nu global: 2.0 rad/s satureaza soldul, nu glezna
    assert verdict_saturatie({"left_hip_joint": 2.0}, LIM)[0] is False
    assert verdict_saturatie({"left_ankle_joint": 2.0}, LIM)[0] is True
    n += 8

    assert verdict_coerenta({}, {}, OFF)[0] is None
    n += 1

    # 6. canalele: si afirmatia, si INVERSA ei
    nem = [("force", "y"), ("torque", "x"), ("torque", "z")]
    bun = {("force", "x"): 1.0, ("force", "z"): 2.0, ("torque", "y"): 3.0,
           ("force", "y"): float("nan"), ("torque", "x"): float("nan"),
           ("torque", "z"): float("nan")}
    assert verdict_nemasurate(bun, nem)[0] is True
    rupt = dict(bun); rupt[("force", "x")] = float("nan")
    ok3, rele = verdict_nemasurate(rupt, nem)
    assert ok3 is False and rele[0][0] == "force.x", rele
    umflat = dict(bun); umflat[("force", "y")] = 0.0
    assert verdict_nemasurate(umflat, nem)[0] is False, "un canal nemasurat cu numar trebuie prins"
    n += 3

    # 7. tabelul se construieste si NU pierde NaN-urile pe drum
    linii = tabel(1.0, {"left_hip_joint": 0.1}, {"left_hip_joint": 0.11},
                  {("left", "hip"): 2.0}, {"left": 0.0, "right": 0.0}, bun, nem,
                  "sintetic", OFF, {"left_ankle_joint": -3.0369},
                  {"hip": 1.5786, "knee": 1.9732, "ankle": 3.0369})
    text = "\n".join(linii)
    assert "NaN" in text, "NaN a disparut din tabel"
    assert text.count("NaN") >= 3, text
    assert "URMARIRE" in text and "COERENTA" in text and "CANALE" in text
    assert "VITEZA" in text and "SATURATE" in text, "saturatia trebuie sa se vada in tabel"
    n += 4

    # 8. bara e monotona si se satureaza, nu creste la infinit
    assert len(_bara(0.0, 0.1).strip()) == 0
    assert len(_bara(1.0, 0.1).strip()) == len(_bara(50.0, 0.1).strip()) == 12
    assert len(_bara(0.05, 0.1).strip()) < len(_bara(0.09, 0.1).strip())
    n += 3

    print("SELFTEST monitor_core OK (%d verificari: NaN pastrat, verdicte cu "
          "control negativ, granite afirmate)." % n)


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
