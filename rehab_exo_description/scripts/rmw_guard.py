#!/usr/bin/env python3
"""rmw_guard.py -- verifica la RUNTIME ca procesul chiar ruleaza pe RMW-ul cerut.

DE CE EXISTA
Auditul din 18 aug a masurat ca bringup-ul twin-ului nu pinuia nimic:
RMW_IMPLEMENTATION nu era setat, deci se folosea implicitul distributiei
(masurat: rmw_fastrtps_cpp), iar niciun launch nu declara nimic. Intr-un proiect
a carui teza e ca alegerea middleware-ului schimba comportamentul masurabil, a
lasa alegerea in seama environment-ului nu e o scapare de configurare -- e o
gaura de reproducibilitate: doua rulari ale aceleiasi comenzi, pe doua masini,
pot masura doua stive diferite fara ca cineva sa afle.

Pinuirea singura NU ajunge. O variabila de mediu poate fi suprascrisa de un
parinte, pierduta printr-un GroupAction ne-scoped, sau ignorata daca RMW-ul cerut
nu e instalat -- caz in care rclpy cade linistit pe implicit. De aceea exista si
gardianul asta: citeste implementarea EFECTIV incarcata si iese cu cod nenul daca
difera de cea ceruta. Tiparul e cel validat la C3 (transport_agent.py --rmw-asteptat).

NUCLEU PUR: verdict_rmw() nu importa rclpy si nu atinge mediul; se poate testa
izolat cu 'python3 scripts/rmw_guard.py --selftest'.
"""
import argparse
import sys

# Numele scurte acceptate la linia de comanda, spre identificatorul real raportat
# de rclpy.get_rmw_implementation_identifier().
ALIAS = {
    "cyclonedds": "rmw_cyclonedds_cpp",
    "cyclone": "rmw_cyclonedds_cpp",
    "zenoh": "rmw_zenoh_cpp",
    "fastrtps": "rmw_fastrtps_cpp",
    "fastdds": "rmw_fastrtps_cpp",
}
IMPLICIT = "rmw_cyclonedds_cpp"   # decizia din registru (18 aug): stiva plictisitoare

# Coduri de iesire DISTINCTE. Nu e pedanterie: prima versiune folosea 2 pentru
# nepotrivire, adica exact codul cu care iese argparse la argument necunoscut. Cand
# gardianul a murit din argparse (launch ii pasa '-r __node:=...' dupa --ros-args, iar
# filtrul meu scotea doar tokenul '--ros-args', nu si ce urma dupa el), controlul
# negativ a "trecut" din motivul gresit -- un esec de parsare citit ca detectie de
# nepotrivire. Codurile separate fac imposibila confuzia.
COD_NEPOTRIVIRE = 3


def normalizeaza(nume):
    """Nume scurt sau complet -> identificatorul complet. None ramane None."""
    if nume is None:
        return None
    n = str(nume).strip()
    if not n:
        return None
    return ALIAS.get(n.lower(), n)


def verdict_rmw(cerut, efectiv):
    """(ok, mesaj) -- FUNCTIE PURA, fara rclpy si fara os.environ.

    'cerut' poate fi scurt sau complet; 'efectiv' e ce raporteaza rclpy.
    Cerut absent = nu se poate verifica nimic, si asta e un ESEC, nu o trecere:
    un gardian care nu stie ce sa apere nu apara."""
    c, e = normalizeaza(cerut), normalizeaza(efectiv)
    if c is None:
        return (False, "niciun RMW cerut: gardianul nu are ce verifica "
                       "(lipseste argumentul rmw:= sau nu a ajuns pana aici)")
    if e is None:
        return (False, "implementarea RMW efectiva nu a putut fi citita "
                       "(rclpy nu a raportat niciun identificator)")
    if c != e:
        return (False, "NEPOTRIVIRE RMW: s-a cerut '%s', ruleaza '%s'.\n"
                       "  Cauze uzuale: (1) RMW-ul cerut nu e instalat, iar rclpy a cazut "
                       "pe implicit; (2) variabila a fost suprascrisa de un proces parinte; "
                       "(3) SetEnvironmentVariable nu a ajuns la acest nod (GroupAction "
                       "ne-scoped). Verifica: ros2 doctor --report | grep -i rmw" % (c, e))
    return (True, "RMW confirmat: %s" % e)


def _selftest():
    v = 0

    def ok(cond, mesaj):
        assert cond, mesaj
        return 1

    # 1. potrivire, pe nume complet si pe alias
    v += ok(verdict_rmw("rmw_cyclonedds_cpp", "rmw_cyclonedds_cpp")[0] is True, "complet")
    v += ok(verdict_rmw("cyclonedds", "rmw_cyclonedds_cpp")[0] is True, "alias scurt")
    v += ok(verdict_rmw("zenoh", "rmw_zenoh_cpp")[0] is True, "alias zenoh")
    v += ok(verdict_rmw("CycloneDDS", "rmw_cyclonedds_cpp")[0] is True, "alias, alta capitalizare")

    # 2. NEPOTRIVIRE -- cazul pentru care exista gardianul. Mesajul trebuie sa poarte
    # ambele nume, altfel omul nu stie ce sa repare.
    ok_, m = verdict_rmw("cyclonedds", "rmw_fastrtps_cpp")
    v += ok(ok_ is False, "nepotrivirea trebuie sa PICE")
    v += ok("rmw_cyclonedds_cpp" in m and "rmw_fastrtps_cpp" in m,
            "mesajul trebuie sa numeasca si ce s-a cerut, si ce ruleaza: %s" % m)

    # 3. Absentele sunt ESEC, nu trecere. Fara asta, un gardian caruia nu i-a ajuns
    # argumentul ar raporta 'totul bine' exact cand pinuirea s-a pierdut pe drum --
    # adica ar tacea fix in scenariul pentru care a fost scris.
    v += ok(verdict_rmw(None, "rmw_cyclonedds_cpp")[0] is False, "cerut absent = esec")
    v += ok(verdict_rmw("", "rmw_cyclonedds_cpp")[0] is False, "cerut gol = esec")
    v += ok(verdict_rmw("cyclonedds", None)[0] is False, "efectiv necitit = esec")
    v += ok(verdict_rmw(None, None)[0] is False, "ambele absente = esec")

    # 4. normalizarea nu inventeaza: un RMW necunoscut ramane cum a fost scris,
    # ca mesajul de eroare sa arate exact ce a cerut omul
    v += ok(normalizeaza("rmw_ceva_exotic") == "rmw_ceva_exotic", "nume necunoscut pastrat")
    v += ok(verdict_rmw("rmw_ceva_exotic", "rmw_ceva_exotic")[0] is True,
            "doua nume necunoscute identice se potrivesc")

    # 5. implicitul e chiar decizia din registru
    v += ok(IMPLICIT == "rmw_cyclonedds_cpp", "implicitul trebuie sa fie cyclonedds")

    # 6. codul de nepotrivire NU are voie sa fie 2: acolo iese argparse la argument
    # necunoscut, iar confuzia dintre ele a facut deja un control negativ sa treaca
    # din motivul gresit.
    v += ok(COD_NEPOTRIVIRE != 2, "codul de nepotrivire nu poate fi 2 (= eroare argparse)")
    v += ok(COD_NEPOTRIVIRE != 0, "codul de nepotrivire nu poate fi 0")

    print("SELFTEST rmw_guard OK (%d verificari)." % v)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    ap = argparse.ArgumentParser(description="Gardian RMW (vezi docstringul).")
    ap.add_argument("--rmw-asteptat", default=None,
                    help="RMW-ul cerut (nume scurt sau complet)")
    ap.add_argument("--eticheta", default="rmw_guard", help="nume de nod")
    # Curatarea argumentelor ROS se face cu unealta oficiala, nu cu un filtru scris de
    # mana: launch adauga '--ros-args -r __node:=<nume>', iar un filtru care scoate doar
    # tokenul '--ros-args' lasa in urma '-r' si '__node:=...', pe care argparse le respinge.
    from rclpy.utilities import remove_ros_args
    a = ap.parse_args(remove_ros_args(args=["rmw_guard.py"] + argv)[1:])

    import rclpy
    rclpy.init()
    try:
        efectiv = rclpy.get_rmw_implementation_identifier()
        nod = rclpy.create_node(a.eticheta)
        ok, mesaj = verdict_rmw(a.rmw_asteptat, efectiv)
        if ok:
            nod.get_logger().info(mesaj)
        else:
            nod.get_logger().error(mesaj)
        nod.destroy_node()
    finally:
        try:
            rclpy.shutdown()
        except Exception:
            pass
    return 0 if ok else COD_NEPOTRIVIRE


if __name__ == "__main__":
    sys.exit(main())
