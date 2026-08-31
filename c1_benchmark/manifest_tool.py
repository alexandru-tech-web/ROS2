#!/usr/bin/env python3
"""manifest_tool.py -- manifest SHA256 pentru setul canonic C1.

  make <radacina> <subarbore>... [--extra <fisier>...]   scrie manifestul la stdout
  check <radacina> <MANIFEST>                            nepotriviri / lipsa / extra
  --selftest                                             pe un director temporar

Antetul poarta cifrele (cate fisiere, pe subarbore si pe tip); textul din README
trimite aici, ca sa nu existe doua locuri cu aceleasi numere. 'check' limiteaza
cautarea de 'extra' la subarborii declarati in antet.
"""
import argparse, datetime, hashlib, os, re, shutil, sys, tempfile


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def culege(root, subarbori, extra):
    out = []
    for s in subarbori:
        for r, _, fs in os.walk(os.path.join(root, s)):
            out += [os.path.relpath(os.path.join(r, f), root) for f in fs]
    out += [e for e in extra if os.path.isfile(os.path.join(root, e))]
    return sorted(out)


RX_TR = re.compile(r"^transport_p(\d+)(_summary)?\.(csv|json)$")


def analiza(rels):
    """Descompune <env>/date/<rmw>/<cond>/rep<N>/transport_p<P>.{csv,json}.

    Intoarce (celule, payloads, in_celule, afara), ca antetul sa poata scrie
    ARITMETICA, nu doar totalul: cine nu poate reface 32 x rep x payload din
    antet nu poate spune daca setul e complet."""
    celule, payloads, in_cel, afara = {}, set(), {"json": 0, "csv": 0}, {}
    for r in rels:
        p = r.split("/")
        m = RX_TR.match(p[-1])
        if len(p) >= 5 and p[1] == "date" and p[4].startswith("rep") and m:
            payloads.add(int(m.group(1)))
            celule.setdefault((p[0], p[2], p[3]), set()).add(p[4])
            in_cel["json" if p[-1].endswith(".json") else "csv"] += 1
        else:
            e = os.path.splitext(p[-1])[1].lstrip(".") or "(fara)"
            afara[e] = afara.get(e, 0) + 1
    return celule, payloads, in_cel, afara


def make(root, subarbori, extra, ies=sys.stdout, nume="C1_CANONIC"):
    rels = culege(root, subarbori, extra)
    w = ies.write
    w("# Manifest SHA256 -- set canonic C1\n")
    w("# Generat: %sZ\n" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"))
    w("# Radacina logica: %s\n" % nume)
    for s in subarbori:
        w("# subarbore: %s\n" % s)
    for e in extra:
        w("# extra: %s\n" % e)
    w("# Total fisiere: %d\n" % len(rels))
    for s in subarbori:
        w("#   %-12s %5d\n" % (s + "/", sum(1 for r in rels if r.startswith(s + "/"))))
    tip = {}
    for r in rels:
        e = os.path.splitext(r)[1].lstrip(".") or "(fara)"
        tip[e] = tip.get(e, 0) + 1
    w("# Pe tip: %s\n" % ", ".join("%s=%d" % kv for kv in sorted(tip.items())))
    cel, pay, inc, afara = analiza(rels)
    if cel:
        env = {}
        for (e, _, _), reps in cel.items():
            n, R = env.get(e, (0, set()))
            env[e] = (n + 1, R | {len(reps)})
        w("# celule rmw x conditie: %d (%s) | repetitii: %s\n"
          % (len(cel),
             ", ".join("%d per %s" % (v[0], e) for e, v in sorted(env.items())),
             ", ".join("%s=%s" % (e, "|".join(map(str, sorted(v[1])))) for e, v in sorted(env.items()))))
        asteptat = sum(len(v) for v in cel.values()) * len(pay)
        w("# payload-uri: %d (p=%s) -> %d x (%s) x %d = %d json + %d csv\n"
          % (len(pay), ",".join(map(str, sorted(pay))), len(cel),
             "|".join("|".join(map(str, sorted(v[1]))) for _, v in sorted(env.items())),
             len(pay), asteptat, asteptat))
        w("# in afara celulelor: %s\n" % ", ".join("%s=%d" % kv for kv in sorted(afara.items())))
        if inc["json"] != asteptat or inc["csv"] != asteptat:
            w("# ARITMETICA NU SE INCHIDE: gasit %d json + %d csv in celule, asteptat %d din fiecare\n"
              % (inc["json"], inc["csv"], asteptat))
    w("# Format: sha256  cale-relativa-la-radacina\n")
    for r in rels:
        w("%s  %s\n" % (sha(os.path.join(root, r)), r))
    return len(rels)


def citeste(man):
    sub, ext, ent = [], [], {}
    for l in open(man, encoding="utf-8"):
        if l.startswith("# subarbore: "): sub.append(l[13:].strip())
        elif l.startswith("# extra: "): ext.append(l[9:].strip())
        elif not l.startswith("#") and l.strip():
            h, _, r = l.rstrip("\n").partition("  ")
            ent[r] = h
    return sub, ext, ent


def check(root, man):
    sub, ext, ent = citeste(man)
    lipsa = [r for r in ent if not os.path.isfile(os.path.join(root, r))]
    rau = [r for r in ent if r not in lipsa and sha(os.path.join(root, r)) != ent[r]]
    extra = [r for r in culege(root, sub, ext) if r not in ent]
    print("nepotriviri %d | lipsa %d | extra %d | verificate %d"
          % (len(rau), len(lipsa), len(extra), len(ent) - len(lipsa)))
    for et, L in (("NEPOTRIVIRE", rau), ("LIPSA", lipsa), ("EXTRA", extra)):
        for r in L[:20]:
            print("  %-12s %s" % (et, r))
    return 1 if (rau or lipsa or extra) else 0


def selftest():
    d = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(d, "S", "date", "rmw", "cond", "rep1"))
        for n, c in (("S/date/rmw/cond/rep1/a.csv", "a"), ("S/date/rmw/cond/rep1/b.csv", "b")):
            open(os.path.join(d, n), "w").write(c)
        mp = os.path.join(d, "M")
        with open(mp, "w") as f:
            n = make(d, ["S"], [], f)
        assert n == 2, n
        assert check(d, mp) == 0, "manifest proaspat trebuie sa fie curat"
        open(os.path.join(d, "S/date/rmw/cond/rep1/a.csv"), "w").write("MODIFICAT")
        open(os.path.join(d, "S/date/rmw/cond/rep1/c.csv"), "w").write("nou")
        sub, ext, ent = citeste(mp)
        rau = [r for r in ent if sha(os.path.join(d, r)) != ent[r]]
        extra = [r for r in culege(d, sub, ext) if r not in ent]
        assert len(rau) == 1 and len(extra) == 1, (rau, extra)
        assert check(d, mp) == 1, "trebuie sa iasa 1"
        print("SELFTEST manifest_tool OK (1 nepotrivire + 1 extra detectate, exit 1).")
    finally:
        shutil.rmtree(d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("actiune", nargs="?", choices=["make", "check"])
    ap.add_argument("cai", nargs="*")
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--nume", default="C1_CANONIC", help="nume logic al radacinii, pus in antet")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); sys.exit(0)
    if a.actiune == "make":
        make(a.cai[0], a.cai[1:], a.extra, nume=a.nume); sys.exit(0)
    if a.actiune == "check":
        sys.exit(check(a.cai[0], a.cai[1]))
    ap.error("alege 'make', 'check' sau --selftest")
