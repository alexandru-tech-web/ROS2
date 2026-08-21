#!/usr/bin/env python3
"""senzori_core.py -- NUCLEU PUR pentru familia de senzori documentati. SINTETIC.

ETICHETA CARE NU SE STERGE: tot ce produce fisierul asta e SINTETIC, cu model
DECLARAT, si NU are nicio pretentie de fidelitate fizica. Decizia e inghetata in
registru (18 aug): senzorii NU se deriva din contactele Gazebo, fiindca fortele de
contact s-ar calcula din masele fabricate (GAP 1) si ar spala cifre NEVERIFICAT in
date cu aspect de masuratoare. Sintetic cu model scris e onest prin constructie;
"derivat din fizica" pe mase inventate nu e.

CE MODELEAZA, si de unde vine fiecare marime:
  cuplu sold + genunchi   senzori M2210B (SRI) [PDF Tabel 6.1 p.23; foaie p.178],
                          montati intre iesirea reductorului si axul de transmisie
                          (reper 115 la sold, 320 la genunchi) [PDF p.6-8]
  forta 6D sub talpa      TR69-1500 (TAIER) [PDF Tabel 6.1 p.23; foaie p.181].
                          Documentul numeste TREI marimi [PDF p.11]:
                            Ff  forta paralela cu pedala
                            FN  apasarea pe pedala
                            MC  momentul in plan sagital
                          Restul componentelor unui wrench NU sunt numite in
                          document, deci se publica NaN, nu zero: zero ar afirma
                          "masurat si e nul", NaN spune "nu se masoara". Distinctia
                          conteaza pentru oricine citeste topicul fara sa fi citit PDF-ul.
  unghi glezna            BWK216 (BEWIS) [PDF Tabel 6.1 p.23; foaie p.188]. Senzor
                          DEDICAT, separat de joint_states: glezna nu are encoder pe
                          articulatie (vezi transmisie_core).
  rigla de gamba          rigla electronica 406 [PDF p.9]. Push rod-ul 403 comanda
                          lungimea gambei FARA feedback de pozitie ("limitare de
                          spatiu"); lungimea se MASOARA separat, cu rigla. Twin-ul
                          reproduce exact asta: comanda in bucla DESCHISA, masura pe
                          alt topic.

Ruleaza singur: python3 scripts/senzori_core.py --selftest
"""
import math
import sys

# Semantica celor trei componente masurate ale senzorului 6D [PDF p.11].
# Maparea pe campurile unui geometry_msgs/Wrench e o CONVENTIE a acestui pachet, scrisa
# aici o singura data, ca sa nu existe doua versiuni ale ei.
MAPARE_6D = {
    "Ff": ("force", "x", "forta paralela cu pedala"),
    "FN": ("force", "z", "apasarea pe pedala"),
    "MC": ("torque", "y", "momentul in plan sagital"),
}
NEMASURATE = [("force", "y"), ("torque", "x"), ("torque", "z")]

ETICHETA = "sintetic, model declarat, fara pretentie de fidelitate fizica"


def _zgomot(t, amplitudine, perioada, faza=0.0):
    """Zgomot DETERMINIST (nu aleator): acelasi t da acelasi rezultat, deci o rulare
    se poate reproduce si compara. Un zgomot aleator ar face testele nedeterministe
    si ar ascunde regresii sub 'variatie normala'."""
    if perioada <= 0.0:
        return 0.0
    return amplitudine * math.sin(2.0 * math.pi * t / perioada + faza)


def cuplu_sintetic(comanda_rad, viteza_rad_s, t, k=40.0, b=4.0, zgomot_nm=0.4,
                   perioada_s=0.7, faza=0.0):
    """Model DECLARAT: cuplu = k * pozitie + b * viteza + zgomot determinist.
    NU e un model fizic al pacientului si nu pretinde sa fie -- e un semnal plauzibil
    ca forma si ca ordin de marime, ca traficul si consumatorii sa aiba ce procesa.
    k si b sunt parametri, nu constante ascunse."""
    return k * comanda_rad + b * viteza_rad_s + _zgomot(t, zgomot_nm, perioada_s, faza)


def forta_6d_sintetica(unghi_glezna_rad, incarcare_n, t, zgomot_n=1.5, perioada_s=1.1):
    """Cele TREI marimi numite in document. Intoarce un dict cu chei Ff, FN, MC.
    FN (apasarea) e mereu >= 0: o pedala nu trage de talpa. Ff urmeaza inclinarea
    gleznei; MC e momentul sagital, proportional cu apasarea si cu bratul dat de unghi."""
    fn = max(0.0, incarcare_n + _zgomot(t, zgomot_n, perioada_s))
    ff = fn * math.sin(unghi_glezna_rad) + _zgomot(t, zgomot_n * 0.4, perioada_s, 1.3)
    mc = fn * 0.09 * math.sin(unghi_glezna_rad) + _zgomot(t, 0.3, perioada_s, 2.1)
    return {"Ff": ff, "FN": fn, "MC": mc}


def unghi_glezna_sintetic(unghi_articulatie_rad, t, offset_rad=0.0, zgomot_rad=0.0015,
                          perioada_s=0.9):
    """Senzorul DEDICAT de unghi. Nu e o copie a lui joint_states: are offset de montaj
    (parametru) si zgomot propriu, ca un consumator sa nu poata presupune ca sunt
    aceeasi marime."""
    return unghi_articulatie_rad + offset_rad + _zgomot(t, zgomot_rad, perioada_s)


def rigla_gamba_sintetica(lungime_comandata_m, t, eroare_m=0.0008, perioada_s=1.7,
                          intarziere_m=0.0):
    """Rigla electronica 406. Masoara lungimea REALA, care nu e egala cu cea comandata:
    push rod-ul 403 nu are feedback de pozitie [PDF p.9], deci intre comanda si
    realitate exista o diferenta pe care DOAR rigla o poate arata. 'intarziere_m'
    modeleaza aceasta diferenta si e parametru, nu zero ascuns."""
    return lungime_comandata_m - intarziere_m + _zgomot(t, eroare_m, perioada_s)


def _selftest():
    v = 0

    def ok(c, m):
        assert c, m
        return 1

    # 1. semantica 6D e cea din document, si componentele NEMASURATE sunt declarate
    v += ok(set(MAPARE_6D) == {"Ff", "FN", "MC"}, "exact trei marimi numite in document")
    v += ok(MAPARE_6D["FN"][:2] == ("force", "z"), "FN = apasare pe pedala -> force.z")
    v += ok(MAPARE_6D["MC"][:2] == ("torque", "y"), "MC = moment sagital -> torque.y")
    campuri = {(a, b) for a, b, _ in MAPARE_6D.values()}
    v += ok(campuri.isdisjoint(set(NEMASURATE)), "masurate si nemasurate nu se suprapun")
    v += ok(len(campuri) + len(NEMASURATE) == 6, "impreuna acopera cele 6 componente")

    # 2. DETERMINISM: acelasi t da acelasi rezultat. Fara asta, testele ar fi
    # nedeterministe si orice regresie s-ar ascunde sub "variatie normala".
    for f, arg in ((cuplu_sintetic, (0.3, 0.1, 2.5)),
                   (unghi_glezna_sintetic, (0.2, 2.5)),
                   (rigla_gamba_sintetica, (0.05, 2.5))):
        v += ok(f(*arg) == f(*arg), "%s trebuie sa fie determinista" % f.__name__)
    a = forta_6d_sintetica(0.2, 300.0, 2.5)
    b = forta_6d_sintetica(0.2, 300.0, 2.5)
    v += ok(a == b, "forta 6D trebuie sa fie determinista")

    # 3. semnalele CHIAR depind de intrari (altfel ar fi zgomot pur cu eticheta)
    v += ok(cuplu_sintetic(0.5, 0.0, 1.0) > cuplu_sintetic(0.1, 0.0, 1.0),
            "cuplul trebuie sa creasca cu pozitia comandata")
    v += ok(cuplu_sintetic(0.3, 1.0, 1.0) > cuplu_sintetic(0.3, 0.0, 1.0),
            "cuplul trebuie sa creasca cu viteza")
    v += ok(forta_6d_sintetica(0.0, 500.0, 1.0)["FN"]
            > forta_6d_sintetica(0.0, 100.0, 1.0)["FN"], "FN creste cu incarcarea")

    # 4. FN nu are voie sa fie negativa: o pedala nu TRAGE de talpa
    for inc in (0.0, -50.0, 5.0):
        for t in (0.0, 0.3, 0.55, 1.2, 3.7):
            v += ok(forta_6d_sintetica(0.1, inc, t)["FN"] >= 0.0,
                    "FN negativa la incarcare %.1f, t=%.2f" % (inc, t))

    # 5. senzorul de unghi NU e o copie a lui joint_states: cu offset de montaj difera
    v += ok(unghi_glezna_sintetic(0.3, 1.0, offset_rad=0.02)
            != unghi_glezna_sintetic(0.3, 1.0, offset_rad=0.0),
            "offsetul de montaj trebuie sa conteze")
    v += ok(abs(unghi_glezna_sintetic(0.3, 1.0, zgomot_rad=0.0) - 0.3) < 1e-12,
            "cu zgomot zero si offset zero, senzorul da chiar unghiul")

    # 6. RIGLA: bucla deschisa inseamna ca masura POATE sa difere de comanda. Daca
    # rigla ar reflecta perfect comanda, nu ar avea niciun rost sa existe -- si ar
    # rata exact particularitatea din PDF p.9.
    com = 0.05
    v += ok(rigla_gamba_sintetica(com, 1.0, intarziere_m=0.003) < com,
            "cu intarziere, rigla trebuie sa arate MAI PUTIN decat comanda")
    v += ok(abs(rigla_gamba_sintetica(com, 1.0, eroare_m=0.0, intarziere_m=0.0) - com)
            < 1e-12, "fara eroare si fara intarziere, rigla da comanda")
    dif = [abs(rigla_gamba_sintetica(com, t) - com) for t in (0.1, 0.5, 1.0, 1.4)]
    v += ok(max(dif) > 0.0, "rigla trebuie sa aiba eroare proprie, altfel e inutila")

    # 7. ASERTTIA INVERSA: cele trei marimi NUMITE nu au voie sa fie NaN niciodata.
    # Fara ea, "NaN pe nemasurate" ar fi doar jumatate de contract: un bug care ar face
    # si Ff sau MC sa iasa NaN ar trece neobservat, iar consumatorul ar primi un canal
    # otravit exact acolo unde documentul promite o masuratoare.
    for unghi in (-0.6, -0.1, 0.0, 0.35, 0.61):
        for inc in (0.0, 120.0, 300.0, 900.0):
            for t in (0.0, 0.4, 1.3, 7.7):
                f = forta_6d_sintetica(unghi, inc, t)
                for cheie in ("Ff", "FN", "MC"):
                    v += ok(not math.isnan(f[cheie]) and not math.isinf(f[cheie]),
                            "%s a iesit %s la unghi=%.2f inc=%.1f t=%.2f"
                            % (cheie, f[cheie], unghi, inc, t))
    # si maparea e canonica: definita O SINGURA data, fara duplicat in nod
    import os as _os
    nod = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "senzori_node.py")
    if _os.path.isfile(nod):
        text = open(nod).read()
        v += ok('"force", "x"' not in text and '"torque", "y"' not in text,
                "maparea 6D nu are voie sa fie rescrisa in nod: se importa MAPARE_6D")
        v += ok("MAPARE_6D" in text and "NEMASURATE" in text,
                "nodul trebuie sa foloseasca maparea canonica din nucleu")

    # 8. eticheta exista si spune ce trebuie
    v += ok("sintetic" in ETICHETA and "fara pretentie" in ETICHETA, "eticheta")

    print("SELFTEST senzori_core OK (%d verificari)." % v)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
