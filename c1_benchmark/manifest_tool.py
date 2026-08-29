#!/usr/bin/env python3
"""manifest_tool.py -- manifest SHA256 pentru setul canonic C1.

  make <radacina> <subarbore>... [--extra <fisier>...]   scrie manifestul la stdout
  check <radacina> <MANIFEST>                            nepotriviri / lipsa / extra
  --selftest                                             pe un director temporar

Antetul poarta cifrele (cate fisiere, pe subarbore si pe tip); textul din README
trimite aici, ca sa nu existe doua locuri cu aceleasi numere. 'check' limiteaza
cautarea de 'extra' la subarborii declarati in antet.
"""
import argparse, datetime, hashlib, os, shutil, sys, tempfile


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


def descompune(rels):
    """rmw x conditie -> set de rep, daca structura <env>/date/<rmw>/<cond>/rep<N>/ o permite."""
    d = {}
    for r in rels:
        p = r.split("/")
        if len(p) >= 5 and p[1] == "date" and p[4].startswith("rep"):
            d.setdefault((p[0], p[2], p[3]), set()).add(p[4])
    return d


def make(root, subarbori, extra, ies=sys.stdout):
    rels = culege(root, subarbori, extra)
    w = ies.write
    w("# Manifest SHA256 -- set canonic C1\n")
    w("# Generat: %sZ\n" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"))
    w("# Radacina: %s\n" % root)
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
    dec = descompune(rels)
    if dec:
        w("# Celule rmw x conditie: %d; repetitii: %s\n"
          % (len(dec), ", ".join(sorted({"%s=%d" % (e, len(v)) for (e, _, _), v in dec.items()}))))
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
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); sys.exit(0)
    if a.actiune == "make":
        make(a.cai[0], a.cai[1:], a.extra); sys.exit(0)
    if a.actiune == "check":
        sys.exit(check(a.cai[0], a.cai[1]))
    ap.error("alege 'make', 'check' sau --selftest")
