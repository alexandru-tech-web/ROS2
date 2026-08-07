#!/usr/bin/env python3
"""bench_ipc.py -- microbenchmark al canalului local (UDS vs shm).

CE MASOARA, si de ce fiecare
  1. LATENTA DE HANDOFF la 50 Hz: de la send() in gateway pana la iesirea din recv() in
     agent. Se raporteaza p50/p95/p99, nu media: coada conteaza, media o ascunde.
     Ceasul e CLOCK_MONOTONIC, comparabil intre procese pe Linux.
  2. THROUGHPUT MAXIM: cate mesaje/s trec cand nu se impune ritm. Nu ne trebuie in
     productie (rulam la 50 Hz), dar arata cat cap de tabel avem.
  3. COST CPU: secunde de CPU (utilizator+sistem, ambele procese) per 1000 de mesaje la
     50 Hz. Un canal care e cu 20 us mai rapid dar arde un nucleu nu e mai bun.
  4. DETECTIA PERECHII MOARTE: se OMOARA agentul cu SIGKILL si se cronometreaza pana cand
     stare().viu devine False. Mecanismele difera fundamental (vezi shm.py/uds.py), deci
     cifra asta e la fel de importanta ca latenta.
  5. SIMETRIA celor doua cai (spre agentul cdds si spre agentul zenoh): daca o cale e
     sistematic mai rapida decat cealalta, diferenta dintre transporturi masurata in
     etapele urmatoare ar fi contaminata. Se testeaza cu ETICHETELE INVERSATE la jumatate
     din rulari, ca sa nu confundam 'calea A' cu 'canalul creat primul'.

Iesire: ~/DATE_CAMPANIE/ANALIZA_C3/ (director nou, creat de acest script) -- tabel .md +
.json cu toate cifrele brute. Arhivele C1/C2 nu sunt atinse.

Uz:
  python3 tools/bench_ipc.py [--rulari 10] [--esantioane 600] [--out DIR]
  python3 tools/bench_ipc.py --rapid        # 3 rulari x 200 esantioane (verificare)
  python3 tools/bench_ipc.py --selftest
"""
import json
import multiprocessing as mp
import os
import resource
import signal
import statistics as st
import sys
import time

AICI = os.path.dirname(os.path.abspath(__file__))
IPC = os.path.join(os.path.dirname(AICI), "c3_gateway", "ipc")
sys.path.insert(0, IPC)

from channel import TIPURI, acum, creeaza_canal            # noqa: E402

OUT_IMPLICIT = os.path.join(os.path.expanduser("~"), "DATE_CAMPANIE", "ANALIZA_C3")
PAYLOADS = (4096, 65536)
HZ = 50.0
ESANTIOANE = 600            # 12 s la 50 Hz: destul pentru p99 pe 10 rulari
RULARI = 10


def _p(valori, q):
    s = sorted(valori)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


# ------------------------------------------------------------------ agent (ecou)
def _agent(tip, nume, payload_max, gata, opreste):
    """Agentul de transport, simulat: primeste si raspunde imediat. Nu face altceva, ca
    sa masuram conducta, nu agentul."""
    c = creeaza_canal(tip, nume, "oaspete", max_payload=payload_max)
    try:
        c.conecteaza(timeout=10.0)
        gata.set()
        while not opreste.is_set():
            m = c.recv(timeout=0.1)
            if m is not None:
                c.send(m.payload, m.seq)
    finally:
        c.close()


def _agent_consumator(tip, nume, payload_max, gata, opreste, contor):
    """Agent care DOAR consuma, fara ecou. Pentru throughput: cu ecou, ambele sensuri se
    umplu deodata si masuram contrapresiunea, nu debitul (prima varianta chiar asta
    facea, si se bloca)."""
    c = creeaza_canal(tip, nume, "oaspete", max_payload=payload_max)
    try:
        c.conecteaza(timeout=10.0)
        gata.set()
        while not opreste.is_set():
            if c.recv(timeout=0.05) is not None:
                with contor.get_lock():
                    contor.value += 1
        while True:                     # golim ce a mai ramas in conducta
            if c.recv(timeout=0.05) is None:
                break
            with contor.get_lock():
                contor.value += 1
    finally:
        c.close()


def _porneste_agent(tip, nume, payload_max, tinta=None, extra=()):
    gata, opreste = mp.Event(), mp.Event()
    p = mp.Process(target=(tinta or _agent),
                   args=(tip, nume, payload_max, gata, opreste) + tuple(extra))
    p.start()
    return p, gata, opreste


# ------------------------------------------------------------------- masuratori
def masoara_latenta(tip, payload_len, esantioane, eticheta):
    """Dus-intors gateway -> agent -> gateway, la ritm fix. Se raporteaza jumatatea
    drumului (handoff unidirectional), care e ce ne intereseaza."""
    nume = "bench_%s_%s_%d" % (tip, eticheta, os.getpid())
    gazda = creeaza_canal(tip, nume, "gazda", max_payload=max(PAYLOADS))
    proc, gata, opreste = _porneste_agent(tip, nume, max(PAYLOADS))
    lat = []
    try:
        gazda.conecteaza(timeout=10.0)
        gata.wait(timeout=10.0)
        sarcina = b"x" * payload_len
        interval = 1.0 / HZ
        t_start = acum()
        for i in range(esantioane):
            tinta = t_start + i * interval
            dt = tinta - acum()
            if dt > 0:
                time.sleep(dt)
            t0 = acum()
            gazda.send(sarcina, i)
            m = gazda.recv(timeout=1.0)
            t1 = acum()
            if m is not None and m.seq == i:
                lat.append((t1 - t0) / 2.0)          # o singura traversare
    finally:
        opreste.set()
        proc.join(timeout=3.0)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=2.0)
        gazda.close()
    return lat


def masoara_throughput(tip, payload_len, durata=3.0):
    """Cate mesaje/s trec cand nu impunem ritm. Producatorul nu asteapta raspuns pentru
    fiecare mesaj; se numara ce a confirmat agentul."""
    nume = "bencht_%s_%d" % (tip, os.getpid())
    gazda = creeaza_canal(tip, nume, "gazda", max_payload=max(PAYLOADS))
    contor = mp.Value("L", 0)
    proc, gata, opreste = _porneste_agent(tip, nume, max(PAYLOADS),
                                          tinta=_agent_consumator, extra=(contor,))
    n_trimise, blocaje = 0, 0
    try:
        gazda.conecteaza(timeout=10.0)
        gata.wait(timeout=10.0)
        sarcina = b"x" * payload_len
        t0 = acum()
        while acum() - t0 < durata:
            try:
                gazda.send(sarcina, n_trimise)
                n_trimise += 1
            except Exception:
                blocaje += 1               # contrapresiune: consumatorul a ramas in urma
        t_scurs = acum() - t0
    finally:
        time.sleep(0.3)                    # lasam consumatorul sa termine coada
        opreste.set()
        proc.join(timeout=5.0)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=2.0)
        gazda.close()
    n = min(contor.value, n_trimise)
    return n / t_scurs, n * payload_len / t_scurs / 1e6


def masoara_cpu(tip, payload_len, esantioane):
    """Secunde CPU (utilizator+sistem) pentru gateway SI agent, per 1000 de mesaje la
    50 Hz. Copiii se contorizeaza cu RUSAGE_CHILDREN, dupa ce au fost asteptati."""
    c0 = resource.getrusage(resource.RUSAGE_SELF)
    ch0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    lat = masoara_latenta(tip, payload_len, esantioane, "cpu")
    c1 = resource.getrusage(resource.RUSAGE_SELF)
    ch1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = ((c1.ru_utime - c0.ru_utime) + (c1.ru_stime - c0.ru_stime)
           + (ch1.ru_utime - ch0.ru_utime) + (ch1.ru_stime - ch0.ru_stime))
    return cpu / max(1, len(lat)) * 1000.0


def masoara_moarte(tip):
    """SIGKILL pe agent; cat dureaza pana canalul RAPORTEAZA ca perechea nu mai e."""
    nume = "benchm_%s_%d" % (tip, os.getpid())
    gazda = creeaza_canal(tip, nume, "gazda", max_payload=4096)
    proc, gata, opreste = _porneste_agent(tip, nume, 4096)
    try:
        gazda.conecteaza(timeout=10.0)
        gata.wait(timeout=10.0)
        gazda.send(b"ping", 1)
        gazda.recv(timeout=1.0)
        os.kill(proc.pid, signal.SIGKILL)
        t0 = acum()
        while acum() - t0 < 5.0:
            gazda.recv(timeout=0.02)
            if not gazda.stare().viu:
                return acum() - t0, gazda.stare().motiv
        return None, "NEDETECTAT in 5 s"
    finally:
        proc.join(timeout=2.0)
        if proc.is_alive():
            proc.terminate()
        gazda.close()


def masoara_simetrie(tip, payload_len, esantioane, rulari):
    """Cele doua cai (spre agentul cdds si spre agentul zenoh) trebuie sa fie IDENTICE.
    Etichetele se inverseaza la fiecare a doua rulare: daca am masura mereu 'cdds' primul,
    n-am putea distinge intre 'calea cdds e mai lenta' si 'canalul creat primul e mai lent'."""
    dif, per_cale = [], {"cdds": [], "zenoh": []}
    for k in range(rulari):
        ordine = ["cdds", "zenoh"] if k % 2 == 0 else ["zenoh", "cdds"]
        med = {}
        for cale in ordine:
            lat = masoara_latenta(tip, payload_len, esantioane, cale)
            med[cale] = st.median(lat) * 1e6
            per_cale[cale].append(med[cale])
        dif.append(med["cdds"] - med["zenoh"])
    return dif, per_cale


def permutare_p(dif, iteratii=20000):
    """Test de permutare pe SEMNUL diferentelor perechi: sub ipoteza 'cele doua cai sunt
    la fel', semnul fiecarei diferente e la fel de probabil + sau -. Nu presupune
    normalitate si nu are nevoie de multe rulari.
    Determinist: parcurge toate cele 2^n combinatii de semne cand n e mic."""
    n = len(dif)
    obs = abs(sum(dif) / n)
    if n <= 20:
        extreme = 0
        for masca in range(1 << n):
            s = sum(d if (masca >> i) & 1 else -d for i, d in enumerate(dif))
            if abs(s / n) >= obs - 1e-12:
                extreme += 1
        return extreme / float(1 << n)
    return float("nan")


# ------------------------------------------------------------------------ raport
def ruleaza(rulari, esantioane, out):
    rezultat = {"config": {"rulari": rulari, "esantioane": esantioane, "hz": HZ,
                           "payloads": list(PAYLOADS)},
                "latenta": {}, "throughput": {}, "cpu": {}, "moarte": {}, "simetrie": {}}
    for tip in TIPURI:
        for payload in PAYLOADS:
            cheie = "%s_%d" % (tip, payload)
            toate, p50s = [], []
            for _ in range(rulari):
                lat = masoara_latenta(tip, payload, esantioane, "cdds")
                toate += lat
                p50s.append(st.median(lat) * 1e6)
            us = [x * 1e6 for x in toate]
            rezultat["latenta"][cheie] = {
                "n": len(us), "p50": _p(us, 0.50), "p95": _p(us, 0.95),
                "p99": _p(us, 0.99), "p50_per_rulare": p50s,
                "p50_mediana_rulari": st.median(p50s),
                "p50_spread_rulari": max(p50s) - min(p50s)}
            print("  %-12s p50=%7.1f us  p95=%7.1f us  p99=%7.1f us  (n=%d)"
                  % (cheie, _p(us, 0.50), _p(us, 0.95), _p(us, 0.99), len(us)))

            msg_s, mb_s = masoara_throughput(tip, payload)
            rezultat["throughput"][cheie] = {"msg_s": msg_s, "MB_s": mb_s}
            print("  %-12s throughput %8.0f msg/s (%6.1f MB/s)" % (cheie, msg_s, mb_s))

            cpu_ms = masoara_cpu(tip, payload, esantioane)
            rezultat["cpu"][cheie] = {"cpu_s_per_1000_msg": cpu_ms}
            print("  %-12s CPU %.3f s / 1000 msg la 50 Hz" % (cheie, cpu_ms))
        t, motiv = masoara_moarte(tip)
        rezultat["moarte"][tip] = {"secunde": t, "motiv": motiv}
        print("  %-12s detectie pereche moarta: %s (%s)"
              % (tip, ("%.3f s" % t) if t is not None else "NEDETECTATA", motiv))

    print("\n  --- simetria celor doua cai (etichete inversate la fiecare a doua rulare) ---")
    for tip in TIPURI:
        dif, per_cale = masoara_simetrie(tip, 4096, max(200, esantioane // 3),
                                         min(rulari, 10))
        p = permutare_p(dif)
        rezultat["simetrie"][tip] = {
            "diferente_us": dif, "medie_us": sum(dif) / len(dif),
            "p_permutare": p,
            "cdds_p50_us": per_cale["cdds"], "zenoh_p50_us": per_cale["zenoh"],
            "spread_intra_cale_us": max(max(per_cale["cdds"]) - min(per_cale["cdds"]),
                                        max(per_cale["zenoh"]) - min(per_cale["zenoh"]))}
        r = rezultat["simetrie"][tip]
        print("  %-5s dif medie cdds-zenoh = %+.1f us | imprastiere in interiorul unei "
              "cai = %.1f us | p=%.3f" % (tip, r["medie_us"], r["spread_intra_cale_us"], p))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "bench_ipc.json"), "w") as f:
        json.dump(rezultat, f, indent=1)
    with open(os.path.join(out, "bench_ipc.md"), "w") as f:
        f.write(tabel_md(rezultat))
    print("\n  scris %s/{bench_ipc.json,bench_ipc.md}" % out)
    return rezultat


def tabel_md(r):
    c = r["config"]
    L = ["# Microbenchmark canal IPC local (C3, etapa 2)", "",
         "Generat de `tools/bench_ipc.py`. %d rulari x %d esantioane la %g Hz, "
         "sarcini utile %s octeti." % (c["rulari"], c["esantioane"], c["hz"],
                                       " si ".join(str(p) for p in c["payloads"])),
         "Ceas: CLOCK_MONOTONIC (comparabil intre procese). Latenta raportata e pentru o "
         "SINGURA traversare (dus-intors / 2).", "",
         "## Latenta de handoff [us]", "",
         "| canal | payload | p50 | p95 | p99 | imprastierea p50 intre rulari |",
         "|---|---|---|---|---|---|"]
    for cheie, v in sorted(r["latenta"].items()):
        tip, payload = cheie.rsplit("_", 1)
        L.append("| %s | %s | %.1f | %.1f | %.1f | %.1f |"
                 % (tip, payload, v["p50"], v["p95"], v["p99"], v["p50_spread_rulari"]))
    L += ["", "## Throughput si cost CPU", "",
          "| canal | payload | msg/s | MB/s | CPU [s] / 1000 msg @50 Hz |", "|---|---|---|---|---|"]
    for cheie in sorted(r["throughput"]):
        tip, payload = cheie.rsplit("_", 1)
        t, cpu = r["throughput"][cheie], r["cpu"][cheie]
        L.append("| %s | %s | %.0f | %.1f | %.3f |"
                 % (tip, payload, t["msg_s"], t["MB_s"], cpu["cpu_s_per_1000_msg"]))
    L += ["", "## Detectia perechii moarte (SIGKILL pe agent)", "",
          "| canal | timp pana la detectie | mecanism raportat |", "|---|---|---|"]
    for tip, v in sorted(r["moarte"].items()):
        L.append("| %s | %s | %s |" % (tip,
                                       ("%.3f s" % v["secunde"]) if v["secunde"] is not None
                                       else "NEDETECTATA", v["motiv"]))
    L += ["", "## Simetria celor doua cai (cdds vs zenoh)", "",
          "Etichetele sunt inversate la fiecare a doua rulare, ca sa nu se confunde calea "
          "cu ordinea crearii. p = test de permutare pe semnele diferentelor perechi.", "",
          "| canal | dif. medie cdds-zenoh [us] | imprastiere in interiorul unei cai [us] | p |",
          "|---|---|---|---|"]
    for tip, v in sorted(r["simetrie"].items()):
        L.append("| %s | %+.1f | %.1f | %.3f |"
                 % (tip, v["medie_us"], v["spread_intra_cale_us"], v["p_permutare"]))
    L.append("")
    return "\n".join(L)


def _selftest():
    # 1. percentile
    assert _p([1, 2, 3, 4, 5], 0.5) == 3 and _p([1, 2, 3, 4, 5], 0.99) == 5

    # 2. testul de permutare: diferente clar asimetrice -> p mic; simetrice -> p mare
    assert permutare_p([5.0] * 8) < 0.01, permutare_p([5.0] * 8)
    p_sim = permutare_p([1.0, -1.0, 1.2, -1.1, 0.9, -0.8])
    assert p_sim > 0.2, p_sim

    # 3. lantul complet, in mic, pe AMBELE implementari
    for tip in TIPURI:
        lat = masoara_latenta(tip, 4096, 20, "test")
        assert len(lat) >= 15, (tip, len(lat))
        assert all(0 < x < 0.5 for x in lat), (tip, min(lat), max(lat))
        t, motiv = masoara_moarte(tip)
        assert t is not None and t < 5.0, (tip, t, motiv)
        assert motiv, tip

    # 4. tabelul se genereaza din structura, fara sa arunce
    fals = {"config": {"rulari": 1, "esantioane": 10, "hz": 50, "payloads": [4096]},
            "latenta": {"uds_4096": {"p50": 1.0, "p95": 2.0, "p99": 3.0,
                                     "p50_spread_rulari": 0.5}},
            "throughput": {"uds_4096": {"msg_s": 1.0, "MB_s": 2.0}},
            "cpu": {"uds_4096": {"cpu_s_per_1000_msg": 0.1}},
            "moarte": {"uds": {"secunde": 0.01, "motiv": "eof"}},
            "simetrie": {"uds": {"medie_us": 0.1, "spread_intra_cale_us": 5.0,
                                 "p_permutare": 0.5}}}
    md = tabel_md(fals)
    assert "Latenta de handoff" in md and "| uds | 4096 |" in md, md
    print("SELFTEST bench_ipc OK (percentile, test de permutare, lant pe ambele canale).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    rulari, esantioane, out = RULARI, ESANTIOANE, OUT_IMPLICIT
    if "--rapid" in argv:
        rulari, esantioane = 3, 200
    if "--rulari" in argv:
        rulari = int(argv[argv.index("--rulari") + 1])
    if "--esantioane" in argv:
        esantioane = int(argv[argv.index("--esantioane") + 1])
    if "--out" in argv:
        out = os.path.expanduser(argv[argv.index("--out") + 1])
    print("bench_ipc: %d rulari x %d esantioane la %g Hz -> %s"
          % (rulari, esantioane, HZ, out))
    ruleaza(rulari, esantioane, out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
