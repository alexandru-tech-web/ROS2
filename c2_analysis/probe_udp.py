#!/usr/bin/env python3
"""probe_udp.py -- sonda UDP BEST-EFFORT pe loopback, pentru a VALIDA injectia netem.

De ce: pe calea ROS cu QoS RELIABLE, pierderea de la nivel de aplicatie NU e cea
injectata de netem (CycloneDDS retransmite si recupereaza, Zenoh amplifica). O sonda
UDP one-way, best-effort, vede pierderea EXACT cum o aplica netem pe lo -- deci
L_real/B_real de aici valideaza calibrarea (tabelul app-level din QUICKLOOK e REZULTAT,
nu calibrare).

Un pachet = magic + seq (12 B), o singura directie (sender -> receiver pe 127.0.0.1).
Scriptul NU seteaza tc/netem: Alexandru il seteaza INAINTE; sonda doar trimite/primeste,
logheaza seq receptionate in CSV si scrie summary JSON (sent, received, L_real, si prin
burst_metrics IMPORTAT: B_real mediu, longest burst, nr rafale). Fara ROS, fara reliability.
"""
import argparse
import json
import os
import socket
import statistics as st
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from burst_metrics import failure_bursts, _p95

MAGIC = b"C2PR"
PKT = struct.Struct(">4sQ")   # magic(4) + seq(8) = 12 octeti


def summarize(received_seqs, sent):
    """Fapte dintr-o rulare: pierdere + rafale (via burst_metrics). JSON-abil."""
    rs = sorted(set(int(x) for x in received_seqs))
    recv = len(rs)
    bursts = failure_bursts(rs)
    return {
        "sent": sent,
        "received": recv,
        "L_real": round(100.0 * (1 - recv / sent), 4) if sent else 0.0,
        "B_real": round(st.mean(bursts), 3) if bursts else 0.0,
        "longest_burst": max(bursts) if bursts else 0,
        "burst_p95": _p95(bursts) if bursts else 0,
        "n_bursts": len(bursts),
    }


def run_probe(port, rate, count, out, host="127.0.0.1", grace=2.0):
    """Trimite `count` pachete la `rate` Hz catre un receiver local; logheaza seq
    receptionate. NU atinge tc/netem. Scrie CSV (seq) + summary JSON."""
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    rx.bind((host, port))
    rx.settimeout(0.5)
    received = []
    stop = threading.Event()

    def receiver():
        while not stop.is_set():
            try:
                data, _ = rx.recvfrom(64)
            except socket.timeout:
                continue
            except OSError:
                break
            if len(data) >= PKT.size:
                magic, seq = PKT.unpack(data[:PKT.size])
                if magic == MAGIC:
                    received.append(seq)

    t = threading.Thread(target=receiver, daemon=True)
    t.start()
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = 1.0 / rate
    nxt = time.time()
    for seq in range(1, count + 1):
        tx.sendto(PKT.pack(MAGIC, seq), (host, port))
        nxt += interval
        dt = nxt - time.time()
        if dt > 0:
            time.sleep(dt)
    time.sleep(grace)                 # asteapta pachetele in zbor
    stop.set()
    t.join(timeout=1.0)
    tx.close()
    rx.close()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        f.write("seq\n")
        for s in sorted(set(received)):
            f.write("%d\n" % s)
    summ = summarize(received, count)
    json.dump(summ, open(os.path.splitext(out)[0] + "_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))
    return summ


def _selftest():
    """>=5 cazuri sintetice cu goluri CUNOSCUTE (fara retea)."""
    # 1. fara pierdere
    s = summarize(range(1, 101), 100)
    assert s["received"] == 100 and s["L_real"] == 0.0 and s["n_bursts"] == 0, s
    # 2. o rafala scurta (seq 13 lipsa din 1..20)
    r = [i for i in range(1, 21) if i != 13]
    s = summarize(r, 20)
    assert s["n_bursts"] == 1 and s["longest_burst"] == 1, s
    # 3. RAFALA LUNGA: seq 30..49 lipsa (20 consecutive)
    r = [i for i in range(1, 101) if not (30 <= i <= 49)]
    s = summarize(r, 100)
    assert s["longest_burst"] == 20 and s["n_bursts"] == 1 and abs(s["L_real"] - 20.0) < 1e-9, s
    # 4. mai multe rafale: goluri {5},{10,11,12},{50..54} -> lungimi [1,3,5]
    miss = {5, 10, 11, 12, 50, 51, 52, 53, 54}
    r = [i for i in range(1, 101) if i not in miss]
    assert sorted(failure_bursts(r)) == [1, 3, 5], failure_bursts(r)
    s = summarize(r, 100)
    assert s["n_bursts"] == 3 and s["longest_burst"] == 5, s
    # 5. pierdere TOTALA (0 primite)
    s = summarize([], 1000)
    assert s["received"] == 0 and s["L_real"] == 100.0 and s["n_bursts"] == 0, s
    # 6. Bernoulli-like: goluri izolate -> B_real ~ 1
    r = [i for i in range(1, 1001) if i % 10 != 0]
    s = summarize(r, 1000)
    assert s["longest_burst"] == 1 and abs(s["B_real"] - 1.0) < 1e-9, s
    print("SELFTEST probe_udp OK (6 verificari).")


def main(argv):
    ap = argparse.ArgumentParser(description="sonda UDP best-effort de validare netem")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--port", type=int, default=5005)
    ap.add_argument("--rate", type=float, default=50.0)
    ap.add_argument("--count", type=int, default=10000)
    ap.add_argument("--out", default="probe_udp.csv")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return 0
    run_probe(a.port, a.rate, a.count, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
