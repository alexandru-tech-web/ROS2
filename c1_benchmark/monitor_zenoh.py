#!/usr/bin/env python3
"""monitor_zenoh.py -- OBSERVATOR PUR pentru sesiunea Zenoh in timpul unei rulari HIL.
Scrie o linie CSV pe secunda:
    t_iso,tcp_estab_7447,err_cum
  tcp_estab_7447 -- cate conexiuni TCP ESTAB ating portul 7447 (local SAU peer), din
                    iesirea 'ss -tn' (portul routerului rmw_zenoh; --port pentru altul);
                    -1 = 'ss' a esuat / lipseste (NECUNOSCUT, nu zero)
    err_cum        -- numarul CUMULAT de linii ERROR din logul routerului dat ca argument,
                    citit INCREMENTAL (stil tail: se reia din offsetul precedent)

NU INTERACTIONEAZA cu procesele masurate: nu porneste/opreste nimic, nu publica pe ROS,
nu atinge tc/netem, nu are nevoie de sudo. Doar 'ss -tn' (read-only) si citirea logului.
De rulat pe un al treilea terminal, in paralel cu campania; Ctrl+C opreste curat (fisierul
se inchide, se scrie un rezumat pe stderr).

Uz:
  python3 monitor_zenoh.py /cale/spre/zenohd.log -o monitor_ge_15_8.csv
  python3 monitor_zenoh.py /cale/spre/zenohd.log --interval 1 --duration 300
  python3 monitor_zenoh.py --selftest        # fara retea, fara fisiere reale

LIMITE (onest): 'ss -tn' vede conexiunile de pe MASINA ACEASTA; un router pe M2 se vede
doar prin conexiunea catre el. Numaratoarea e un instantaneu la fiecare tact, deci o
conexiune care apare si dispare intre doua tacte nu e vazuta. Rotatia logului (fisier
mai scurt decat offsetul) reia citirea de la 0, dar contorul cumulat NU se reseteaza.
"""
import argparse
import datetime
import os
import subprocess
import sys
import time

PORT_ZENOH = 7447
STARI_SS = ("ESTAB", "SYN-SENT", "SYN-RECV", "FIN-WAIT-1", "FIN-WAIT-2", "TIME-WAIT",
            "CLOSE-WAIT", "LAST-ACK", "LISTEN", "CLOSING", "UNCONN", "CLOSED")


def _port_din_adresa(adr):
    """Portul dintr-o adresa 'ip:port' ('1.2.3.4:7447', '[::1]:7447', '*:7447').
    None daca nu se poate citi."""
    if ":" not in adr:
        return None
    try:
        return int(adr.rsplit(":", 1)[1])
    except ValueError:
        return None


def count_estab(ss_text, port=PORT_ZENOH):
    """Numara conexiunile ESTAB care ating portul dat, din iesirea 'ss -tn'.
    Suporta AMBELE formate observate:
      'ss -tn'                    -> antet 'State Recv-Q ...', starea pe coloana 0
      'ss -tn state established'  -> antet 'Recv-Q Send-Q ...', FARA coloana de stare
    Functie PURA (text -> numar), de aceea selftestul nu are nevoie de retea."""
    n = 0
    for linie in ss_text.splitlines():
        t = linie.split()
        if not t:
            continue
        if t[0] in ("State", "Recv-Q"):        # antet
            continue
        if t[0] in STARI_SS:                   # format cu coloana de stare
            stare, adrese = t[0], t[3:5]
        else:                                  # format filtrat: randurile sunt deja ESTAB
            stare, adrese = "ESTAB", t[2:4]
        if stare != "ESTAB" or len(adrese) < 2:
            continue
        if any(_port_din_adresa(a) == port for a in adrese):
            n += 1
    return n


def citeste_ss(port=PORT_ZENOH, timeout=2.0):
    """Instantaneul curent: numarul de ESTAB pe port. -1 daca 'ss' nu poate fi rulat
    (necunoscut, ca sa nu se confunde cu un 0 real)."""
    try:
        r = subprocess.run(["ss", "-tn"], capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return -1
    if r.returncode != 0:
        return -1
    return count_estab(r.stdout, port)


class ErrTail(object):
    """Contor CUMULAT de linii care contin un tipar (implicit 'ERROR'), citite
    INCREMENTAL dintr-un fisier care creste (stil tail -f):
      - fisier inexistent inca -> 0, se reincearca la tactul urmator;
      - se numara doar liniile COMPLETE (terminate cu \\n); un rest partial ramane
        in tampon si se numara cand se completeaza;
      - fisier mai scurt decat offsetul (rotatie/trunchiere) -> se reia de la 0,
        contorul cumulat se pastreaza."""

    def __init__(self, path, pattern="ERROR"):
        self.path = path
        self.pattern = pattern
        self.offset = 0
        self.rest = ""
        self.count = 0

    def poll(self):
        """Citeste ce s-a adaugat de la ultimul apel; intoarce contorul cumulat."""
        if self.path is None:
            return self.count
        try:
            dim = os.path.getsize(self.path)
        except OSError:
            return self.count                  # inca nu exista: reincercam mai tarziu
        if dim < self.offset:                  # rotatie / trunchiere
            self.offset = 0
            self.rest = ""
        if dim == self.offset:
            return self.count
        try:
            with open(self.path, "r", errors="replace") as f:
                f.seek(self.offset)
                bucata = f.read()
                self.offset = f.tell()
        except OSError:
            return self.count
        date = self.rest + bucata
        linii = date.split("\n")
        self.rest = linii.pop()                # ultima bucata, fara '\n' = linie partiala
        for ln in linii:
            if self.pattern in ln:
                self.count += 1
        return self.count


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def antet(port=PORT_ZENOH):
    return "t_iso,tcp_estab_%d,err_cum" % port


def linie_csv(t_iso, estab, err):
    return "%s,%d,%d" % (t_iso, estab, err)


def monitorizeaza(log_path, out, interval=1.0, duration=0.0, port=PORT_ZENOH,
                  pattern="ERROR"):
    """Bucla de observare. Ctrl+C -> oprire curata (rezumat pe stderr, fisier inchis)."""
    tail = ErrTail(log_path, pattern)
    out.write(antet(port) + "\n")
    out.flush()
    t0 = time.time()
    k = 0
    n_linii = 0
    try:
        while True:
            linie = linie_csv(now_iso(), citeste_ss(port), tail.poll())
            out.write(linie + "\n")
            out.flush()                        # tail-abil in timp real, rezista la kill
            n_linii += 1
            k += 1
            if duration and (time.time() - t0) >= duration:
                break
            # tact ancorat in t0: nu acumuleaza derapaj din durata masuratorii
            dormi = t0 + k * interval - time.time()
            if dormi > 0:
                time.sleep(dormi)
    except KeyboardInterrupt:
        print("\n[monitor] oprit la Ctrl+C", file=sys.stderr)
    print("[monitor] %d linii, err_cum final=%d" % (n_linii, tail.count), file=sys.stderr)
    return 0


def _selftest():
    """Fara retea si fara procese: parserul pe iesire 'ss' FALSA + tail pe fisier temporar."""
    import tempfile
    # 1. format 'ss -tn' (cu coloana State): 2 conexiuni ating 7447 (una local, una peer)
    ss_cu_stare = (
        "State      Recv-Q Send-Q      Local Address:Port      Peer Address:Port Process\n"
        "ESTAB      0      0           192.168.100.14:7447     192.168.100.20:51234\n"
        "ESTAB      0      0           192.168.100.14:57342    160.79.104.10:443\n"
        "ESTAB      0      0           192.168.100.14:44120    192.168.100.20:7447\n"
        "TIME-WAIT  0      0           192.168.100.14:44121    192.168.100.20:7447\n"
        "LISTEN     0      128         0.0.0.0:7447            0.0.0.0:*\n")
    assert count_estab(ss_cu_stare) == 2, count_estab(ss_cu_stare)
    assert count_estab(ss_cu_stare, port=443) == 1
    # 2. format 'ss -tn state established' (FARA coloana State)
    ss_fara_stare = (
        "Recv-Q Send-Q                Local Address:Port      Peer Address:Port Process\n"
        "0      0                     192.168.100.14:44120    192.168.100.20:7447\n"
        "0      0                     192.168.100.14:57342    160.79.104.10:443\n")
    assert count_estab(ss_fara_stare) == 1, count_estab(ss_fara_stare)
    # 3. IPv6 si adrese cu '*'
    ss_v6 = ("State  Recv-Q Send-Q Local Address:Port Peer Address:Port\n"
             "ESTAB  0      0      [::1]:7447         [::1]:40000\n")
    assert count_estab(ss_v6) == 1, count_estab(ss_v6)
    # 4. iesire goala / doar antet -> 0
    assert count_estab("") == 0
    assert count_estab("State Recv-Q Send-Q Local Address:Port Peer Address:Port\n") == 0

    # 5. ErrTail: incremental, linie partiala, rotatie
    d = tempfile.mkdtemp()
    try:
        lp = os.path.join(d, "zenohd.log")
        t = ErrTail(lp)
        assert t.poll() == 0                   # fisierul nu exista inca
        with open(lp, "w") as f:
            f.write("INFO pornit\nERROR ceva rau\nINFO ok\nERROR alta\n")
        assert t.poll() == 2, t.count
        assert t.poll() == 2, t.count          # fara continut nou -> acelasi contor
        with open(lp, "a") as f:
            f.write("ERROR a treia\nERROR partia")   # ultima linie INCOMPLETA
        assert t.poll() == 3, t.count          # linia partiala inca nu se numara
        with open(lp, "a") as f:
            f.write("la\n")
        assert t.poll() == 4, t.count          # completata -> se numara
        with open(lp, "w") as f:               # rotatie: fisier mai scurt
            f.write("ERROR dupa rotatie\n")
        assert t.poll() == 5, t.count          # contorul cumulat NU se reseteaza
        # tipar configurabil
        t2 = ErrTail(lp, pattern="rotatie")
        assert t2.poll() == 1, t2.count
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    # 6. formatarea liniei CSV si a antetului
    assert antet() == "t_iso,tcp_estab_7447,err_cum", antet()
    assert linie_csv("2026-08-02T12:00:00+03:00", 3, 7) == "2026-08-02T12:00:00+03:00,3,7"
    assert linie_csv("2026-08-02T12:00:00+03:00", -1, 0).split(",")[1] == "-1"
    print("SELFTEST monitor_zenoh OK (16 verificari: parser ss fals + tail incremental).")


def main():
    ap = argparse.ArgumentParser(
        description="Observator pur: ESTAB pe portul Zenoh + linii ERROR din logul routerului.")
    ap.add_argument("log", nargs="?", default=None,
                    help="logul routerului Zenoh (poate sa nu existe inca; se reincearca)")
    ap.add_argument("-o", "--out", default=None, help="CSV de iesire (implicit stdout)")
    ap.add_argument("--interval", type=float, default=1.0, help="secunde intre tacte")
    ap.add_argument("--duration", type=float, default=0.0, help="0 = pana la Ctrl+C")
    ap.add_argument("--port", type=int, default=PORT_ZENOH)
    ap.add_argument("--err-pattern", default="ERROR",
                    help="tiparul numarat in log (implicit ERROR)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
        return
    log_path = os.path.expanduser(a.log) if a.log else None
    if log_path is None:
        print("[monitor] fara log de router: err_cum ramane 0 (da calea ca argument)",
              file=sys.stderr)
    f = open(a.out, "w") if a.out else sys.stdout
    try:
        monitorizeaza(log_path, f, a.interval, a.duration, a.port, a.err_pattern)
    finally:
        if f is not sys.stdout:
            f.close()


if __name__ == "__main__":
    main()
