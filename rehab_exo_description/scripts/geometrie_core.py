#!/usr/bin/env python3
"""geometrie_core.py -- DE UNDE VINE FIECARE COTA A MODELULUI. NUCLEU PUR.

DE CE EXISTA FISIERUL ASTA
Pana pe 22 aug 2026 toata geometria URDF-ului era inventata: lungimi de segment,
inaltimea soldului, dimensiunile placii. Nu era marcata nicaieri ca atare -- masele
primisera MASE_NEVERIFICATE.md si interdictie explicita, geometria n-a primit nimic
si a trecut drept reala. Rezultatul s-a vazut in simulare: piciorul atarna drept in
jos din sold si trecea PRIN placa de baza si sub podea.

CE SPUNE DOCUMENTUL SURSA
Cautat in tot PDF-ul (240 de pagini, text integral): NU exista nicio cota a
dispozitivului. Singurele dimensiuni sunt cutia de transport (1850 x 1750 x 1450 mm,
ambalaj) si fisele componentelor. Desenele Fig 2.2-2.9 au numere de reper, nu cote.
Asta confirma GAP LIST punctele 2, 3 si 8 din SPEC_LLR_twin_din_PDF.md.

TREI CLASE DE PROVENIENTA, si nimic in afara lor:
  FISA      -- din fisa unei componente numite in document. Cifre reale.
  INVARIANT -- valoare ALEASA ca un invariant sa treaca. E clasa cu cea mai SLABA
               provenienta din tot modelul: nu vine nici din document, nici din
               antropometrie, ci dintr-o cerinta pe care i-am impus-o eu. Merita
               nume propriu tocmai ca sa nu se ascunda printre cele derivate, si
               urca prima pe agenda vizitei fizice.
  ANTROPO   -- din antropometria adultului. Argumentul NU e comoditatea: coapsa si
               gamba sunt REGLABILE prin push rod 306 si 403 tocmai ca sa se
               potriveasca pacientului, deci intervalul lor trebuie sa acopere
               antropometria adulta. Cifra nominala e o alegere in interiorul ei.
  LAYOUT    -- derivata geometric din celelalte doua plus postura de lucru.

NIMIC de aici nu descrie dispozitivul REAL cu precizie. Descrie un dispozitiv
PLAUZIBIL si COERENT. Interdictia e aceeasi ca la mase: nicio concluzie despre
dimensiunile masinii reale. Se inlocuieste la prima vizita fizica.

Rulare: python3 scripts/geometrie_core.py --selftest
        python3 scripts/geometrie_core.py            (tabelul, pentru raport)
"""
import sys

# --- FISA: gabaritul articulatiilor ----------------------------------------
# Reductoarele si motorul sunt NUMITE in document; diametrele lor exterioare vin din
# fisele anexate, deci sunt cifre reale si dau SCARA articulatiilor.
D_SOLD = 0.170        # SHG-40-100-2UH, oA h7 = 170 mm [tabel Harmonic Drive "SHF SHG 2UH Dimensions"]
D_GENUNCHI = 0.142    # SHG-32-100-2UH, oA h7 = 142 mm [acelasi tabel]
D_GLEZNA = 0.060      # TBM60-25, frame 60 mm [fisa TBM, "3 frame sizes ranging from 60mm"]

# --- ANTROPO: proportiile segmentelor --------------------------------------
# Fractii din statura, dupa Winter, "Biomechanics and Motor Control of Human
# Movement" (tabelul standard de segmente). Coapsa = trohanter mare -> condil
# femural; gamba = condil femural -> maleola; adica exact distantele intre axele
# articulare care ne trebuie.
FRACTIE_COAPSA = 0.245
FRACTIE_GAMBA = 0.246
FRACTIE_TALPA_LUNGIME = 0.152
FRACTIE_INALTIME_GLEZNA = 0.039

# Staturile care definesc intervalul de reglaj. Un dispozitiv de reabilitare trebuie
# sa acopere de la femeia mica la barbatul mare; capetele sunt percentilele uzuale.
STATURA_MIN = 1.51    # ~P5 femeie adulta
STATURA_NOM = 1.75    # ~P50 barbat adult; de aici ies cotele NOMINALE ale modelului
STATURA_MAX = 1.87    # ~P95 barbat adult


def segment(fractie, statura=STATURA_NOM):
    return fractie * statura


def interval_reglaj(fractie):
    """(minim, nominal, maxim, cursa) pentru un segment reglabil."""
    lo, no, hi = (segment(fractie, s) for s in (STATURA_MIN, STATURA_NOM, STATURA_MAX))
    return (lo, no, hi, hi - lo)


# --- LAYOUT: unde stau axele, in postura de LUCRU ---------------------------
# Postura de lucru e SEZUT (confirmata de om, 22 aug): coapsa orizontala, gamba
# verticala, talpa sprijinita. In conventia noua a soldului, asta e ZERO.
#
# Lantul pe verticala, de jos in sus, in postura sezut:
#   talpa (suprafata de sprijin)
#   + inaltimea gleznei deasupra tapei
#   + lungimea gambei
#   = inaltimea axei genunchiului = inaltimea axei soldului (coapsa e orizontala)
GROSIME_PLACA_BAZA = 0.060       # LAYOUT: placa de baza a modulului de picior
# ALES PRIN MASURARE, nu arbitrar. Prima valoare pusa aici a fost 0.100, fara niciun
# criteriu. Baleierea din test/test_podea.py a aratat ca la ea un colt al placii de
# talpa coboara la -0.099 m in cea mai defavorabila configuratie LEGALA (genunchi
# 105 grade, glezna in flexie plantara maxima, gamba la reglajul maxim): cu genunchiul
# flectat peste 90 de grade gamba trece de verticala si duce varful in jos.
# Criteriul de acum, care e o cerinta de proiectare reala: intreaga fereastra de
# unghiuri DOCUMENTATA trebuie sa fie utilizabila fara ca ceva sa atinga podeaua.
# Valoarea se alege ca sa ramana o MARGINE de proiectare, nu doar ca sa nu atinga:
# la 0.200 baleierea da +0.0007 m, adica 0.7 mm, ceea ce nu e o margine, e o
# coincidenta. La 0.230 raman circa 0.030 m in cel mai defavorabil caz, si testul
# aserteaza marginea, nu doar semnul.
# Consecinta acceptata: axa soldului urca la ~0.73 m si scaunul la ~0.67 m in pozitia
# de LUCRU. Pentru transferul pacientului, coloana 101 il COBOARA (cursa devine
# negativa fata de pozitia de lucru); nu e o cota de scaun obisnuit, e o statie de
# antrenament la care pacientul e adus, nu pe care se urca singur.
MARGINE_PODEA = 0.030            # ALES: cat trebuie sa ramana sub cel mai jos punct
# CLASA: INVARIANT. Nu LAYOUT. Cifra asta nu descrie dispozitivul, descrie o cerinta
# pe care i-am impus-o eu modelului. E cota cu cea mai slaba provenienta din tot
# pachetul si prima de masurat la vizita, alaturi de geometria scaunului.
# Verificare ieftina cu ochiul, la orice inspectie in RViz: ancora de scara de la
# glezna e motorul TBM60, adica 60 mm diametru DOCUMENTAT. O talpa de 230 mm langa
# un motor de 60 mm se vede imediat daca e absurda ca proportie.
INALTIME_TALPA = 0.230           # INVARIANT (vezi test_podea.py)

# Amplasarea in plan. Axa soldului MASINII sta lateral fata de scaun, fiindca modulul
# de picior e un ansamblu propriu langa scaun [Fig 2.2: 001 baza scaun, 003 baza
# picior, stanga si dreapta]. Nu coincide cu soldul OMULUI; intre ele exista un brat
# lateral, ca la orice exoschelet cu module laterale.
SOLD_X = 0.000                   # LAYOUT: axa soldului la marginea din fata a scaunului
SOLD_Y = 0.260                   # LAYOUT: semidistanta intre cele doua module
SCAUN_LUNGIME = 0.460            # LAYOUT
SCAUN_GROSIME = 0.070            # LAYOUT
SOLD_PESTE_SCAUN = 0.060         # LAYOUT: axa soldului deasupra fetei scaunului
MARGINE_PLACA = 0.120            # LAYOUT: cat depaseste placa ansamblul, in fata si spate


def inaltime_glezna():
    return INALTIME_TALPA + segment(FRACTIE_INALTIME_GLEZNA)


def inaltime_sold():
    """Axa soldului deasupra podelei, in postura sezut."""
    return inaltime_glezna() + segment(FRACTIE_GAMBA)


def scaun_sus():
    """Fata superioara a scaunului. Sub axa soldului: omul sta PE perna, iar centrul
    articulatiei lui e deasupra ei."""
    return inaltime_sold() - SOLD_PESTE_SCAUN


def intindere_x():
    """(spate, fata) ale ansamblului in x, in postura de lucru. Determina placa.
    In fata, punctul extrem e varful talpei; in spate, spatarul."""
    genunchi_x = SOLD_X + segment(FRACTIE_COAPSA)
    # talpa porneste din glezna si merge inainte; se ia jumatatea din fata
    varf_talpa = genunchi_x + 0.75 * segment(FRACTIE_TALPA_LUNGIME)
    spate = SOLD_X - SCAUN_LUNGIME - MARGINE_PLACA
    return (spate, varf_talpa + MARGINE_PLACA)


def cote():
    """Toate cotele modelului, intr-un singur dict. Cheile sunt numele
    proprietatilor xacro, ca sa nu existe traducere pe drum."""
    c_lo, c_no, c_hi, c_cursa = interval_reglaj(FRACTIE_COAPSA)
    g_lo, g_no, g_hi, g_cursa = interval_reglaj(FRACTIE_GAMBA)
    return {
        # FISA
        "d_sold": D_SOLD, "d_genunchi": D_GENUNCHI, "d_glezna": D_GLEZNA,
        # ANTROPO
        "coapsa_nom": c_no, "coapsa_cursa": c_cursa,
        "gamba_nom": g_no, "gamba_cursa": g_cursa,
        "talpa_lungime": segment(FRACTIE_TALPA_LUNGIME),
        "glezna_offset": segment(FRACTIE_INALTIME_GLEZNA),
        # LAYOUT
        "placa_grosime": GROSIME_PLACA_BAZA,
        "margine_podea": MARGINE_PODEA,
        "talpa_inaltime": INALTIME_TALPA,
        "sold_inaltime": inaltime_sold(),
        "glezna_inaltime": inaltime_glezna(),
        "sold_x": SOLD_X, "sold_y": SOLD_Y,
        "scaun_lungime": SCAUN_LUNGIME, "scaun_grosime": SCAUN_GROSIME,
        "scaun_sus": scaun_sus(),
        "scaun_centru_z": scaun_sus() - SCAUN_GROSIME / 2.0,
        "scaun_centru_x": SOLD_X - SCAUN_LUNGIME / 2.0,
        "placa_lungime": intindere_x()[1] - intindere_x()[0],
        "placa_centru_x": (intindere_x()[0] + intindere_x()[1]) / 2.0,
        "placa_latime": 2.0 * (SOLD_Y + 0.090),
        "coloana_sold_h": inaltime_sold() - GROSIME_PLACA_BAZA,
    }


def _tabel():
    c = cote()
    linii = [
        ("d_sold", c["d_sold"], "FISA", "reductor SHG-40-100-2UH, diametru exterior"),
        ("d_genunchi", c["d_genunchi"], "FISA", "reductor SHG-32-100-2UH"),
        ("d_glezna", c["d_glezna"], "FISA", "motor TBM60-25, frame 60 mm"),
        ("coapsa_nom", c["coapsa_nom"], "ANTROPO", "0.245 x statura 1.75 (P50 barbat)"),
        ("coapsa_cursa", c["coapsa_cursa"], "ANTROPO", "push rod 306; acopera P5 femeie .. P95 barbat"),
        ("gamba_nom", c["gamba_nom"], "ANTROPO", "0.246 x statura 1.75"),
        ("gamba_cursa", c["gamba_cursa"], "ANTROPO", "push rod 403; acelasi interval"),
        ("talpa_lungime", c["talpa_lungime"], "ANTROPO", "0.152 x statura"),
        ("glezna_offset", c["glezna_offset"], "ANTROPO", "0.039 x statura, glezna peste talpa"),
        ("talpa_inaltime", c["talpa_inaltime"], "INVARIANT", "ALEASA ca invariantul podelei sa treaca; PROVENIENTA CEA MAI SLABA din model"),
        ("glezna_inaltime", c["glezna_inaltime"], "LAYOUT", "talpa + offset de glezna"),
        ("sold_inaltime", c["sold_inaltime"], "LAYOUT", "glezna + gamba; coapsa e orizontala la sezut"),
        ("placa_grosime", c["placa_grosime"], "LAYOUT", "placa de baza a modulului de picior"),
    ]
    out = ["%-16s %9s  %-8s %s" % ("cota", "valoare[m]", "clasa", "de unde"),
           "-" * 92]
    for n, v, cls, de in linii:
        out.append("%-16s %9.4f  %-8s %s" % (n, v, cls, de))
    return "\n".join(out)


def _xacro():
    """Cotele, ca fisier xacro inclus de descriere. Se GENEREAZA la build, ca sa nu
    existe o a doua copie a cifrelor care sa se desparta de asta in timp -- exact
    tiparul folosit si pentru SPEC_DERIVATE.md."""
    c = cote()
    L = ['<?xml version="1.0"?>',
         '<!-- GENERAT de scripts/geometrie_core.py. NU se editeaza manual.',
         '     Fiecare cota are o clasa de provenienta; vezi antetul acelui fisier',
         '     si IPOTEZE.md. Statut general: geometria NU e masurata pe dispozitiv. -->',
         '<robot xmlns:xacro="http://www.ros.org/wiki/xacro">']
    for k in sorted(c):
        L.append('  <xacro:property name="g_%s" value="%.6f"/>' % (k, c[k]))
    L.append('</robot>')
    return "\n".join(L) + "\n"


def _selftest():
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    c = cote()

    # 1. ANTROPOMETRIA: intervalul de reglaj chiar acopera plaja de statura, iar
    # nominalul e INAUNTRU. Daca nominalul ar cadea in afara, reglajul nu l-ar putea
    # atinge -- exact genul de incoerenta care nu se vede in nicio imagine.
    for fractie, nume in ((FRACTIE_COAPSA, "coapsa"), (FRACTIE_GAMBA, "gamba")):
        lo, no, hi, cursa = interval_reglaj(fractie)
        ok(lo < no < hi, "%s: nominalul trebuie sa fie strict in interval" % nume)
        ok(abs(cursa - (hi - lo)) < 1e-12, "%s: cursa = hi - lo" % nume)
        ok(0.05 < cursa < 0.15, "%s: cursa de %.3f m e implauzibila pentru un push rod" % (nume, cursa))
    n[0] += 1

    # 2. Cele doua segmente sunt aproape egale la om, si trebuie sa ramana asa:
    # daca cineva schimba o fractie si uita cealalta, se vede aici.
    ok(abs(c["coapsa_nom"] - c["gamba_nom"]) < 0.01,
       "coapsa si gamba difera cu %.3f m; la om sunt aproape egale"
       % abs(c["coapsa_nom"] - c["gamba_nom"]))

    # 3. LANTUL VERTICAL SE INCHIDE. Asta e afirmatia care lipsea si din cauza careia
    # piciorul trecea prin placa: inaltimea soldului NU e o cifra libera, e suma
    # segmentelor de sub el in postura de lucru.
    ok(abs(c["sold_inaltime"] - (c["talpa_inaltime"] + c["glezna_offset"]
                                 + c["gamba_nom"])) < 1e-12,
       "inaltimea soldului trebuie sa fie suma lantului de sub el")

    # 4. NIMIC NU INTRA IN PLACA, in postura de lucru. Controlul care ar fi prins
    # bugul original: glezna trebuie sa fie DEASUPRA fetei superioare a placii.
    ok(c["glezna_inaltime"] > c["placa_grosime"],
       "glezna la %.3f m e sub fata placii (%.3f m) -- exact bugul din 21 aug"
       % (c["glezna_inaltime"], c["placa_grosime"]))
    ok(c["talpa_inaltime"] >= c["placa_grosime"],
       "suportul de talpa nu are voie sa fie sub placa")

    # 5. CONTROL NEGATIV pe verificarea 4: cu vechile cifre (sold la 0.520 si gamba
    # 0.400, adica glezna la 0.120 masurat de la sold in jos) lantul NU se inchidea.
    # Reconstituim vechea aritmetica si aratam ca pica.
    vechi_sold, vechi_gamba, vechi_coapsa = 0.520, 0.400, 0.400
    vechi_glezna = vechi_sold - vechi_coapsa - vechi_gamba   # picior atarnat, hip=0
    ok(vechi_glezna < 0.0,
       "controlul negativ nu mai reproduce bugul vechi (glezna iesea la %.3f m)"
       % vechi_glezna)
    ok(vechi_glezna < c["glezna_inaltime"],
       "geometria noua trebuie sa fie strict mai buna decat cea veche")

    # 6. Gabaritul articulatiilor e mai mic decat segmentele pe care le leaga --
    # altfel carcasele s-ar suprapune si niciun unghi n-ar fi realizabil.
    ok(c["d_sold"] < c["coapsa_nom"], "carcasa soldului nu incape pe coapsa")
    ok(c["d_genunchi"] < min(c["coapsa_nom"], c["gamba_nom"]),
       "carcasa genunchiului nu incape intre sold si glezna")
    ok(c["d_glezna"] < c["talpa_lungime"], "carcasa gleznei e mai lata decat talpa")

    # 7. ordinea de marime, ca sa nu treaca o greseala de factor 10 sau de unitati
    ok(0.30 < c["coapsa_nom"] < 0.55, "coapsa %.3f m in afara plajei umane" % c["coapsa_nom"])
    ok(0.30 < c["gamba_nom"] < 0.55, "gamba %.3f m in afara plajei umane" % c["gamba_nom"])
    ok(0.40 < c["sold_inaltime"] < 0.75,
       "sold la %.3f m: implauzibil pentru un scaun" % c["sold_inaltime"])

    # 7b. AMPLASAREA: placa trebuie sa acopere ansamblul in postura de lucru.
    # Verificarea care lipsea si din cauza careia talpa iesea in gol.
    spate, fata = intindere_x()
    ok(spate < 0.0 < fata, "placa trebuie sa cuprinda axa soldului")
    genunchi_x = SOLD_X + segment(FRACTIE_COAPSA)
    ok(genunchi_x < fata, "genunchiul (%.3f) trebuie sa fie in fata placii (%.3f)"
       % (genunchi_x, fata))
    ok(abs(c["placa_lungime"] - (fata - spate)) < 1e-12, "lungimea placii = intinderea")
    ok(c["placa_latime"] > 2 * SOLD_Y, "placa trebuie sa fie mai lata decat modulele")
    ok(c["scaun_sus"] < c["sold_inaltime"],
       "fata scaunului trebuie sa fie SUB axa soldului; omul sta pe perna")
    ok(c["coloana_sold_h"] > 0.30,
       "coloana soldului de %.3f m e prea joasa pentru un cadru vertical"
       % c["coloana_sold_h"])

    # 7c. CONTROL NEGATIV pe amplasare: cu placa VECHE (0.7 lungime, centrata in 0)
    # varful talpei cadea in afara ei. Se arata ca vechea configuratie pica.
    ok(genunchi_x > 0.35,
       "controlul negativ nu mai are sens: genunchiul ar incapea in placa veche")

    # 8. sanatatea tipurilor. LUNGIMILE sunt strict pozitive; COORDONATELE au voie
    # sa fie zero sau negative, si distinctia conteaza: 'sold_x = 0' e o pozitie
    # perfect valida, nu o cota lipsa.
    COORDONATE = {"sold_x", "scaun_centru_x", "placa_centru_x"}
    for k, v in c.items():
        ok(isinstance(v, float), "%s = %r nu e numeric" % (k, v))
        if k in COORDONATE:
            ok(abs(v) < 5.0, "%s = %.3f e implauzibil pentru o coordonata" % (k, v))
        else:
            ok(v > 0.0, "%s = %r: lungimile trebuie sa fie strict pozitive" % (k, v))

    print("SELFTEST geometrie_core OK (%d verificari: lantul vertical se inchide, "
          "reglajul acopera antropometria, controlul negativ reproduce bugul vechi)."
          % n[0])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    if argv and argv[0] == "--xacro":
        text = _xacro()
        if len(argv) > 1:
            with open(argv[1], "w") as f:
                f.write(text)
        else:
            sys.stdout.write(text)
        return 0
    print(_tabel())
    return 0


if __name__ == "__main__":
    sys.exit(main())
