#!/usr/bin/env python3
"""test_c2_conditions.py -- selftest PUR PYTHON pentru conditiile C2 (fara ROS,
fara retea). Reconstruieste comanda netem pentru FIECARE conditie noua prin
ramura 'gilbert' EXISTENTA din bench_core.netem_cmd si verifica:
  1. (p, r) stocate == tabelul din c2_planning/CALIBRARE_GE_C2.md;
  2. comanda netem la formatul EXACT de afisare (netem_cmd, %.3f);
  3. rata medie implicita L=p/(p+r) si lungimea rafalei B=1/r == tinta grilei.
  4. zavorul HIL din hil_netem.py: ge_15_8 REFUZATA implicit, PERMISA cu --allow-corr
     (subproces cu --dry -- nu se atinge tc si nu e nevoie de sudo);
  5. jurnalul de provenienta din hil_netem.py: formatarea liniei (functie pura),
     append/citire pe fisiere TEMPORARE, --dry care nu scrie, --show care doar observa.
Rulare: python3 test_c2_conditions.py
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, netem_cmd

IFACE = "IFACE"

# Tabelul de referinta, transcris din c2_planning/CALIBRARE_GE_C2.md:
#   name -> (p, r, L_target, B_target)
# bern_L: Bernoulli via gemodel r=1-p (B_target ~ 1/(1-L), aprox 1). B tinta = None
#   (nu se verifica exact; se verifica L). ge_L_B: r=1/B, p=L/(B*(1-L)).
REF = {
    "bern_5":  (0.05,     0.95,     0.05, None),
    "bern_15": (0.15,     0.85,     0.15, None),
    "bern_30": (0.30,     0.70,     0.30, None),
    "ge_5_3":  (0.017544, 0.333333, 0.05, 3),
    "ge_5_8":  (0.006579, 0.125,    0.05, 8),
    "ge_15_3": (0.058824, 0.333333, 0.15, 3),
    "ge_15_8": (0.022059, 0.125,    0.15, 8),
    "ge_30_3": (0.142857, 0.333333, 0.30, 3),
    "ge_30_8": (0.053571, 0.125,    0.30, 8),
}


def expected_cmd(p, r):
    """Comanda asteptata, la formatul de afisare al ramurii gilbert (%.3f)."""
    return ("tc qdisc replace dev %s root netem delay 0ms 0ms "
            "loss gemodel %.3f%% %.3f%% 100%% 0%%" % (IFACE, 100 * p, 100 * r))


def check_hil_gate(fails):
    """Zavorul HIL pe hil_netem.py, verificat pe conditia C2 ge_15_8, cu --dry
    (comanda e doar AFISATA -- fara tc, fara sudo, fara retea):
      a) fara --allow-corr  -> REFUZ (cod de iesire != 0, mesaj 'INGHETATA');
      b) cu   --allow-corr  -> cod 0 si comanda gemodel EXACT ca netem_cmd."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hil_netem.py")
    base = [sys.executable, script, IFACE, "ge_15_8", "--dry"]
    exp = expected_cmd(*REF["ge_15_8"][:2])

    blocat = subprocess.run(base, capture_output=True, text=True)
    if blocat.returncode == 0:
        fails.append("hil_netem ge_15_8 FARA --allow-corr: ar fi trebuit sa refuze "
                     "(cod 0, stdout: %r)" % blocat.stdout.strip())
    if "INGHETATA" not in (blocat.stdout + blocat.stderr):
        fails.append("hil_netem ge_15_8 FARA --allow-corr: lipseste motivul 'INGHETATA' "
                     "(stderr: %r)" % blocat.stderr.strip())
    if exp in blocat.stdout:
        fails.append("hil_netem ge_15_8 FARA --allow-corr: a emis totusi comanda netem")

    permis = subprocess.run(base + ["--allow-corr"], capture_output=True, text=True)
    if permis.returncode != 0:
        fails.append("hil_netem ge_15_8 CU --allow-corr: cod %d (stderr: %r)"
                     % (permis.returncode, permis.stderr.strip()))
    got = permis.stdout.strip()
    if got != exp:
        fails.append("hil_netem ge_15_8 CU --allow-corr: cmd\n    got: %s\n    exp: %s"
                     % (got, exp))
    return exp


def check_journal(fails):
    """Jurnalul de provenienta din hil_netem.py, pe fisiere TEMPORARE (NU se atinge
    ~/DATE_CAMPANIE):
      a) journal_line = formatul cerut, iar comanda tc (cu spatii) ramane INTREAGA
         la split(None, 3);
      b) append_journal creeaza directorul lipsa si adauga la coada; last_journal_line
         intoarce ultima linie (None pe jurnal inexistent);
      c) --dry NU scrie in jurnal;
      d) --show iese cu cod 0, emite EXACT o linie 'JURNAL: ...' si lasa jurnalul
         neatins (deci nici nu curata qdisc-ul, cum ar fi facut ramura 'condition is
         None'). Textul lui tc NU se verifica -- formatul lui nu e contractul nostru."""
    import tempfile
    from hil_netem import (append_journal, journal_line, last_journal_line)

    cmd = expected_cmd(*REF["ge_15_8"][:2])
    ts = "2026-08-02T12:34:56+03:00"
    # a) format exact + reversibilitate
    got = journal_line(ts, "eth0", "ge_15_8", cmd)
    exp = "%s eth0 ge_15_8 %s" % (ts, cmd)
    if got != exp:
        fails.append("journal_line: \n    got: %s\n    exp: %s" % (got, exp))
    campuri = got.split(None, 3)
    if campuri != [ts, "eth0", "ge_15_8", cmd]:
        fails.append("journal_line: split(None,3) nu reface campurile: %r" % (campuri,))
    clear = journal_line(ts, "wlan0", "CLEAR", "tc qdisc del dev wlan0 root")
    if clear.split(None, 3)[2] != "CLEAR":
        fails.append("journal_line: eticheta CLEAR pierduta: %r" % clear)

    tmp = tempfile.mkdtemp()
    jp = os.path.join(tmp, "subdir_inexistent", "netem_journal_M2.log")
    # b) jurnal inexistent -> None; append creeaza directorul; ultima linie = ultima scrisa
    if last_journal_line(jp) is not None:
        fails.append("last_journal_line pe jurnal inexistent: ar trebui None")
    if not append_journal(jp, got) or not append_journal(jp, clear):
        fails.append("append_journal a esuat pe cale temporara %s" % jp)
    if last_journal_line(jp) != clear:
        fails.append("last_journal_line != ultima linie adaugata (%r)" % last_journal_line(jp))
    with open(jp) as f:
        randuri = [ln.rstrip("\n") for ln in f]
    if randuri != [got, clear]:
        fails.append("jurnalul nu s-a scris in ordine append: %r" % (randuri,))

    # c) --dry nu scrie in jurnal (jurnal separat, care nu trebuie sa apara)
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hil_netem.py")
    jdry = os.path.join(tmp, "jurnal_dry.log")
    subprocess.run([sys.executable, script, IFACE, "ge_15_8", "--dry", "--allow-corr",
                    "--journal", jdry], capture_output=True, text=True)
    if os.path.exists(jdry):
        fails.append("--dry a scris in jurnal (%s ar trebui sa nu existe)" % jdry)

    # d) --show: doar observa. Pe 'lo', 'tc qdisc show' e read-only si merge fara sudo.
    # Se verifica DOAR markerul determinist, codul de iesire si jurnalul neatins;
    # raportul lui tc se tipareste ca atare si NU se parseaza.
    inainte = open(jp, "rb").read()
    r = subprocess.run([sys.executable, script, "lo", "--show", "--journal", jp],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("--show pe lo: cod %d (stderr: %r)" % (r.returncode, r.stderr.strip()))
    marker = [ln for ln in r.stdout.splitlines() if ln.startswith("JURNAL:")]
    if len(marker) != 1:
        fails.append("--show: astept EXACT o linie 'JURNAL:', am %d (stdout: %r)"
                     % (len(marker), r.stdout))
    elif marker[0] != "JURNAL: %s" % clear:
        fails.append("--show: markerul nu poarta ultima linie de jurnal\n"
                     "    got: %s\n    exp: JURNAL: %s" % (marker[0], clear))
    if open(jp, "rb").read() != inainte:
        fails.append("--show a modificat jurnalul")
    # jurnal inexistent -> marker 'JURNAL: GOL', si tot nu se creeaza fisierul
    jgol = os.path.join(tmp, "inexistent.log")
    rg = subprocess.run([sys.executable, script, "lo", "--show", "--journal", jgol],
                        capture_output=True, text=True)
    if "JURNAL: GOL" not in rg.stdout.splitlines():
        fails.append("--show pe jurnal inexistent: astept 'JURNAL: GOL' (stdout: %r)"
                     % rg.stdout)
    if os.path.exists(jgol):
        fails.append("--show a creat jurnalul (%s ar trebui sa nu existe)" % jgol)
    shutil.rmtree(tmp, ignore_errors=True)


def run():
    by_name = {c["name"]: c for c in CONDITIONS}
    checks = 0
    fails = []
    for name, (p, r, L_t, B_t) in REF.items():
        if name not in by_name:
            fails.append("%s: LIPSA din CONDITIONS" % name); continue
        c = by_name[name]
        # 1. (p, r) stocate == referinta
        if c.get("p") != p or c.get("r") != r:
            fails.append("%s: (p,r)=(%s,%s) != ref (%s,%s)"
                         % (name, c.get("p"), c.get("r"), p, r))
        # 2. comanda netem la formatul exact
        got = netem_cmd(IFACE, c)
        exp = expected_cmd(p, r)
        if got != exp:
            fails.append("%s: cmd\n    got: %s\n    exp: %s" % (name, got, exp))
        # 3. L si B implicite == tinta
        L = p / (p + r)
        if abs(L - L_t) > 0.003:            # 0.3 pp toleranta pe rata medie
            fails.append("%s: L=%.4f != tinta %.2f" % (name, L, L_t))
        if B_t is not None:
            B = 1.0 / r
            if abs(B - B_t) > 0.01:
                fails.append("%s: B=%.3f != tinta %d" % (name, B, B_t))
        checks += 1
    # 3b. combo lat200_jit50_ge_15_8: delay 200ms 50ms + gemodel ge_15_8 SIMULTAN
    combo = by_name.get("lat200_jit50_ge_15_8")
    if not combo:
        fails.append("lat200_jit50_ge_15_8 LIPSA din CONDITIONS")
    else:
        exp = ("tc qdisc replace dev %s root netem delay 200ms 50ms "
               "loss gemodel 2.206%% 12.500%% 100%% 0%%" % IFACE)
        got = netem_cmd(IFACE, combo)
        if got != exp:
            fails.append("combo: cmd\n    got: %s\n    exp: %s" % (got, exp))
        if combo.get("p") != 0.022059 or combo.get("r") != 0.125:
            fails.append("combo: (p,r) != ge_15_8")
        if combo.get("base_ms") != 200 or combo.get("jitter_ms") != 50:
            fails.append("combo: delay/jitter != 200/50")
        checks += 1
    # 4. bench_core NU a fost stricat: gilbert_* / lat200_* raman
    for must in ("ideal", "gilbert_20", "lat200_jit50", "lat200_l15"):
        if must not in by_name:
            fails.append("REGRES: %s a disparut din CONDITIONS" % must)
    # 5. B=1 corect ELIMINAT (nu exista ge_*_1)
    if any(n.startswith("ge_") and n.endswith("_1") for n in by_name):
        fails.append("B=1 ar fi trebuit eliminat, dar exista o ge_*_1")
    # 6. zavorul HIL: refuz implicit / deschidere deliberata cu --allow-corr
    hil_cmd = check_hil_gate(fails)
    # 7. jurnalul de provenienta (formatare + append/last + --dry/--show)
    check_journal(fails)

    if fails:
        print("FAIL (%d/%d conditii verificate):" % (checks, len(REF)))
        for f in fails:
            print("  - " + f)
        return 1
    print("SELFTEST C2 OK: %d conditii verificate (p,r + comanda netem + L,B)." % checks)
    print("ZAVOR HIL OK: hil_netem.py refuza ge_15_8 implicit; cu --allow-corr emite")
    print("  %s" % hil_cmd)
    print("JURNAL OK: linie '<ISO> <iface> <cond|CLEAR> <cmd>' reversibila la split(None,3);")
    print("  append/last pe cale temporara; --dry nu scrie; --show doar observa (marker JURNAL:).")
    print("Comenzi reconstruite (format campanie netem_cmd, %.3f):")
    for name in REF:
        print("  %-8s %s" % (name, netem_cmd(IFACE, by_name[name])))
    return 0


if __name__ == "__main__":
    sys.exit(run())
