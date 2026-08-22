#!/usr/bin/env python3
"""recorder_core.py -- CSV-ul de sesiune: antet, randuri, subsol. NUCLEU PUR.

DE CE ARE ANTET DE PROVENIENTA
Un CSV fara antet e un fisier de numere care peste sase luni nu mai poate fi legat de
nimic: nu se stie ce model l-a produs, in ce conventie sunt unghiurile, cu ce castig,
sub ce ipoteze. Arhivele de campanie ale proiectului au disciplina asta de mult; aici
se aplica si datelor de sesiune ale twin-ului. Fisierul se autodocumenteaza.

NaN INSEAMNA NEMASURAT, SI SE SCRIE "NaN".
Niciodata 0, niciodata camp gol. Zero e o masuratoare valida si a scrie zero pentru
"nu stiu" e cea mai proasta minciuna posibila intr-un fisier de date; iar campul gol
face ca fiecare consumator sa decida singur ce inseamna, deci sa decida diferit.

FARA PIERDERI TACUTE
Se numara mesajele PRIMITE pe canal si randurile SCRISE. Diferenta e normala si
asteptata (se esantioneaza la o rata fixa, nu la fiecare mesaj), dar ce NU e normal e
ca un canal sa nu fi primit nimic, sau sa fi primit mult mai putin decat rata ceruta.
Ambele se raporteaza in subsolul fisierului si in log.

Rulare: python3 scripts/recorder_core.py --selftest
"""
import math
import sys

NAN = "NaN"
# Sub cate procente din esantioanele asteptate un canal e considerat problematic.
# Nu 100: un canal la 10 Hz esantionat la 50 Hz va avea mereu mai putine mesaje decat
# randuri, si asta e corect. Pragul prinde canalul MUT sau aproape mut.
PRAG_ACOPERIRE = 0.10

CAMPURI_ANTET = ("data_ora", "commit", "conventie", "exercitiu", "postura",
                 "sezut_max_deg", "viteza", "castig", "rtf_mediu", "rata_hz")


def fmt(v):
    """Un numar pentru CSV. NaN si None devin 'NaN', explicit."""
    if v is None:
        return NAN
    if isinstance(v, float) and math.isnan(v):
        return NAN
    return "%.6f" % v


def citeste(text):
    """Inversa lui fmt: 'NaN' redevine float('nan'), nu 0.0."""
    t = text.strip()
    if t == NAN or t == "":
        return float("nan")
    return float(t)


def antet(meta, ipoteze=()):
    """Liniile de provenienta, comentate cu #. Campurile lipsa NU se sar: se scriu
    ca NECUNOSCUT, ca absenta lor sa fie vizibila in fisier."""
    L = ["# sesiune twin rehab_exo -- date de SIMULARE, nu de dispozitiv real"]
    for c in CAMPURI_ANTET:
        v = meta.get(c)
        L.append("# %-14s %s" % (c + ":", "NECUNOSCUT" if v in (None, "") else v))
    if ipoteze:
        L.append("# ipoteze active (vezi IPOTEZE.md pentru lista completa):")
        for i in ipoteze:
            L.append("#   - %s" % i)
    return L


def parse_antet(linii):
    """Antetul, inapoi in dict. Folosit si de plot_sesiune, ca titlurile figurilor sa
    vina din fisier, nu din numele lui."""
    out, ip = {}, []
    for l in linii:
        if not l.startswith("#"):
            break
        c = l[1:].strip()
        if c.startswith("- "):
            ip.append(c[2:].strip())
            continue
        if ":" in c:
            k, v = c.split(":", 1)
            k = k.strip()
            if k in CAMPURI_ANTET:
                out[k] = v.strip()
    out["ipoteze"] = ip
    return out


def rand(t, valori, coloane):
    """Un rand CSV. Ordinea coloanelor e data din afara, ca sa fie una singura."""
    return ",".join([fmt(t)] + [fmt(valori.get(c)) for c in coloane])


def verdict_pierderi(primite, randuri, rata_hz, durata_s, prag=PRAG_ACOPERIRE):
    """(ok, probleme). Un canal e problematic daca a primit sub `prag` din cate
    mesaje ar fi trebuit sa curga pentru rata si durata sesiunii."""
    asteptat = max(1.0, rata_hz * max(0.0, durata_s))
    rele = []
    for canal, n in sorted(primite.items()):
        if n == 0:
            rele.append((canal, n, "MUT: niciun mesaj in toata sesiunea"))
        elif n < prag * asteptat:
            rele.append((canal, n, "sub %.0f%% din asteptat (%d din ~%d)"
                         % (prag * 100, n, int(asteptat))))
    return (not rele, rele)


def subsol(primite, randuri, rata_hz, durata_s, prag=PRAG_ACOPERIRE):
    """Liniile de inchidere. Contoarele intra in FISIER, nu doar in log: un CSV
    trimis mai departe trebuie sa-si poarte singur avertismentele."""
    ok, rele = verdict_pierderi(primite, randuri, rata_hz, durata_s, prag)
    L = ["# --- inchidere ---",
         "# randuri scrise: %d" % randuri,
         "# durata: %.2f s la %.1f Hz" % (durata_s, rata_hz),
         "# mesaje primite per canal:"]
    for canal, n in sorted(primite.items()):
        L.append("#   %-28s %d" % (canal, n))
    if ok:
        L.append("# verdict: toate canalele au livrat")
    else:
        L.append("# verdict: ATENTIE, %d canale problematice" % len(rele))
        for canal, n, motiv in rele:
            L.append("#   ATENTIE %-24s %s" % (canal, motiv))
    return L, ok, rele


def _selftest():
    n = [0]

    def ok(c, m):
        if not c:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    # 1. NaN ROUND-TRIP: scris -> citit ramane NaN, si NU devine 0.
    ok(fmt(float("nan")) == NAN, "NaN trebuie scris ca 'NaN'")
    ok(fmt(None) == NAN, "lipsa trebuie scrisa ca 'NaN'")
    ok(math.isnan(citeste(fmt(float("nan")))), "NaN scris si citit trebuie sa ramana NaN")
    ok(math.isnan(citeste("")), "camp gol se citeste ca NaN, nu ca 0")
    ok(citeste(fmt(0.0)) == 0.0, "zero e o masuratoare valida si ramane zero")
    ok(fmt(0.0) != NAN, "zero NU are voie sa se scrie ca NaN")
    ok(abs(citeste(fmt(-1.234567)) + 1.234567) < 1e-6, "round-trip pe un numar oarecare")

    # 2. ANTETUL are TOATE campurile, chiar si cele lipsa
    a = antet({"exercitiu": "knee_extension", "conventie": "B1"})
    ok(all(l.startswith("#") for l in a), "tot antetul e comentat")
    for c in CAMPURI_ANTET:
        ok(any(l.startswith("# " + c + ":") for l in a),
           "campul '%s' lipseste din antet" % c)
    ok(any("NECUNOSCUT" in l for l in a),
       "un camp nedat trebuie sa apara ca NECUNOSCUT, nu sa fie sarit")

    # 3. antetul se poate CITI inapoi, cu tot cu ipoteze
    a2 = antet({"exercitiu": "hip_raise", "commit": "abc1234", "conventie": "B1"},
               ipoteze=["talpa 0.230 m: clasa INVARIANT", "banda sezut 0..25: ANTROPO"])
    d = parse_antet(a2)
    ok(d["exercitiu"] == "hip_raise" and d["commit"] == "abc1234", d)
    ok(len(d["ipoteze"]) == 2 and "INVARIANT" in d["ipoteze"][0], d["ipoteze"])
    ok(d["postura"] == "NECUNOSCUT", "campurile lipsa se citesc ca NECUNOSCUT")

    # 4. randul respecta ordinea coloanelor si pastreaza NaN pe pozitia lui
    col = ["a", "b", "c"]
    r = rand(1.5, {"a": 1.0, "c": float("nan")}, col)
    ok(r.split(",")[0] == fmt(1.5), r)
    ok(r.split(",")[2] == NAN, "canalul lipsa 'b' trebuie sa fie NaN")
    ok(r.split(",")[3] == NAN, "NaN explicit ramane NaN")
    ok(len(r.split(",")) == 4, "un rand are timpul plus cate o coloana")

    # 5. CONTOARELE. Un canal mut se raporteaza; unul care livreaza mai rar decat
    # rata de esantionare NU e o problema, si asta e la fel de important.
    prim = {"joint_states": 500, "cuplu_left_hip": 480, "rigla_left": 100,
            "forta_6d_left": 0}
    o, rele = verdict_pierderi(prim, 500, 50.0, 10.0)
    ok(not o, "un canal mut trebuie sa produca verdict negativ")
    nume = [r[0] for r in rele]
    ok("forta_6d_left" in nume, "canalul mut trebuie numit")
    ok("rigla_left" not in nume,
       "un canal la 10 Hz esantionat la 50 Hz NU e o pierdere si nu trebuie reclamat")
    ok("joint_states" not in nume, "un canal sanatos nu se reclama")

    # 5b. control negativ: cand toate livreaza, verdictul e curat
    o2, rele2 = verdict_pierderi({"a": 500, "b": 490}, 500, 50.0, 10.0)
    ok(o2 and not rele2, "cu toate canalele sanatoase verdictul trebuie sa fie curat")

    # 6. SUBSOLUL intra in fisier, nu doar in log, si poarta avertismentul
    L, o3, rele3 = subsol(prim, 500, 50.0, 10.0)
    ok(all(l.startswith("#") for l in L), "tot subsolul e comentat")
    ok(any("ATENTIE" in l for l in L), "avertismentul trebuie sa fie IN fisier")
    ok(any("forta_6d_left" in l for l in L), "canalul problematic e numit in fisier")
    ok(any("randuri scrise: 500" in l for l in L), "numarul de randuri intra in subsol")
    L2, o4, _ = subsol({"a": 500}, 500, 50.0, 10.0)
    ok(any("toate canalele au livrat" in l for l in L2),
       "cazul curat trebuie sa se vada ca atare, nu prin absenta avertismentului")

    print("SELFTEST recorder_core OK (%d verificari: NaN round-trip, antet complet "
          "si recitibil, contoare care nu reclama canalele lente)." % n[0])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
