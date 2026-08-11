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
  /home/ubuntu/DATE_CAMPANIE/C2_HIL_WIFI64_20260803/orchestrator_20260803_235016.log

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
  python3 hil_wired_preflight.py --remote ubuntu@10.0.0.2 --iface-remote eth0 --dry
  python3 hil_wired_preflight.py --remote ubuntu@10.0.0.2 --iface-remote eth0 \\
          --peer-ip 10.0.0.2 --raport ~/DATE_CAMPANIE/ANALIZA_C2/preflight.json
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

VERSIUNE = "1.0"

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
    out = {"suportat": None, "status": None, "rc": rc,
           "raw_head": t.strip().splitlines()[0] if t.strip() else ""}
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
           "retransmisii": None, "eroare": None, "raw_head": (text or "").strip()[:200]}
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
    out["ok"] = True
    return out


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
    """P3: EEE oprit daca e suportat. NU aborteaza niciodata -- doar noteaza."""
    masurat = {}
    note = []
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
            if not eee_este_oprit(dupa["status"]):
                m["avertisment"] = ("EEE NU e oprit pe %s (%s): status='%s' (rc_set=%s). "
                                    "P3 nu aborteaza, dar EEE poate adauga latenta de "
                                    "trezire in celulele cu trafic intermitent."
                                    % (iface, host, dupa["status"], rc_s))
                note.append(m["avertisment"])
        masurat[host] = m
        print("   [%s %s] EEE suportat=%s status='%s' -> '%s'"
              % (host, iface, m["suportat"], m["status_inainte"], m["status_dupa"]))
    if ex.dry:
        return (True, "P3 DRY: comenzile de mai sus nu au fost executate", {"dry": True})
    mesaj = "P3: EEE tratat pe ambele capete"
    if note:
        mesaj += " (NOTAT: " + " | ".join(note) + ")"
    return (True, mesaj, masurat)


def poarta4_iperf(ex, a):
    """P4: >= --prag-mbps SUSTINUT in AMBELE sensuri.

    'Bidirectional' e realizat ca DOUA rulari de cate --iperf-dur secunde, una pe
    fiecare sens (a doua cu -R), nu ca o singura rulare '--bidir'. Motiv onest:
    schema JSON a lui --bidir nu a putut fi verificata pe un iperf3 real aici
    (binarul nu e instalat pe masina de dezvoltare), in timp ce end.sum_sent /
    end.sum_received sunt stabile de la iperf3 3.0. LIMITA care decurge: nu se
    testeaza SIMULTANEITATEA celor doua sensuri (full duplex sub sarcina in ambele
    directii in acelasi timp), ci fiecare sens la saturatie, pe rand.

    Se verifica si DURATA raportata de iperf3: o rulare care s-a terminat mai
    devreme nu dovedeste nimic 'sustinut', chiar daca cifra medie e mare."""
    masurat = {"prag_mbps": a.prag_mbps, "durata_ceruta_s": a.iperf_dur,
               "peer_ip": a.peer_ip, "peer_ip_dedus": a.peer_ip_dedus}
    port = a.iperf_port
    # pattern cu clasa de caractere pe ultima cifra: pkill sa nu isi omoare shell-ul
    pat = "iperf3 -s -p %s[%s]" % (str(port)[:-1], str(port)[-1])

    # qdisc-ul de pe ambele capete, inainte de saturatie: e PROVENIENTA (masuram pe
    # legatura curata sau prin netem?), nu o poarta.
    for host, iface in capete(a):
        rc, out, err = ex.sh("tc qdisc show dev %s" % shlex.quote(iface), host=host)
        if ex.dry:
            continue
        q = parse_tc_qdisc(out + "\n" + err)
        masurat.setdefault("qdisc_inainte", {})[host] = q
        if q.get("kind") == "netem":
            print("   [AVERTISMENT] %s (%s) are DEJA netem: '%s' -- cifra P4 e "
                  "masurata PRIN el" % (host, iface, q.get("linie")))

    ex.sh("pkill -f %s ; sleep 0.3 ; setsid nohup iperf3 -s -p %d "
          "> /tmp/iperf3_srv_preflight.log 2>&1 </dev/null &"
          % (shlex.quote(pat), port), host="remote")

    sensuri = [("local_spre_remote", ""), ("remote_spre_local", " -R")]
    rezultate = {}
    picat = None
    for eticheta, flag in sensuri:
        rc, out, err = ex.sh("iperf3 -c %s -p %d -t %g -J%s"
                             % (shlex.quote(a.peer_ip), port, a.iperf_dur, flag),
                             host="local", timeout=a.iperf_dur + 60.0)
        if ex.dry:
            continue
        r = parse_iperf3_json(out if out.strip() else err)
        r["rc"] = rc
        rezultate[eticheta] = r
        if not r["ok"]:
            print("   [%s] ESEC: %s" % (eticheta, r["eroare"]))
            picat = (eticheta, "iperf3 nu a produs o masuratoare: %s" % r["eroare"])
            break
        print("   [%s] recv=%.3f Mbit/s (sent=%.3f) in %.2f s, retransmisii=%s"
              % (eticheta, r["mbps_recv"], r["mbps_sent"], r["secunde"] or 0.0,
                 r["retransmisii"]))
        if r["secunde"] is not None and r["secunde"] < 0.9 * a.iperf_dur:
            picat = (eticheta, "rularea a durat %.2f s din %g s cerute -- cifra NU e "
                               "'sustinut'" % (r["secunde"], a.iperf_dur))
            break
        if r["mbps_recv"] < a.prag_mbps:
            picat = (eticheta, "%.3f Mbit/s receptionat < prag %.1f Mbit/s"
                               % (r["mbps_recv"], a.prag_mbps))
            break

    ex.sh("pkill -f %s" % shlex.quote(pat), host="remote")
    masurat["sensuri"] = rezultate
    if ex.dry:
        return (True, "P4 DRY: comenzile de mai sus nu au fost executate", {"dry": True})
    if picat is not None:
        eticheta, motiv = picat
        return (False,
                "P4 a picat pe sensul %s: %s\n"
                "  REPARA: (1) verifica ca iperf3 exista pe AMBELE capete "
                "(command -v iperf3) si ca serverul a pornit pe %s portul %d; "
                "(2) daca cifra e in jur de 94 Mbit/s, legatura e de fapt 100Mb/s -- "
                "reia P1 cu alt cablu/port; (3) daca sunt multe retransmisii, verifica "
                "duplexul (Half la un capat da coliziuni si prabusire); (4) opreste "
                "orice alt trafic pe cablu si orice qdisc netem ramas "
                "('sudo tc qdisc del dev <iface> root'). Bugetul cerut de protocolul "
                "C2 la 64 KiB x 50 Hz e 26.2 Mbit/s pe sens (52.4 agregat); pragul de "
                "%.1f Mbit/s pe sens e marja x2 fata de agregat."
                % (eticheta, motiv, a.peer_ip, port, a.prag_mbps), masurat)
    return (True, "P4: %.3f / %.3f Mbit/s (>= %.1f) pe cele doua sensuri"
            % (rezultate["local_spre_remote"]["mbps_recv"],
               rezultate["remote_spre_local"]["mbps_recv"], a.prag_mbps), masurat)


def poarta5_tc_limit(ex, a):
    """P5: tc qdisc replace cu limit --tc-limit, DOVEDIT cu tc qdisc show."""
    cond = conditie_dupa_nume(a.cond_limit)
    masurat = {"conditie": a.cond_limit, "limit_cerut": a.tc_limit,
               "limita_nu_persista": limita_nu_persista(cond)}
    for host, iface in capete(a):
        cmd = netem_cmd_cu_limita(iface, cond, a.tc_limit)
        masurat.setdefault("comenzi", {})[host] = cmd
        ex.sh("sudo -n %s" % cmd, host=host)
        rc, out, err = ex.sh("tc qdisc show dev %s" % shlex.quote(iface), host=host)
        if ex.dry:
            continue
        q = parse_tc_qdisc(out + "\n" + err)
        q["rc"] = rc
        masurat.setdefault("qdisc_dupa", {})[host] = q
        print("   [%s %s] qdisc='%s' kind=%s limit=%s"
              % (host, iface, q["linie"], q["kind"], q["limit"]))
        if q["kind"] != "netem" or q["limit"] != a.tc_limit:
            return (False,
                    "P5 a picat pe capatul %s (%s): tc raporteaza kind=%s limit=%s, "
                    "se cerea kind=netem limit=%d.\n  Linia vazuta: %s\n"
                    "  REPARA: ruleaza acolo, manual, '%s' si apoi 'tc qdisc show dev "
                    "%s'. Daca limita ramane 1000, nucleul a IGNORAT parametrul "
                    "(pozitia lui conteaza: 'limit' trebuie sa vina imediat dupa "
                    "'netem'); daca nu apare niciun netem, comanda a esuat -- cel mai "
                    "des din lipsa de sudo fara parola (sudo -n) pe acel capat."
                    % (host, iface, q["kind"], q["limit"], a.tc_limit, q["linie"],
                       cmd, iface), masurat)
    if ex.dry:
        return (True, "P5 DRY: comenzile de mai sus nu au fost executate",
                {"dry": True, "comenzi": masurat.get("comenzi"),
                 "limita_nu_persista": masurat["limita_nu_persista"]})
    mesaj = "P5: limit %d aplicat si DOVEDIT pe ambele capete" % a.tc_limit
    return (True, mesaj, masurat)


PORTI = [
    ("P1", "viteza si duplex", poarta1_link),
    ("P2", "offload-uri oprite", poarta2_offload),
    ("P3", "EEE", poarta3_eee),
    ("P4", "iperf3 TCP", poarta4_iperf),
    ("P5", "tc qdisc limit", poarta5_tc_limit),
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
# /home/ubuntu/DATE_CAMPANIE/C2_HIL_WIFI64_20260803/orchestrator_20260803_235016.log
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

    print("SELFTEST hil_wired_preflight OK (%d verificari)." % _VERIF[0])


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(
        prog="hil_wired_preflight.py",
        description="Preflight in 5 porti pentru bancul HIL cablat (abort la prima picata).")
    ap.add_argument("--iface-local", default="enp2s0",
                    help="NIC-ul cablat de pe masina asta (implicit: enp2s0)")
    ap.add_argument("--iface-remote", default="eth0",
                    help="NIC-ul cablat de pe M2 (implicit: eth0)")
    ap.add_argument("--remote", default=None,
                    help="tinta ssh a lui M2, ex. ubuntu@10.0.0.2 (OBLIGATORIU)")
    ap.add_argument("--peer-ip", default=None,
                    help="adresa lui M2 PE CABLU, pentru iperf3 (implicit: gazda din "
                         "--remote; da-o explicit daca ssh merge pe alta cale)")
    ap.add_argument("--prag-mbps", type=float, default=105.0,
                    help="pragul P4 pe fiecare sens (implicit 105.0)")
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
        print("EROARE: --remote e obligatoriu (ex: --remote ubuntu@10.0.0.2). "
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
    elif cod == 0:
        print("== PREFLIGHT OK (5/5 porti). Raport: %s ==" % cale)
    else:
        print("== PREFLIGHT ABORTAT la %s. Raport: %s ==" % (raport["poarta_picata"], cale))
        print("   REGULA DE AUR: nicio masuratoare pana nu trec TOATE cele 5 porti.")
    return cod


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
