#!/usr/bin/env python3
"""plot_sesiune.py -- figuri dintr-un CSV de sesiune, cu titlul luat din antet.

    python3 scripts/plot_sesiune.py ~/DATE_TWIN/20260822_101439_knee_extension/

Genereaza cate un PNG per familie de canale, in acelasi director. Titlul NU se scrie
de mana si nu se deduce din numele fisierului: se citeste din antetul de provenienta,
ca figura sa poarte aceleasi date ca CSV-ul din care vine. O figura care isi ia
titlul din numele directorului minte in clipa in care cineva redenumeste directorul.

NaN RAMANE GAURA IN GRAFIC, niciodata linie la zero. Canalele nemasurate ale
senzorului 6D (Fy, Mx, Mz) sunt NaN prin constructie; desenate ca zero ar arata ca
masuratori valide de valoare zero.

Nucleu pur (selectia familiilor + titlul) cu selftest:
    python3 scripts/plot_sesiune.py --selftest
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import recorder_core as rc                                        # noqa: E402

FAMILII = (
    ("pozitii", "Pozitii masurate vs comenzi", lambda c: c.endswith((".pos", ".cmd"))),
    ("cupluri", "Cupluri articulare", lambda c: c.startswith("cuplu.")),
    ("forta6d", "Senzor 6D (NaN = canal nemasurat)", lambda c: c.startswith("f6d.")),
    ("glezna", "Unghi de glezna si rigla de gamba",
     lambda c: c.startswith(("unghi_glezna.", "rigla."))),
)


def familii(coloane):
    """{cheie: [coloane]}, in ordinea declarata. O coloana poate lipsi dintr-o
    sesiune fara ca familia sa dispara; o familie GOALA insa nu se deseneaza."""
    out = []
    for cheie, eticheta, test in FAMILII:
        col = [c for c in coloane if test(c)]
        if col:
            out.append((cheie, eticheta, col))
    return out


def titlu(meta, eticheta):
    """Titlul figurii: provenienta, nu numele fisierului."""
    return "%s\n%s | %s | conventie %s | commit %s" % (
        eticheta,
        meta.get("exercitiu", "NECUNOSCUT"),
        meta.get("data_ora", "NECUNOSCUT"),
        meta.get("conventie", "NECUNOSCUT"),
        meta.get("commit", "NECUNOSCUT"))


def incarca(cale):
    """(meta, coloane, t, {coloana: [valori]}). NaN ramane NaN."""
    linii = open(cale).read().splitlines()
    meta = rc.parse_antet(linii)
    corp = [l for l in linii if l and not l.startswith("#")]
    if not corp:
        raise ValueError("%s nu are niciun rand de date" % cale)
    cap = corp[0].split(",")
    coloane = cap[1:]
    t, date = [], {c: [] for c in coloane}
    for l in corp[1:]:
        p = l.split(",")
        if len(p) != len(cap):
            continue
        t.append(rc.citeste(p[0]))
        for c, v in zip(coloane, p[1:]):
            date[c].append(rc.citeste(v))
    return meta, coloane, t, date


def _selftest():
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    import tempfile
    # CSV sintetic, cu antet, cu NaN si cu o coloana integral NaN
    col = ["a_joint.pos", "a_joint.cmd", "cuplu.left_hip", "f6d.left.force.y",
           "unghi_glezna.left", "rigla.left"]
    f = tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False)
    for l in rc.antet({"exercitiu": "test_ex", "commit": "abc1234", "conventie": "B1",
                       "data_ora": "2026-08-22 10:00:00"},
                      ipoteze=["o ipoteza"]):
        f.write(l + "\n")
    f.write("t_sim," + ",".join(col) + "\n")
    f.write("0.0,0.1,0.1,2.0,NaN,0.01,0.5\n")
    f.write("0.1,0.2,0.2,2.1,NaN,0.02,0.5\n")
    f.write("# EVENIMENT t=0.15 ceva\n")           # comentariu in mijlocul datelor
    f.write("0.2,NaN,0.3,2.2,NaN,0.03,0.5\n")
    f.close()

    meta, coloane, t, date = incarca(f.name)

    # 1. antetul ajunge in titlu, si titlul poarta provenienta
    ok(meta["exercitiu"] == "test_ex" and meta["commit"] == "abc1234", meta)
    ti = titlu(meta, "Cupluri")
    for bucata in ("test_ex", "abc1234", "B1", "2026-08-22"):
        ok(bucata in ti, "titlul nu poarta '%s'" % bucata)

    # 2. NaN RAMANE NaN dupa citire. Verificarea centrala a fisierului.
    ok(math.isnan(date["f6d.left.force.y"][0]),
       "un canal nemasurat trebuie sa ramana NaN dupa citire")
    ok(all(math.isnan(v) for v in date["f6d.left.force.y"]),
       "o coloana integral nemasurata ramane integral NaN")
    ok(math.isnan(date["a_joint.pos"][2]), "NaN in mijlocul unei coloane ramane NaN")
    ok(date["a_joint.pos"][0] == 0.1, "valorile normale se citesc corect")
    ok(not any(v == 0.0 for v in date["f6d.left.force.y"]),
       "NaN NU are voie sa devina 0.0 -- ar arata ca o masuratoare valida")

    # 3. randurile-comentariu din mijlocul datelor (evenimente) nu strica citirea
    ok(len(t) == 3, "trebuie 3 randuri de date, am %d" % len(t))
    ok(abs(t[2] - 0.2) < 1e-9, "timpul ultimului rand")

    # 4. familiile grupeaza corect si nu inventeaza familii goale
    fam = dict((k, c) for k, _, c in familii(coloane))
    ok(set(fam["pozitii"]) == {"a_joint.pos", "a_joint.cmd"}, fam.get("pozitii"))
    ok(fam["cupluri"] == ["cuplu.left_hip"], fam.get("cupluri"))
    ok(fam["forta6d"] == ["f6d.left.force.y"], fam.get("forta6d"))
    ok(set(fam["glezna"]) == {"unghi_glezna.left", "rigla.left"}, fam.get("glezna"))
    ok(len(familii(["nimic_relevant"])) == 0,
       "fara coloane potrivite nu se declara nicio familie")

    # 5. o coloana care nu apartine niciunei familii nu se pierde tacut in alta
    ok(all("nimic" not in c for _, _, cc in familii(coloane + ["nimic"]) for c in cc),
       "o coloana necunoscuta nu are voie sa fie adoptata de o familie")

    os.unlink(f.name)
    print("SELFTEST plot_sesiune OK (%d verificari: NaN ramane NaN, titlul vine din "
          "antet, familiile nu adopta coloane straine)." % n[0])


def deseneaza(director):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cale = os.path.join(director, "sesiune.csv")
    meta, coloane, t, date = incarca(cale)
    scrise = []
    for cheie, eticheta, col in familii(coloane):
        fig, ax = plt.subplots(figsize=(12, 5))
        goale = 0
        for c in col:
            v = date[c]
            if all(math.isnan(x) for x in v):
                goale += 1
                continue
            # NaN-urile raman in serie: matplotlib le deseneaza ca INTRERUPERE
            ax.plot(t, v, lw=1.1, label=c.replace("_joint", ""))
        if goale:
            ax.text(0.99, 0.02, "%d canale integral NaN (nemasurate), nedesenate" % goale,
                    transform=ax.transAxes, ha="right", fontsize=8, style="italic")
        ax.set_xlabel("t simulat [s]")
        ax.grid(alpha=.3)
        ax.legend(fontsize=7, ncol=3, loc="upper right")
        ax.set_title(titlu(meta, eticheta), fontsize=10)
        fig.tight_layout()
        p = os.path.join(director, "%s.png" % cheie)
        fig.savefig(p, dpi=110)
        plt.close(fig)
        scrise.append(p)
    return scrise


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    if not argv:
        print(__doc__.strip())
        return 0
    for p in deseneaza(os.path.expanduser(argv[0])):
        print("  scris %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
