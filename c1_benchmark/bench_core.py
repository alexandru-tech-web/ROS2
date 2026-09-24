#!/usr/bin/env python3
"""bench_core.py -- nucleul PUR al campaniei C1 (fara ROS, testat automat):
conditiile de retea SAR-realiste, statisticile de transport, comenzile tc
netem, planul de campanie si extragerea timpului de finalizare a misiunii.

Metodologia C1 (cheia articolului): degradarea este REALA (tc netem pe
interfata), nu simulata -- de aceea misiunea ruleaza cu scenario:=none.yaml
(injectorul publica stare curata; singura degradare e cea fizica), iar
diferentele masurate apartin EXCLUSIV middleware-ului (RMW) sub acea retea.
"""
import csv
import sys as _sys; csv.field_size_limit(min(_sys.maxsize, 2**31 - 1))
import io

# RMW-urile comparate (cheia = numele scurt folosit in foldere/figuri)
RMWS = {"cyclonedds": "rmw_cyclonedds_cpp",
        "zenoh": "rmw_zenoh_cpp",
        "fastdds": "rmw_fastrtps_cpp"}     # optional, al treilea punct

# Conditiile SAR-realiste: planul original (pierderi 0/5/15/30%) + doua
# combinatii cu latenta (varful descoperit in simulari: latenta doare).
CONDITIONS = [
    dict(name="ideal",        base_ms=0,   jitter_ms=0,  loss=0.00),
    dict(name="loss_5",       base_ms=0,   jitter_ms=0,  loss=0.05),
    dict(name="loss_15",      base_ms=0,   jitter_ms=0,  loss=0.15),
    dict(name="loss_20",      base_ms=0,   jitter_ms=0,  loss=0.20),
    dict(name="loss_25",      base_ms=0,   jitter_ms=0,  loss=0.25),
    dict(name="loss_30",      base_ms=0,   jitter_ms=0,  loss=0.30),
    # rafale simple (netem 'loss p% r%'): pierdere CORELATA, aceeasi medie
    # DEPRECATED: model corelat vechi (loss random CORRELATION, deprecat in man);
    # nefolosit in C2 -- vezi CALIBRARE_GE_C2.md
    dict(name="loss_20_burst", base_ms=0,   jitter_ms=0,  loss=0.20, corr=0.50),
    dict(name="loss_25_burst", base_ms=0,   jitter_ms=0,  loss=0.25, corr=0.50),
    dict(name="loss_30_burst", base_ms=0,   jitter_ms=0,  loss=0.30, corr=0.50),
    # gilbert_*: Gilbert-Elliott nativ netem ('loss gemodel'); aceeasi medie ca loss_*,
    # mean_burst_len=5 -> p, r din rf_interference.BurstProcess.from_steady (paritate SIL<->HIL).
    dict(name="gilbert_20",   base_ms=0,   jitter_ms=0,  loss=0.20, type="gilbert", p=0.0500, r=0.2000),
    dict(name="gilbert_25",   base_ms=0,   jitter_ms=0,  loss=0.25, type="gilbert", p=0.0667, r=0.2000),
    dict(name="gilbert_30",   base_ms=0,   jitter_ms=0,  loss=0.30, type="gilbert", p=0.0857, r=0.2000),
    dict(name="lat200_jit50", base_ms=200, jitter_ms=50, loss=0.00),
    dict(name="lat200_l15",   base_ms=200, jitter_ms=50, loss=0.15),
    # --- C2: pierdere corelata (Gilbert-Elliott) vs Bernoulli la ACEEASI rata medie L.
    # Simple Gilbert (1-h=1, 1-k=0), refolosind ramura 'gilbert' EXISTENTA din netem_cmd.
    # bern_L = Bernoulli adevarat (memoryless): via gemodel cu r=1-p (echivalent 'gemodel p';
    #          cu 1-r==p lantul e fara memorie). ge_L_B = rafale: r=1/B, p=L/(B*(1-L)).
    # (p, r) EXACT din CALIBRARE_GE_C2.md (procent afisat la 4 zecimale). B=1 ELIMINAT din
    # grila (r=1 interzice pierderi consecutive => NU e Bernoulli; vezi nota din calibrare).
    # type=gilbert => excluse implicit din campania C1; se aleg cu --conditions in C2.
    dict(name="bern_5",   base_ms=0, jitter_ms=0, loss=0.05, type="gilbert", p=0.05,     r=0.95),
    dict(name="bern_15",  base_ms=0, jitter_ms=0, loss=0.15, type="gilbert", p=0.15,     r=0.85),
    dict(name="bern_30",  base_ms=0, jitter_ms=0, loss=0.30, type="gilbert", p=0.30,     r=0.70),
    dict(name="ge_5_3",   base_ms=0, jitter_ms=0, loss=0.05, type="gilbert", p=0.017544, r=0.333333),
    dict(name="ge_5_8",   base_ms=0, jitter_ms=0, loss=0.05, type="gilbert", p=0.006579, r=0.125),
    dict(name="ge_15_3",  base_ms=0, jitter_ms=0, loss=0.15, type="gilbert", p=0.058824, r=0.333333),
    dict(name="ge_15_8",  base_ms=0, jitter_ms=0, loss=0.15, type="gilbert", p=0.022059, r=0.125),
    dict(name="ge_30_3",  base_ms=0, jitter_ms=0, loss=0.30, type="gilbert", p=0.142857, r=0.333333),
    dict(name="ge_30_8",  base_ms=0, jitter_ms=0, loss=0.30, type="gilbert", p=0.053571, r=0.125),
    # C2 combo: latenta+jitter (lat200_jit50) SI rafala corelata (ge_15_8) SIMULTAN.
    # Refoloseste ramura gilbert din netem_cmd; base_ms/jitter_ms dau 'delay 200ms 50ms',
    # (p,r) = ge_15_8. netem_cmd emite: delay 200ms 50ms loss gemodel 2.206% 12.500% 100% 0%.
    dict(name="lat200_jit50_ge_15_8", base_ms=200, jitter_ms=50, loss=0.15, type="gilbert", p=0.022059, r=0.125),
    # --- CELULE DE CONTROL pe fier, PRE-INREGISTRATE (PLAN_C3_ETAPA_A.md sec. 4c, 23.09.2026).
    # Separa cele trei explicatii ale semnaturii lui lat200_jit50 (zenoh 4/5 repetitii moarte pe HIL):
    # reordonarea introdusa de jitter, HOL la un transport fiabil, si politica publicatorului.
    # K1 lat200_jit50_pfifo: ACEEASI intarziere si acelasi jitter, dar cu un copil pfifo care
    #    reserializeaza ce netem ar livra amestecat -> jitter FARA reordonare.
    # K2 lat200_fix: latenta mare fara jitter si fara reordonare (martorul).
    # K3 NU e o conditie de retea: e acelasi lat200_jit50 cu alta politica de coada la publicator
    #    (KEEP_ALL in loc de KEEP_LAST 50), deci se cere din bench_client, nu de aici.
    dict(name="lat200_jit50_pfifo", base_ms=200, jitter_ms=50, loss=0.00, child="pfifo limit 1000"),
    dict(name="lat200_fix",         base_ms=200, jitter_ms=0,  loss=0.00),
]


def qos_arg(istorie="keep_last", adancime=50):
    """Argumentul de QoS pentru create_publisher/create_subscription.

    Implicitul ('keep_last', 50) intoarce INTREGUL 50 -- exact ce se scria in cod pana acum,
    deci calea implicita ramane neschimbata bit cu bit si nicio cifra veche nu se muta.
    'keep_all' intoarce un QoSProfile EXPLICIT RELIABLE + KEEP_ALL: celula de control K3 din
    PLAN_C3_ETAPA_A sec. 4c, care intreaba daca semnatura lui lat200_jit50 vine din politica
    publicatorului (ce se intampla cu mostrele cand coada se umple), nu din transport.
    Importul de rclpy se face INAUNTRU: bench_core ramane un nucleu pur, testabil fara ROS.
    """
    if istorie == "keep_last":
        return int(adancime)
    if istorie != "keep_all":
        raise ValueError("istorie necunoscuta: %r (keep_last | keep_all)" % (istorie,))
    from rclpy.qos import QoSProfile, HistoryPolicy, ReliabilityPolicy, DurabilityPolicy
    return QoSProfile(history=HistoryPolicy.KEEP_ALL, depth=int(adancime),
                      reliability=ReliabilityPolicy.RELIABLE,
                      durability=DurabilityPolicy.VOLATILE)


def make_payload(n: int) -> str:
    """Sarcina utila de n octeti (ASCII determinist)."""
    return ("x" * max(0, n))


def rtt_stats(rtts_ms, sent, received):
    """Statisticile unei rulari de transport: percentile + pierdere."""
    if not rtts_ms:
        return {"n": 0, "sent": sent, "received": received,
                "loss": 1.0 if sent else 0.0}
    s = sorted(rtts_ms)
    p = lambda q: s[min(len(s) - 1, round(q * (len(s) - 1)))]
    return {"n": len(s), "sent": sent, "received": received,
            "loss": round(1.0 - received / sent, 4) if sent else 0.0,
            "mean_ms": round(sum(s) / len(s), 3),
            "p50_ms": round(p(0.50), 3), "p95_ms": round(p(0.95), 3),
            "p99_ms": round(p(0.99), 3),
            "min_ms": round(s[0], 3), "max_ms": round(s[-1], 3)}


#def netem_cmd(iface: str, c: dict) -> str:
#    """Comanda tc care aplica o conditie (replace = idempotent)."""
#    return (f"tc qdisc replace dev {iface} root netem "
#            f"delay {c.get('base_ms', 0)}ms {c.get('jitter_ms', 0)}ms "
#            f"loss {100 * c.get('loss', 0.0):.1f}%")

def netem_cmd(iface: str, c: dict) -> str:
    """Comanda tc care aplica o conditie (replace = idempotent).
    type=='gilbert': pierdere CORELATA prin Gilbert-Elliott nativ netem
    ('loss gemodel p% r% loss_bad% loss_good%') -- paritate de model SIL<->HIL cu
    rf_interference.BurstProcess. Altfel 'corr'>0: rafale simple ('loss p% r%');
    implicit memoryless ('loss p%')."""
    if c.get("type") == "gilbert":
        loss_tok = "loss gemodel %.3f%% %.3f%% 100%% 0%%" % (100 * c["p"], 100 * c["r"])
    else:
        loss_tok = f"loss {100 * c.get('loss', 0.0):.1f}%"
        if c.get("corr", 0.0):
            loss_tok += f" {100 * c['corr']:.1f}%"
    return (f"tc qdisc replace dev {iface} root netem "
            f"delay {c.get('base_ms', 0)}ms {c.get('jitter_ms', 0)}ms "
            f"{loss_tok}")

def netem_cmds(iface: str, c: dict) -> list:
    """TOATE comenzile tc ale unei conditii, in ordinea in care se emit.

    Fara 'child' e exact netem_cmd de mai sus, intr-o lista de un element: conditiile vechi
    raman bit cu bit ce erau. Cu 'child' (celula de control K1) netem devine radacina cu
    handle explicit, iar copilul se ataseaza dedesubt:
        tc qdisc replace dev X root handle 1: netem delay 200ms 50ms
        tc qdisc replace dev X parent 1:1 handle 10: pfifo limit 1000
    Forma e cea PRE-INREGISTRATA in PLAN_C3_ETAPA_A sec. 4c ('handle 1:' + 'parent 1:1 handle 10:
    pfifo limit 1000'). tc-netem(8) de pe masina asta (iproute2-6.1.0) NU documenteaza copilul
    pfifo, deci sintaxa a fost verificata EMPIRIC pe lo (24.09.2026): dupa cele doua comenzi,
    'tc qdisc show' raporteaza 'qdisc netem 1: root ... delay 200ms 50ms' SI 'qdisc pfifo 10:
    parent 1:1 limit 1000p'. Verificarea asta se reface la fiecare rulare, pe ambele masini,
    si intra in manifest -- nu ne bazam pe faptul ca tc a acceptat comanda.
    'replace' (nu 'add') si aici: idempotent, ca restul bancului.
    """
    baza = netem_cmd(iface, c)
    if not c.get("child"):
        return [baza]
    radacina = baza.replace("root netem", "root handle 1: netem", 1)
    return [radacina, "tc qdisc replace dev %s parent 1:1 handle 10: %s" % (iface, c["child"])]


def netem_clear_cmd(iface: str) -> str:
    return f"tc qdisc del dev {iface} root"


def build_plan(rmws, conditions, reps, layers=("transport", "mission")):
    """Planul ordonat al campaniei: blocat pe RMW (routerul Zenoh pornit o
    singura data per bloc), conditiile in ordine crescatoare de severitate,
    repetitiile consecutive. Intoarce o lista de rulari-dict."""
    plan = []
    for rmw in rmws:
        if rmw not in RMWS:
            raise ValueError(f"RMW necunoscut: {rmw!r} "
                             f"(stiute: {sorted(RMWS)})")
        for c in conditions:
            for rep in range(1, reps + 1):
                for layer in layers:
                    plan.append(dict(
                        rmw=rmw, rmw_impl=RMWS[rmw], condition=c["name"],
                        netem=c, rep=rep, layer=layer,
                        needs_router=(rmw == "zenoh")))
    return plan


def mission_done_time(metrics_csv_text: str, victims_total: int = 5,
                      coverage_goal: float = 0.95):
    """Primul t la care misiunea e completa, din mission_metrics.csv;
    None daca nu s-a terminat (plafon)."""
    rdr = csv.DictReader(io.StringIO(metrics_csv_text))
    for row in rdr:
        try:
            if (float(row["coverage"]) >= coverage_goal
                    and int(row["victims_found"]) >= victims_total):
                return float(row["t_s"])
        except (KeyError, ValueError):
            return None
    return None
