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

JURNAL DE PROVENIENTA (~/DATE_CAMPANIE/netem_journal_M2.log, --journal pentru alta cale):
la FIECARE aplicare REALA si la fiecare --clear se adauga o linie
  <ISO-timestamp> <iface> <conditie|CLEAR> <comanda tc emisa>
Primele trei campuri sunt fara spatii, comanda (care contine spatii) e ULTIMA -> linia se
desface cu split(None, 3). --dry si --show NU scriu nimic in jurnal. Linia se scrie DUPA
executie si consemneaza comanda EMISA (tc ruleaza cu check=False, ca inainte); un jurnal
nescriibil da doar avertisment pe stderr, nu opreste aplicarea conditiei.

Conditiile *_burst / gilbert_* sunt INGHETATE pe HIL (corelate; in afara drumului critic A1) ->
refuzate aici, la fel ca in run_campaign.py --mode hil. Deschiderea DELIBERATA pentru C2 (GE pe
legatura fizica) se cere explicit cu --allow-corr, acelasi flag ca in run_campaign.py:
  sudo python3 hil_netem.py eth0 ge_15_8 --allow-corr"""
import argparse
import datetime
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, netem_cmd, netem_clear_cmd

JOURNAL_DEFAULT = os.path.join(os.path.expanduser("~"), "DATE_CAMPANIE",
                               "netem_journal_M2.log")


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


def main():
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
    a = ap.parse_args()
    journal = os.path.expanduser(a.journal)

    # --show inaintea oricarei ramuri de aplicare: fara el, 'hil_netem.py <iface> --show'
    # ar cadea pe ramura 'condition is None' si ar CURATA qdisc-ul in loc sa-l arate.
    if a.show:
        show(a.iface, journal)
        return

    if a.clear or a.condition is None:
        cmd = netem_clear_cmd(a.iface)
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
        cmd = netem_cmd(a.iface, c)
        label = c["name"]

    print(cmd)
    if a.dry:
        return
    subprocess.run(["sudo", "bash", "-c", cmd], check=False)
    append_journal(journal, journal_line(now_iso(), a.iface, label, cmd))


if __name__ == "__main__":
    main()
