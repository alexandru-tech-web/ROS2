#!/usr/bin/env python3
"""hil_netem.py -- aplica/curata regula tc netem a UNEI conditii pe o interfata, pentru a OGLINDI
SIMETRIC pe M2 (RPi) exact regula pe care run_campaign.py o aplica pe M1 (PC). Reutilizeaza
bench_core.netem_cmd (SURSA UNICA a regulii) -> M1 si M2 aplica regula IDENTICA per conditie,
deci pierderea round-trip ~ 1-(1-p)^2 si RTT ~ 2x one-way raman coerente cu SIL.

Folosire pe M2 (RPi), conditie cu conditie:
  sudo python3 hil_netem.py <iface> <conditie>     # ex: sudo python3 hil_netem.py eth0 loss_15
  sudo python3 hil_netem.py <iface> --clear        # curata netem la finalul conditiei
  python3 hil_netem.py <iface> <conditie> --dry    # arata comanda, NU o executa
  python3 hil_netem.py <iface> --show              # qdisc curent + 'JURNAL: <ultima linie>'

PROGRAM TEMPORIZAT (DIAG-Z2, 28.09.2026 -- reparatia A024): netem pornit si oprit la epoci FIXATE DINAINTE, de un
proces lansat INAINTE de degradare, ca driverul sa nu mai dea nicio comanda ssh prin legatura degradata:
  sudo python3 hil_netem.py <iface> <conditie> --program ON:OFF[,ON:OFF...] --eticheta <id> [--journal ...]
      ON / OFF = epoci Unix (secunde, cu zecimale); ferestrele in ordine, nesuprapuse; prima nu poate fi in trecut
      (> 1 s) si programul nu poate depasi 4 h. La fiecare ON: comenzile conditiei; la fiecare OFF: stergerea. Dupa
      FIECARE schimbare, `tc qdisc show` e scris in jurnal (linia SHOW), ca verificarea S5 sa se faca DUPA fereastra,
      din jurnal, fara ssh in timpul ei. SIGTERM / SIGINT in timpul unei ferestre -> sterge netem, apoi iese.
  sudo python3 hil_netem.py <iface> --anuleaza [--journal ...]
      opreste (SIGTERM) orice alt program temporizat inca viu (care isi sterge singur netem-ul, daca e activ).
  python3 hil_netem.py --selftest                    # verificari pure (ceas si tc falsificate), fara sudo

JURNAL DE PROVENIENTA (~/DATE_CAMPANIE/netem_journal_M2.log, --journal pentru alta cale):
la FIECARE aplicare REALA si la fiecare --clear se adauga o linie
  <ISO-timestamp> <iface> <conditie|CLEAR> <comanda tc emisa>
Primele trei campuri sunt fara spatii, comanda (care contine spatii) e ULTIMA -> linia se
desface cu split(None, 3). --dry si --show NU scriu nimic in jurnal. Linia se scrie DUPA
executie si consemneaza comanda EMISA (tc ruleaza cu check=False, ca inainte); un jurnal
nescriibil da doar avertisment pe stderr, nu opreste aplicarea conditiei.
In modul --program acelasi format, cu marca de timp la MILISECUNDA si eticheta la coada comenzii ('  # <eticheta>');
etichetele suplimentare: PROGRAM (pornire), SHOW (tc qdisc show, pe un rand), PROGRAM_GATA, PROGRAM_ANULAT, ANULEAZA.

Conditiile *_burst / gilbert_* sunt INGHETATE pe HIL (corelate; in afara drumului critic A1) ->
refuzate aici, la fel ca in run_campaign.py --mode hil. Deschiderea DELIBERATA pentru C2 (GE pe
legatura fizica) se cere explicit cu --allow-corr, acelasi flag ca in run_campaign.py:
  sudo python3 hil_netem.py eth0 ge_15_8 --allow-corr"""
import argparse
import datetime
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, netem_cmd, netem_cmds, netem_clear_cmd

JOURNAL_DEFAULT = os.path.join(os.path.expanduser("~"), "DATE_CAMPANIE",
                               "netem_journal_M2.log")
MAX_PROGRAM_S = 4 * 3600          # un program temporizat nu poate tine mai mult de 4 h
TOLERANTA_TRECUT_S = 1.0          # prima fereastra poate incepe cel mult 1 s in trecut (lansare tarzie)


def journal_line(ts_iso, iface, label, cmd):
    """Formateaza o linie de jurnal: '<ISO> <iface> <conditie|CLEAR> <comanda tc>'.
    Functie PURA (fara I/O, fara ceas) -- de aceea e testabila direct. Primele trei
    campuri nu contin spatii, comanda e ultima, deci split(None, 3) reface exact
    cele patru campuri (comanda ramane intreaga)."""
    return "%s %s %s %s" % (ts_iso, iface, label, cmd)


def now_iso():
    """Timbrul de timp al jurnalului: ISO-8601 la secunda, CU fus orar (provenienta
    pe M2 trebuie sa fie comparabila cu ceasul lui M1)."""
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def now_iso_ms():
    """Ca now_iso, dar la milisecunda: in modul --program epocile ON / OFF se compara cu cele de pe M1."""
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def append_journal(path, line):
    """Adauga o linie in jurnal (creeaza directorul parinte daca lipseste).
    Intoarce True/False; un esec NU opreste campania -- doar avertisment pe stderr."""
    try:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "a") as f:
            f.write(line + "\n")
        return True
    except OSError as e:
        print("[jurnal] AVERTISMENT: nu am putut scrie %s (%s)" % (path, e),
              file=sys.stderr)
        return False


def last_journal_line(path):
    """Ultima linie nevida din jurnal; None daca fisierul lipseste sau e gol."""
    try:
        with open(path) as f:
            lines = [ln.rstrip("\n") for ln in f if ln.strip()]
    except OSError:
        return None
    return lines[-1] if lines else None


def show(iface, journal):
    """--show: DOAR observa. Tipareste NEATINS raportul 'tc qdisc show dev <iface>'
    (nu se parseaza si nu se interpreteaza: formatul lui tc nu e contractul nostru),
    apoi o ULTIMA linie cu marker determinist -- singurul lucru pe care se sprijina
    testele si scripturile:
      JURNAL: <ultima linie de jurnal>   sau   JURNAL: GOL
    Nu aplica nimic, nu curata, nu scrie in jurnal. 'tc qdisc show' merge fara sudo."""
    tc = shutil.which("tc") or "/usr/sbin/tc"
    sys.stdout.flush()          # tc scrie direct pe fd: golim bufferul ca sa ramana in ordine
    try:
        subprocess.run([tc, "qdisc", "show", "dev", iface], check=False)
    except OSError as e:
        print("(nu am putut rula %s: %s)" % (tc, e))
    last = last_journal_line(journal)
    print("JURNAL: %s" % (last if last is not None else "GOL"), flush=True)


# ------------------------------------------------------------------ program temporizat (DIAG-Z2, A024)

def parse_program(text):
    """'ON:OFF[,ON:OFF...]' -> [(on, off)]. Functie PURA. Refuza: ON >= OFF, ferestre suprapuse sau neordonate."""
    ferestre = []
    for bucata in (text or "").split(","):
        bucata = bucata.strip()
        if not bucata:
            continue
        parti = bucata.split(":")
        if len(parti) != 2:
            raise ValueError("fereastra '%s' nu are forma ON:OFF" % bucata)
        on, off = float(parti[0]), float(parti[1])
        if not on < off:
            raise ValueError("fereastra '%s': ON trebuie sa fie inainte de OFF" % bucata)
        if ferestre and on < ferestre[-1][1]:
            raise ValueError("fereastra '%s' incepe inainte sa se termine cea precedenta" % bucata)
        ferestre.append((on, off))
    if not ferestre:
        raise ValueError("program gol")
    return ferestre


def verifica_program(ferestre, acum):
    """Garzile de timp, PURE: prima fereastra nu e (mult) in trecut, programul nu depaseste MAX_PROGRAM_S."""
    if ferestre[0][0] < acum - TOLERANTA_TRECUT_S:
        raise ValueError("prima fereastra a inceput deja de %.1f s -- programul NU porneste" % (acum - ferestre[0][0]))
    if ferestre[-1][1] - acum > MAX_PROGRAM_S:
        raise ValueError("programul s-ar termina peste %.0f s (> %d s) -- refuzat" % (ferestre[-1][1] - acum, MAX_PROGRAM_S))


def tc_show_text(iface):
    tc = shutil.which("tc") or "/usr/sbin/tc"
    try:
        p = subprocess.run([tc, "qdisc", "show", "dev", iface], capture_output=True, text=True, check=False)
        return " ".join(p.stdout.split()) or "(gol)"
    except OSError as e:
        return "(tc indisponibil: %s)" % e


def _executa_tc(cmd):
    subprocess.run(["sudo", "bash", "-c", cmd], check=False)


def ruleaza_program(iface, label, cmds, ferestre, journal, eticheta,
                    ceas=time.time, dormi=time.sleep, executa=_executa_tc, arata=None, ms=now_iso_ms):
    """Aplica 'cmds' la fiecare ON si sterge netem la fiecare OFF, cu jurnal. Injectabil (ceas, somn, tc) pentru test."""
    arata = arata or (lambda: tc_show_text(iface))
    verifica_program(ferestre, ceas())
    clear = netem_clear_cmd(iface)
    stare = {"activ": False}

    def jurnal(eticheta_linie, text):
        append_journal(journal, journal_line(ms(), iface, eticheta_linie, text))

    def sterge(motiv):
        executa(clear)
        jurnal("CLEAR", "%s  # %s %s" % (clear, eticheta, motiv))
        jurnal("SHOW", "%s %s" % (eticheta, arata()))
        stare["activ"] = False

    def la_semnal(signum, _frame):
        if stare["activ"]:
            sterge("ANULAT")
        jurnal("PROGRAM_ANULAT", "%s semnal %d" % (eticheta, signum))
        sys.exit(3)

    try:
        signal.signal(signal.SIGTERM, la_semnal)
        signal.signal(signal.SIGINT, la_semnal)
    except ValueError:
        pass                                   # nu in firul principal (doar in teste)
    jurnal("PROGRAM", "%s %s ferestre=%d pid=%d %s" % (eticheta, label, len(ferestre), os.getpid(),
                                                       ",".join("%.3f:%.3f" % w for w in ferestre)))
    for on, off in ferestre:
        dormi(max(0.0, on - ceas()))
        for cmd in cmds:
            executa(cmd)
            jurnal(label, "%s  # %s" % (cmd, eticheta))
        stare["activ"] = True
        jurnal("SHOW", "%s %s" % (eticheta, arata()))
        dormi(max(0.0, off - ceas()))
        sterge("OFF")
    jurnal("PROGRAM_GATA", eticheta)


def anuleaza_programe(journal, exclude=()):
    """SIGTERM tuturor proceselor 'hil_netem.py ... --program' in afara de acesta si parintii lui (sudo)."""
    ale_mele = {os.getpid(), os.getppid()} | set(exclude)
    oprite = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) in ale_mele:
            continue
        try:
            with open("/proc/%s/cmdline" % pid, "rb") as f:
                arg = f.read().split(b"\0")
        except OSError:
            continue
        if any(a.endswith(b"hil_netem.py") for a in arg) and b"--program" in arg:
            try:
                os.kill(int(pid), signal.SIGTERM)
                oprite.append(int(pid))
            except OSError:
                pass
    append_journal(journal, journal_line(now_iso_ms(), "-", "ANULEAZA", "oprite=%s" % (oprite or "0")))
    return oprite


def _selftest():
    rez = []

    def verifica(ok, text):
        rez.append(ok)
        print("  %s %s" % ("OK  " if ok else "PICA", text))

    verifica(parse_program("100.5:110,120:130.25") == [(100.5, 110.0), (120.0, 130.25)], "program cu doua ferestre")
    for rau, motiv in (("110:100", "ON dupa OFF"), ("100:120,110:130", "ferestre suprapuse"), ("", "program gol"),
                       ("100-120", "fara ':'")):
        try:
            parse_program(rau)
            verifica(False, "CONTROL NEGATIV (%s) acceptat" % motiv)
        except ValueError:
            verifica(True, "CONTROL NEGATIV: %s -> refuzat" % motiv)
    try:
        verifica_program([(95.0, 99.0)], 100.0)
        verifica(False, "CONTROL NEGATIV: fereastra in trecut acceptata")
    except ValueError:
        verifica(True, "CONTROL NEGATIV: prima fereastra cu 5 s in trecut -> programul NU porneste")
    # rularea, cu ceas si tc falsificate: la ON comenzile conditiei, la OFF stergerea, dupa fiecare un SHOW
    t = {"acum": 1000.0}
    executate = []

    def dormi(s):
        t["acum"] += s

    with tempfile.TemporaryDirectory() as d:
        j = os.path.join(d, "j.log")
        c = {x["name"]: x for x in CONDITIONS}["lat200_jit50_rate"]
        ruleaza_program("wlan0", "lat200_jit50_rate", netem_cmds("wlan0", c), [(1003.0, 1013.0), (1020.0, 1021.5)], j,
                        "r007", ceas=lambda: t["acum"], dormi=dormi, executa=executate.append,
                        arata=lambda: "qdisc netem 8001: root delay 200ms 50ms rate 1Gbit",
                        ms=lambda: "T%.1f" % t["acum"])
        linii = open(j).read().splitlines()
    etich = [ln.split(None, 3)[2] for ln in linii]
    verifica(etich == ["PROGRAM", "lat200_jit50_rate", "SHOW", "CLEAR", "SHOW", "lat200_jit50_rate", "SHOW", "CLEAR",
                       "SHOW", "PROGRAM_GATA"], "ordinea liniilor de jurnal: %s" % etich)
    verifica(linii[1].startswith("T1003.0 ") and linii[3].startswith("T1013.0 ") and linii[5].startswith("T1020.0 "),
             "ON la 1003, OFF la 1013, al doilea ON la 1020 (ceasul falsificat)")
    verifica(executate == [netem_cmds("wlan0", c)[0], netem_clear_cmd("wlan0")] * 2 and "rate 1000mbit" in executate[0],
             "tc executat: conditia (cu rate) si stergerea, de doua ori")
    verifica(all("# r007" in ln or " r007" in ln for ln in linii), "eticheta r007 pe fiecare linie")
    ok = all(rez)
    print("selftest hil_netem: %s (%d/%d)" % ("OK" if ok else "PICA", sum(rez), len(rez)))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv[1:]:
        sys.exit(_selftest())
    ap = argparse.ArgumentParser(description="Aplica/curata netem simetric pe M2 (vezi HIL_RUNBOOK.md).")
    ap.add_argument("iface", help="interfata reala (ex. eth0, wlan0)")
    ap.add_argument("condition", nargs="?", default=None, help="numele conditiei din bench_core.CONDITIONS")
    ap.add_argument("--clear", action="store_true", help="curata netem pe iface (in loc sa aplice o conditie)")
    ap.add_argument("--dry", action="store_true", help="arata comanda, NU o executa")
    ap.add_argument("--allow-corr", action="store_true",
                    help="permite EXPLICIT conditiile corelate (gilbert_*/bern_*/ge_*/*_burst) "
                         "pe HIL; implicit sunt refuzate (zavorul C1)")
    ap.add_argument("--show", action="store_true",
                    help="DOAR observa: qdisc-ul curent de pe iface + ultima linie de jurnal "
                         "(nu aplica, nu curata, nu scrie in jurnal)")
    ap.add_argument("--journal", default=JOURNAL_DEFAULT,
                    help="jurnalul de provenienta (implicit: %s)" % JOURNAL_DEFAULT)
    ap.add_argument("--program", default=None, help="ON:OFF[,ON:OFF...] -- netem temporizat (epoci Unix)")
    ap.add_argument("--eticheta", default="-", help="eticheta programului in jurnal (ex. run_id)")
    ap.add_argument("--anuleaza", action="store_true", help="opreste programele temporizate inca vii")
    a = ap.parse_args()
    journal = os.path.expanduser(a.journal)

    # --show inaintea oricarei ramuri de aplicare: fara el, 'hil_netem.py <iface> --show'
    # ar cadea pe ramura 'condition is None' si ar CURATA qdisc-ul in loc sa-l arate.
    if a.show:
        show(a.iface, journal)
        return
    if a.anuleaza:
        print("anulate: %s" % (anuleaza_programe(journal) or "niciunul"))
        return

    if a.clear or a.condition is None:
        if a.program:
            sys.exit("--program cere o conditie")
        cmds = [netem_clear_cmd(a.iface)]
        label = "CLEAR"
    else:
        by_name = {c["name"]: c for c in CONDITIONS}
        c = by_name.get(a.condition)
        if c is None:
            sys.exit("conditie necunoscuta: %s (stiute: %s)" % (a.condition, sorted(by_name)))
        if (c.get("type") == "gilbert" or "corr" in c) and not a.allow_corr:
            sys.exit("conditie INGHETATA pe HIL (interferenta corelata): %s. "
                     "Pe legatura fizica ruleaza doar loss_* + lat200_* "
                     "(deschidere deliberata: --allow-corr)." % a.condition)
        # netem_cmds, nu netem_cmd: o conditie cu qdisc-copil (celula de control K1,
        # lat200_jit50_pfifo) are DOUA comenzi -- radacina netem si copilul pfifo. Conditiile
        # fara copil intorc exact o comanda, identica cu cea de pana acum.
        cmds = netem_cmds(a.iface, c)
        label = c["name"]

    if a.program:
        try:
            ferestre = parse_program(a.program)
            ruleaza_program(a.iface, label, cmds, ferestre, journal, a.eticheta)
        except ValueError as e:
            append_journal(journal, journal_line(now_iso_ms(), a.iface, "PROGRAM_REFUZAT", "%s %s" % (a.eticheta, e)))
            sys.exit("program refuzat: %s" % e)
        return

    for cmd in cmds:
        print(cmd)
    if a.dry:
        return
    for cmd in cmds:
        subprocess.run(["sudo", "bash", "-c", cmd], check=False)
        append_journal(journal, journal_line(now_iso(), a.iface, label, cmd))


if __name__ == "__main__":
    main()
