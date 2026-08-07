#!/usr/bin/env python3
"""derive_policy.py -- genereaza c3_gateway/core/policy_table.json din TABELELE CANONICE
C2 (~/DATE_CAMPANIE/ANALIZA_C2/tabel_hil_4k.md si tabel_hil_64k.md).

De ce generata si nu scrisa de mana: o tabela de politica scrisa din memorie e o opinie
deghizata in date. Asa, fiecare celula poarta provenienta (fisierul sursa + amprenta lui),
si daca datele se schimba, tabela se regenereaza si diferenta se vede in git.

READ-ONLY pe ~/DATE_CAMPANIE (arhivele sunt sigilate). Scrie DOAR in core/policy_table.json.

CUM SE COMPARA DOUA TRANSPORTURI PE O CELULA
Tabelele C2 raporteaza mediana livrarii CONDITIONATA pe rularile supravietuitoare (n>0) si,
separat, n0=k/N (rulari cu zero esantioane). Niciuna singura nu e comparabila intre
transporturi: un transport cu mediana 90% dar 8/10 rulari moarte e mai prost decat unul cu
mediana 50% si 0/10 moarte. Se foloseste numarul NECONDITIONAT, exact cum indica nota din
tabelul canonic:
    livrare_efectiva = (1 - n0/N) * mediana_supravietuitori
O celula fara niciun supravietuitor are livrare_efectiva 0 (nu 'lipsa').

MAPAREA CONDITIE -> (L, B)
    ideal      -> L=0,  B=1     (fara pierdere; B nu are sens, se ia 1 = fara rafale)
    bern_L     -> L,    B=1     (Bernoulli = memoryless, rafala medie ~1)
    ge_L_B     -> L,    B
Conditia combinata lat200_jit50_ge_15_8 e EXCLUSA din grila: cheia politicii e (L, B,
payload), iar acolo intervine si latenta, care nu e reprezentata in cheie. A o baga in
grila ar insemna sa pretindem ca stim ceva ce cheia nu poate exprima. E raportata separat.

Uz:
  python3 tools/derive_policy.py [--analiza DIR] [--out FISIER]
  python3 tools/derive_policy.py --selftest
"""
import hashlib
import json
import os
import re
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
ANALIZA_DEFAULT = os.path.join(os.path.expanduser("~"), "DATE_CAMPANIE", "ANALIZA_C2")
OUT_DEFAULT = os.path.join(PACHET, "c3_gateway", "core", "policy_table.json")

SURSE = [("tabel_hil_4k.md", 4096), ("tabel_hil_64k.md", 65536)]
# etichetele din tabelele C2 -> numele de transport folosite de gateway
TRANSPORT = {"cdds": "cyclonedds", "zenoh": "zenoh"}
EXCLUSE = ("lat200_jit50_ge_15_8",)


def cond_la_LB(cond):
    """'ge_15_8' -> (15, 8); 'bern_15' -> (15, 1); 'ideal' -> (0, 1). None daca nu se
    poate exprima in cheia (L, B)."""
    if cond in EXCLUSE:
        return None
    if cond == "ideal":
        return (0.0, 1.0)
    m = re.match(r"^bern_(\d+)$", cond)
    if m:
        return (float(m.group(1)), 1.0)
    m = re.match(r"^ge_(\d+)_(\d+)$", cond)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    return None


def _num(text):
    try:
        return float(text)
    except ValueError:
        return None


def citeste_tabel(cale):
    """Randurile unui tabel markdown canonic C2. Intoarce lista de dict-uri cu campurile
    de care avem nevoie; ignora antetul, separatorul si notele."""
    randuri = []
    with open(cale) as f:
        for linie in f:
            if not linie.startswith("|"):
                continue
            c = [x.strip() for x in linie.strip().strip("|").split("|")]
            if len(c) < 6 or c[0] in ("conditie",) or set(c[0]) <= {"-"}:
                continue
            m = re.match(r"^(\d+)/(\d+)$", c[3])
            if not m:
                continue
            randuri.append({"cond": c[0], "rmw": c[1], "N": int(m.group(2)),
                            "n0": int(m.group(1)), "mediana": _num(c[5])})
    return randuri


def livrare_efectiva(rand):
    """(1 - n0/N) * mediana. Celula fara supravietuitori -> 0.0 (rezultat, nu date lipsa)."""
    if rand["N"] == 0:
        return None
    if rand["mediana"] is None:
        return 0.0 if rand["n0"] == rand["N"] else None
    return (1.0 - rand["n0"] / float(rand["N"])) * rand["mediana"]


def sha256(cale):
    h = hashlib.sha256()
    with open(cale, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def deriva(dir_analiza):
    """Construieste structura tabelei de politica. Functie pura de I/O simplu: citeste
    fisiere, nu scrie nimic."""
    celule, surse, sarite = [], [], []
    for nume, payload in SURSE:
        cale = os.path.join(dir_analiza, nume)
        if not os.path.isfile(cale):
            sarite.append("%s (lipseste)" % nume)
            continue
        randuri = citeste_tabel(cale)
        surse.append({"fisier": nume, "sha256": sha256(cale), "randuri": len(randuri)})
        pe_cond = {}
        for r in randuri:
            t = TRANSPORT.get(r["rmw"])
            if t is None:
                continue
            pe_cond.setdefault(r["cond"], {})[t] = r
        for cond, per_transport in sorted(pe_cond.items()):
            LB = cond_la_LB(cond)
            if LB is None:
                sarite.append("%s (%s: nereprezentabil in cheia (L,B))" % (cond, nume))
                continue
            scoruri = {}
            for t, r in per_transport.items():
                v = livrare_efectiva(r)
                if v is not None:
                    scoruri[t] = {"livrare_efectiva": round(v, 2), "n0": r["n0"],
                                  "N": r["N"], "mediana_supr": r["mediana"]}
            if len(scoruri) < 2:
                sarite.append("%s (%s: doar %d transport)" % (cond, nume, len(scoruri)))
                continue
            ordine = sorted(scoruri, key=lambda t: -scoruri[t]["livrare_efectiva"])
            castigator, pierzator = ordine[0], ordine[1]
            marja = (scoruri[castigator]["livrare_efectiva"]
                     - scoruri[pierzator]["livrare_efectiva"])
            celule.append({
                "L": LB[0], "B": LB[1], "payload": payload,
                "transport": castigator, "marja": round(marja, 2),
                "covered": True, "sursa": nume, "conditie": cond,
                "detaliu": scoruri,
            })
    # implicitul CONSERVATOR: transportul care castiga cele mai multe celule acoperite.
    # Nu e o preferinta, e un numar; motivul se scrie in tabela ca sa poata fi contestat.
    voturi = {}
    for c in celule:
        voturi[c["transport"]] = voturi.get(c["transport"], 0) + 1
    implicit = max(voturi, key=lambda t: voturi[t]) if voturi else "cyclonedds"
    return {
        "schema": "c3_policy_table/1",
        "generat_de": "tools/derive_policy.py",
        "surse": surse,
        "default_transport": implicit,
        "default_motiv": ("castiga %d din %d celule acoperite (%s); folosit pentru celule "
                          "neacoperite de grila si cand vecinul e prea departe"
                          % (voturi.get(implicit, 0), len(celule),
                             ", ".join("%s=%d" % (t, n) for t, n in sorted(voturi.items())))),
        "excluse": sarite,
        "celule": sorted(celule, key=lambda c: (c["payload"], c["L"], c["B"])),
    }


def _selftest():
    """Fixture in /tmp: doua tabele markdown minimale, scrise ca cele canonice."""
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="derive_policy_selftest_")
    try:
        cap = ("| conditie | RMW | N | n0 | supr. | livrare% med | min | max | first_seq med |\n"
               "|---|---|---|---|---|---|---|---|---|\n")
        with open(os.path.join(d, "tabel_hil_4k.md"), "w") as f:
            f.write("## titlu\n\n" + cap)
            # cdds castiga clar la ge_15_8; zenoh are 3/10 moarte
            f.write("| ge_15_8 | cdds | 10 | 0/10 | 10 | 95.7 | 90.1 | 99.9 | 11 |\n")
            f.write("| ge_15_8 | zenoh | 10 | 3/10 | 7 | 8.7 | 1.5 | 12.4 | 651 |\n")
            # celula in care zenoh e mort complet (mediana '-')
            f.write("| bern_30 | cdds | 10 | 0/10 | 10 | 19.0 | 9.8 | 21.2 | 12 |\n")
            f.write("| bern_30 | zenoh | 10 | 10/10 | 0 | - | - | - | - |\n")
            # conditia combinata: trebuie SARITA, nu bagata in grila
            f.write("| lat200_jit50_ge_15_8 | cdds | 10 | 0/10 | 10 | 55.3 | 10.9 | 62.4 | 96 |\n")
            f.write("| lat200_jit50_ge_15_8 | zenoh | 10 | 8/10 | 2 | 1.7 | 1.3 | 2.0 | 112 |\n")
            f.write("\nnota de subsol care nu trebuie parsata\n")
        with open(os.path.join(d, "tabel_hil_64k.md"), "w") as f:
            f.write(cap)
            f.write("| bern_15 | cdds | 10 | 0/10 | 10 | 0.5 | 0.1 | 1.3 | 365 |\n")
            f.write("| bern_15 | zenoh | 10 | 0/10 | 10 | 2.2 | 1.4 | 3.3 | 51 |\n")

        t = deriva(d)
        assert t["schema"] == "c3_policy_table/1"
        chei = {(c["L"], c["B"], c["payload"]): c for c in t["celule"]}
        assert set(chei) == {(15.0, 8.0, 4096), (30.0, 1.0, 4096), (15.0, 1.0, 65536)}, chei

        c = chei[(15.0, 8.0, 4096)]
        assert c["transport"] == "cyclonedds", c
        # 95.7 vs 0.7*8.7=6.09 -> marja 89.61
        assert abs(c["marja"] - 89.61) < 0.02, c["marja"]
        assert c["sursa"] == "tabel_hil_4k.md" and c["covered"] is True
        assert c["detaliu"]["zenoh"]["n0"] == 3

        m = chei[(30.0, 1.0, 4096)]
        assert m["transport"] == "cyclonedds" and abs(m["marja"] - 19.0) < 0.01, m
        assert m["detaliu"]["zenoh"]["livrare_efectiva"] == 0.0, m   # mort complet = 0

        z = chei[(15.0, 1.0, 65536)]
        assert z["transport"] == "zenoh", z      # la 64KB zenoh castiga celula asta

        assert any("lat200" in s for s in t["excluse"]), t["excluse"]
        assert t["default_transport"] == "cyclonedds", t["default_transport"]
        assert "castiga 2 din 3" in t["default_motiv"], t["default_motiv"]
        assert all(len(s["sha256"]) == 64 for s in t["surse"])

        # maparea conditie -> (L,B), inclusiv cazurile care trebuie respinse
        assert cond_la_LB("ideal") == (0.0, 1.0)
        assert cond_la_LB("bern_5") == (5.0, 1.0)
        assert cond_la_LB("ge_30_3") == (30.0, 3.0)
        assert cond_la_LB("lat200_jit50_ge_15_8") is None
        assert cond_la_LB("altceva") is None
        print("SELFTEST derive_policy OK (16 verificari, tabele sintetice in /tmp).")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    dir_analiza = ANALIZA_DEFAULT
    out = OUT_DEFAULT
    if "--analiza" in argv:
        dir_analiza = os.path.expanduser(argv[argv.index("--analiza") + 1])
    if "--out" in argv:
        out = os.path.expanduser(argv[argv.index("--out") + 1])
    if not os.path.isdir(dir_analiza):
        print("director de analiza inexistent: %s" % dir_analiza)
        return 2
    t = deriva(dir_analiza)
    if not t["celule"]:
        print("nicio celula derivata din %s -- nu scriu o tabela goala" % dir_analiza)
        return 2
    with open(out, "w") as f:
        json.dump(t, f, indent=1, sort_keys=False)
        f.write("\n")
    print("scris %s" % out)
    print("  celule: %d | implicit: %s" % (len(t["celule"]), t["default_transport"]))
    print("  %s" % t["default_motiv"])
    for s in t["surse"]:
        print("  sursa %s (%d randuri) sha256=%s..." % (s["fisier"], s["randuri"],
                                                        s["sha256"][:12]))
    for s in t["excluse"]:
        print("  EXCLUS: %s" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
