#!/usr/bin/env python3
"""check_addresses.py -- invariant: nicio adresa IPv4 din codul si documentatia
artefactului in afara blocurilor rezervate documentatiei.

  python3 check_addresses.py [radacina]   # implicit: directorul acestui fisier
  python3 check_addresses.py --selftest

Iese 1 la prima adresa neacceptata, cu fisier:linie. Datele brute sunt excluse
prin constructie: ele pastreaza adresele de la momentul campaniei si nu se rescriu.
"""
import ipaddress, os, re, sys, tempfile

EXT = {".py", ".sh", ".md", ".json5", ".yaml", ".yml", ".tex"}
EXCLUS = {"c1_data", "CAMPANII", "__pycache__", ".git", "manifests"}
PERMISE = [ipaddress.ip_network(n) for n in ("192.0.2.0/24",      # TEST-NET-1
                                             "198.51.100.0/24",   # TEST-NET-2
                                             "203.0.113.0/24",    # TEST-NET-3
                                             "127.0.0.0/8",       # loopback
                                             "224.0.0.0/4")]      # multicast (DDS)
# Exceptii explicite, fiecare cu justificarea ei. Cheie: (nume fisier, literal).
EXCEPTII = {
    ("count_wire_units.py", "9.6.1.1"):
        "nu este o adresa: 9.6.1.1 e numarul sectiunii din specificatia DDSI-RTPS 2.2 "
        "(formula de porturi), citat in comentariu si in docstring",
}
RX = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")


def e_masca(a):
    """0.0.0.0 si mastile de retea (zerouri contigue la coada) sunt acceptate."""
    b = int(a)
    return b == 0 or (((b ^ 0xFFFFFFFF) + 1) & (b ^ 0xFFFFFFFF)) == 0


def verifica(radacina):
    # Fisierul acesta se exclude pe sine: el CONTINE, prin constructie, literalele
    # neacceptate -- tabelul de exceptii si fixture-urile propriului selftest.
    eu = os.path.realpath(__file__)
    rele = []
    for r, d, fs in os.walk(radacina):
        d[:] = [x for x in d if x not in EXCLUS]
        for fn in sorted(fs):
            if os.path.splitext(fn)[1] not in EXT:
                continue
            p = os.path.join(r, fn)
            if os.path.realpath(p) == eu:
                continue
            with open(p, encoding="utf-8", errors="ignore") as f:
                for i, l in enumerate(f, 1):
                    for lit in RX.findall(l):
                        try:
                            a = ipaddress.ip_address(lit)
                        except ValueError:
                            continue
                        if any(a in n for n in PERMISE) or e_masca(a):
                            continue
                        if (fn, lit) in EXCEPTII:
                            continue
                        rele.append((os.path.relpath(p, radacina), i, lit))
    return rele


def selftest():
    d = tempfile.mkdtemp()
    open(os.path.join(d, "bun.py"), "w").write("A = '192.0.2.10'\nB = '127.0.0.1'\nC = '0.0.0.0'\n")
    assert verifica(d) == [], verifica(d)
    open(os.path.join(d, "rau.md"), "w").write("gazda 10.1.2.3 aici\n")
    r = verifica(d)
    assert len(r) == 1 and r[0][1] == 1 and r[0][2] == "10.1.2.3", r
    os.makedirs(os.path.join(d, "c1_data"))
    open(os.path.join(d, "c1_data", "brut.md"), "w").write("192.168.1.1\n")
    assert len(verifica(d)) == 1, "c1_data/ trebuie exclus"
    print("SELFTEST check_addresses OK (3 verificari: acceptate, respinsa, c1_data exclus).")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    rad = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    rele = verifica(rad)
    for f, i, lit in rele:
        print("%s:%d: adresa neacceptata %s" % (f, i, lit))
    if rele:
        print("ESEC: %d adrese in afara blocurilor RFC 5737 / exceptiilor documentate." % len(rele))
        sys.exit(1)
    print("OK: nicio adresa IPv4 in afara blocurilor permise (%d exceptii documentate)." % len(EXCEPTII))
