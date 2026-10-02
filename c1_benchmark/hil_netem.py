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

IPTABLES TEMPORIZAT (Etapa A C3, Z17, 01.10.2026; DECIZII 01.10 Z16b (3): iptables prin acest script, fara regula
sudoers noua -- regula NOPASSWD existenta acopera 'python3 hil_netem.py *'):
  sudo python3 hil_netem.py <iface> ipt --peer <IP_M1> [--port 7447] --program ON:OFF --eticheta <id> [--journal ...]
      DROP pe fluxul router-router: in lantul propriu C3IPT, intrarea pe <iface> de la <IP_M1> spre portul local
      <port> si iesirea pe <iface> spre <IP_M1> din portul local <port> (TCP). Sesiunile locale (localhost:7447) si
      ssh-ul nu se ating. La ON: curatenie + lantul + cele doua reguli; la OFF si la SIGTERM / SIGINT: curatenia.
      Linia SHOW poarta contoarele lantului (iptables -L C3IPT -v -n -x, pe un rand).
  sudo python3 hil_netem.py <iface> --curata-ipt [--journal ...]
      sterge lantul C3IPT si salturile spre el (idempotent; folosit si de paznic).

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
import ipaddress
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
LANT_IPT = "C3IPT"                # lantul propriu (Z17): curatenia nu atinge nimic altceva din iptables
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


def ipt_cmds(iface, peer, port=7447):
    """Comenzile de aplicare (PURE): curatenie, lantul C3IPT, salturile, cele doua reguli DROP pe fluxul router-router.
    Refuza un IP invalid, un port in afara 1-65535 sau o interfata cu spatii (ValueError)."""
    ip = str(ipaddress.ip_address(peer))
    port = int(port)
    if not 0 < port < 65536:
        raise ValueError("port invalid: %s" % port)
    if not iface or any(c.isspace() for c in iface):
        raise ValueError("interfata invalida: %r" % iface)
    return [ipt_clear_cmd(),
            "iptables -N %s" % LANT_IPT,
            "iptables -I INPUT 1 -j %s" % LANT_IPT,
            "iptables -I OUTPUT 1 -j %s" % LANT_IPT,
            "iptables -A %s -i %s -s %s -p tcp --dport %d -j DROP" % (LANT_IPT, iface, ip, port),
            "iptables -A %s -o %s -d %s -p tcp --sport %d -j DROP" % (LANT_IPT, iface, ip, port)]


def ipt_clear_cmd():
    """Curatenia, IDEMPOTENTA (PURA): scoate toate salturile spre lant, il goleste si il sterge; nu esueaza niciodata."""
    return ("while iptables -D INPUT -j {l} 2>/dev/null; do :; done; "
            "while iptables -D OUTPUT -j {l} 2>/dev/null; do :; done; "
            "iptables -F {l} 2>/dev/null; iptables -X {l} 2>/dev/null; true").format(l=LANT_IPT)


def ipt_show_text():
    """Contoarele lantului, pe un rand (merge doar ca root; altfel textul erorii)."""
    try:
        p = subprocess.run(["iptables", "-L", LANT_IPT, "-v", "-n", "-x"], capture_output=True, text=True, check=False)
        return " ".join((p.stdout or p.stderr).split()) or "(gol)"
    except OSError as e:
        return "(iptables indisponibil: %s)" % e


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
                    ceas=time.time, dormi=time.sleep, executa=_executa_tc, arata=None, ms=now_iso_ms, clear=None,
                    arata_pre_off=None):
    """Aplica 'cmds' la fiecare ON si sterge la fiecare OFF (implicit netem; Z17: 'clear' dat = alta curatenie, ex.
    iptables), cu jurnal. Injectabil (ceas, somn, executie) pentru test. Z17 (revizia B, B1): 'arata_pre_off' dat ->
    o linie SHOW_PRE_OFF INAINTE de curatenie (la ipt: contoarele DROP, care la ON sunt 0 si dupa OFF dispar)."""
    arata = arata or (lambda: tc_show_text(iface))
    verifica_program(ferestre, ceas())
    clear = clear or netem_clear_cmd(iface)
    stare = {"activ": False}

    def jurnal(eticheta_linie, text):
        append_journal(journal, journal_line(ms(), iface, eticheta_linie, text))

    def sterge(motiv):
        if arata_pre_off is not None:
            jurnal("SHOW_PRE_OFF", "%s %s" % (eticheta, arata_pre_off()))
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
    # Z17: iptables temporizat
    c_ipt = ipt_cmds("wlan0", "192.168.100.14", 7447)
    verifica(c_ipt[0] == ipt_clear_cmd() and c_ipt[1:] == [
        "iptables -N C3IPT", "iptables -I INPUT 1 -j C3IPT", "iptables -I OUTPUT 1 -j C3IPT",
        "iptables -A C3IPT -i wlan0 -s 192.168.100.14 -p tcp --dport 7447 -j DROP",
        "iptables -A C3IPT -o wlan0 -d 192.168.100.14 -p tcp --sport 7447 -j DROP"],
        "ipt: curatenie, lant C3IPT, salturi, DROP doar pe fluxul router-router (wlan0, IP-ul M1, TCP 7447, ambele sensuri)")
    for args, motiv in ((("wlan0", "192.168.100", 7447), "IP incomplet"), (("wlan0", "192.168.100.14", 0), "port 0"),
                        (("wlan0", "192.168.100.14", 70000), "port > 65535"), (("wlan 0", "192.168.100.14", 7447),
                                                                              "interfata cu spatiu")):
        try:
            ipt_cmds(*args)
            verifica(False, "CONTROL NEGATIV (%s) acceptat" % motiv)
        except ValueError:
            verifica(True, "CONTROL NEGATIV: ipt cu %s -> refuzat" % motiv)
    cl = ipt_clear_cmd()
    verifica(cl.endswith("; true") and cl.count("while iptables -D") == 2 and "-X C3IPT" in cl and "INPUT -F" not in cl
             and "-F INPUT" not in cl and "-F OUTPUT" not in cl,
             "curatenia ipt e idempotenta (bucle + 'true') si atinge DOAR lantul C3IPT (nu goleste INPUT / OUTPUT)")
    t["acum"] = 2000.0
    executate[:] = []
    with tempfile.TemporaryDirectory() as d:
        j = os.path.join(d, "j.log")
        ruleaza_program("wlan0", "ipt", c_ipt, [(2003.0, 2050.0)], j, "r011", ceas=lambda: t["acum"], dormi=dormi,
                        executa=executate.append, arata=lambda: "Chain C3IPT 2 references pkts 512 DROP",
                        ms=lambda: "T%.1f" % t["acum"], clear=cl, arata_pre_off=lambda: "C3IPT 41 2460 DROP 9 540 DROP")
        linii = open(j).read().splitlines()
    etich = [ln.split(None, 3)[2] for ln in linii]
    verifica(executate == c_ipt + [cl] and etich == ["PROGRAM"] + ["ipt"] * 6 + ["SHOW", "SHOW_PRE_OFF", "CLEAR", "SHOW",
                                                                               "PROGRAM_GATA"]
             and linii[1].startswith("T2003.0 ") and linii[9].startswith("T2050.0 ") and "pkts 512" in linii[7]
             and "41 2460 DROP" in linii[8],
             "program ipt: la ON cele 6 comenzi, SHOW; la OFF intai SHOW_PRE_OFF cu contoarele DROP (revizia B, B1), apoi "
             "curatenia ipt (NU stergerea netem)")
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
    ap.add_argument("--peer", default=None, help="ipt: IP-ul lui M1 (capatul router-router)")
    ap.add_argument("--port", type=int, default=7447, help="ipt: portul routerului de pe Pi (implicit 7447)")
    ap.add_argument("--curata-ipt", action="store_true", help="sterge lantul C3IPT si salturile (idempotent)")
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
    if a.curata_ipt:
        cl = ipt_clear_cmd()
        if not a.dry:
            subprocess.run(["sudo", "bash", "-c", cl], check=False)
            append_journal(journal, journal_line(now_iso_ms(), a.iface, "CLEAR_IPT", cl))
        print(cl)
        return
    if a.condition == "ipt":
        if not a.peer or not a.program:
            sys.exit("ipt cere --peer <IP_M1> si --program ON:OFF")
        try:
            cmds = ipt_cmds(a.iface, a.peer, a.port)
            if a.dry:
                print("\n".join(cmds + [ipt_clear_cmd()]))
                return
            ferestre = parse_program(a.program)
            ruleaza_program(a.iface, "ipt", cmds, ferestre, journal, a.eticheta, arata=ipt_show_text,
                            clear=ipt_clear_cmd(), arata_pre_off=ipt_show_text)
        except ValueError as e:
            append_journal(journal, journal_line(now_iso_ms(), a.iface, "PROGRAM_REFUZAT", "%s %s" % (a.eticheta, e)))
            sys.exit("program ipt refuzat: %s" % e)
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
