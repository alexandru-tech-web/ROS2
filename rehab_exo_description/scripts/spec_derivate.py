#!/usr/bin/env python3
"""spec_derivate.py -- NUCLEU PUR: limitele de efort si viteza, derivate din documentatie.

Fiecare cifra de aici are proveniente: ori e citita din documentul tehnic si poarta
[PDF p.X], ori e calculata si poarta formula plus sursele ei. Nicio cifra rotunda fara
eticheta -- exact ce a lipsit modelului mostenit, unde limitele erau 120/300/500 Nm si
2.0/0.03/0.05 rad/s, fara nicio sursa.

Se ruleaza singur: python3 scripts/spec_derivate.py            (tabelul)
                   python3 scripts/spec_derivate.py --selftest (verificarile)
"""
import sys

# ---------------------------------------------------------------- FAPTE din document
# Rapoartele TOTALE de transmisie [PDF Tabel 3.1, p.10-11]
RAPORT = {"sold": 2700.0 / 11.0, "genunchi": 2160.0 / 11.0, "glezna": 100.0}

# Reductoare armonice, cuplu nominal la raport 100 [PDF Tabel 6.1 p.23; foi p.25-28]
REDUCTOR = {"sold": ("SHG-40-100-2UH", 345.0), "genunchi": ("SHG-32-100-2UH", 178.0),
            "glezna": ("SHG-20-100-2UH", 52.0)}

# Motoare [PDF Tabel 3.2 p.11; foi p.29-33 si p.34-42]
MOTOR = {
    "sold":     {"nume": "SMP8024B", "foaie": "SMP8048", "cuplu_cont_nm": 0.9,
                 "rpm_nominal": 3700.0},
    "genunchi": {"nume": "SMP8024B", "foaie": "SMP8048", "cuplu_cont_nm": 0.9,
                 "rpm_nominal": 3700.0},
    "glezna":   {"nume": "TBM(S)-6025", "foaie": "TBM(S)-6025", "cuplu_cont_nm": 0.706,
                 "rpm_nominal": None},
}

# ------------------------------------------------------------------ IPOTEZE declarate
# Randamentul lantului (curea + reductor armonic). NU e in document.
ETA_IMPLICIT = 0.80
# Turatia TBM(S)-6025. NU e in SPEC_LLR_twin_din_PDF.md, care da pentru TBM doar cuplu
# continuu/varf, tensiuni, poli, masa si inertie.
#
# ISTORIC, si merita scris: prima versiune a acestui fisier folosea 1500 rpm, o cifra
# pe care am ALES-O, nu am citit-o de undeva. Era exact incalcarea regulii anti-fabricare
# pe care o aplic peste tot in rest, si a scapat pentru ca era etichetata "ipoteza" --
# eticheta corecta, dar proveniente inexistenta. O ipoteza tot are nevoie de un DE UNDE.
#
# Valorile de mai jos vin din foaia de catalog TBM-6025, pe cele doua bobinaje,
# COMUNICATE de autor pe 21 aug 2026; NU sunt in extractul SPEC pe care il am.
# DE CONFIRMAT LA SURSA inainte de a fi folosite intr-o afirmatie publicata.
RPM_BOBINAJ = {
    "A": 2900.0,   # bobinaj A, 48 V [foaie TBM-6025; comunicat 21 aug, NEconfirmat aici]
    "B": 2450.0,   # bobinaj B, 24 V [idem]
}
BOBINAJ_IMPLICIT = "A"     # driverul e ADP-090-40 (90 V) [PDF Tabel 3.2, p.11]
RPM_GLEZNA_IMPLICIT = RPM_BOBINAJ[BOBINAJ_IMPLICIT]


def viteza_nominala_rad_s(art, rpm=None):
    """rad/s la iesirea articulatiei = rpm_motor / raport, convertit din rot/min.
    Formula: (rpm / 60) * 2*pi / raport_total."""
    import math
    r = rpm if rpm is not None else (MOTOR[art]["rpm_nominal"] or RPM_GLEZNA_IMPLICIT)
    return (r / 60.0) * 2.0 * math.pi / RAPORT[art]


def efort_continuu_nm(art, eta=ETA_IMPLICIT):
    """min(cuplu_motor x raport x eta, cuplu_nominal_reductor).
    Cine limiteaza se raporteaza explicit: e o informatie de proiectare, nu un detaliu."""
    prin_motor = MOTOR[art]["cuplu_cont_nm"] * RAPORT[art] * eta
    prin_reductor = REDUCTOR[art][1]
    if prin_motor <= prin_reductor:
        return prin_motor, "motorul"
    return prin_reductor, "reductorul"


def tabel(eta=ETA_IMPLICIT, rpm_glezna=None, bobinaj=BOBINAJ_IMPLICIT):
    if rpm_glezna is None:
        rpm_glezna = RPM_BOBINAJ[bobinaj]
    out = []
    for art in ("sold", "genunchi", "glezna"):
        rpm = rpm_glezna if art == "glezna" else MOTOR[art]["rpm_nominal"]
        v = viteza_nominala_rad_s(art, rpm)
        e, cine = efort_continuu_nm(art, eta)
        out.append({"articulatie": art, "raport": RAPORT[art], "rpm": rpm,
                    "viteza_rad_s": v, "efort_nm": e, "limitat_de": cine,
                    "reductor": REDUCTOR[art][0], "motor": MOTOR[art]["nume"]})
    return out


def _selftest():
    import math
    v = 0

    def ok(c, m):
        assert c, m
        return 1

    # 1. rapoartele sunt EXACT cele documentate, ca fractii, nu ca zecimale rotunjite
    v += ok(abs(RAPORT["sold"] - 245.4545454545) < 1e-9, "2700:11")
    v += ok(abs(RAPORT["genunchi"] - 196.3636363636) < 1e-9, "2160:11")
    v += ok(RAPORT["glezna"] == 100.0, "glezna 100")

    # 2. CINE limiteaza -- afirmatia din SPEC sectiunea 4, reprodusa cu eta=1
    for art, asteptat in (("sold", "motorul"), ("genunchi", "motorul"),
                          ("glezna", "reductorul")):
        _, cine = efort_continuu_nm(art, eta=1.0)
        v += ok(cine == asteptat, "%s: limiteaza %s, se astepta %s" % (art, cine, asteptat))
    # cifrele din SPEC la eta=1
    v += ok(abs(efort_continuu_nm("sold", 1.0)[0] - 220.9) < 0.1, "sold ~220 Nm")
    v += ok(abs(efort_continuu_nm("genunchi", 1.0)[0] - 176.7) < 0.1, "genunchi ~177 Nm")
    v += ok(abs(efort_continuu_nm("glezna", 1.0)[0] - 52.0) < 1e-9, "glezna 52 Nm")

    # 3. eta MUSCA: cu randament sub 1, efortul scade si poate schimba cine limiteaza
    e1, _ = efort_continuu_nm("sold", 1.0)
    e8, _ = efort_continuu_nm("sold", 0.8)
    v += ok(e8 < e1, "eta trebuie sa reduca efortul")
    v += ok(abs(e8 - 0.8 * e1) < 1e-9, "eta intra liniar la sold (motorul limiteaza)")
    # La glezna, la eta implicit reductorul limiteaza, deci eta NU schimba rezultatul...
    v += ok(efort_continuu_nm("glezna", ETA_IMPLICIT)[0]
            == efort_continuu_nm("glezna", 1.0)[0],
            "la eta implicit, glezna e limitata de reductor, deci eta nu are efect")
    # ...dar sub un PRAG, MOTORUL preia limitarea. Pragul: cuplu*raport*eta = 52
    # -> eta = 52 / (0.706 * 100) = 0.7365. Peste el reductorul limiteaza, sub el motorul.
    prag = REDUCTOR["glezna"][1] / (MOTOR["glezna"]["cuplu_cont_nm"] * RAPORT["glezna"])
    v += ok(abs(prag - 0.7365) < 1e-3, "pragul de basculare la glezna: %.4f" % prag)
    v += ok(efort_continuu_nm("glezna", prag + 0.01)[1] == "reductorul", "peste prag")
    v += ok(efort_continuu_nm("glezna", prag - 0.01)[1] == "motorul", "sub prag")
    # COMPLETITUDINE: glezna e SINGURA articulatie cu prag de basculare in (0,1).
    # La sold  eta* = 345/(0.9*245.45) = 1.5617  -> peste 1, deci motorul limiteaza
    # la ORICE randament fizic posibil. La genunchi eta* = 178/(0.9*196.36) = 1.0072,
    # tot peste 1, dar la limita: cu numai 0.7% mai mult raport sau cuplu, reductorul ar
    # prelua. Analiza de prag e pusa unde conteaza, si se DOVEDESTE ca acolo conteaza.
    praguri = {a: REDUCTOR[a][1] / (MOTOR[a]["cuplu_cont_nm"] * RAPORT[a])
               for a in ("sold", "genunchi", "glezna")}
    v += ok(praguri["sold"] > 1.0 and praguri["genunchi"] > 1.0,
            "sold si genunchi trebuie sa aiba pragul peste 1: %s" % praguri)
    v += ok(0.0 < praguri["glezna"] < 1.0,
            "glezna trebuie sa fie singura cu prag fizic: %s" % praguri)
    v += ok(abs(praguri["genunchi"] - 1.0072) < 1e-3,
            "genunchiul e la 0.7%% de basculare: %.4f" % praguri["genunchi"])
    v += ok(ETA_IMPLICIT > prag,
            "ipoteza de randament (%.2f) e PESTE pragul de basculare (%.4f): daca "
            "randamentul real e mai mic, glezna devine limitata de motor si efortul "
            "scade sub 52 Nm" % (ETA_IMPLICIT, prag))

    # 4. viteza: formula verificata de mana pe sold
    #    3700 rpm / 245.4545 = 15.074 rpm la iesire = 1.578 rad/s
    v += ok(abs(viteza_nominala_rad_s("sold") - 1.5784) < 1e-3,
            "sold: %.4f rad/s" % viteza_nominala_rad_s("sold"))
    v += ok(viteza_nominala_rad_s("genunchi") > viteza_nominala_rad_s("sold"),
            "genunchiul are raport mai mic, deci e mai rapid")
    # Glezna: NU se aserteaza ca e mai rapida decat soldul -- ar fi o ASTEPTARE, nu un
    # fapt. Viteza ei depinde de rpm-ul TBM, care e IPOTEZA declarata, nu cifra din
    # document. Ce decurge din rapoarte e raportul de viteze LA ACELASI rpm:
    LA_FEL = 3700.0
    rv = viteza_nominala_rad_s("glezna", LA_FEL) / viteza_nominala_rad_s("sold", LA_FEL)
    v += ok(abs(rv - RAPORT["sold"] / RAPORT["glezna"]) < 1e-9,
            "la acelasi rpm, viteza scaleaza invers cu raportul")
    v += ok(abs(rv - 2.4545) < 1e-3, "raportul de viteze glezna/sold: %.4f" % rv)
    v += ok(viteza_nominala_rad_s("glezna", RPM_BOBINAJ["A"])
            != viteza_nominala_rad_s("glezna", RPM_BOBINAJ["B"]),
            "viteza gleznei trebuie sa depinda de bobinaj")
    # bobinajul e PARAMETRU si diferenta lui e materiala: 2900 vs 2450 rpm
    v += ok(abs(tabel(bobinaj="A")[2]["viteza_rad_s"]
                / tabel(bobinaj="B")[2]["viteza_rad_s"] - 2900.0 / 2450.0) < 1e-9,
            "raportul de viteze intre bobinaje = raportul turatiilor")
    # si NU afecteaza efortul (acolo limiteaza reductorul)
    v += ok(tabel(bobinaj="A")[2]["efort_nm"] == tabel(bobinaj="B")[2]["efort_nm"],
            "bobinajul schimba viteza, nu efortul")
    # nicio cifra de turatie nu mai e inventata: ambele sunt in RPM_BOBINAJ
    v += ok(set(RPM_BOBINAJ) == {"A", "B"} and 1500.0 not in RPM_BOBINAJ.values(),
            "turatia inventata de 1500 rpm nu mai are voie sa existe")

    # 5. rpm-ul e PARAMETRU, nu constanta: discrepanta 8024B vs 8048 din SPEC
    v += ok(viteza_nominala_rad_s("sold", 1850.0) < viteza_nominala_rad_s("sold", 3700.0),
            "rpm-ul trebuie sa fie parametru")
    v += ok(MOTOR["sold"]["nume"] != MOTOR["sold"]["foaie"],
            "discrepanta 8024B vs 8048 trebuie sa ramana VIZIBILA in date")

    # 6. tabelul e complet si nicio cifra nu e None
    t = tabel()
    v += ok(len(t) == 3, "tabelul trebuie sa aiba 3 randuri")
    for r in t:
        v += ok(all(r[k] is not None for k in ("viteza_rad_s", "efort_nm", "rpm")),
                "rand incomplet: %s" % r)
    print("SELFTEST spec_derivate OK (%d verificari)." % v)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    print("%-10s %8s %7s %10s %10s %-12s %s"
          % ("art", "raport", "rpm", "vit[rad/s]", "efort[Nm]", "limitat de", "reductor"))
    for r in tabel():
        print("%-10s %8.2f %7.0f %10.4f %10.1f %-12s %s"
              % (r["articulatie"], r["raport"], r["rpm"], r["viteza_rad_s"],
                 r["efort_nm"], r["limitat_de"], r["reductor"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
