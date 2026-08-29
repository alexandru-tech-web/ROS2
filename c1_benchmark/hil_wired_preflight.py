#!/usr/bin/env python3
"""hil_wired_preflight.py -- preflight pentru bancul HIL CABLAT (M1 <-> M2 pe cablu).

Ruleaza CINCI porti, in ordine, si ABORTEAZA la PRIMA care pica (cod de iesire 1).
Fiecare poarta raporteaza CIFRA masurata, nu doar trecut/picat, si scrie un raport
JSON (--raport) ca preflight-ul sa fie PROVENIENTA campaniei, nu doar o bariera.

  P1 viteza+duplex   ethtool <iface> pe AMBELE capete; se accepta DOAR
                     'Speed: 1000Mb/s' + 'Duplex: Full'. Orice altceva = ABORT cu cifra.
  P2 offload-uri     sudo ethtool -K <iface> gso off tso off gro off lro off, apoi
                     ethtool -k <iface> ca DOVADA. 'off [fixed]' se accepta (hardware-ul
                     nu are optiunea); orice ramane 'on' = ABORT.
  P3 EEE             sudo ethtool --set-eee <iface> eee off daca e suportat; daca nu e
                     suportat se NOTEAZA si se continua (P3 nu aborteaza NICIODATA).
  P4 iperf3 TCP      doua rulari de <--iperf-dur> s, una pe sens; se cere >= <--prag-mbps>
                     Mbit/s SUSTINUT in AMBELE sensuri. Sub prag = ABORT cu cifra.
  P5 tc limit        tc qdisc replace ... netem limit <--tc-limit> pe ambele capete, apoi
                     tc qdisc show ca DOVADA ca limita e chiar aplicata.

BUGETUL DE BANDA (aritmetica verificata, cea din enuntul portii P4):
    65536 B/mesaj x 50 mesaje/s = 3 276 800 B/s pe sens
    x 8 biti                    = 26 214 400 bit/s = 26.2144 Mbit/s pe sens
    x 2 sensuri (ping + pong)   = 52.4288 Mbit/s agregat  -> 'bugetul de 52.4 Mbit/s'
    x 2 (marja ceruta)          = 104.8576 Mbit/s         -> PRAGUL 105 Mbit/s
  CITIRE ONESTA A PRAGULUI: 105 Mbit/s se cere PE FIECARE SENS, deci fata de nevoia
  reala de 26.2 Mbit/s pe sens marja e 4x, nu 2x; 'dublul bugetului' se refera la
  cifra AGREGATA de 52.4. Marja in plus nu e risipa: aritmetica de mai sus numara
  doar sarcina utila, iar pe fir mai vin JSON-ul clientului (campul 'd'), anteturile
  ROS/RTPS si TCP/IP/Ethernet; la MTU 1500 un mesaj de 64 KiB intra in ~45 cadre
  (65536/1448), deci overheadul de cadru adauga singur ~3.7%.

PACHETE PE SECUNDA (de ce P5 cere limit 100000):
    65536 / 1448 B (sarcina TCP utila la MTU 1500) = ~45.3 cadre/mesaj
    x 50 Hz                                        = ~2265 cadre/s pe sens
    x 2 sensuri                                    = ~4530 cadre/s -> '~4500 pkt/s'
  netem tine implicit 'limit 1000' PACHETE. La 200 ms intarziere (lat200_*) coada
  netem trebuie sa tina ~2265 pkt/s x 0.2 s = ~453 pachete pe sens: inca sub 1000,
  dar cu marja sub 2.2x, iar jitterul de 50 ms si rafalele TCP o pot depasi. Ce trece
  peste limita e ARUNCAT TACIT de qdisc si se contabilizeaza ca pierdere de retea --
  adica exact marimea masurata se contamineaza. La 4096 B sunt ~3 cadre/mesaj
  (~150 pkt/s) si problema nu apare; ea apare la 64 KiB.
  MASURAT: toata campania C2 HIL a rulat pe implicitul 1000 -- liniile
  'qdisc netem 8005: root refcnt 2 limit 1000 ...' din
  ~/DATE_CAMPANIE/C2_HIL_WIFI64_20260803/orchestrator_20260803_235016.log

AVERTISMENT DE PERSISTENTA (verificat static la fiecare rulare, si in --dry):
  bench_core.netem_cmd (SURSA UNICA a regulii, folosita si de run_campaign.py pe M1 si
  de hil_netem.py pe M2) NU emite 'limit'. Deci limita pusa de P5 traieste doar pana la
  PRIMA aplicare de conditie a campaniei, care face 'tc qdisc replace ... root netem
  delay ... loss ...' fara 'limit' si readuce qdisc-ul la implicitul 1000. P5 dovedeste
  ca nucleul ACCEPTA limita; ca ea sa REZISTE trebuie modificata bench_core.netem_cmd.

ORDINEA PORTILOR NU E ARBITRARA: P4 (saturatie) ruleaza pe legatura CURATA, inainte ca
P5 sa instaleze un qdisc netem; P5 e ultima si lasa bancul in starea 'ideal' (netem cu
pierdere 0.0%, nu absenta qdisc-ului -- vezi hil_netem.py).

INTERFATA NU E HARDCODATA. Pe M1 NIC-ul cablat e 'enp2s0' (implicitul lui --iface-local),
pe M2 se da explicit cu --iface-remote. Nu exista IP hardcodat: --remote (user@host ssh)
e OBLIGATORIU, iar --peer-ip separa adresa de test (cablul) de gazda ssh (care poate
merge pe alta cale, ex. Wi-Fi) -- daca nu se da, se deduce din --remote si se NOTEAZA.

FOLOSIRE:
  python3 hil_wired_preflight.py --remote ubuntu@192.0.2.20 --iface-remote eth0 --dry
  python3 hil_wired_preflight.py --remote ubuntu@192.0.2.20 --iface-remote eth0 \\
          --peer-ip 192.0.2.20 --raport ~/DATE_CAMPANIE/ANALIZA_C2/preflight.json
  python3 hil_wired_preflight.py --selftest      # doar parsere, NU atinge reteaua

Interpretorul: /usr/bin/python3 (3.12). 'python3' din PATH poate fi venv/Anaconda.
"""
import argparse
import datetime
import json
import os
import platform
import re
import shlex
import socket
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import CONDITIONS, netem_cmd

# ---------------------------------------------------------------------------
# CUSATURI CUNOSCUTE PENTRU ZIUA DE BANC (checklist Etapa 2)
#
# 1. EEE PE RASPBERRY PI. Unele drivere nu expun deloc EEE ('ethtool --show-eee'
#    intoarce 'Operation not supported'), altele raporteaza intr-un format pe care
#    parserul de aici nu il recunoaste. Semantica portii e deliberat asimetrica:
#    FAIL doar cand EEE e DEMONSTRABIL activ; nesuportat, necunoscut si
#    'enabled - inactive' trec, fiecare cu nota in raport. O poarta care pica pe
#    'nu stiu' ar opri bancul din motivul gresit, si ar opri chiar capatul M2.
#    REZERVA declarata: 'enabled - inactive' inseamna EEE negociat dar link-ul nu e
#    momentan in LPI; poate intra in LPI in mijlocul unei masuratori. Nota exista
#    tocmai ca sa poata fi confruntata ulterior cu o anomalie de latenta.
#
# 2. PARSERUL DE iperf3 NU A VAZUT NICIODATA BINARUL REAL. Intervalele, retransmisiile
#    si perechea sent/recv sunt validate pe iesiri JSON INREGISTRATE, fiindca iperf3 nu
#    e instalat pe masina de dezvoltare. Prima rulare reala a preflightului, la Etapa 2,
#    probeaza cusatura in cateva minute -- daca schema difera, P4 va spune 'JSON fara
#    end.sum_sent/end.sum_received' sau 'iperf3 nu a raportat intervale', nu va da o
#    cifra gresita. De verificat atunci: 'iperf3 --version' pe ambele capete.
#
# 3. BIDIRECTIONALITATEA e testata ca doua rulari secventiale (una pe sens), nu
#    simultan ('--bidir'), fiindca schema JSON a lui --bidir nu a putut fi verificata
#    aici. Se certifica sanatatea legaturii pe fiecare sens la saturatie, nu
#    full-duplex sub sarcina simultana.
# ---------------------------------------------------------------------------

VERSIUNE = "2.1"

# PRAGURI DE SANATATE, RELATIVE LA CE GARANTEAZA P1 (gigabit negociat).
# Pana la v2.0 pragul era 105 Mbit/s, derivat din bugetul campaniei (52.4 agregat x2).
# Derivarea era corecta dar pragul era INUTIL: 105 inseamna 11.2% dintr-o legatura
# gigabit sanatoasa (~941 Mbit/s TCP), deci o legatura negociata gigabit dar degradata
# la 150 trecea senin. Odata ce P1 garanteaza 1000Mb/s Full, poarta de banda trebuie sa
# ceara ce da o legatura gigabit SANATOASA, nu ce ii ajunge campaniei.
PRAG_MBPS = 850.0            # ~90% din ~941 Mbit/s, TCP idle pe gigabit
PRAG_RETRANS_FRACT = 0.01    # retransmisii <= 1% din segmentele emise
PRAG_GAP_RECV = 0.95         # recv >= 95% din sent: prapastia dintre ele e un simptom
PRAG_DELTA_BYTES = 0.95      # >= 95% din volum contabilizat pe interfata CABLATA
MSS_IMPLICIT = 1448          # pentru a converti octeti in segmente (retransmisii)
BUGET_CAMPANIE_MBPS = 52.4288  # 65536 B x 50 Hz x 2 sensuri -- ramane SANITY, nu poarta

# Numele EXACTE sub care 'ethtool -k' raporteaza cele patru offload-uri cerute.
# Cheia scurta e cea din 'ethtool -K <iface> gso off tso off gro off lro off'.
FEATURE_KEYS = [
    ("gso", "generic-segmentation-offload"),
    ("tso", "tcp-segmentation-offload"),
    ("gro", "generic-receive-offload"),
    ("lro", "large-receive-offload"),
]

SIGILAT = os.path.join(os.path.expanduser("~"), "DATE_CAMPANIE")
PERMIS = os.path.join(SIGILAT, "ANALIZA_C2")


# ---------------------------------------------------------------------------
# PARSERE PURE (fara I/O, fara retea, fara ceas) -- singurele lucruri testabile
# offline si, de aceea, singurele in care are voie sa stea logica de decizie.
# ---------------------------------------------------------------------------

def parse_ethtool_link(text):
    """Parseaza iesirea lui 'ethtool <iface>' (P1).

    Toleranta ceruta de realitate: cand ethtool ruleaza fara privilegii pe unele
    drivere, prima linie e 'netlink error: Operation not permitted' iar raportul
    vine oricum dupa ea -- se ignora orice linie care nu e o pereche cunoscuta.
    'Speed' se pastreaza SI brut (speed_raw), pentru ca mesajul de abort trebuie sa
    arate cifra gasita ('Unknown!', '100Mb/s'), nu doar ca nu e 1000."""
    out = {"speed_raw": None, "speed_mbps": None, "duplex": None,
           "link_detected": None, "iface_raportat": None}
    for ln in (text or "").splitlines():
        s = ln.strip()
        if s.startswith("Settings for "):
            out["iface_raportat"] = s[len("Settings for "):].rstrip(":")
        elif s.startswith("Speed:"):
            out["speed_raw"] = s.split(":", 1)[1].strip()
            m = re.match(r"^(\d+)Mb/s$", out["speed_raw"])
            out["speed_mbps"] = int(m.group(1)) if m else None
        elif s.startswith("Duplex:"):
            out["duplex"] = s.split(":", 1)[1].strip()
        elif s.startswith("Link detected:"):
            out["link_detected"] = s.split(":", 1)[1].strip().lower() == "yes"
    return out


def verdict_link(d, cerut_mbps=1000):
    """(ok, motiv) pentru P1. Ordinea verificarilor e aleasa ca mesajul sa fie
    ACTIONABIL: 'Link detected: no' se raporteaza inaintea vitezei, pentru ca la
    cablu nebagat ethtool da oricum 'Speed: Unknown!' si cifra ar induce in eroare."""
    if d.get("speed_raw") is None and d.get("duplex") is None:
        return (False, "ethtool nu a raportat nici Speed nici Duplex "
                       "(interfata inexistenta? ethtool lipsa? nume gresit de iface?)")
    if d.get("link_detected") is False:
        return (False, "Link detected: no (Speed=%s, Duplex=%s)"
                % (d.get("speed_raw"), d.get("duplex")))
    if d.get("speed_mbps") != cerut_mbps:
        return (False, "Speed=%s (se cere EXACT %dMb/s)" % (d.get("speed_raw"), cerut_mbps))
    if d.get("duplex") != "Full":
        return (False, "Duplex=%s (se cere Full)" % (d.get("duplex"),))
    return (True, "Speed=%s Duplex=%s" % (d.get("speed_raw"), d.get("duplex")))


def parse_ethtool_features(text):
    """Parseaza iesirea lui 'ethtool -k <iface>' (P2) intr-un dict
    nume -> {stare, fixed, requested, raw, indentat}.

    Doua capcane reale, amandoua acoperite de selftest:
      (a) sub-optiunile sunt INDENTATE cu TAB ('\\ttx-tcp-segmentation: off [fixed]')
          si NU trebuie confundate cu optiunea de nivel zero; la nume duplicat se
          pastreaza varianta neindentata;
      (b) valoarea poate avea sufixe: 'off [requested on]' inseamna OFF (kernelul a
          refuzat cererea de a-l porni), deci un test naiv 'on in valoare' ar da un
          fals pozitiv. Starea e PRIMUL token, restul sunt adnotari."""
    out = {}
    for ln in (text or "").splitlines():
        if ":" not in ln:
            continue
        indentat = ln[:1] in (" ", "\t")
        nume, _, val = ln.partition(":")
        nume = nume.strip()
        val = val.strip()
        if not nume or " " in nume:
            continue    # 'Features for enp2s0:' / 'netlink error: ...' nu sunt optiuni
        prec = out.get(nume)
        if prec is not None and not prec["indentat"] and indentat:
            continue
        toks = val.split()
        out[nume] = {
            "stare": toks[0] if toks else "",
            "fixed": "[fixed]" in val,
            "requested": "[requested" in val,
            "raw": val,
            "indentat": indentat,
        }
    return out


def verdict_offloads(feats):
    """(ok, motiv, masurat) pentru P2. masurat = valoarea BRUTA a fiecarui offload,
    ca raportul sa poarte dovada, nu concluzia. Lipsa unei optiuni din raportul lui
    ethtool NU se trece cu vederea: nu se poate DOVEDI ca e off, deci e abort."""
    masurat = {}
    lipsa, rele = [], []
    for scurt, nume in FEATURE_KEYS:
        f = feats.get(nume)
        if f is None:
            lipsa.append("%s (%s)" % (scurt, nume))
            masurat[scurt] = None
            continue
        masurat[scurt] = f["raw"]
        if f["stare"] != "off":
            rele.append((scurt, nume, f))
    if lipsa:
        return (False, "'ethtool -k' NU raporteaza deloc: %s" % ", ".join(lipsa), masurat)
    if rele:
        buc = []
        for scurt, nume, f in rele:
            if f["fixed"]:
                buc.append("%s (%s) = '%s' -> NIC-ul il FORTEAZA pornit, "
                           "'ethtool -K' nu il poate opri" % (scurt, nume, f["raw"]))
            else:
                buc.append("%s (%s) = '%s'" % (scurt, nume, f["raw"]))
        return (False, "offload-uri INCA pornite: " + "; ".join(buc), masurat)
    return (True, "toate cele 4 offload-uri sunt off", masurat)


def parse_eee(text, rc=0):
    """Parseaza 'ethtool --show-eee <iface>' (P3) -> {suportat, status}.

    Iesiri REALE intalnite: pe un NIC fara EEE ethtool scrie 'netlink error:
    Operation not supported' si iese cu rc!=0; pe unul cu EEE apare linia
    'EEE status: enabled - inactive' (sau 'disabled'). 'suportat=None' inseamna
    NECUNOSCUT (rc 0 dar fara linie de status) -- se noteaza, nu se ghiceste."""
    t = text or ""
    out = {"suportat": None, "status": None, "activ": None, "rc": rc,
           "raw_head": t.strip().splitlines()[0] if t.strip() else ""}
    # Unele versiuni de ethtool raporteaza starea pe o linie separata 'Active: yes/no'
    # in loc de (sau pe langa) 'EEE status: enabled - active'. Ambele formate se citesc;
    # daca lipseste, campul ramane None = NECUNOSCUT, nu False.
    for ln in t.splitlines():
        z = ln.strip().lower()
        if z.startswith("active:"):
            v = z.split(":", 1)[1].strip()
            out["activ"] = True if v.startswith("yes") else (
                False if v.startswith("no") else None)
    if "not supported" in t.lower():
        out["suportat"] = False
        return out
    for ln in t.splitlines():
        s = ln.strip()
        if s.lower().startswith("eee status:"):
            out["status"] = s.split(":", 1)[1].strip()
            out["suportat"] = True
            return out
    if rc != 0:
        out["suportat"] = False
    return out


def eee_este_oprit(status):
    """True doar daca statusul EEE incepe cu 'disabled'. 'enabled - inactive'
    NU e oprit: e pornit dar momentan inactiv, deci se poate activa in timpul
    unei masuratori si introduce latenta de trezire."""
    return bool(status) and status.strip().lower().startswith("disabled")


def parse_iperf3_json(text):
    """Parseaza iesirea lui 'iperf3 -c <ip> -J' (P4).

    Contract folosit: obiect JSON cu 'end.sum_sent' si 'end.sum_received', fiecare
    cu 'bits_per_second' si 'seconds'; la esec, iperf3 -J scrie un obiect cu cheia
    'error'. Se raporteaza AMBELE cifre: cea de emisie si cea de RECEPTIE. Cifra
    care conteaza pentru poarta e sum_received -- ce a ajuns efectiv la celalalt
    capat; sum_sent e ce a bagat emitatorul in socket si poate fi mai mare."""
    out = {"ok": False, "mbps_sent": None, "mbps_recv": None, "secunde": None,
           "retransmisii": None, "octeti_sent": None, "intervale_mbps": [],
           "eroare": None, "raw_head": (text or "").strip()[:200]}
    t = (text or "").strip()
    if not t:
        out["eroare"] = "iesire GOALA de la iperf3 (binar lipsa? ssh cazut? rulare ucisa?)"
        return out
    try:
        obj = json.loads(t)
    except ValueError:
        out["eroare"] = "iesire care NU e JSON: %s" % out["raw_head"]
        return out
    if not isinstance(obj, dict):
        out["eroare"] = "JSON care nu e obiect: %s" % out["raw_head"]
        return out
    if obj.get("error"):
        out["eroare"] = str(obj["error"])
        return out
    end = obj.get("end") or {}
    s = end.get("sum_sent") or {}
    r = end.get("sum_received") or {}
    bs, br = s.get("bits_per_second"), r.get("bits_per_second")
    if bs is None or br is None:
        out["eroare"] = ("JSON fara end.sum_sent/end.sum_received "
                         "(rulare UDP? versiune de iperf3 neasteptata?)")
        return out
    out["mbps_sent"] = round(float(bs) / 1e6, 3)
    out["mbps_recv"] = round(float(br) / 1e6, 3)
    sec = r.get("seconds", s.get("seconds"))
    out["secunde"] = round(float(sec), 2) if sec is not None else None
    out["retransmisii"] = s.get("retransmits")
    out["octeti_sent"] = s.get("bytes")
    # INTERVALELE, nu doar media. Pana la v2.0 erau aruncate, si de aceea o legatura
    # care dadea 941 Mbit/s timp de 5 s si apoi ZERO 25 de secunde trecea poarta: media
    # peste 30 s iesea 157. Media nu poate distinge o legatura buna de una care se
    # prabuseste; intervalele pot, si iperf3 le raporteaza deja.
    for it in (obj.get("intervals") or []):
        b = (it.get("sum") or {}).get("bits_per_second")
        if b is not None:
            out["intervale_mbps"].append(round(float(b) / 1e6, 3))
    out["ok"] = True
    return out


# ---------------------------------------------------------------------------
# NUCLEUL PUR DE VERDICT (v2.0)
#
# Fiecare poarta isi are decizia intr-o functie PURA verdict_*(masuratori) ->
# (ok, motive[]). Fara I/O, fara CLI, fara Executor. Motivul e masurat, nu estetic:
# la revizia adversariala din 2026-08-13, 13 din 14 regresii injectate in logica
# portilor 4 si 5 au trecut neobservate de selftest, fiindca decizia statea INLINE in
# poarta iar selftestul o re-implementa cu literali proprii. Acele asertii testau
# fixture-ul, nu codul. Cu decizia intr-o functie pura, mutantii lovesc exact codul
# care decide, si nu mai exista unde sa se ascunda.
# ---------------------------------------------------------------------------


def verdict_mtu(mtu, cerut=1500):
    """MTU-ul trebuie sa fie exact cel al campaniei. Un MTU mai mare pe un capat
    schimba fragmentarea, adica insasi marimea pe care o masoara C2 la 64 KB."""
    if mtu is None:
        return (False, ["MTU necitit (interfata inexistenta? ip link a esuat?)"])
    if int(mtu) != int(cerut):
        return (False, ["MTU=%s, se cere EXACT %s" % (mtu, cerut)])
    return (True, [])


def verdict_rutare(ruta, iface_cerut):
    """Stratul UNU al legarii la cablu: ruta spre peer trebuie sa iasa pe interfata
    cablata. Fara asta, tot preflightul poate certifica Wi-Fi in timp ce netem se
    aplica pe cablu -- iar cifrele de campanie ar fi de pe alta legatura decat cea
    despre care scrie articolul."""
    if not ruta or not ruta.get("iface"):
        return (False, ["'ip route get' nu a raportat nicio interfata (%s)"
                        % (ruta or {}).get("raw", "")])
    if ruta["iface"] != iface_cerut:
        return (False, ["traficul spre peer se ruteaza pe '%s', NU pe interfata "
                        "cablata '%s' (src=%s, via=%s)"
                        % (ruta["iface"], iface_cerut, ruta.get("src"),
                           ruta.get("via"))])
    return (True, [])


def verdict_delta_bytes(delta_total, volum_asteptat, prag=PRAG_DELTA_BYTES):
    """Stratul DOI: adevarul de teren. Tabela de rutare DECLARA; octetii DOVEDESC.
    Se cere ca cel putin `prag` din volumul transferat de iperf3 sa apara in
    contoarele interfetei cablate. O ruta corecta cu octeti care nu apar acolo
    inseamna ca masuratoarea a mers pe alta cale."""
    if delta_total is None:
        return (False, ["contoarele interfetei nu au putut fi citite "
                        "(/sys/class/net/<if>/statistics)"])
    if not volum_asteptat:
        return (False, ["volum de referinta necunoscut: nu se poate verifica nimic"])
    fract = float(delta_total) / float(volum_asteptat)
    if fract < prag:
        return (False, ["doar %.1f%% din volumul transferat (%d din %d octeti) apare "
                        "in contoarele interfetei cablate; se cere >= %.0f%%. Traficul "
                        "a mers pe alta interfata."
                        % (100.0 * fract, delta_total, volum_asteptat, 100.0 * prag)])
    return (True, [])


def verdict_mediu_curat(qdiscuri):
    """Un qdisc netem preexistent NU e un avertisment, e un FAIL. Pana la v2.0 era
    doar tiparit, iar cum P5 lasa intentionat netem instalat, FIECARE re-rulare a
    preflightului masura banda prin qdisc-ul rularii precedente -- si trecea."""
    motive = []
    for host in sorted(qdiscuri or {}):
        q = qdiscuri[host] or {}
        if q.get("kind") == "netem":
            motive.append("%s are DEJA netem instalat ('%s'): banda nu poate fi "
                          "masurata prin el. Sterge-l ('sudo tc qdisc del dev <if> "
                          "root') si reia." % (host, q.get("linie")))
    return (not motive, motive)


def eee_este_activ(eee):
    """True doar cand EEE e DEMONSTRABIL activ pe link. None-ul nu se converteste in
    False nicaieri: 'nu stiu' si 'nu' sunt lucruri diferite."""
    if not eee:
        return None
    if eee.get("activ") is not None:            # formatul cu 'Active: yes/no'
        return eee["activ"]
    st = (eee.get("status") or "").strip().lower()
    if not st:
        return None
    if "inactive" in st:                        # 'enabled - inactive' NU e activ
        return False
    if "active" in st:
        return True
    if st.startswith("disabled"):
        return False
    return None


def verdict_eee(eee):
    """Verdictul P3, cu semantica ceruta pentru ziua de banc.

    FAIL doar cand EEE e DEMONSTRABIL ACTIV pe link. Motivul e practic: pe Raspberry
    Pi unele drivere nu expun deloc EEE ('Operation not supported'), iar altele
    raporteaza intr-un format pe care parserul nu il recunoaste. O poarta care pica pe
    'nu stiu' ar opri bancul din motivul gresit -- si ar fi oprit chiar capatul M2.

      nesuportat        -> TRECE, cu nota
      necunoscut        -> TRECE, cu nota (nu se poate dovedi nimic, nici intr-un sens)
      disabled          -> TRECE
      enabled-inactive  -> TRECE, cu nota TARE (vezi rezerva de mai jos)
      active / Active:yes -> FAIL

    REZERVA DE METODA, declarata ca sa nu fie descoperita in date: 'enabled - inactive'
    inseamna EEE negociat dar link-ul nu e momentan in LPI. Poate intra in LPI in
    mijlocul unei masuratori si adauga latenta de trezire -- exact in celulele cu
    trafic intermitent, adica regimul degradat pe care il studiaza C2. Nota apare in
    raport tocmai ca sa poata fi confruntata ulterior cu o anomalie de latenta.
    """
    if eee is None:
        return (True, [], ["EEE necitit -- nu s-a putut verifica"])
    if eee.get("suportat") is False:
        return (True, [], ["EEE nesuportat de driver -- nimic de oprit"])
    activ = eee_este_activ(eee)
    if activ is True:
        return (False, ["EEE este ACTIV pe link (status='%s', Active=%s)"
                        % (eee.get("status"), eee.get("activ"))], [])
    if activ is None:
        return (True, [], ["EEE in stare NECUNOSCUTA (rc=%s, '%s') -- poarta trece, "
                           "dar starea NU e dovedita"
                           % (eee.get("rc"), eee.get("raw_head"))])
    st = (eee.get("status") or "").strip().lower()
    if st.startswith("disabled"):
        return (True, [], [])
    return (True, [], ["EEE e pornit dar inactiv (status='%s'): poate intra in LPI in "
                       "timpul unei masuratori" % eee.get("status")])


def _fract_retransmisii(r, mss=MSS_IMPLICIT):
    """Retransmisii ca fractie din segmentele emise. None cand nu se poate calcula."""
    rt, oct_s = r.get("retransmisii"), r.get("octeti_sent")
    if rt is None or not oct_s or mss <= 0:
        return None
    segmente = float(oct_s) / float(mss)
    return (float(rt) / segmente) if segmente > 0 else None


def verdict_banda(sensuri, prag_mbps=PRAG_MBPS, durata_ceruta=None,
                  prag_retrans=PRAG_RETRANS_FRACT, prag_gap=PRAG_GAP_RECV,
                  mss=MSS_IMPLICIT):
    """Verdictul P4. Patru criterii, toate obligatorii, pe FIECARE sens:

      1. FIECARE interval de 1 s >= prag. Media NU mai e criteriu: o legatura care da
         941 Mbit/s cinci secunde si apoi zero douazeci si cinci are media 157 si
         trecea. Absenta intervalelor din JSON e FAIL, nu 'sarim peste'.
      2. durata raportata >= 90% din cea ceruta (o rulare scurtata nu dovedeste nimic).
      3. retransmisii <= prag_retrans din segmentele emise. Cifra exista de la inceput
         in JSON, era parsata, tiparita si salvata -- si nu intra in niciun verdict.
      4. recv >= prag_gap * sent. O prapastie intre ce s-a bagat in socket si ce a
         ajuns e un simptom, chiar daca recv trece pragul absolut.
    """
    motive = []
    if not sensuri:
        return (False, ["nicio masuratoare de banda"])
    for eticheta in sorted(sensuri):
        r = sensuri[eticheta] or {}
        if not r.get("ok"):
            motive.append("%s: iperf3 nu a produs o masuratoare (%s)"
                          % (eticheta, r.get("eroare")))
            continue
        iv = r.get("intervale_mbps") or []
        if not iv:
            motive.append("%s: iperf3 nu a raportat intervale; fara ele nu se poate "
                          "deosebi o legatura sustinuta de una care se prabuseste"
                          % eticheta)
        else:
            sub = [(i, v) for i, v in enumerate(iv) if v < prag_mbps]
            if sub:
                motive.append("%s: %d din %d intervale de 1 s sub prag (%.1f Mbit/s); "
                              "cel mai slab: %.3f Mbit/s la secunda %d"
                              % (eticheta, len(sub), len(iv), prag_mbps,
                                 min(v for _, v in sub),
                                 min(sub, key=lambda x: x[1])[0]))
        if durata_ceruta and r.get("secunde") is not None:
            if r["secunde"] < 0.9 * durata_ceruta:
                motive.append("%s: rularea a durat %.2f s din %g s cerute"
                              % (eticheta, r["secunde"], durata_ceruta))
        elif durata_ceruta and r.get("secunde") is None:
            motive.append("%s: iperf3 nu a raportat durata" % eticheta)
        fr = _fract_retransmisii(r, mss)
        if fr is None:
            motive.append("%s: retransmisiile nu pot fi evaluate (retransmits=%s, "
                          "bytes=%s)" % (eticheta, r.get("retransmisii"),
                                         r.get("octeti_sent")))
        elif fr > prag_retrans:
            motive.append("%s: %.2f%% retransmisii (%s segmente retransmise), peste "
                          "pragul de %.2f%%"
                          % (eticheta, 100.0 * fr, r.get("retransmisii"),
                             100.0 * prag_retrans))
        ms, mr = r.get("mbps_sent"), r.get("mbps_recv")
        if ms and mr is not None and mr < prag_gap * ms:
            motive.append("%s: receptionat %.3f din %.3f Mbit/s emis (%.1f%%), sub "
                          "%.0f%% -- octetii se pierd pe drum"
                          % (eticheta, mr, ms, 100.0 * mr / ms, 100.0 * prag_gap))
    return (not motive, motive)


def verdict_tc_limit(q, limita_ceruta):
    """Verdictul P5, scos din poarta ca sa poata fi lovit de mutanti."""
    if not q or q.get("kind") is None:
        return (False, ["'tc qdisc show' nu a raportat niciun qdisc radacina"])
    if q.get("limit") is None:
        return (False, ["qdisc-ul radacina ('%s') nu raporteaza 'limit'"
                        % q.get("linie")])
    if int(q["limit"]) != int(limita_ceruta):
        return (False, ["limit=%s, s-a cerut %s (netem a ignorat valoarea?)"
                        % (q["limit"], limita_ceruta)])
    return (True, [])


def parse_ip_route_get(text):
    """Parseaza 'ip route get <ip>' -> {iface, src, via}.

    Stratul UNU al legarii la cablu: tabela de rutare DECLARA pe unde ar trebui sa
    plece traficul. Nu e o dovada (rutarea se poate schimba, si oricum nu spune ce s-a
    intamplat CU ADEVARAT), dar e verificarea ieftina care prinde greseala tipica:
    --peer-ip pe adresa de Wi-Fi in loc de cea de pe cablu."""
    out = {"iface": None, "src": None, "via": None, "raw": (text or "").strip()[:200]}
    m = re.search(r"\bdev\s+(\S+)", text or "")
    if m:
        out["iface"] = m.group(1)
    m = re.search(r"\bsrc\s+(\S+)", text or "")
    if m:
        out["src"] = m.group(1)
    m = re.search(r"\bvia\s+(\S+)", text or "")
    if m:
        out["via"] = m.group(1)
    return out


def parse_statistics(text):
    """Parseaza iesirea 'cat /sys/class/net/<if>/statistics/{rx_bytes,tx_bytes}'
    (doua numere, cate unul pe linie) -> {rx, tx, total}."""
    nums = []
    for ln in (text or "").splitlines():
        s = ln.strip()
        if s.isdigit():
            nums.append(int(s))
    if len(nums) < 2:
        return {"rx": None, "tx": None, "total": None}
    return {"rx": nums[0], "tx": nums[1], "total": nums[0] + nums[1]}


def parse_mtu(text):
    """MTU din 'ip link show dev <if>' sau dintr-un /sys/class/net/<if>/mtu."""
    t = (text or "").strip()
    if t.isdigit():
        return int(t)
    m = re.search(r"\bmtu\s+(\d+)", t)
    return int(m.group(1)) if m else None


def parse_tc_qdisc(text):
    """Parseaza 'tc qdisc show dev <iface>' (P5) -> {kind, limit, linie}.

    Se cauta linia qdisc-ului ROOT (cea care contine ' root'), nu vreun copil cu
    'parent'. Parserul tolereaza un prefix de jurnal inaintea cuvantului 'qdisc'
    (asa arata liniile din orchestrator_*.log), ca fixture-le de campanie sa poata
    fi date direct. 'limit' lipsa se raporteaza ca None, NU ca 0."""
    prima = None
    for ln in (text or "").splitlines():
        i = ln.find("qdisc ")
        if i < 0:
            continue
        seg = ln[i:].strip()
        toks = seg.split()
        m = re.search(r"\blimit (\d+)\b", seg)
        d = {"kind": toks[1] if len(toks) > 1 else None,
             "limit": int(m.group(1)) if m else None,
             "linie": seg}
        if prima is None:
            prima = d
        if " root" in seg:
            return d
    return prima if prima is not None else {"kind": None, "limit": None, "linie": None}


def netem_cmd_cu_limita(iface, cond, limit):
    """Comanda tc a portii P5: EXACT regula emisa de bench_core.netem_cmd (SURSA
    UNICA, ca M1 si M2 sa nu divergheze), cu 'limit <N>' inserat imediat dupa
    'netem'. Nu se rescrie regula aici: se injecteaza doar limita, ca sa nu apara
    o a doua definitie a conditiilor in repo."""
    baza = netem_cmd(iface, cond)
    marker = " root netem "
    if marker not in baza:
        raise ValueError("netem_cmd si-a schimbat forma: %r" % baza)
    return baza.replace(marker, " root netem limit %d " % int(limit), 1)


def conditie_dupa_nume(nume):
    by = {c["name"]: c for c in CONDITIONS}
    if nume not in by:
        raise KeyError("conditie necunoscuta: %s (stiute: %s)" % (nume, sorted(by)))
    return by[nume]


def limita_nu_persista(cond):
    """True daca bench_core.netem_cmd NU emite 'limit' -- adica prima aplicare de
    conditie a campaniei sterge limita pusa de P5. Verificare STATICA (fara retea),
    ruleaza si in --dry si in selftest."""
    return " limit " not in netem_cmd("IFACE", cond)


def cale_raport_permisa(cale):
    """~/DATE_CAMPANIE e SIGILAT si READ-ONLY; singura tinta scriibila de acolo e
    ANALIZA_C2/. Orice cale din afara arhivei e permisa."""
    p = os.path.realpath(os.path.expanduser(cale))
    sig = os.path.realpath(SIGILAT)
    per = os.path.realpath(PERMIS)
    if p == sig or p.startswith(sig + os.sep):
        return p == per or p.startswith(per + os.sep)
    return True


# ---------------------------------------------------------------------------
# EXECUTIE (singurul loc cu efecte secundare)
# ---------------------------------------------------------------------------

class Executor:
    """Ruleaza comenzi local (bash -c) sau pe M2 (ssh) si le JURNALIZEAZA pe toate.
    In modul --dry NU executa nimic: doar tipareste si inregistreaza -> scriptul se
    poate verifica integral fara banc, fara ssh si fara sudo."""

    def __init__(self, dry=False, remote=None, timeout=60.0):
        self.dry = dry
        self.remote = remote
        self.timeout = timeout
        self.comenzi = []

    def _argv(self, cmd, host):
        if host == "remote":
            return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                    self.remote, cmd]
        return ["bash", "-c", cmd]

    def sh(self, cmd, host="local", timeout=None):
        argv = self._argv(cmd, host)
        afis = " ".join(shlex.quote(a) for a in argv)
        rec = {"host": host, "cmd": cmd, "argv_afisat": afis,
               "executat": not self.dry, "rc": None}
        self.comenzi.append(rec)
        print("$ %s" % afis, flush=True)
        if self.dry:
            return (0, "", "")
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout or self.timeout)
        except (OSError, subprocess.SubprocessError) as e:
            rec["rc"] = -1
            rec["eroare"] = "%s: %s" % (type(e).__name__, e)
            return (-1, "", rec["eroare"])
        rec["rc"] = p.returncode
        return (p.returncode, p.stdout, p.stderr)


def capete(a):
    """Cele doua capete ale legaturii, in ordinea in care se raporteaza."""
    return [("local", a.iface_local), ("remote", a.iface_remote)]


# ---------------------------------------------------------------------------
# PORTILE. Fiecare intoarce (ok: bool, mesaj: str, masurat: dict).
# ---------------------------------------------------------------------------

def poarta1_link(ex, a):
    """P1: 1000Mb/s + Full pe AMBELE capete."""
    masurat = {}
    for host, iface in capete(a):
        rc, out, err = ex.sh("ethtool %s" % shlex.quote(iface), host=host)
        if ex.dry:
            continue
        d = parse_ethtool_link(out + "\n" + err)
        d["rc"] = rc
        masurat[host] = {"iface": iface, **d}
        ok, motiv = verdict_link(d, a.cerut_mbps)
        print("   [%s %s] %s" % (host, iface, motiv))
        if not ok:
            return (False,
                    "P1 a picat pe capatul %s (%s): %s\n"
                    "  REPARA: (1) baga cablul si ridica interfata: "
                    "sudo ip link set %s up; (2) cablu Cat5e/Cat6 INTREG (toate 4 "
                    "perechile) si port de switch gigabit -- un cablu cu 2 perechi "
                    "negociaza 100Mb/s; (3) forteaza negocierea: sudo ethtool -s %s "
                    "autoneg on speed 1000 duplex full; (4) daca ramane 100Mb/s, "
                    "schimba cablul sau portul. NU porni campania la alta viteza: "
                    "bugetul de 52.4 Mbit/s la 64 KiB nu incape onest pe 100Mb/s."
                    % (host, iface, motiv, iface, iface), masurat)
    if ex.dry:
        return (True, "P1 DRY: nu s-a citit nimic (ethtool nu a fost rulat)", {"dry": True})
    return (True, "P1: ambele capete la %dMb/s Full" % a.cerut_mbps, masurat)


def poarta2_offload(ex, a):
    """P2: gso/tso/gro/lro off pe ambele capete, cu DOVADA din 'ethtool -k'.

    'ethtool -K' poate iesi cu rc!=0 cand una dintre optiuni e [fixed] -- si poate
    sa nu le aplice pe celelalte din acelasi apel. De aceea: (1) se emite comanda
    combinata ceruta, (2) se cere dovada, (3) daca ceva a ramas 'on' si NU e [fixed]
    se reincearca optiune cu optiune, (4) se cere dovada din nou. Verdictul se da
    EXCLUSIV pe dovada, niciodata pe codul de iesire al lui 'ethtool -K'."""
    masurat = {}
    setari = " ".join("%s off" % scurt for scurt, _ in FEATURE_KEYS)
    for host, iface in capete(a):
        rc_k, _, _ = ex.sh("sudo -n ethtool -K %s %s" % (shlex.quote(iface), setari),
                           host=host)
        rc, out, err = ex.sh("ethtool -k %s" % shlex.quote(iface), host=host)
        if ex.dry:
            continue
        feats = parse_ethtool_features(out + "\n" + err)
        ok, motiv, m = verdict_offloads(feats)
        if not ok:
            # retry individual, doar pentru cele care NU sunt [fixed]
            for scurt, nume in FEATURE_KEYS:
                f = feats.get(nume)
                if f is not None and f["stare"] != "off" and not f["fixed"]:
                    ex.sh("sudo -n ethtool -K %s %s off" % (shlex.quote(iface), scurt),
                          host=host)
            rc, out, err = ex.sh("ethtool -k %s" % shlex.quote(iface), host=host)
            feats = parse_ethtool_features(out + "\n" + err)
            ok, motiv, m = verdict_offloads(feats)
        m["rc_ethtool_K"] = rc_k
        m["rc_ethtool_k"] = rc
        masurat[host] = {"iface": iface, **m}
        print("   [%s %s] %s" % (host, iface, motiv))
        if not ok:
            return (False,
                    "P2 a picat pe capatul %s (%s): %s\n"
                    "  REPARA: ruleaza pe acel capat 'sudo ethtool -K %s gso off tso "
                    "off gro off lro off' si verifica cu 'ethtool -k %s'. Daca rc-ul "
                    "lui -K e nenul (rc_K=%s): fie n-ai sudo fara parola (sudo -n a "
                    "esuat), fie optiunea e [fixed]. O optiune ramasa 'on [fixed]' NU "
                    "se poate opri din software -- schimba NIC-ul sau declara explicit "
                    "in raportul campaniei ca segmentarea ramane pornita (ea sparge "
                    "corespondenta mesaj-pachet pe care se sprijina netem)."
                    % (host, iface, motiv, iface, iface, rc_k), masurat)
    if ex.dry:
        return (True, "P2 DRY: comenzile de mai sus nu au fost executate", {"dry": True})
    return (True, "P2: gso/tso/gro/lro off (dovedit) pe ambele capete", masurat)


def poarta3_eee(ex, a):
    """P3 (v2.0): EEE trebuie DOVEDIT oprit -- e o POARTA, nu o nota.

    Pana la v2.0 P3 nu aborta niciodata: constata ca EEE a ramas pornit si continua.
    Dar EEE se poate activa in mijlocul unei masuratori si adauga latenta de trezire
    exact in celulele cu trafic intermitent, adica exact regimul degradat pe care il
    studiaza C2. O poarta care observa problema si o lasa sa treaca nu e o poarta.
    NEsuportat ramane trecut (si notat): nu se poate opri ce nu exista."""
    masurat = {}
    note = []
    picate = []
    for host, iface in capete(a):
        rc0, out0, err0 = ex.sh("ethtool --show-eee %s" % shlex.quote(iface), host=host)
        if ex.dry:
            ex.sh("sudo -n ethtool --set-eee %s eee off" % shlex.quote(iface), host=host)
            ex.sh("ethtool --show-eee %s" % shlex.quote(iface), host=host)
            continue
        inainte = parse_eee(out0 + "\n" + err0, rc0)
        m = {"iface": iface, "suportat": inainte["suportat"],
             "status_inainte": inainte["status"], "status_dupa": None,
             "rc_set": None, "avertisment": None}
        if inainte["suportat"] is False:
            m["nota"] = "EEE nesuportat pe %s (%s) -- se continua" % (iface, host)
            note.append(m["nota"])
        else:
            rc_s, _, _ = ex.sh("sudo -n ethtool --set-eee %s eee off"
                               % shlex.quote(iface), host=host)
            rc1, out1, err1 = ex.sh("ethtool --show-eee %s" % shlex.quote(iface),
                                    host=host)
            dupa = parse_eee(out1 + "\n" + err1, rc1)
            m["rc_set"] = rc_s
            m["status_dupa"] = dupa["status"]
            ok_e, mot_e, note_e = verdict_eee(dupa)
            note += ["%s (%s): %s" % (iface, host, x) for x in note_e]
            if not ok_e:
                m["motiv"] = "%s (%s): %s (rc_set=%s)" % (iface, host,
                                                          "; ".join(mot_e), rc_s)
                picate.append(m["motiv"])
        masurat[host] = m
        print("   [%s %s] EEE suportat=%s status='%s' -> '%s'"
              % (host, iface, m["suportat"], m["status_inainte"], m["status_dupa"]))
    if ex.dry:
        return (True, "P3 DRY: comenzile de mai sus nu au fost executate", {"dry": True})
    if picate:
        return (False, "P3 a picat: EEE nu a putut fi oprit.\n  " + "\n  ".join(picate)
                + "\n  REPARA: incearca manual 'sudo ethtool --set-eee <if> eee off' "
                  "si verifica cu 'ethtool --show-eee <if>'. Daca driverul refuza, "
                  "opreste EEE din BIOS/UEFI sau foloseste alt NIC: o legatura care isi "
                  "adoarme faza fizica NU poate sustine o masuratoare de latenta.",
                masurat)
    mesaj = "P3: EEE oprit (sau nesuportat) pe ambele capete"
    if note:
        mesaj += " (NOTAT: " + " | ".join(note) + ")"
    return (True, mesaj, masurat)


def _citeste_contoare(ex, host, iface):
    """rx_bytes + tx_bytes de pe interfata, de pe capatul cerut."""
    rc, out, err = ex.sh("cat /sys/class/net/%s/statistics/rx_bytes "
                         "/sys/class/net/%s/statistics/tx_bytes"
                         % (shlex.quote(iface), shlex.quote(iface)), host=host)
    if ex.dry:
        return None
    return parse_statistics(out)


def poarta4_iperf(ex, a):
    """P4: banda SUSTINUTA pe legatura CABLATA, dovedita pe interfata cablata.

    v2.0 -- trei schimbari, toate din revizia adversariala:

    LEGAREA LA CABLU, in doua straturi. Pana acum P4 masura spre --peer-ip fara sa
    verifice niciodata pe unde pleaca traficul, in timp ce P1/P2/P3/P5 lucrau pe
    --iface-*. Preflightul putea certifica Wi-Fi in timp ce netem se aplica pe cablu.
    Stratul unu: 'ip route get <peer>' trebuie sa iasa pe interfata cablata, pe ambele
    capete. Stratul doi, adevarul de teren: contoarele rx/tx ale interfetei, citite
    inainte si dupa, trebuie sa contina >= 95% din volumul transferat. Tabela de
    rutare declara; octetii dovedesc.

    MEDIU CURAT: un netem preexistent nu mai e avertisment, e FAIL.

    VERDICTUL e in verdict_banda(), pur: fiecare interval de 1 s peste prag (media nu
    mai e criteriu), durata, retransmisii sub 1%, prapastia sent/recv.
    """
    masurat = {"prag_mbps": a.prag_mbps, "durata_ceruta_s": a.iperf_dur,
               "peer_ip": a.peer_ip, "peer_ip_dedus": a.peer_ip_dedus,
               "prag_retrans_fract": PRAG_RETRANS_FRACT,
               "prag_gap_recv": PRAG_GAP_RECV,
               "prag_delta_bytes": PRAG_DELTA_BYTES}
    port = a.iperf_port
    pat = "iperf3 -s -p %s[%s]" % (str(port)[:-1], str(port)[-1])

    # --- strat 1: rutarea, pe ambele capete
    tinte = {"local": a.peer_ip, "remote": a.local_ip}
    for host, iface in capete(a):
        tinta = tinte.get(host)
        if not tinta:
            # FAIL LOUD: fara adresa celuilalt capat nu se poate verifica pe unde iese
            # traficul de pe M2. Un 'sarim peste' aici ar lasa jumatate din legarea la
            # cablu neverificata, exact defectul reparat in v2.0.
            return (False, "P4 nu poate verifica rutarea de pe capatul %s: lipseste "
                           "adresa celuilalt capat.\n  REPARA: da --local-ip cu adresa "
                           "lui M1 DE PE CABLU (si --peer-ip cu a lui M2)." % host,
                    masurat)
        rc, out, err = ex.sh("ip route get %s" % shlex.quote(tinta), host=host)
        if ex.dry:
            continue
        ruta = parse_ip_route_get(out + "\n" + err)
        masurat.setdefault("rutare", {})[host] = ruta
        ok, mot = verdict_rutare(ruta, iface)
        if not ok:
            return (False, "P4 a picat inainte de masuratoare, pe capatul %s: %s\n"
                           "  REPARA: da --peer-ip adresa lui M2 DE PE CABLU (nu cea "
                           "de pe Wi-Fi), si verifica ca interfata cablata are adresa "
                           "pe acelasi segment." % (host, "; ".join(mot)), masurat)

    # --- mediu curat: netem preexistent = FAIL
    qd = {}
    for host, iface in capete(a):
        rc, out, err = ex.sh("tc qdisc show dev %s" % shlex.quote(iface), host=host)
        if ex.dry:
            continue
        qd[host] = parse_tc_qdisc(out + "\n" + err)
    masurat["qdisc_inainte"] = qd
    ok, mot = verdict_mediu_curat(qd)
    if not ok:
        return (False, "P4 a picat: mediul nu e curat.\n  " + "\n  ".join(mot)
                       + "\n  NOTA: de la v2.0 preflightul NU mai instaleaza netem "
                         "(vezi P5), tocmai ca sa nu-si masoare propria urma.", masurat)

    # --- contoare INAINTE
    c0 = {}
    for host, iface in capete(a):
        c0[host] = _citeste_contoare(ex, host, iface)

    ex.sh("pkill -f %s ; sleep 0.3 ; setsid nohup iperf3 -s -p %d "
          "> /tmp/iperf3_srv_preflight.log 2>&1 </dev/null &"
          % (shlex.quote(pat), port), host="remote")

    sensuri = {}
    for eticheta, flag in (("local_spre_remote", ""), ("remote_spre_local", " -R")):
        rc, out, err = ex.sh("iperf3 -c %s -p %d -t %g -i 1 -J%s"
                             % (shlex.quote(a.peer_ip), port, a.iperf_dur, flag),
                             host="local", timeout=a.iperf_dur + 60.0)
        if ex.dry:
            continue
        r = parse_iperf3_json(out if out.strip() else err)
        r["rc"] = rc
        sensuri[eticheta] = r
        if r["ok"]:
            print("   [%s] recv=%.3f Mbit/s (sent=%.3f) in %.2f s, retransmisii=%s, "
                  "%d intervale" % (eticheta, r["mbps_recv"], r["mbps_sent"],
                                    r["secunde"] or 0.0, r["retransmisii"],
                                    len(r["intervale_mbps"])))
        else:
            print("   [%s] ESEC: %s" % (eticheta, r["eroare"]))

    ex.sh("pkill -f %s" % shlex.quote(pat), host="remote")
    masurat["sensuri"] = sensuri

    if ex.dry:
        return (True, "P4 DRY: comenzile de mai sus nu au fost executate", {"dry": True})

    # --- contoare DUPA + delta
    volum = 0
    for r in sensuri.values():
        if r.get("octeti_sent"):
            volum += int(r["octeti_sent"])
    for host, iface in capete(a):
        c1 = _citeste_contoare(ex, host, iface)
        d = None
        if c0.get(host) and c1 and c0[host].get("total") is not None \
                and c1.get("total") is not None:
            d = c1["total"] - c0[host]["total"]
        masurat.setdefault("delta_bytes", {})[host] = {
            "inainte": (c0.get(host) or {}).get("total"),
            "dupa": (c1 or {}).get("total"), "delta": d,
            "volum_iperf3": volum}
        ok, mot = verdict_delta_bytes(d, volum)
        if not ok:
            return (False, "P4 a picat pe capatul %s: %s\n"
                           "  Ruta spre peer arata corect, dar octetii NU au trecut "
                           "prin interfata cablata. Cel mai des: exista o a doua cale "
                           "spre acelasi peer (Wi-Fi in aceeasi retea), sau adresa "
                           "sursa aleasa de nucleu e a altei interfete."
                           % (host, "; ".join(mot)), masurat)

    ok, motive = verdict_banda(sensuri, a.prag_mbps, a.iperf_dur)
    if not ok:
        return (False, "P4 a picat:\n  " + "\n  ".join(motive)
                + "\n  REPARA: (1) iperf3 pe AMBELE capete; (2) pragul de %.0f Mbit/s "
                  "e ~90%% din ce da o legatura gigabit sanatoasa (~941 Mbit/s TCP) -- "
                  "o cifra mult sub el pe o legatura negociata 1000Mb/s Full inseamna "
                  "cablu prost, port prost sau trafic concurent; (3) retransmisii peste "
                  "1%% arata duplex nepotrivit sau cablu la limita; (4) intervale care "
                  "cad la zero arata o legatura care se prabuseste periodic -- media ar "
                  "fi ascuns-o. Bugetul campaniei (%.1f Mbit/s agregat) e mult sub prag "
                  "si NU e criteriul aici." % (a.prag_mbps, BUGET_CAMPANIE_MBPS),
                masurat)
    return (True, "P4: banda sustinuta pe ambele sensuri, toate intervalele >= %.0f "
                  "Mbit/s, retransmisii sub %.0f%%, octeti dovediti pe interfata "
                  "cablata" % (a.prag_mbps, 100.0 * PRAG_RETRANS_FRACT), masurat)


def poarta5_mediu_curat(ex, a):
    """P5 (v2.0): preflightul certifica bancul CURAT si iese CURAT.

    Pana la v2.0, P5 INSTALA netem cu limit 100000 si il lasa acolo. Doua consecinte,
    amandoua confirmate la revizie: (1) fiecare re-rulare a preflightului masura P4
    prin qdisc-ul rularii precedente; (2) responsabilitatea era in locul gresit --
    preflightul e o POARTA, iar instalarea conditiei apartine orchestratorului de
    campanie, unde e oricum validata independent de sonda UDP (Etapa 3).

    Ce ramane aici e verificarea care conteaza pentru banc: MTU-ul si absenta oricarui
    qdisc care ar falsifica masuratoarea. Limita de 100000 de pachete se aplica de
    orchestrator, cu netem_cmd_cu_limita(), si tot el o dovedeste cu 'tc qdisc show'.
    """
    masurat = {"mtu_cerut": a.mtu, "tc_limit_recomandat": a.tc_limit,
               "nota": ("preflightul NU instaleaza netem; limita se aplica de "
                        "orchestratorul de campanie")}
    motive = []
    for host, iface in capete(a):
        rc, out, err = ex.sh("cat /sys/class/net/%s/mtu" % shlex.quote(iface),
                             host=host)
        if ex.dry:
            continue
        mtu = parse_mtu(out)
        masurat.setdefault("mtu", {})[host] = mtu
        ok, mot = verdict_mtu(mtu, a.mtu)
        if not ok:
            motive += ["%s (%s): %s" % (host, iface, m) for m in mot]
        rc, out, err = ex.sh("tc qdisc show dev %s" % shlex.quote(iface), host=host)
        q = parse_tc_qdisc(out + "\n" + err)
        masurat.setdefault("qdisc", {})[host] = q
        print("   [%s %s] mtu=%s qdisc='%s'" % (host, iface, mtu, q["linie"]))
    if ex.dry:
        return (True, "P5 DRY: comenzile de mai sus nu au fost executate", {"dry": True})
    ok, mot = verdict_mediu_curat(masurat.get("qdisc", {}))
    motive += mot
    if motive:
        return (False, "P5 a picat:\n  " + "\n  ".join(motive)
                + "\n  REPARA: MTU-ul trebuie sa fie exact %d pe ambele capete "
                  "('sudo ip link set dev <if> mtu %d'); orice qdisc netem ramas se "
                  "sterge cu 'sudo tc qdisc del dev <if> root'." % (a.mtu, a.mtu),
                masurat)
    return (True, "P5: MTU %d pe ambele capete, niciun qdisc netem -- banc curat"
            % a.mtu, masurat)


PORTI = [
    ("P1", "viteza si duplex", poarta1_link),
    ("P2", "offload-uri oprite", poarta2_offload),
    ("P3", "EEE", poarta3_eee),
    ("P4", "banda sustinuta pe cablu", poarta4_iperf),
    ("P5", "mediu curat (MTU + fara netem)", poarta5_mediu_curat),
]


# ---------------------------------------------------------------------------
# RAPORT
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def scrie_raport(cale, raport):
    """Scrie raportul JSON. Se scrie SI la abort -- un preflight picat e la fel de
    mult provenienta ca unul trecut."""
    cale = os.path.expanduser(cale)
    parinte = os.path.dirname(os.path.abspath(cale))
    if parinte:
        os.makedirs(parinte, exist_ok=True)
    with open(cale, "w") as f:
        json.dump(raport, f, indent=2, sort_keys=False)
        f.write("\n")
    return os.path.abspath(cale)


# ---------------------------------------------------------------------------
# SELFTEST -- fixture REALE, zero retea
# ---------------------------------------------------------------------------

# Capturat pe masina asta (2026-08-07): '/usr/sbin/ethtool enp2s0 2>&1', fara root,
# cu cablul SCOS. Contine si linia 'netlink error' pe care parserul o ignora, si un
# TAB in interiorul '[ TP\t MII ]'.
FIX_ETHTOOL_ENP2S0_JOS = """netlink error: Operation not permitted
Settings for enp2s0:
	Supported ports: [ TP	 MII ]
	Supported link modes:   10baseT/Half 10baseT/Full
	                        100baseT/Half 100baseT/Full
	                        1000baseT/Full
	Supports auto-negotiation: Yes
	Advertised auto-negotiation: Yes
	Speed: Unknown!
	Duplex: Unknown! (255)
	Auto-negotiation: on
	Port: Twisted Pair
	PHYAD: 0
	Transceiver: external
	MDI-X: Unknown
	Link detected: no
"""

# Aceeasi forma, cu legatura ridicata la gigabit (cazul care TREBUIE sa treaca).
FIX_ETHTOOL_1000_FULL = """Settings for enp2s0:
	Supported ports: [ TP	 MII ]
	Speed: 1000Mb/s
	Duplex: Full
	Auto-negotiation: on
	Port: Twisted Pair
	Link detected: yes
"""

FIX_ETHTOOL_100_FULL = """Settings for enp2s0:
	Speed: 100Mb/s
	Duplex: Full
	Link detected: yes
"""

FIX_ETHTOOL_1000_HALF = """Settings for enp2s0:
	Speed: 1000Mb/s
	Duplex: Half
	Link detected: yes
"""

# Capturat pe masina asta (2026-08-07): '/usr/sbin/ethtool -k wlp4s0'. Cazuri urate
# REALE: 'off [requested on]', 'off [fixed]', sub-optiuni indentate cu TAB si un gro
# ramas 'on'.
FIX_ETHTOOL_K_WLP4S0 = """Features for wlp4s0:
rx-checksumming: on
tx-checksumming: off
	tx-checksum-ipv4: off [fixed]
scatter-gather: off
tcp-segmentation-offload: off
	tx-tcp-segmentation: off [fixed]
	tx-tcp-ecn-segmentation: off [fixed]
	tx-tcp-mangleid-segmentation: off [fixed]
	tx-tcp6-segmentation: off [fixed]
	tx-tcp-accecn-segmentation: off [fixed]
udp-fragmentation-offload: off
generic-segmentation-offload: off [requested on]
generic-receive-offload: on
large-receive-offload: off [fixed]
rx-vlan-offload: off [fixed]
tx-vlan-offload: off [fixed]
tx-gso-robust: off [fixed]
tx-gso-partial: off [fixed]
"""

# Acelasi format, dupa 'ethtool -K ... gro off' (cazul care TREBUIE sa treaca).
FIX_ETHTOOL_K_TOATE_OFF = """Features for enp2s0:
rx-checksumming: on
tcp-segmentation-offload: off
	tx-tcp-segmentation: off [fixed]
generic-segmentation-offload: off [requested on]
generic-receive-offload: off
large-receive-offload: off [fixed]
"""

# NIC care FORTEAZA gro pornit: 'on [fixed]' nu se poate opri din software.
FIX_ETHTOOL_K_ON_FIXED = """Features for enp2s0:
tcp-segmentation-offload: off
generic-segmentation-offload: off
generic-receive-offload: on [fixed]
large-receive-offload: off [fixed]
"""

# Driver care nu raporteaza deloc lro (nu se poate DOVEDI ca e off).
FIX_ETHTOOL_K_FARA_LRO = """Features for enp2s0:
tcp-segmentation-offload: off
generic-segmentation-offload: off
generic-receive-offload: off
"""

# Capturat pe masina asta (2026-08-07): 'ethtool --show-eee enp2s0' (rc=0).
FIX_EEE_ENP2S0 = """EEE settings for enp2s0:
	EEE status: enabled - inactive
	Tx LPI: 0 (us)
	Supported EEE link modes:  100baseT/Full
	                           1000baseT/Full
	Advertised EEE link modes:  100baseT/Full
	                            1000baseT/Full
	Link partner advertised EEE link modes:  Not reported
"""

# Capturat pe masina asta (2026-08-07): 'ethtool --show-eee wlp4s0 2>&1', rc=1.
FIX_EEE_NESUPORTAT = "netlink error: Operation not supported\n"

FIX_EEE_DISABLED = """EEE settings for enp2s0:
	EEE status: disabled
	Tx LPI: 0 (us)
"""

# Linii REALE de 'tc qdisc show', din jurnalul campaniei C2 (prefixul de timp al
# orchestratorului e lasat INTENTIONAT, ca sa dovedeasca toleranta parserului):
# ~/DATE_CAMPANIE/C2_HIL_WIFI64_20260803/orchestrator_20260803_235016.log
FIX_TC_NETEM_LIMIT_1000 = ("2026-08-03T23:55:00+03:00   | qdisc netem 8005: root "
                           "refcnt 2 limit 1000 loss gemodel p 15% r 85% 1-h 100% "
                           "1-k 0%\n")
# Capturat pe masina asta (2026-08-07): 'tc qdisc show dev wlp4s0'.
FIX_TC_NOQUEUE = "qdisc noqueue 0: root refcnt 2\n"
FIX_TC_NETEM_LIMIT_100000 = ("qdisc netem 8006: root refcnt 2 limit 100000 delay "
                             "0ms loss 0%\n")
# Copil cu 'parent' inaintea radacinii: parserul trebuie sa aleaga radacina.
FIX_TC_MQ = """qdisc mq 0: root
qdisc fq_codel 0: parent :4 limit 10240p flows 1024 quantum 1514
qdisc fq_codel 0: parent :3 limit 10240p flows 1024 quantum 1514
"""

# FIXTURE RECONSTRUIT, NU capturat: iperf3 nu e instalat pe masina asta
# ('command -v iperf3' -> gol), deci JSON-ul de mai jos e scris dupa contractul
# documentat al lui 'iperf3 -J' (obiect cu end.sum_sent / end.sum_received, fiecare
# cu bits_per_second si seconds; la esec, obiect cu cheia 'error'). E SINGURUL
# fixture din acest selftest care nu e o iesire reala -- de confirmat la prima
# rulare pe banc cu 'iperf3 -c <peer> -J | head -40'.
FIX_IPERF_OK = json.dumps({
    "start": {"connected": [{"socket": 5}]},
    "intervals": [],
    "end": {
        "sum_sent": {"seconds": 30.0, "bytes": 3538944000,
                     "bits_per_second": 943718400.0, "retransmits": 12},
        "sum_received": {"seconds": 30.0, "bytes": 3532000000,
                         "bits_per_second": 941866666.0},
    },
})
FIX_IPERF_LENT = json.dumps({
    "end": {"sum_sent": {"seconds": 30.0, "bits_per_second": 94371840.0,
                         "retransmits": 0},
            "sum_received": {"seconds": 30.0, "bits_per_second": 93800000.0}},
})
FIX_IPERF_SCURT = json.dumps({
    "end": {"sum_sent": {"seconds": 3.1, "bits_per_second": 900000000.0,
                         "retransmits": 0},
            "sum_received": {"seconds": 3.1, "bits_per_second": 899000000.0}},
})
FIX_IPERF_EROARE = json.dumps({
    "error": "unable to connect to server - server may have stopped running or "
             "use a different port, number: Connection refused"})
FIX_IPERF_UDP = json.dumps({"end": {"sum": {"bits_per_second": 1000.0}}})
FIX_IPERF_GUNOI = "bash: line 1: iperf3: command not found\n"


_VERIF = [0]


def _ver(cond, mesaj):
    """Asertiune numarata: numarul tiparit la final NU poate ramane in urma codului."""
    _VERIF[0] += 1
    if not cond:
        raise AssertionError(mesaj)


# ---------------------------------------------------------------------------
# FIXTURE PENTRU NUCLEUL PUR (rezultate DUPA parsare, ca sa se poata testa decizia
# separat de parsare). Cifrele sunt alese ca sa fie realiste pe gigabit: 30 s la
# ~941 Mbit/s inseamna 3.53 GB, adica ~2.44 milioane de segmente la MSS 1448; 1% din
# ele e ~24400, deci 1000 de retransmisii trec si 400000 pica.
# ---------------------------------------------------------------------------
_OCT_30S = int(941e6 / 8 * 30)


def _sens(intervale, secunde=30.0, retrans=1000, sent=941.0, recv=940.0,
          octeti=None, ok=True, eroare=None):
    return {"ok": ok, "mbps_sent": sent, "mbps_recv": recv, "secunde": secunde,
            "retransmisii": retrans, "octeti_sent": (_OCT_30S if octeti is None
                                                     else octeti),
            "intervale_mbps": list(intervale), "eroare": eroare, "raw_head": ""}


SENS_BUN = _sens([941.0] * 30)
# 941 timp de 5 s, apoi ZERO 25 de secunde: media iese 156.8, deci trecea pragul
SENS_PRABUSIT = _sens([941.0] * 5 + [0.0] * 25)
SENS_RETRANS = _sens([941.0] * 30, retrans=400000)
SENS_GAP = _sens([941.0] * 30, sent=941.0, recv=300.0)
SENS_SCURT = _sens([941.0] * 5, secunde=5.0)
SENS_FARA_INTERVALE = _sens([])
SENS_LENT = _sens([150.0] * 30, sent=150.0, recv=150.0)

RUTA_CABLU = {"iface": "enp2s0", "src": "198.51.100.1", "via": None, "raw": ""}
RUTA_WIFI = {"iface": "wlp4s0", "src": "203.0.113.14", "via": "203.0.113.1", "raw": ""}
QD_CURAT = {"kind": "noqueue", "limit": None, "linie": "qdisc noqueue 0: root"}
QD_NETEM = {"kind": "netem", "limit": 1000,
            "linie": "qdisc netem 8001: root limit 1000 delay 200ms"}
EEE_OFF = {"activ": None, "suportat": True, "status": "disabled", "rc": 0, "raw_head": ""}
EEE_ON = {"activ": None, "suportat": True, "status": "enabled - inactive", "rc": 0, "raw_head": ""}
EEE_NESUP = {"activ": None, "suportat": False, "status": None, "rc": 1, "raw_head": ""}
EEE_NECUNOSCUT = {"suportat": None, "status": None, "activ": None, "rc": 0,
                  "raw_head": "EEE settings for end0:"}
EEE_ACTIV = {"suportat": True, "status": "enabled - active", "activ": None, "rc": 0,
             "raw_head": ""}
EEE_ACTIV_CAMP = {"suportat": True, "status": "enabled", "activ": True, "rc": 0,
                  "raw_head": ""}


def _nucleu_asertii():
    """TOATE deciziile nucleului pur, intr-un singur loc. Mutantii de mai jos lovesc
    exact functiile chemate de aici; daca o asertie lipseste, mutantul corespunzator
    supravietuieste si suita o spune pe nume. Ridica AssertionError la prima abatere."""
    # --- P1 link
    assert verdict_link(parse_ethtool_link(FIX_ETHTOOL_1000_FULL))[0] is True
    assert verdict_link(parse_ethtool_link(FIX_ETHTOOL_100_FULL))[0] is False
    assert verdict_link(parse_ethtool_link(FIX_ETHTOOL_1000_HALF))[0] is False
    assert verdict_link(parse_ethtool_link(FIX_ETHTOOL_ENP2S0_JOS))[0] is False
    # EXACT 1000, nu '>= 1000': un 2.5GbE nu e bancul descris in metodologie
    assert verdict_link({"speed_raw": "2500Mb/s", "speed_mbps": 2500,
                         "duplex": "Full", "link_detected": True})[0] is False
    assert verdict_link({"speed_raw": "1000Mb/s", "speed_mbps": 1000,
                         "duplex": "Full", "link_detected": True},
                        cerut_mbps=100)[0] is False

    # --- P2 offloads
    assert verdict_offloads(parse_ethtool_features(FIX_ETHTOOL_K_TOATE_OFF))[0] is True
    assert verdict_offloads(parse_ethtool_features(FIX_ETHTOOL_K_ON_FIXED))[0] is False
    assert verdict_offloads(parse_ethtool_features(FIX_ETHTOOL_K_FARA_LRO))[0] is False

    # --- P3 EEE
    # Semantica de banc: FAIL doar cand EEE e DEMONSTRABIL activ. Cazurile 'nesuportat'
    # si 'necunoscut' TREBUIE sa treaca -- altfel poarta opreste bancul pe Raspberry Pi
    # din motivul gresit. Notele exista ca sa ramana urma in raport.
    assert verdict_eee(EEE_OFF)[0] is True
    assert verdict_eee(EEE_NESUP)[0] is True and verdict_eee(EEE_NESUP)[2]
    assert verdict_eee(EEE_NECUNOSCUT)[0] is True and verdict_eee(EEE_NECUNOSCUT)[2]
    assert verdict_eee(EEE_ON)[0] is True and verdict_eee(EEE_ON)[2]      # inactiv + nota
    assert verdict_eee(EEE_ACTIV)[0] is False
    assert verdict_eee(EEE_ACTIV_CAMP)[0] is False
    assert eee_este_activ(EEE_ON) is False and eee_este_activ(EEE_ACTIV) is True
    assert eee_este_activ(EEE_NECUNOSCUT) is None

    # --- MTU
    assert verdict_mtu(1500)[0] is True
    assert verdict_mtu(9000)[0] is False
    assert verdict_mtu(None)[0] is False

    # --- legare la cablu, stratul 1
    assert verdict_rutare(RUTA_CABLU, "enp2s0")[0] is True
    assert verdict_rutare(RUTA_WIFI, "enp2s0")[0] is False
    assert verdict_rutare({}, "enp2s0")[0] is False

    # --- legare la cablu, stratul 2
    assert verdict_delta_bytes(1000, 1000)[0] is True
    assert verdict_delta_bytes(960, 1000)[0] is True          # 96% >= 95%
    assert verdict_delta_bytes(500, 1000)[0] is False         # jumatate pe alta cale
    assert verdict_delta_bytes(0, 1000)[0] is False
    assert verdict_delta_bytes(None, 1000)[0] is False

    # --- mediu curat
    assert verdict_mediu_curat({"local": QD_CURAT, "remote": QD_CURAT})[0] is True
    assert verdict_mediu_curat({"local": QD_CURAT, "remote": QD_NETEM})[0] is False

    # --- P4 banda: fiecare criteriu separat, ca sa nu se acopere unul pe altul
    assert verdict_banda({"a": SENS_BUN}, 850.0, 30.0)[0] is True
    ok, mot = verdict_banda({"a": SENS_PRABUSIT}, 850.0, 30.0)
    assert ok is False and any("intervale" in m for m in mot), mot
    ok, mot = verdict_banda({"a": SENS_RETRANS}, 850.0, 30.0)
    assert ok is False and any("retransmisii" in m for m in mot), mot
    ok, mot = verdict_banda({"a": SENS_GAP}, 850.0, 30.0)
    assert ok is False and any("receptionat" in m for m in mot), mot
    ok, mot = verdict_banda({"a": SENS_SCURT}, 850.0, 30.0)
    assert ok is False and any("durat" in m for m in mot), mot
    ok, mot = verdict_banda({"a": SENS_FARA_INTERVALE}, 850.0, 30.0)
    assert ok is False and any("intervale" in m for m in mot), mot
    assert verdict_banda({"a": SENS_LENT}, 850.0, 30.0)[0] is False
    assert verdict_banda({}, 850.0, 30.0)[0] is False
    # media NU e criteriu: media lui SENS_PRABUSIT e peste vechiul prag de 105
    assert sum(SENS_PRABUSIT["intervale_mbps"]) / 30.0 > 105.0
    # un sens bun si unul rau => FAIL (nu se face media intre sensuri)
    assert verdict_banda({"a": SENS_BUN, "b": SENS_LENT}, 850.0, 30.0)[0] is False

    # --- P5 limita (functia ramane, chiar daca preflightul nu mai instaleaza netem:
    #     orchestratorul de campanie o foloseste ca sa dovedeasca limita aplicata)
    assert verdict_tc_limit({"kind": "netem", "limit": 100000, "linie": ""},
                            100000)[0] is True
    assert verdict_tc_limit({"kind": "netem", "limit": 1000, "linie": ""},
                            100000)[0] is False
    assert verdict_tc_limit({"kind": None, "limit": None, "linie": ""},
                            100000)[0] is False
    assert verdict_tc_limit({"kind": "netem", "limit": None, "linie": ""},
                            100000)[0] is False


# ---------------------------------------------------------------------------
# SUITA DE MUTANTI (A5). Fiecare intrare strica DELIBERAT o regula din nucleul pur;
# _nucleu_asertii() trebuie sa o prinda. Un singur supravietuitor = instrumentul
# ramane carantinat. Cele 14 de la revizia din 2026-08-13 sunt marcate 'v1'.
# ---------------------------------------------------------------------------
def _mutanti():
    g = globals()

    def m(nume, tinta, inlocuitor):
        return (nume, tinta, inlocuitor)

    vb, vl, vo, vt, vr, vd, vm, ve, vmtu = (
        g["verdict_banda"], g["verdict_link"], g["verdict_offloads"],
        g["verdict_tc_limit"], g["verdict_rutare"], g["verdict_delta_bytes"],
        g["verdict_mediu_curat"], g["verdict_eee"], g["verdict_mtu"])

    def banda_fara_prag(sensuri, prag=850.0, dur=None, *a, **k):
        return vb(sensuri, 0.0, dur, *a, **k)

    def banda_prag_inversat(sensuri, prag=850.0, dur=None, *a, **k):
        mot = [x for x in vb(sensuri, prag, dur, *a, **k)[1] if "intervale" not in x]
        return (not mot, mot)

    def banda_pe_medie(sensuri, prag=850.0, dur=None, *a, **k):
        # media in loc de fiecare interval -- exact regula inlocuita in v2.0
        mot = []
        for et in sorted(sensuri):
            r = sensuri[et]
            iv = r.get("intervale_mbps") or []
            if iv and sum(iv) / len(iv) < prag:
                mot.append("%s: medie sub prag" % et)
        return (not mot, mot)

    def banda_pe_sent(sensuri, prag=850.0, dur=None, *a, **k):
        mot = [x for x in vb(sensuri, prag, dur, *a, **k)[1] if "receptionat" not in x]
        return (not mot, mot)

    def banda_fara_durata(sensuri, prag=850.0, dur=None, *a, **k):
        return vb(sensuri, prag, None, *a, **k)

    def banda_fara_retrans(sensuri, prag=850.0, dur=None, *a, **k):
        return vb(sensuri, prag, dur, 1e9, *a[1:], **k) if a else \
            vb(sensuri, prag, dur, 1e9)

    def banda_prag_mic(sensuri, prag=850.0, dur=None, *a, **k):
        return vb(sensuri, 105.0, dur, *a, **k)

    def link_mereu_ok(d, cerut_mbps=1000):
        return (True, "ok")

    def link_prag_100(d, cerut_mbps=1000):
        return vl(d, 100)

    def link_mai_mare_egal(d, cerut_mbps=1000):
        if d.get("speed_mbps") is not None and d["speed_mbps"] >= cerut_mbps \
                and d.get("duplex") == "Full" and d.get("link_detected") is not False:
            return (True, "ok")
        return vl(d, cerut_mbps)

    def offload_mereu_ok(feats):
        return (True, "ok", {})

    def offload_fixed_e_off(feats):
        f2 = dict(feats)
        for k2, v2 in list(f2.items()):
            if isinstance(v2, dict) and v2.get("fixed"):
                f2[k2] = dict(v2, stare="off")
        return vo(f2)

    def tc_doar_kind(q, limita):
        if not q or q.get("kind") != "netem":
            return (False, ["fara netem"])
        return (True, [])

    def tc_limita_1000(q, limita):
        return vt(q, 1000)

    def rutare_mereu_ok(ruta, iface):
        return (True, [])

    def rutare_ignora_iface(ruta, iface):
        return (True, []) if (ruta or {}).get("iface") else (False, ["fara iface"])

    def delta_mereu_ok(d, volum, prag=PRAG_DELTA_BYTES):
        return (True, [])

    def delta_prag_zero(d, volum, prag=PRAG_DELTA_BYTES):
        return vd(d, volum, 0.0)

    def mediu_doar_avertisment(qd):
        return (True, [])

    def eee_activ_acceptat(eee):
        return (True, [], [])

    def eee_nesuportat_pica(eee):
        # REGRESIA CARE AR OPRI BANCUL PE Pi: driverul nu expune EEE si poarta pica
        if eee and eee.get("suportat") is False:
            return (False, ["nesuportat"], [])
        return ve(eee)

    def eee_necunoscut_pica(eee):
        # a doua regresie Pi-safe: format nerecunoscut tratat ca esec
        if eee and eee.get("suportat") is None:
            return (False, ["necunoscut"], [])
        return ve(eee)

    def eee_fara_note(eee):
        # notele dispar: 'enabled - inactive' ar trece FARA urma in raport
        ok, mot, _ = ve(eee)
        return (ok, mot, [])

    def mtu_orice(mtu, cerut=1500):
        return (True, [])

    return [
        # --- clasa PRAG (v1 + noi)
        m("v1 P4: pragul de banda ELIMINAT", "verdict_banda", banda_fara_prag),
        m("v1 P4: comparatia de prag inversata", "verdict_banda", banda_prag_inversat),
        m("v1 P4: prag implicit 850 -> 105", "verdict_banda", banda_prag_mic),
        m("NOU P4: media in loc de fiecare interval", "verdict_banda", banda_pe_medie),
        m("v1 P4: verdict pe sent, nu pe recv", "verdict_banda", banda_pe_sent),
        m("v1 P4: verificarea de durata eliminata", "verdict_banda", banda_fara_durata),
        m("NOU P4: retransmisiile nu mai conteaza", "verdict_banda", banda_fara_retrans),
        # --- clasa LEGARE LA MEDIU (noua)
        m("NOU P4: rutarea nu se mai verifica", "verdict_rutare", rutare_mereu_ok),
        m("NOU P4: rutarea accepta orice interfata", "verdict_rutare",
          rutare_ignora_iface),
        m("NOU P4: delta de bytes nu se mai verifica", "verdict_delta_bytes",
          delta_mereu_ok),
        m("NOU P4: pragul delta de bytes = 0", "verdict_delta_bytes", delta_prag_zero),
        m("NOU P4/P5: netem preexistent redevine avertisment", "verdict_mediu_curat",
          mediu_doar_avertisment),
        # --- clasa P1/P2/P3/P5 (v1)
        m("v1 P1: verdictul ignorat, poarta trece mereu", "verdict_link", link_mereu_ok),
        m("v1 P1: viteza ceruta 1000 -> 100", "verdict_link", link_prag_100),
        m("v1 P1: EXACT 1000 devine >= 1000", "verdict_link", link_mai_mare_egal),
        m("v1 P2: verdictul ignorat, poarta trece mereu", "verdict_offloads",
          offload_mereu_ok),
        m("v1 P2: 'on [fixed]' acceptat ca off", "verdict_offloads", offload_fixed_e_off),
        m("v1 P5: limita nu se mai compara (doar kind)", "verdict_tc_limit", tc_doar_kind),
        m("v1 P5: limita ceruta 100000 -> 1000", "verdict_tc_limit", tc_limita_1000),
        m("NOU P3: EEE ACTIV acceptat ca oprit", "verdict_eee", eee_activ_acceptat),
        m("NOU P3: EEE nesuportat pica (ar opri bancul pe Pi)", "verdict_eee",
          eee_nesuportat_pica),
        m("NOU P3: EEE necunoscut pica (ar opri bancul pe Pi)", "verdict_eee",
          eee_necunoscut_pica),
        m("NOU P3: notele EEE dispar din raport", "verdict_eee", eee_fara_note),
        m("NOU P5: MTU-ul nu mai conteaza", "verdict_mtu", mtu_orice),
    ]


class _Args(object):
    """Argumente minimale pentru a rula portile in selftest, fara CLI."""

    def __init__(self, **kw):
        self.iface_local = "enp2s0"
        self.iface_remote = "enp3s0"
        self.remote = "user@m2"
        self.peer_ip = "198.51.100.2"
        self.local_ip = "198.51.100.1"
        self.prag_mbps = PRAG_MBPS
        self.iperf_dur = 30.0
        self.iperf_port = 5201
        self.mtu = 1500
        self.tc_limit = 100000
        self.cond_limit = "ideal"
        self.cerut_mbps = 1000
        self.peer_ip_dedus = False
        self.dry = False
        self.__dict__.update(kw)


class _ExecutorFals(Executor):
    """Executor care raspunde dintr-o tabela de fixture, dupa un fragment din comanda.
    NU atinge reteaua, NU porneste procese: cheia e ca portile sa poata fi rulate
    INTREGI in selftest, nu doar functiile lor de verdict."""

    def __init__(self, raspunsuri):
        Executor.__init__(self, dry=False, remote="user@m2")
        self.raspunsuri = raspunsuri
        self.vazute = []

    def sh(self, cmd, host="local", timeout=None):
        self.vazute.append((host, cmd))
        for fragment, val in self.raspunsuri:
            if fragment in cmd:
                if callable(val):
                    return val(host, cmd)
                return val
        return (0, "", "")


def _iperf_json(mbps, retrans, secunde=30.0, intervale=None):
    """Construieste o iesire iperf3 -J realista, cu intervale."""
    octeti = int(mbps * 1e6 / 8 * secunde)
    iv = intervale if intervale is not None else [mbps] * int(secunde)
    return json.dumps({
        "intervals": [{"sum": {"bits_per_second": v * 1e6}} for v in iv],
        "end": {"sum_sent": {"bits_per_second": mbps * 1e6, "seconds": secunde,
                             "retransmits": retrans, "bytes": octeti},
                "sum_received": {"bits_per_second": mbps * 1e6, "seconds": secunde}}})


def _ruta_buna(host, cmd):
    """Ruta care iese pe interfata CABLATA a capatului interogat."""
    iface = "enp2s0" if host == "local" else "enp3s0"
    tinta = "198.51.100.2" if host == "local" else "198.51.100.1"
    sursa = "198.51.100.1" if host == "local" else "198.51.100.2"
    return (0, "%s dev %s src %s\n" % (tinta, iface, sursa), "")


def _stat_care_creste(mbps=941.0, secunde=30.0):
    """Contoare care cresc exact cu volumul transferat de iperf3 (doua sensuri).
    Prima citire per capat e 'inainte', a doua 'dupa'. Parametrizat pe rata, ca fiecare
    scenariu sa pice pe motivul pe care il DEMONSTREAZA, nu pe contabilitate."""
    volum = int(mbps * 1e6 / 8 * secunde) * 2
    stare = {}

    def f(host, cmd):
        n = stare.get(host, 0)
        stare[host] = n + 1
        v = 0 if n == 0 else volum
        return (0, "%d\n%d\n" % (v, 0), "")
    return f


def _demonstratie_banc_rupt():
    """ACCEPTAREA A5: bancul rupt din revizia din 2026-08-13 trebuie sa PICE, cu
    motivele enumerate. Pana la v2.0 exact acest banc dadea 'PREFLIGHT OK (5/5)',
    cod 0: netem instalat pe ambele capete, 150 Mbit/s din ~941, 400000 de
    retransmisii, EEE pornit si --peer-ip pe alt subnet decat interfata cablata.

    Se ruleaza PORTILE INTREGI, nu doar verdictele, ca sa se dovedeasca si cablajul
    dintre masuratoare si decizie."""
    rezultate = {}

    # --- P3: EEE ACTIV pe link -> singurul caz de FAIL
    ex = _ExecutorFals([("--show-eee", (0, "EEE settings for enp2s0:\n"
                                          "\tEEE status: enabled - active\n", ""))])
    ok, mesaj, _ = poarta3_eee(ex, _Args())
    rezultate["P3 EEE ACTIV pe link"] = (ok, mesaj)

    # --- P3: Raspberry Pi fara EEE -> TREBUIE sa treaca (control pozitiv Pi)
    ex = _ExecutorFals([("--show-eee", (1, "", "netlink error: Operation not "
                                             "supported\n"))])
    ok, mesaj, _ = poarta3_eee(ex, _Args())
    rezultate["P3 Pi fara EEE (control pozitiv)"] = (ok, mesaj)

    # --- P3: format nerecunoscut -> trece, dar cu urma in raport (control pozitiv Pi)
    ex = _ExecutorFals([("--show-eee", (0, "EEE settings for end0:\n\t(alt format)\n",
                                        ""))])
    ok, mesaj, _ = poarta3_eee(ex, _Args())
    rezultate["P3 format nerecunoscut (control pozitiv)"] = (ok, mesaj)

    # --- P4: peer pe alt subnet (ruta iese pe Wi-Fi)
    ex = _ExecutorFals([("ip route get",
                         (0, "203.0.113.50 via 203.0.113.1 dev wlp4s0 src 203.0.113.14\n",
                          ""))])
    ok, mesaj, _ = poarta4_iperf(ex, _Args(peer_ip="203.0.113.50"))
    rezultate["P4 peer pe alt subnet"] = (ok, mesaj)

    # --- P4: netem preexistent pe ambele capete
    ex = _ExecutorFals([
        ("ip route get", _ruta_buna),
        ("tc qdisc show", (0, "qdisc netem 8001: root refcnt 2 limit 1000 "
                              "delay 200ms  50ms loss 15%\n", ""))])
    ok, mesaj, _ = poarta4_iperf(ex, _Args())
    rezultate["P4 netem preexistent"] = (ok, mesaj)

    # --- P4: legatura curata dar 150 Mbit/s si 400000 retransmisii
    ex = _ExecutorFals([
        ("ip route get", _ruta_buna),
        ("tc qdisc show", (0, "qdisc noqueue 0: root refcnt 2\n", "")),
        ("statistics", _stat_care_creste(150.0)),
        ("iperf3 -c", (0, _iperf_json(150.0, 400000), ""))])
    ok, mesaj, _ = poarta4_iperf(ex, _Args())
    rezultate["P4 150 Mbit/s + 400k retransmisii"] = (ok, mesaj)

    # --- P4: legatura care se PRABUSESTE (941 cinci secunde, apoi zero) -- media
    # peste 30 s iese 156.8 si trecea vechiul prag de 105
    ex = _ExecutorFals([
        ("ip route get", _ruta_buna),
        ("tc qdisc show", (0, "qdisc noqueue 0: root refcnt 2\n", "")),
        ("statistics", _stat_care_creste(156.8)),
        ("iperf3 -c", (0, _iperf_json(156.8, 1000, intervale=[941.0] * 5 + [0.0] * 25),
                       ""))])
    ok, mesaj, _ = poarta4_iperf(ex, _Args())
    rezultate["P4 legatura care se prabuseste"] = (ok, mesaj)

    # --- P4: banda buna, dar octetii NU trec prin interfata cablata
    contor = {"n": 0}

    def _stat(host, cmd):
        contor["n"] += 1
        # contoarele nu cresc: traficul a mers pe alta interfata
        return (0, "1000\n1000\n", "")

    ex = _ExecutorFals([
        ("ip route get", _ruta_buna),
        ("tc qdisc show", (0, "qdisc noqueue 0: root refcnt 2\n", "")),
        ("statistics", _stat),
        ("iperf3 -c", (0, _iperf_json(941.0, 1000), ""))])
    ok, mesaj, _ = poarta4_iperf(ex, _Args())
    rezultate["P4 octeti pe alta interfata"] = (ok, mesaj)

    # --- P4: TOTUL bun -> trebuie sa TREACA (altfel poarta ar fi doar pesimista)
    ex = _ExecutorFals([
        ("ip route get", _ruta_buna),
        ("tc qdisc show", (0, "qdisc noqueue 0: root refcnt 2\n", "")),
        ("statistics", _stat_care_creste(941.0)),
        ("iperf3 -c", (0, _iperf_json(941.0, 1000), ""))])
    ok_bun, mesaj_bun, _ = poarta4_iperf(ex, _Args())
    rezultate["P4 banc SANATOS (control pozitiv)"] = (ok_bun, mesaj_bun)

    # --- P5: netem ramas
    ex = _ExecutorFals([
        ("/mtu", (0, "1500\n", "")),
        ("tc qdisc show", (0, "qdisc netem 8001: root limit 1000 delay 200ms\n", ""))])
    ok, mesaj, _ = poarta5_mediu_curat(ex, _Args())
    rezultate["P5 netem ramas"] = (ok, mesaj)

    # --- P5: MTU gresit
    ex = _ExecutorFals([
        ("/mtu", (0, "9000\n", "")),
        ("tc qdisc show", (0, "qdisc noqueue 0: root\n", ""))])
    ok, mesaj, _ = poarta5_mediu_curat(ex, _Args())
    rezultate["P5 MTU 9000"] = (ok, mesaj)

    return rezultate


def _ruleaza_mutanti(verbose=False):
    """Aplica fiecare mutant si cere ca _nucleu_asertii() sa il OMOARE.
    Intoarce (injectati, omorati, supravietuitori[])."""
    g = globals()
    supravietuitori = []
    mut = _mutanti()
    for nume, tinta, inlocuitor in mut:
        original = g[tinta]
        g[tinta] = inlocuitor
        try:
            _nucleu_asertii()
        except AssertionError:
            omorat = True
        except Exception as e:
            omorat = True                       # o exceptie e tot o prindere
            if verbose:
                print("    (mutant '%s' a dat %s)" % (nume, type(e).__name__))
        else:
            omorat = False
        finally:
            g[tinta] = original
        if not omorat:
            supravietuitori.append(nume)
        elif verbose:
            print("    omorat: %s" % nume)
    return (len(mut), len(mut) - len(supravietuitori), supravietuitori)


def _selftest():
    """Verifica parserele pe iesiri REALE (vezi fixture-le de mai sus) si logica de
    verdict, inclusiv cazurile urate. NU atinge reteaua, NU ruleaza sudo, NU scrie
    in arhiva."""
    # --- P1: ethtool <iface> -------------------------------------------------
    d = parse_ethtool_link(FIX_ETHTOOL_ENP2S0_JOS)
    _ver(d["speed_raw"] == "Unknown!" and d["speed_mbps"] is None, d)
    _ver(d["duplex"] == "Unknown! (255)" and d["link_detected"] is False, d)
    _ver(d["iface_raportat"] == "enp2s0", d)
    ok, motiv = verdict_link(d)
    _ver(not ok and "Link detected: no" in motiv, motiv)

    d = parse_ethtool_link(FIX_ETHTOOL_1000_FULL)
    _ver(d["speed_mbps"] == 1000 and d["duplex"] == "Full", d)
    ok, motiv = verdict_link(d)
    _ver(ok, motiv)

    d = parse_ethtool_link(FIX_ETHTOOL_100_FULL)
    _ver(d["speed_mbps"] == 100, d)
    ok, motiv = verdict_link(d)
    _ver(not ok and "100Mb/s" in motiv, motiv)

    ok, motiv = verdict_link(parse_ethtool_link(FIX_ETHTOOL_1000_HALF))
    _ver(not ok and "Half" in motiv, motiv)

    ok, motiv = verdict_link(parse_ethtool_link(""))
    _ver(not ok and "nici Speed" in motiv, motiv)

    # --- P2: ethtool -k ------------------------------------------------------
    f = parse_ethtool_features(FIX_ETHTOOL_K_WLP4S0)
    _ver(f["generic-segmentation-offload"]["stare"] == "off", f["generic-segmentation-offload"])
    _ver(f["generic-segmentation-offload"]["requested"] is True, "off [requested on]")
    _ver(f["large-receive-offload"]["stare"] == "off"
         and f["large-receive-offload"]["fixed"] is True, f["large-receive-offload"])
    _ver(f["tcp-segmentation-offload"]["indentat"] is False, "nivelul zero")
    _ver(f["tx-tcp-segmentation"]["indentat"] is True, "sub-optiune indentata cu TAB")
    _ver("Features" not in " ".join(f.keys()), "antetul nu e optiune")
    ok, motiv, m = verdict_offloads(f)
    _ver(not ok and "generic-receive-offload" in motiv, motiv)
    _ver(m["gso"] == "off [requested on]" and m["lro"] == "off [fixed]", m)

    ok, motiv, m = verdict_offloads(parse_ethtool_features(FIX_ETHTOOL_K_TOATE_OFF))
    _ver(ok, motiv)
    _ver(m["tso"] == "off" and m["gro"] == "off", m)

    ok, motiv, m = verdict_offloads(parse_ethtool_features(FIX_ETHTOOL_K_ON_FIXED))
    _ver(not ok and "FORTEAZA" in motiv, motiv)

    ok, motiv, m = verdict_offloads(parse_ethtool_features(FIX_ETHTOOL_K_FARA_LRO))
    _ver(not ok and "NU raporteaza" in motiv and m["lro"] is None, motiv)

    # --- P3: EEE -------------------------------------------------------------
    e = parse_eee(FIX_EEE_ENP2S0, 0)
    _ver(e["suportat"] is True and e["status"] == "enabled - inactive", e)
    _ver(eee_este_oprit(e["status"]) is False, "'enabled - inactive' NU e oprit")

    e = parse_eee(FIX_EEE_NESUPORTAT, 1)
    _ver(e["suportat"] is False and e["status"] is None, e)

    e = parse_eee(FIX_EEE_DISABLED, 0)
    _ver(e["suportat"] is True and eee_este_oprit(e["status"]) is True, e)

    e = parse_eee("", 1)
    _ver(e["suportat"] is False, e)

    # --- P4: iperf3 ----------------------------------------------------------
    r = parse_iperf3_json(FIX_IPERF_OK)
    _ver(r["ok"] and abs(r["mbps_recv"] - 941.867) < 0.01, r)
    _ver(abs(r["mbps_sent"] - 943.718) < 0.01 and r["retransmisii"] == 12, r)
    _ver(r["secunde"] == 30.0, r)
    _ver(r["mbps_recv"] >= 105.0, "gigabit trece pragul")

    r = parse_iperf3_json(FIX_IPERF_LENT)
    _ver(r["ok"] and abs(r["mbps_recv"] - 93.8) < 0.01, r)
    _ver(r["mbps_recv"] < 105.0, "cifra de 100Mb/s pica pragul")

    r = parse_iperf3_json(FIX_IPERF_SCURT)
    _ver(r["ok"] and r["secunde"] == 3.1, r)
    _ver(r["secunde"] < 0.9 * 30.0, "rulare prea scurta = NU e sustinut")

    r = parse_iperf3_json(FIX_IPERF_EROARE)
    _ver(not r["ok"] and "Connection refused" in r["eroare"], r)

    r = parse_iperf3_json(FIX_IPERF_UDP)
    _ver(not r["ok"] and "sum_sent" in r["eroare"], r)

    r = parse_iperf3_json(FIX_IPERF_GUNOI)
    _ver(not r["ok"] and "NU e JSON" in r["eroare"], r)
    _ver(not parse_iperf3_json("")["ok"], "iesire goala = esec")
    _ver("GOALA" in parse_iperf3_json("   ")["eroare"], "spatii = iesire goala")

    # --- P5: tc --------------------------------------------------------------
    q = parse_tc_qdisc(FIX_TC_NETEM_LIMIT_1000)
    _ver(q["kind"] == "netem" and q["limit"] == 1000, q)
    _ver(q["linie"].startswith("qdisc netem 8005:"), "prefixul de jurnal e taiat")

    q = parse_tc_qdisc(FIX_TC_NOQUEUE)
    _ver(q["kind"] == "noqueue" and q["limit"] is None, q)

    q = parse_tc_qdisc(FIX_TC_NETEM_LIMIT_100000)
    _ver(q["kind"] == "netem" and q["limit"] == 100000, q)

    q = parse_tc_qdisc(FIX_TC_MQ)
    _ver(q["kind"] == "mq" and q["limit"] is None,
         "radacina, nu copilul fq_codel cu 'limit 10240p'")

    q = parse_tc_qdisc("")
    _ver(q["kind"] is None and q["limit"] is None, q)

    # tc care IGNORA limita: se cere 100000, show raporteaza 1000 -> poarta pica
    _ver(parse_tc_qdisc(FIX_TC_NETEM_LIMIT_1000)["limit"] != 100000,
         "tc a ignorat limita")

    # --- P5: comanda, cu bench_core ca SURSA UNICA ---------------------------
    ideal = conditie_dupa_nume("ideal")
    c = netem_cmd_cu_limita("enp2s0", ideal, 100000)
    _ver(c == "tc qdisc replace dev enp2s0 root netem limit 100000 "
              "delay 0ms 0ms loss 0.0%", c)
    _ver(c.replace(" limit 100000", "", 1) == netem_cmd("enp2s0", ideal),
         "limita e SINGURA diferenta fata de bench_core.netem_cmd")
    _ver(parse_tc_qdisc("qdisc netem 8007: root refcnt 2 limit 100000 delay 0ms "
                        "loss 0%")["limit"] == 100000, "dus-intors comanda->show")
    bern = conditie_dupa_nume("bern_15")
    cb = netem_cmd_cu_limita("eth0", bern, 100000)
    _ver(" root netem limit 100000 delay 0ms 0ms loss gemodel 15.000%" in cb, cb)
    _ver(limita_nu_persista(ideal) is True,
         "bench_core.netem_cmd NU emite 'limit' -> limita P5 nu supravietuieste "
         "primei aplicari de conditie")
    try:
        conditie_dupa_nume("nu_exista")
        _ver(False, "conditie inexistenta trebuia sa arunce")
    except KeyError:
        _ver(True, "")

    # --- arhiva sigilata -----------------------------------------------------
    _ver(cale_raport_permisa(os.path.join(PERMIS, "x.json")) is True, "ANALIZA_C2 e ok")
    _ver(cale_raport_permisa(os.path.join(SIGILAT, "x.json")) is False,
         "radacina DATE_CAMPANIE e SIGILATA")
    _ver(cale_raport_permisa(os.path.join(SIGILAT, "C2_HIL_WIFI_20260801", "x.json"))
         is False, "arhiva de campanie e SIGILATA")
    _ver(cale_raport_permisa("/tmp/x.json") is True, "in afara arhivei e ok")

    # --- executorul in mod --dry NU executa nimic ----------------------------
    print("-- verificare mod --dry: cele doua comenzi de mai jos sunt DOAR tiparite --")
    ex = Executor(dry=True, remote="user@exemplu")
    rc, out, err = ex.sh("ethtool enp2s0", host="local")
    _ver((rc, out, err) == (0, "", ""), "dry nu produce iesire")
    ex.sh("sudo -n tc qdisc del dev eth0 root", host="remote")
    _ver(len(ex.comenzi) == 2 and all(not c["executat"] for c in ex.comenzi),
         ex.comenzi)
    _ver(ex.comenzi[1]["argv_afisat"].startswith("ssh -o BatchMode=yes"),
         ex.comenzi[1])

    # --- NUCLEUL PUR si SUITA DE MUTANTI (v2.0) ---
    print("-- nucleul pur de verdict --")
    _nucleu_asertii()
    _VERIF[0] += 1
    print("   toate deciziile nucleului pur: OK")
    print("-- suita de mutanti (A5) --")
    inj, om, supr = _ruleaza_mutanti()
    print("   mutanti injectati=%d  omorati=%d  supravietuitori=%d" % (inj, om, len(supr)))
    for x in supr:
        print("   SUPRAVIETUITOR: %s" % x)
    _ver(not supr, "toti mutantii trebuie omoriti; supravietuitori: %s" % supr)
    _ver(inj >= 22, "suita de mutanti trebuie sa acopere cel putin 22 de regresii")
    print("-- demonstratia A5: bancul rupt din revizie --")
    dem = _demonstratie_banc_rupt()
    for nume in sorted(dem):
        ok, mesaj = dem[nume]
        prima = mesaj.splitlines()[0] if mesaj else ""
        print("   %-42s %s  %s" % (nume, "TRECE" if ok else "PICA ", prima[:74]))
    # fiecare scenariu rupt trebuie sa PICE, iar controlul pozitiv sa TREACA.
    # Fara controlul pozitiv, o poarta care intoarce mereu False ar trece testul.
    for nume, (ok, mesaj) in dem.items():
        if "control pozitiv" in nume:
            _ver(ok, "bancul SANATOS trebuie sa treaca P4 (control pozitiv): %s" % mesaj)
        else:
            _ver(not ok, "scenariul rupt '%s' trebuie sa PICE" % nume)
    _ver(any("rutare" in m or "ruteaza" in m for _, m in dem.values()),
         "motivul de rutare trebuie sa apara explicit")
    _ver(any("netem" in m for _, m in dem.values()),
         "motivul de netem preexistent trebuie sa apara explicit")
    _ver(any("retransmisii" in m for _, m in dem.values()),
         "motivul de retransmisii trebuie sa apara explicit")
    _ver(any("contoarele" in m or "interfetei cablate" in m for _, m in dem.values()),
         "motivul de delta-bytes trebuie sa apara explicit")
    _ver(any("MTU" in m for _, m in dem.values()),
         "motivul de MTU trebuie sa apara explicit")
    _ver(any("intervale de 1 s sub prag" in m for _, m in dem.values()),
         "prabusirea trebuie raportata pe INTERVALE, nu pe medie")
    _ver(any("EEE este ACTIV" in m for _, m in dem.values()),
         "FAIL-ul de EEE trebuie sa spuna ca e ACTIV, nu doar 'pornit'")
    _ver(any("nesuportat" in m for _, m in dem.values()),
         "cazul Pi fara EEE trebuie sa lase o nota in raport, nu sa taca")
    _ver(any("NECUNOSCUTA" in m for _, m in dem.values()),
         "formatul nerecunoscut trebuie notat, nu trecut in tacere")

    print("SELFTEST hil_wired_preflight OK (%d verificari, %d mutanti omoriti %d/%d)."
          % (_VERIF[0], om, om, inj))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main(argv):
    # --selftest se trateaza INAINTE de argparse: de la v2.0 --iface-remote e
    # obligatoriu, iar selftestul nu are nevoie de niciun argument de banc ca sa ruleze.
    if "--selftest" in argv:
        _selftest()
        return 0
    ap = argparse.ArgumentParser(
        prog="hil_wired_preflight.py",
        description="Preflight in 5 porti pentru bancul HIL cablat (abort la prima picata).")
    ap.add_argument("--iface-local", default="enp2s0",
                    help="NIC-ul cablat de pe masina asta (implicit: enp2s0)")
    # OBLIGATORIU, fara default. Pana la v2.0 avea implicit 'eth0', ceea ce contrazicea
    # direct docstringul care promitea ca se da explicit -- si pe Linux modern eth0 de
    # obicei nici nu exista, deci portile picau cu un mesaj despre interfata gresita in
    # loc sa spuna ca lipseste argumentul.
    ap.add_argument("--iface-remote", required=True,
                    help="NIC-ul cablat de pe M2 (OBLIGATORIU, fara implicit)")
    ap.add_argument("--remote", default=None,
                    help="tinta ssh a lui M2, ex. ubuntu@192.0.2.20 (OBLIGATORIU)")
    ap.add_argument("--peer-ip", default=None,
                    help="adresa lui M2 PE CABLU, pentru iperf3 (implicit: gazda din "
                         "--remote; da-o explicit daca ssh merge pe alta cale)")
    ap.add_argument("--prag-mbps", type=float, default=PRAG_MBPS,
                    # argparse formateaza help-ul INCA o data, cu un dict ca
                    # operand: procentul literal trebuie sa ajunga la el ca '%%',
                    # deci aici se scrie '%%%%'. Fara asta, '~90%% din' devine
                    # conversia '%% d' si --help crapa cu TypeError.
                    help="pragul P4 pe FIECARE interval de 1 s (implicit %.0f = ~90%%%% "
                         "din ce da o legatura gigabit sanatoasa)" % PRAG_MBPS)
    ap.add_argument("--mtu", type=int, default=1500,
                    help="MTU cerut pe ambele capete (implicit 1500)")
    ap.add_argument("--local-ip", default=None,
                    help="adresa lui M1 PE CABLU, pentru verificarea rutarii de pe M2")
    ap.add_argument("--iperf-dur", type=float, default=30.0,
                    help="durata unei rulari iperf3, secunde (implicit 30)")
    ap.add_argument("--iperf-port", type=int, default=5201, help="portul iperf3")
    ap.add_argument("--tc-limit", type=int, default=100000,
                    help="limita netem in PACHETE (implicit 100000)")
    ap.add_argument("--cond-limit", default="ideal",
                    help="conditia din bench_core.CONDITIONS aplicata de P5 "
                         "(implicit 'ideal' = netem cu pierdere 0.0%%)")
    ap.add_argument("--cerut-mbps", type=int, default=1000,
                    help="viteza ceruta de P1, Mb/s (implicit 1000)")
    ap.add_argument("--raport", default=None,
                    help="calea raportului JSON (implicit: %s/hil_wired_preflight_"
                         "<AAAALLZZ_HHMMSS>.json)" % PERMIS)
    ap.add_argument("--dry", action="store_true",
                    help="arata comenzile, NU le executa (merge fara banc si fara sudo)")
    ap.add_argument("--selftest", action="store_true",
                    help="verifica parserele pe fixture reale; NU atinge reteaua")
    a = ap.parse_args(argv)

    if a.selftest:
        _selftest()
        return 0

    if not a.remote:
        print("EROARE: --remote e obligatoriu (ex: --remote ubuntu@192.0.2.20). "
              "Nu exista gazda implicita: bancul cablat NU are IP hardcodat.",
              file=sys.stderr)
        return 2
    try:
        conditie_dupa_nume(a.cond_limit)
    except KeyError as e:
        print("EROARE: %s" % e, file=sys.stderr)
        return 2

    a.peer_ip_dedus = a.peer_ip is None
    if a.peer_ip is None:
        a.peer_ip = a.remote.split("@")[-1]

    ts = now_iso()
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cale_raport = a.raport or os.path.join(PERMIS, "hil_wired_preflight_%s.json" % stamp)
    if not cale_raport_permisa(cale_raport):
        print("EROARE: %s este in ~/DATE_CAMPANIE, care e SIGILAT si READ-ONLY. "
              "Scrie raportul in %s/ ." % (cale_raport, PERMIS), file=sys.stderr)
        return 2

    ex = Executor(dry=a.dry, remote=a.remote)
    print("== PREFLIGHT HIL CABLAT (mod=%s, %s) ==" % ("dry" if a.dry else "real", ts))
    print("   local=%s iface=%s | remote=%s iface=%s | peer_ip=%s%s"
          % (socket.gethostname(), a.iface_local, a.remote, a.iface_remote,
             a.peer_ip, " (DEDUS din --remote)" if a.peer_ip_dedus else ""))
    if a.peer_ip_dedus:
        print("   [NOTA] --peer-ip nu a fost dat: iperf3 va merge pe gazda ssh. Daca "
              "ssh-ul nu trece prin cablu, cifra P4 NU descrie cablul.")

    raport = {
        "script": "hil_wired_preflight.py",
        "versiune": VERSIUNE,
        "ts_iso": ts,
        "mod": "dry" if a.dry else "real",
        "argv": list(argv),
        "masina_locala": {"host": socket.gethostname(),
                          "kernel": platform.release(),
                          "iface": a.iface_local},
        "masina_remota": {"ssh": a.remote, "host": None, "kernel": None,
                          "iface": a.iface_remote, "peer_ip": a.peer_ip,
                          "peer_ip_dedus": a.peer_ip_dedus},
        "praguri": {"viteza_ceruta_mbps": a.cerut_mbps, "prag_iperf_mbps": a.prag_mbps,
                    "iperf_dur_s": a.iperf_dur, "tc_limit": a.tc_limit,
                    "cond_limit": a.cond_limit},
        "porti": [],
        "verdict": None,
        "poarta_picata": None,
        "note": [],
        "comenzi": ex.comenzi,
    }

    rc_id, out_id, _ = ex.sh("hostname && uname -r", host="remote")
    if not a.dry and rc_id == 0:
        linii = [x.strip() for x in out_id.splitlines() if x.strip()]
        if len(linii) >= 2:
            raport["masina_remota"]["host"] = linii[0]
            raport["masina_remota"]["kernel"] = linii[1]

    try:
        cond = conditie_dupa_nume(a.cond_limit)
        if limita_nu_persista(cond):
            nota = ("bench_core.netem_cmd NU emite 'limit', deci limita pusa de P5 "
                    "dispare la PRIMA aplicare de conditie a campaniei (run_campaign.py "
                    "pe M1, hil_netem.py pe M2) si qdisc-ul revine la implicitul 1000 "
                    "pachete. Ca sa reziste, adauga 'limit' in bench_core.netem_cmd.")
            raport["note"].append(nota)
            print("   [NOTA PERSISTENTA] %s" % nota)
    except KeyError:
        pass

    cod = 0
    for pid, nume, fn in PORTI:
        print("-- %s %s --" % (pid, nume))
        try:
            ok, mesaj, masurat = fn(ex, a)
        except Exception as e:                      # nicio poarta nu are voie sa lase
            ok = False                              # raportul nescris
            mesaj = "%s a aruncat %s: %s" % (pid, type(e).__name__, e)
            masurat = {"exceptie": str(e)}
        raport["porti"].append({"id": pid, "nume": nume, "ok": bool(ok),
                                "mesaj": mesaj, "masurat": masurat})
        if ok:
            print("   [OK] %s" % mesaj)
        else:
            print("   [ABORT] %s" % mesaj)
            raport["verdict"] = "ABORT"
            raport["poarta_picata"] = pid
            cod = 1
            break
    if cod == 0:
        # In --dry verdictul NU are voie sa fie 'OK': raportul ar arata ca un
        # preflight trecut, desi nu s-a masurat nimic.
        raport["verdict"] = "DRY" if a.dry else "OK"

    cale = scrie_raport(cale_raport, raport)
    print()
    if cod == 0 and a.dry:
        print("== DRY: 5/5 porti PARCURSE, ZERO masurate. Raport: %s ==" % cale)
        print("   Verdictul din raport e 'DRY', nu 'OK' -- nu il confunda cu un "
              "preflight trecut.")
        # Cod de iesire NENUL, dinadins: pana la v2.0 --dry iesea cu 0, deci
        # 'preflight.py --dry && run_campaign.py' pornea campania fara ca vreo poarta
        # sa fi masurat ceva. Textul avertiza; codul de iesire nu. Acum si el o face.
        cod = 3
    elif cod == 0:
        print("== PREFLIGHT OK (5/5 porti). Raport: %s ==" % cale)
    else:
        print("== PREFLIGHT ABORTAT la %s. Raport: %s ==" % (raport["poarta_picata"], cale))
        print("   REGULA DE AUR: nicio masuratoare pana nu trec TOATE cele 5 porti.")
    return cod


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
