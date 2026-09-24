#!/usr/bin/python3
"""rmw_guard.py -- verifica la RUNTIME ca procesul chiar ruleaza pe RMW-ul cerut.

DE CE EXISTA
Auditul din 18 aug a masurat ca bringup-ul twin-ului nu pinuia nimic:
RMW_IMPLEMENTATION nu era setat, deci se folosea implicitul distributiei
(masurat: rmw_fastrtps_cpp), iar niciun launch nu declara nimic. Intr-un proiect
a carui teza e ca alegerea middleware-ului schimba comportamentul masurabil, a
lasa alegerea in seama environment-ului nu e o scapare de configurare -- e o
gaura de reproducibilitate: doua rulari ale aceleiasi comenzi, pe doua masini,
pot masura doua stive diferite fara ca cineva sa afle.

Pinuirea singura NU ajunge, dar motivul REAL nu e cel scris aici initial.

CORECTIE, masurata pe 21 aug 2026. Textul de dinainte spunea ca daca RMW-ul cerut
nu e instalat 'rclpy cade linistit pe implicit', si ca de aceea e nevoie de gardian.
E FALS pe ROS 2 Jazzy: cu RMW_IMPLEMENTATION=rmw_connextdds (neinstalat), rclpy da
eroare zgomotoasa ('RMW implementation not installed') si procesul moare cu cod 1.
Nu e nimic tacut acolo. Gardianul a fost deci construit impotriva unei amenintari
care nu exista.

Amenintarea care CHIAR exista, si care e complet tacuta, s-a aratat abia pe 21 aug:
mediul pinuit nu ajunge la procesele nascute dintr-un RegisterEventHandler daca a
fost pus intr-un GroupAction scoped, fiindca grupul isi retrage mediul la iesire.
Atunci jumatate din lant porneste pe alt RMW, iar FastRTPS si CycloneDDS
interopereaza pe discovery si pub/sub dar NU pe request/reply -- deci totul pare
sanatos si doar serviciile mor. Ironia utila: gardianul v1 era ORB exact la asta,
fiindca rula in procesul launch-ului, unde mediul grupului era inca activ.

De aici cele doua verificari de azi, care raspund la intrebari DIFERITE:
  pasiva (verdict_rmw)      -- 'pe ce RMW rulez EU'; cod 3 la nepotrivire
  activa  (verdict_serviciu) -- 'ajung eu la restul lantului'; cod 6 la esec
si pozitia noua: gardianul se porneste din lant, pe acelasi drum ca spawnerele.

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

# Verificarea ACTIVA are cod propriu, si asta nu e cosmetica. Cele doua esecuri sunt
# lucruri diferite: 3 inseamna 'procesul asta ruleaza pe alt RMW decat s-a cerut',
# 6 inseamna 'RMW-ul e cel cerut, dar lantul nu raspunde'. Un mutant care ar trebui
# sa moara din nepotrivire si moare din serviciu mut a fost prins din motivul
# gresit, si asta trebuie sa se poata distinge fara sa citesti loguri.
COD_SERVICIU_MUT = 6


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


def verdict_serviciu(nume, anuntat, a_raspuns, secunde):
    """Verdictul probei ACTIVE. Pur: primeste ce s-a observat, nu observa el.

    De ce exista proba asta, cand exista deja verificarea de identificator: fiindca
    verificarea de identificator raspunde la 'pe ce RMW rulez EU', si asta a fost
    verde in tot timpul in care sistemul era mixt. Gardianul din Valul 1 rula in
    procesul launch-ului, unde mediul grupului scoped era inca activ, deci masura
    exact partea care functiona. Proba activa raspunde la alta intrebare, singura
    care conteaza pentru un lant: 'ajung EU la restul lantului'.

    Se alege un APEL DE SERVICIU si nu un topic pentru ca exact serviciile mor la
    nepotrivire de RMW; topicurile trec, si un gardian care s-ar uita la ele ar
    raporta verde pe un sistem nefunctional.

    Cele doua esecuri se disting: neanuntat inseamna ca nici discovery-ul nu a
    trecut; anuntat-dar-mut inseamna ca discovery-ul a trecut si request/reply nu --
    semnatura clasica a nepotrivirii."""
    if not anuntat:
        return (False, "SERVICIU NEGASIT: '%s' nu a fost anuntat in %.1f s. "
                       "Nici discovery-ul nu trece; lantul e rupt sau nu a pornit."
                       % (nume, secunde))
    if not a_raspuns:
        return (False, "SERVICIU MUT: '%s' e ANUNTAT dar apelul nu s-a intors in "
                       "%.1f s. Semnatura clasica a nepotrivirii de RMW: discovery-ul "
                       "si pub/sub-ul trec, request/reply-ul nu." % (nume, secunde))
    return (True, "serviciu confirmat: '%s' a raspuns" % nume)


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

    # 7. PROBA ACTIVA. Cele trei rezultate posibile sunt distincte si spun de ce.
    o, m = verdict_serviciu("/cm/list", True, True, 20.0)
    v += ok(o, "serviciu care raspunde trebuie sa treaca")
    o, m = verdict_serviciu("/cm/list", True, False, 20.0)
    v += ok(not o and "MUT" in m, "anuntat dar fara raspuns = SERVICIU MUT")
    v += ok("request/reply" in m, "mesajul trebuie sa numeasca mecanismul, nu doar sa pice")
    o, m = verdict_serviciu("/cm/list", False, False, 20.0)
    v += ok(not o and "NEGASIT" in m, "neanuntat = SERVICIU NEGASIT")
    v += ok("MUT" not in m, "cele doua esecuri NU au voie sa dea acelasi mesaj")

    # 8. Codurile celor doua clase de esec sunt DISTINCTE intre ele si fata de 2.
    # Fara asta, un mutant care moare din alt motiv decat cel testat ar trece drept
    # prins -- exact clasa de greseala pe care o inchidem azi.
    v += ok(COD_SERVICIU_MUT != COD_NEPOTRIVIRE,
            "nepotrivirea de RMW si serviciul mut trebuie sa aiba coduri diferite")
    v += ok(COD_SERVICIU_MUT != 2, "codul de serviciu mut nu poate fi 2 (= argparse)")
    v += ok(COD_SERVICIU_MUT != 0, "codul de serviciu mut nu poate fi 0")

    # 9. Gardianul VECHI era ORB la bugul real, si asta se poate arata la nivel pur:
    # verificarea de identificator raspunde 'da' pentru procesul care o ruleaza, chiar
    # daca restul lantului e pe alt RMW. Nu e o slabiciune de implementare, e limita
    # intrebarii puse. De aceea v2 pune a doua intrebare, nu o formuleaza mai bine pe
    # prima.
    orb, _ = verdict_rmw("cyclonedds", "rmw_cyclonedds_cpp")
    v += ok(orb, "verificarea pasiva zice OK pentru procesul propriu -- asta e limita ei")
    prins, m2 = verdict_serviciu("/controller_manager/list_controllers", True, False, 20.0)
    v += ok(not prins, "proba activa prinde exact cazul in care cea pasiva e verde")
    v += ok(COD_NEPOTRIVIRE != 0, "codul de nepotrivire nu poate fi 0")

    print("SELFTEST rmw_guard OK (%d verificari)." % v)
    return 0


def _proba_activa(nod, nume, secunde):
    """Partea care OBSERVA. Subtire cu intentie: tot ce se poate decide fara lume
    sta in verdict_serviciu, ca sa fie testabil fara sa pornesti un lant."""
    from controller_manager_msgs.srv import ListControllers
    cli = nod.create_client(ListControllers, nume)
    anuntat = cli.wait_for_service(timeout_sec=secunde)
    a_raspuns = False
    if anuntat:
        import rclpy
        fut = cli.call_async(ListControllers.Request())
        rclpy.spin_until_future_complete(nod, fut, timeout_sec=secunde)
        a_raspuns = fut.done() and fut.result() is not None
    return verdict_serviciu(nume, anuntat, a_raspuns, secunde)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    ap = argparse.ArgumentParser(description="Gardian RMW (vezi docstringul).")
    ap.add_argument("--rmw-asteptat", default=None,
                    help="RMW-ul cerut (nume scurt sau complet)")
    ap.add_argument("--eticheta", default="rmw_guard", help="nume de nod")
    ap.add_argument("--verifica-serviciu", default=None, metavar="NUME",
                    help="proba ACTIVA: cere ca serviciul NUME sa raspunda. "
                         "Deocamdata se cunoaste doar tipul lui "
                         "controller_manager_msgs/srv/ListControllers.")
    ap.add_argument("--asteapta", type=float, default=20.0,
                    help="secunde de asteptare pentru proba activa")
    # Curatarea argumentelor ROS se face cu unealta oficiala, nu cu un filtru scris de
    # mana: launch adauga '--ros-args -r __node:=<nume>', iar un filtru care scoate doar
    # tokenul '--ros-args' lasa in urma '-r' si '__node:=...', pe care argparse le respinge.
    from rclpy.utilities import remove_ros_args
    a = ap.parse_args(remove_ros_args(args=["rmw_guard.py"] + argv)[1:])

    import rclpy
    rclpy.init()
    cod_esec = COD_NEPOTRIVIRE
    try:
        efectiv = rclpy.get_rmw_implementation_identifier()
        nod = rclpy.create_node(a.eticheta)
        ok, mesaj = verdict_rmw(a.rmw_asteptat, efectiv)
        if ok:
            nod.get_logger().info(mesaj)
        else:
            nod.get_logger().error(mesaj)
        if ok and a.verifica_serviciu:
            ok, mesaj = _proba_activa(nod, a.verifica_serviciu, a.asteapta)
            (nod.get_logger().info if ok else nod.get_logger().error)(mesaj)
            cod_esec = COD_SERVICIU_MUT
        nod.destroy_node()
    finally:
        try:
            rclpy.shutdown()
        except Exception:
            pass
    return 0 if ok else cod_esec


if __name__ == "__main__":
    sys.exit(main())
