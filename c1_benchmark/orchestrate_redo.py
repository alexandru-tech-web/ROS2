#!/usr/bin/env python3
"""orchestrate_redo.py -- ORCHESTRATOR pentru redo-urile zenoh HIL, rulat pe M1 (laptop).

Automatizeaza LANTUL MANUAL rulat per conditie (repornire router Pi + router M1 + ecou
zenoh, porti de verificare, netem pe M2, monitor, driverul campaniei, audit), ca sa nu mai
depinda de retastare corecta la ora 2 noaptea. NU inventeaza pasi noi: fiecare comanda e
cea din blocul manual, tiparita inainte de executie si scrisa in jurnalul orchestratorului.

  python3 orchestrate_redo.py ge_5_8 ge_15_3        # conditii literale, in ordine
  python3 orchestrate_redo.py --all                 # cele 6 conditii de redo
  python3 orchestrate_redo.py --all --dry           # tipareste TOT, executa NIMIC
  python3 orchestrate_redo.py ge_15_8 --no-pause    # fara ENTER intre conditii
  python3 orchestrate_redo.py --selftest            # doar functiile pure

CE NU FACE (deliberat):
  - NU sigileaza datele (chmod a-w) si NU scrie in jurnalul de sesiune: sigiliul si
    jurnalul raman gesturi UMANE, dupa ce omul se uita la audit.
  - NU atinge stratul cyclonedds: ecoul CDDS de pe M2 e selectat pe dinafara (vezi
    ENVIRON_MARKER) tocmai ca sa NU fie omorat.
  - NU modifica run_campaign.py / bench_client.py / bench_echo_server.py (protocol
    INGHETAT mid-campanie): le apeleaza doar ca pe niste binare.

PORTI (fiecare oprire e un ABORT cu mesaj despre CE s-a rupt si CE sa verifice omul):
  1. routerul Pi a pornit    -- logul contine 'reached at'
  2. routerul M1 a pornit    -- logul contine 'reached at'
  3. sesiunea s-a atasat     -- pe M2: pereche loopback [::1]:7447 (ecoul <-> router local)
                                SI o linie cu 192.168.100.14 (M1 <-> router M2)
  4. netem aplicat pe M2     -- hil_netem.py iese cu 0 (altfel conditia NU e aplicata si
                                rularea ar fi invalida, deci nu se porneste driverul)
  5. driverul a terminat 0   -- run_campaign.py sub 'set -o pipefail' (tee nu mascheaza codul)

COMENZI REMOTE: shell-ul ssh non-interactiv NU are ROS in mediu, de aceea fiecare comanda
remota e completa: ssh PI 'bash -lc "export ROS_DOMAIN_ID=7 && export RMW_IMPLEMENTATION=
rmw_zenoh_cpp && source ~/ros2_ws/install/setup.bash && ..."'. In interiorul ghilimelelor
duble, '$' e ESCAPAT (\\$) pentru ca substitutia sa se faca in bash -lc de pe Pi, nu in
shell-ul care primeste comanda ssh (verificat: fara escapare, $p ajunge gol).
"""
import argparse
import datetime
import os
import signal
import subprocess
import sys
import time

# ------------------------------------------------------------------ constante
PI = "ubuntu@192.168.100.19"
IP_PI = "192.168.100.19"
IP_M1 = "192.168.100.14"
IFACE_M1 = "wlp4s0"
IFACE_PI = "wlan0"
PORT = 7447
ROS_DOMAIN = 7

HOME = os.path.expanduser("~")
ARCH = os.path.join(HOME, "DATE_CAMPANIE", "C2_HIL_WIFI_20260801")
# logurile routerului M1 au mers aici in lantul manual de azi (nu in ARCH):
LOGDIR_M1 = os.path.join(HOME, "DATE_CAMPANIE", "C2_HIL_SMOKE")
# cale REMOTA (se expandeaza pe Pi, deci ramane cu tilde):
LOGDIR_PI = "~/DATE_CAMPANIE/C2_HIL_WIFI_20260801_pi"

SRC_M1 = os.path.join(HOME, "ros2_ws", "src", "c1_benchmark")
SRC_M1_C2 = os.path.join(HOME, "ros2_ws", "src", "c2_analysis")
SRC_PI = "/home/ubuntu/ros2_ws/src/c1_benchmark"    # cale absoluta, ca in blocul manual

COND_ALL = ["ge_5_8", "ge_15_3", "ge_15_8", "bern_30", "ge_30_3", "ge_30_8"]

# Criteriul de selectie a ecoului ZENOH de pe M2. Se cere potrivire EXACTA pe variabila,
# nu substring 'rmw_zenoh_cpp': daca workspace-ul de pe Pi are rmw_zenoh_cpp construit din
# surse, substringul apare si in AMENT_PREFIX_PATH/LD_LIBRARY_PATH al ecoului CDDS -- si
# l-am omori exact pe cel care nu trebuie atins.
ENVIRON_MARKER = "RMW_IMPLEMENTATION=rmw_zenoh_cpp"

STARI_SS = ("ESTAB", "SYN-SENT", "SYN-RECV", "FIN-WAIT-1", "FIN-WAIT-2", "TIME-WAIT",
            "CLOSE-WAIT", "LAST-ACK", "LISTEN", "CLOSING", "UNCONN", "CLOSED")


class Abort(Exception):
    """Poarta picata: mesajul spune CE s-a rupt, 'verifica' spune ce se uita omul."""

    def __init__(self, poarta, mesaj, verifica):
        Exception.__init__(self, mesaj)
        self.poarta = poarta
        self.mesaj = mesaj
        self.verifica = verifica


# ------------------------------------------------------- functii PURE (testate)
def prefix_ros():
    """Preambulul mediului ROS pentru orice comanda remota (shell ssh non-interactiv)."""
    return ("export ROS_DOMAIN_ID=%d && export RMW_IMPLEMENTATION=rmw_zenoh_cpp"
            " && source ~/ros2_ws/install/setup.bash" % ROS_DOMAIN)


def ssh_payload(inner):
    """Argumentul unic dat lui ssh: bash -lc \"<inner>\", cu '$' escapat pentru stratul
    de shell care despacheteaza comanda pe Pi."""
    return 'bash -lc "%s"' % inner.replace("$", "\\$")


def ssh_argv(inner, gazda=PI):
    return ["ssh", gazda, ssh_payload(inner)]


def ssh_display(inner, gazda=PI):
    """Forma exact copiabila in terminal (ghilimele simple in jurul payload-ului)."""
    return "ssh %s '%s'" % (gazda, ssh_payload(inner))


def cmd_selectie_ecou_zenoh(proc_root="/proc", sursa_pids="pgrep -f bench_echo_server",
                            actiune="kill"):
    """Omoara DOAR ecoul zenoh de pe M2: pentru fiecare pid de bench_echo_server se citeste
    <proc_root>/<pid>/environ (NUL-separat, de aceea 'grep -z') si se actioneaza numai daca
    are EXACT variabila ENVIRON_MARKER ('-x' ancoreaza pe tot recordul). Ecoul CDDS ramane
    viu. Parametrii exista ca selftestul sa poata rula ACEEASI comanda pe un /proc fals,
    cu actiune inofensiva."""
    return ("for p in $(%s); do grep -qzx %s %s/$p/environ 2>/dev/null && %s $p; done"
            % (sursa_pids, ENVIRON_MARKER, proc_root, actiune))


def log_router_pi(cond):
    return "%s/zenoh_router_pi_redo_%s.log" % (LOGDIR_PI, cond)


def log_ecou_pi(cond):
    return "%s/echo_zenoh_redo_%s.log" % (LOGDIR_PI, cond)


def log_router_m1(cond):
    return os.path.join(LOGDIR_M1, "zenoh_router_m1_redo_%s.log" % cond)


def console_m1(cond):
    return os.path.join(ARCH, "console_%s_zenohredo.log" % cond)


def monitor_csv(cond):
    return os.path.join(ARCH, "monitor_%s_redo.csv" % cond)


def cmd_curat_pi():
    """Pi: omoara routerul si DOAR ecoul zenoh, apoi curata memoria partajata zenoh."""
    return ("pkill -f rmw_zenohd; %s; rm -f /dev/shm/*zenoh*"
            % cmd_selectie_ecou_zenoh())


def cmd_curat_m1():
    return "pkill -f rmw_zenohd ; rm -f /dev/shm/*zenoh*"


def cmd_router_pi(cond):
    return ("%s && export RUST_LOG=info"
            " && export ZENOH_ROUTER_CONFIG_URI=~/ros2_ws/src/c1_benchmark/router_pi.json5"
            " && mkdir -p %s"
            " && nohup ros2 run rmw_zenoh_cpp rmw_zenohd > %s 2>&1 </dev/null &"
            % (prefix_ros(), LOGDIR_PI, log_router_pi(cond)))


def cmd_router_m1(cond):
    return ("%s && export RUST_LOG=info"
            " && export ZENOH_ROUTER_CONFIG_URI=~/ros2_ws/src/c1_benchmark/router_m1.json5"
            " && mkdir -p %s"
            " && nohup ros2 run rmw_zenoh_cpp rmw_zenohd > %s 2>&1 </dev/null &"
            % (prefix_ros(), LOGDIR_M1, log_router_m1(cond)))


def cmd_ecou_pi(cond):
    return ("%s && mkdir -p %s"
            " && nohup python3 %s/bench_echo_server.py > %s 2>&1 </dev/null &"
            % (prefix_ros(), LOGDIR_PI, SRC_PI, log_ecou_pi(cond)))


def cmd_poarta_log(cale):
    """Poarta 'a pornit routerul': 'reached at' din logul zenoh. Punctul din regex tine
    locul spatiului, ca sa nu fie nevoie de ghilimele in interiorul payload-ului."""
    return "grep -cE reached.at %s" % cale


def cmd_ss_pi():
    return "ss -tn | grep %d" % PORT


def cmd_netem_pi(cond):
    return ("sudo -n python3 %s/hil_netem.py %s %s --allow-corr"
            % (SRC_PI, IFACE_PI, cond))


def cmd_netem_show_pi():
    return "sudo -n python3 %s/hil_netem.py %s --show" % (SRC_PI, IFACE_PI)


def cmd_driver(cond):
    """Driverul campaniei, cu tee ca in blocul manual. 'set -o pipefail' e adaugat ca sa
    conteze codul lui run_campaign.py, nu al lui tee (altfel poarta 5 ar fi decorativa)."""
    return ("set -o pipefail; python3 %s/run_campaign.py --mode hil --iface %s --reps 10"
            " --rmws zenoh --conditions %s --layers transport --allow-corr --out %s"
            " 2>&1 | tee %s"
            % (SRC_M1, IFACE_M1, cond, ARCH, console_m1(cond)))


def cmd_audit():
    return "python3 %s/audit_campanie.py %s" % (SRC_M1_C2, ARCH)


def parse_ss(text, port=PORT, ip_m1=IP_M1):
    """Poarta de atasare, din iesirea 'ss -tn | grep <port>' rulata pe M2.
    Cere DOUA lucruri simultan:
      - o pereche loopback [::1]:<port>  = ecoul zenoh e atasat la routerul LOCAL de pe M2;
      - o linie cu IP-ul lui M1          = M1 e conectat la routerul de pe M2.
    Functie pura (text -> verdict), de aceea se testeaza fara retea."""
    active = []
    for linie in text.splitlines():
        t = linie.split()
        if not t or str(port) not in linie:
            continue
        if t[0] in ("State", "Recv-Q"):                 # antet
            continue
        if t[0] in STARI_SS and t[0] != "ESTAB":        # LISTEN/TIME-WAIT etc.
            continue
        active.append(linie)
    loopback = [l for l in active if "[::1]" in l]
    m1 = [l for l in active if ip_m1 in l]
    motive = []
    if not loopback:
        motive.append("nicio pereche loopback [::1]:%d pe M2 -- ecoul zenoh nu s-a atasat "
                      "la routerul local" % port)
    if not m1:
        motive.append("nicio linie cu %s -- M1 nu e conectat la routerul de pe M2" % ip_m1)
    return {"active": len(active), "loopback": len(loopback), "m1": len(m1),
            "ok": not motive, "motive": motive}


def filtreaza_audit(text, cond):
    """Din iesirea audit_campanie.py pastreaza antetul (titlu + cap de tabel + linia de
    separare) si DOAR randurile conditiei cerute."""
    out = []
    for linie in text.splitlines():
        t = linie.split()
        if linie.startswith("==") or linie.startswith("conditie") or set(linie.strip()) == {"-"}:
            out.append(linie)
        elif t and t[0] == cond:
            out.append(linie)
    return "\n".join(out)


# --------------------------------------------------------------- infrastructura
class Jurnal(object):
    """Tot ce face scriptul, cu timbru de timp, pe ecran SI in ARCH/orchestrator_*.log."""

    def __init__(self, cale=None):
        self.cale = cale
        self.f = open(cale, "a") if cale else None

    def scrie(self, text, prefix="  "):
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        for linie in str(text).splitlines() or [""]:
            randul = "%s %s%s" % (stamp, prefix, linie)
            print(randul, flush=True)
            if self.f:
                self.f.write(randul + "\n")
        if self.f:
            self.f.flush()

    def titlu(self, text):
        self.scrie(text, prefix="")

    def cmd(self, display):
        self.scrie(display, prefix="$ ")

    def inchide(self):
        if self.f:
            self.f.close()
            self.f = None


def ruleaza(jur, argv, display, dry, capture=False, timeout=None):
    """Tipareste comanda EXACT cum ar rula, apoi (daca nu e --dry) o executa.
    Intoarce (cod, iesire). In --dry: (0, '')."""
    jur.cmd(display)
    if dry:
        return 0, ""
    try:
        r = subprocess.run(argv, capture_output=capture, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Abort("timeout", "comanda a depasit %ss: %s" % (timeout, display),
                    "verifica daca Pi-ul raspunde: ping %s ; ssh %s true" % (IP_PI, PI))
    except OSError as e:
        raise Abort("executie", "nu am putut rula: %s (%s)" % (display, e),
                    "verifica daca binarul exista si e in PATH")
    iesire = (r.stdout or "") if capture else ""
    if iesire.strip():
        jur.scrie(iesire.strip(), prefix="  | ")
    return r.returncode, iesire


def asteapta(jur, secunde, dry):
    jur.scrie("sleep %g" % secunde, prefix="$ ")
    if not dry:
        time.sleep(secunde)


# ------------------------------------------------------------------- lantul
def ruleaza_conditie(jur, cond, dry):
    """Lantul complet pentru o conditie. Ridica Abort la prima poarta picata."""
    jur.titlu("")
    jur.titlu("=============== CONDITIA %s ===============" % cond)
    monitor = None
    try:
        # 1. local: deblocheaza datele vechi ale conditiei (daca au fost sigilate)
        vechi = os.path.join(ARCH, "zenoh", cond)
        if dry or os.path.isdir(vechi):
            ruleaza(jur, ["chmod", "-R", "u+w", vechi],
                    "chmod -R u+w %s" % vechi, dry)
        else:
            jur.scrie("(fara date vechi pentru %s: %s nu exista)" % (cond, vechi))

        # 2. Pi: router jos + DOAR ecoul zenoh jos + shm zenoh curatat
        ruleaza(jur, ssh_argv(cmd_curat_pi()), ssh_display(cmd_curat_pi()), dry, timeout=60)
        # 3. M1: router jos + shm zenoh curatat
        ruleaza(jur, ["bash", "-lc", cmd_curat_m1()],
                'bash -lc "%s"' % cmd_curat_m1(), dry)

        # 4. Pi: routerul sus + POARTA 'reached at'
        ruleaza(jur, ssh_argv(cmd_router_pi(cond)), ssh_display(cmd_router_pi(cond)),
                dry, timeout=60)
        asteapta(jur, 3, dry)
        cod, _ = ruleaza(jur, ssh_argv(cmd_poarta_log(log_router_pi(cond))),
                         ssh_display(cmd_poarta_log(log_router_pi(cond))),
                         dry, capture=True, timeout=60)
        if cod != 0:
            raise Abort("1 (router Pi)",
                        "logul routerului de pe M2 nu contine 'reached at'",
                        "pe Pi: tail -30 %s ; verifica ZENOH_ROUTER_CONFIG_URI si daca "
                        "portul %d e liber (ss -tln | grep %d)"
                        % (log_router_pi(cond), PORT, PORT))

        # 5. M1: routerul sus + POARTA 'reached at'
        ruleaza(jur, ["bash", "-lc", cmd_router_m1(cond)],
                'bash -lc "%s"' % cmd_router_m1(cond), dry)
        asteapta(jur, 3, dry)
        cod, _ = ruleaza(jur, ["bash", "-lc", cmd_poarta_log(log_router_m1(cond))],
                         'bash -lc "%s"' % cmd_poarta_log(log_router_m1(cond)),
                         dry, capture=True)
        if cod != 0:
            raise Abort("2 (router M1)",
                        "logul routerului de pe M1 nu contine 'reached at'",
                        "local: tail -30 %s ; verifica router_m1.json5 si portul %d"
                        % (log_router_m1(cond), PORT))

        # 6. Pi: ecoul zenoh sus
        ruleaza(jur, ssh_argv(cmd_ecou_pi(cond)), ssh_display(cmd_ecou_pi(cond)),
                dry, timeout=60)
        asteapta(jur, 2, dry)

        # 7. POARTA de atasare (loopback pe M2 + M1 conectat)
        cod, iesire = ruleaza(jur, ssh_argv(cmd_ss_pi()), ssh_display(cmd_ss_pi()),
                              dry, capture=True, timeout=60)
        if not dry:
            v = parse_ss(iesire)
            jur.scrie("atasare: %d conexiuni active pe %d (loopback=%d, M1=%d)"
                      % (v["active"], PORT, v["loopback"], v["m1"]))
            if not v["ok"]:
                raise Abort("3 (atasare sesiune)", "; ".join(v["motive"]),
                            "pe Pi: tail -30 %s si tail -30 %s ; verifica daca ecoul zenoh "
                            "chiar ruleaza (pgrep -af bench_echo_server) si daca routerele "
                            "s-au vazut reciproc"
                            % (log_ecou_pi(cond), log_router_pi(cond)))

        # 8. Pi: netem pentru conditie + confirmarea qdisc-ului
        cod, _ = ruleaza(jur, ["ssh", PI, cmd_netem_pi(cond)],
                         "ssh %s \"%s\"" % (PI, cmd_netem_pi(cond)),
                         dry, capture=True, timeout=60)
        if cod != 0:
            raise Abort("4 (netem M2)",
                        "hil_netem.py a iesit cu cod %d pe M2 -- conditia %s NU e aplicata"
                        % (cod, cond),
                        "pe Pi: verifica sudo fara parola (sudo -n true) si ruleaza manual "
                        "sudo python3 %s/hil_netem.py %s %s --allow-corr"
                        % (SRC_PI, IFACE_PI, cond))
        ruleaza(jur, ["ssh", PI, cmd_netem_show_pi()],
                "ssh %s \"%s\"" % (PI, cmd_netem_show_pi()), dry, capture=True, timeout=60)

        # 9. local: monitorul (observator pur) in fundal
        argv_mon = ["python3", os.path.join(SRC_M1, "monitor_zenoh.py"),
                    log_router_m1(cond), "-o", monitor_csv(cond)]
        jur.cmd(" ".join(argv_mon) + "   &")
        if not dry:
            monitor = subprocess.Popen(argv_mon, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
            jur.scrie("monitor pornit (pid %d) -> %s" % (monitor.pid, monitor_csv(cond)))

        # 10. local: sudo -v (omul retasteaza daca a expirat) + driverul + POARTA cod 0
        jur.cmd("sudo -v")
        if not dry:
            subprocess.run(["sudo", "-v"])
        cod, _ = ruleaza(jur, ["bash", "-c", cmd_driver(cond)],
                         'bash -c "%s"' % cmd_driver(cond), dry)
        if cod != 0:
            raise Abort("5 (driver)",
                        "run_campaign.py a iesit cu cod %d" % cod,
                        "vezi %s (ultimele randuri) -- daca a picat pe sudo, reia conditia; "
                        "datele partiale din %s/zenoh/%s sunt SUSPECTE"
                        % (console_m1(cond), ARCH, cond))
    finally:
        if monitor is not None and monitor.poll() is None:
            jur.scrie("opresc monitorul (SIGINT, pid %d)" % monitor.pid)
            monitor.send_signal(signal.SIGINT)
            try:
                monitor.wait(timeout=10)
            except subprocess.TimeoutExpired:
                jur.scrie("monitorul nu s-a inchis in 10s -- SIGKILL")
                monitor.kill()

    # 11. audit, filtrat pe conditia curenta
    cod, iesire = ruleaza(jur, ["python3", os.path.join(SRC_M1_C2, "audit_campanie.py"), ARCH],
                          cmd_audit(), dry, capture=True)
    if not dry and iesire:
        jur.titlu("--- audit %s ---" % cond)
        jur.scrie(filtreaza_audit(iesire, cond), prefix="  ")
    jur.scrie("conditia %s TERMINATA. Sigilarea si jurnalul raman in seama ta." % cond)


def _selftest():
    """Doar functiile pure + comanda de selectie rulata pe un /proc FALS (actiune
    inofensiva). Fara ssh, fara retea, fara procese reale."""
    import shutil
    import tempfile

    # --- 1. parse_ss, formatul cu coloana State (asa arata pe M2, dupa atasare)
    cu_stare = (
        "ESTAB      0      0            [::1]:7447            [::1]:47238\n"
        "ESTAB      0      0            [::1]:47238           [::1]:7447\n"
        "ESTAB      0      0            [::ffff:192.168.100.19]:7447 "
        "[::ffff:192.168.100.14]:44988\n")
    v = parse_ss(cu_stare)
    assert v["ok"] and v["loopback"] == 2 and v["m1"] == 1, v
    assert v["active"] == 3, v

    # --- 2. formatul FARA coloana State ('ss -tn state established')
    fara_stare = ("0      0            [::1]:7447            [::1]:47238\n"
                  "0      0            [::ffff:192.168.100.19]:7447 "
                  "[::ffff:192.168.100.14]:44988\n")
    v2 = parse_ss(fara_stare)
    assert v2["ok"] and v2["loopback"] == 1 and v2["m1"] == 1, v2

    # --- 3. cazuri NEGATIVE
    doar_loopback = "ESTAB 0 0 [::1]:7447 [::1]:47238\n"
    v3 = parse_ss(doar_loopback)
    assert not v3["ok"] and len(v3["motive"]) == 1 and IP_M1 in v3["motive"][0], v3
    doar_m1 = "ESTAB 0 0 [::ffff:192.168.100.19]:7447 [::ffff:192.168.100.14]:44988\n"
    v4 = parse_ss(doar_m1)
    assert not v4["ok"] and "loopback" in v4["motive"][0], v4
    # LISTEN si antetul nu conteaza ca atasare
    v5 = parse_ss("State Recv-Q Send-Q Local Address:Port Peer Address:Port\n"
                  "LISTEN 0 128 [::]:7447 [::]:*\n")
    assert not v5["ok"] and v5["active"] == 0, v5
    assert not parse_ss("")["ok"]

    # --- 4. constructia comenzilor remote: SIR EXACT pentru o conditie
    P = ("export ROS_DOMAIN_ID=7 && export RMW_IMPLEMENTATION=rmw_zenoh_cpp"
         " && source ~/ros2_ws/install/setup.bash")
    assert prefix_ros() == P, prefix_ros()
    astept_router = (P + " && export RUST_LOG=info"
                     " && export ZENOH_ROUTER_CONFIG_URI=~/ros2_ws/src/c1_benchmark/router_pi.json5"
                     " && mkdir -p ~/DATE_CAMPANIE/C2_HIL_WIFI_20260801_pi"
                     " && nohup ros2 run rmw_zenoh_cpp rmw_zenohd >"
                     " ~/DATE_CAMPANIE/C2_HIL_WIFI_20260801_pi/zenoh_router_pi_redo_ge_15_8.log"
                     " 2>&1 </dev/null &")
    assert cmd_router_pi("ge_15_8") == astept_router, cmd_router_pi("ge_15_8")
    astept_ecou = (P + " && mkdir -p ~/DATE_CAMPANIE/C2_HIL_WIFI_20260801_pi"
                   " && nohup python3 /home/ubuntu/ros2_ws/src/c1_benchmark/bench_echo_server.py >"
                   " ~/DATE_CAMPANIE/C2_HIL_WIFI_20260801_pi/echo_zenoh_redo_ge_15_8.log"
                   " 2>&1 </dev/null &")
    assert cmd_ecou_pi("ge_15_8") == astept_ecou, cmd_ecou_pi("ge_15_8")
    assert cmd_netem_pi("ge_15_8") == ("sudo -n python3 /home/ubuntu/ros2_ws/src/c1_benchmark"
                                       "/hil_netem.py wlan0 ge_15_8 --allow-corr"), cmd_netem_pi("ge_15_8")
    # payload-ul ssh: '$' escapat, ghilimele duble in jurul lui bash -lc
    p = ssh_payload("for p in $(pgrep x); do echo $p; done")
    assert p == 'bash -lc "for p in \\$(pgrep x); do echo \\$p; done"', p
    assert ssh_display("true") == 'ssh ubuntu@192.168.100.19 \'bash -lc "true"\'', ssh_display("true")
    assert ssh_argv("true")[:2] == ["ssh", PI]
    # driverul: --rmws zenoh, --allow-corr, tee in consola conditiei, pipefail
    d = cmd_driver("ge_15_8")
    for bucata in ("set -o pipefail;", "--mode hil", "--iface wlp4s0", "--reps 10",
                   "--rmws zenoh", "--conditions ge_15_8", "--layers transport",
                   "--allow-corr", "| tee ", "console_ge_15_8_zenohredo.log"):
        assert bucata in d, (bucata, d)
    assert "bench_client" not in d and "PAYLOADS" not in d

    # --- 5. selectia environ-based, rulata pe un /proc FALS, cu actiune inofensiva
    fals = tempfile.mkdtemp(prefix="orch_selftest_")
    try:
        def scrie_environ(pid, variabile):
            d = os.path.join(fals, str(pid))
            os.makedirs(d)
            with open(os.path.join(d, "environ"), "wb") as f:
                f.write(b"\0".join(v.encode() for v in variabile) + b"\0")

        scrie_environ(101, ["HOME=/home/ubuntu", "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp",
                            # capcana: substringul apare in cale, dar NU e RMW-ul ales
                            "AMENT_PREFIX_PATH=/home/ubuntu/ros2_ws/install/rmw_zenoh_cpp"])
        scrie_environ(102, ["HOME=/home/ubuntu", "RMW_IMPLEMENTATION=rmw_zenoh_cpp"])
        scrie_environ(103, ["HOME=/home/ubuntu"])
        cmd = cmd_selectie_ecou_zenoh(proc_root=fals, sursa_pids="echo 101 102 103",
                                      actiune="echo ALES")
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        alesi = r.stdout.split()
        assert alesi == ["ALES", "102"], (alesi, cmd)
        # comanda de productie: pgrep + kill + /proc real
        prod = cmd_selectie_ecou_zenoh()
        assert "pgrep -f bench_echo_server" in prod and "/proc/$p/environ" in prod, prod
        assert "grep -qzx RMW_IMPLEMENTATION=rmw_zenoh_cpp" in prod, prod
        assert prod.endswith("&& kill $p; done"), prod
        assert "pkill -f bench_echo" not in cmd_curat_pi(), cmd_curat_pi()
    finally:
        shutil.rmtree(fals, ignore_errors=True)

    # --- 6. filtrarea auditului: antet + DOAR linia conditiei
    audit_text = ("== AUDIT COMPLETITUDINE: /x ==\n"
                  "conditie  rmw  payload reps\n"
                  "----------\n"
                  "ge_15_8   zenoh 4096 10\n"
                  "bern_30   zenoh 4096 10\n"
                  "total 2 celule: 2 OK, 0 ATENTIE\n")
    f = filtreaza_audit(audit_text, "ge_15_8")
    assert "ge_15_8" in f and "bern_30" not in f, f
    assert f.startswith("== AUDIT") and "conditie  rmw" in f, f

    # --- 7. caile derivate din conditie
    assert console_m1("bern_30").endswith("/console_bern_30_zenohredo.log")
    assert monitor_csv("bern_30").endswith("/monitor_bern_30_redo.csv")
    assert log_router_m1("bern_30").endswith("/zenoh_router_m1_redo_bern_30.log")
    assert COND_ALL == ["ge_5_8", "ge_15_3", "ge_15_8", "bern_30", "ge_30_3", "ge_30_8"]
    print("SELFTEST orchestrate_redo OK (32 verificari: parse_ss, comenzi remote, "
          "selectie environ pe /proc fals, filtrare audit).")


def main(argv):
    ap = argparse.ArgumentParser(
        description="Orchestrator pentru redo-urile zenoh HIL (M1). Vezi docstringul.")
    ap.add_argument("conditii", nargs="*", help="nume literale de conditii (ex. ge_5_8)")
    ap.add_argument("--all", action="store_true",
                    help="cele 6 conditii de redo: %s" % " ".join(COND_ALL))
    ap.add_argument("--dry", action="store_true",
                    help="tipareste FIECARE comanda exact cum ar rula; executa NIMIC")
    ap.add_argument("--no-pause", action="store_true",
                    help="fara ENTER intre conditii (implicit se face pauza)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        _selftest()
        return 0
    conditii = COND_ALL if a.all else a.conditii
    if not conditii:
        ap.print_usage()
        print("da cel putin o conditie, sau --all (%s)" % " ".join(COND_ALL))
        return 2

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cale_jurnal = None
    if not a.dry:
        if not os.path.isdir(ARCH):
            print("arhiva nu exista: %s" % ARCH)
            return 2
        cale_jurnal = os.path.join(ARCH, "orchestrator_%s.log" % stamp)
    jur = Jurnal(cale_jurnal)
    jur.titlu("orchestrate_redo: %d conditii (%s)%s"
              % (len(conditii), " ".join(conditii), "  [DRY-RUN]" if a.dry else ""))
    if cale_jurnal:
        jur.titlu("jurnal: %s" % cale_jurnal)
    cod = 0
    try:
        for i, cond in enumerate(conditii, 1):
            try:
                ruleaza_conditie(jur, cond, a.dry)
            except Abort as e:
                jur.titlu("")
                jur.titlu("!!! ABORT la conditia %s -- POARTA %s" % (cond, e.poarta))
                jur.scrie("motiv:   %s" % e.mesaj)
                jur.scrie("verifica: %s" % e.verifica)
                jur.scrie("lantul se opreste aici; conditiile ramase NU au rulat: %s"
                          % (" ".join(conditii[i:]) or "(niciuna)"))
                cod = 1
                break
            if i < len(conditii) and not a.no_pause and not a.dry:
                jur.titlu("")
                try:
                    input("ENTER pentru conditia urmatoare (%s), Ctrl+C ca sa te opresti: "
                          % conditii[i])
                except EOFError:
                    jur.scrie("(stdin inchis -- continui fara pauza)")
    except KeyboardInterrupt:
        jur.titlu("")
        jur.scrie("intrerupt de la tastatura (Ctrl+C)")
        cod = 130
    finally:
        jur.titlu("gata (cod %d)" % cod)
        jur.inchide()
    return cod


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
