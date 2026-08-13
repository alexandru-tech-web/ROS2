#!/usr/bin/env python3
"""count_wire_units.py -- cate UNITATI DE FIR produce fiecare stiva RMW per
esantion de aplicatie.

Acesta este instrumentul care RASPUNDE la fraza din draft "the exact
multiplicity requires packet capture". Citeste o captura tcpdump (.pcap sau
.pcapng), o parseaza in Python PUR (fara scapy/dpkt/tshark) si numara, per
rulare:

  - cadre capturate si octeti pe fir (nivel 2), total si per esantion;
  - FRAGMENTE IP si DATAGRAME UDP reconstruite (nu acelasi lucru: un datagram
    UDP de 13,5 KB devine 10 fragmente IP la MTU 1500, si numai primul are
    antet UDP);
  - SEGMENTE TCP (unitatea de fir a lui Zenoh, care nu foloseste UDP);
  - BATCH-uri Zenoh, reconstruite din fluxul TCP dupa prefixul de lungime
    u16 little-endian;
  - submesaje RTPS, inclusiv DATA_FRAG cu campurile fragmentStartingNum /
    fragmentsInSubmessage / fragmentSize / sampleSize, ceea ce da direct
    numarul de fragmente RTPS si de datagrame per esantion, MASURAT, nu deja
    dedus;
  - MULTIPLICITATEA: unitati de fir / esantion de aplicatie (--numar-esantioane).

Iesire: tabel pe stdout si, optional, JSON (--json).


COMANDA tcpdump RECOMANDATA PE BANC
-----------------------------------
tcpdump scrie pcap CLASIC cu -w (nu pcapng; pcapng il produc dumpcap/tshark).
Instrumentul acesta citeste ambele formate, deci oricare varianta merge.

  # captura completa, pe nodul emitator sau receptor, cu marci de timp in ns
  sudo tcpdump -i enp2s0 -n -s 0 -B 65536 --time-stamp-precision=nano \\
       -w /tmp/c1_cyclone_p65536.pcap \\
       'host 192.168.1.10 and host 192.168.1.11'

  # varianta economica pentru rulari lungi: se retin doar antetele.
  # NUMARATOAREA RAMANE EXACTA (se foloseste orig_len din pcap si campul
  # totalLength din IP, nu lungimea captata); se pierde doar analiza RTPS
  # adanca si reconstructia batch-urilor Zenoh.
  sudo tcpdump -i enp2s0 -n -s 128 -w /tmp/c1.pcap host 192.168.1.11

  # Zenoh: fara asta captura NU arata segmentele reale (vezi AVERTISMENT GSO)
  # DE RULAT PE BANC, NU AICI (regulile de proiect interzic ethtool/sudo):
  sudo ethtool -K enp2s0 tso off gso off gro off lro off

Recomandare: capteaza de la INCEPUTUL sesiunii TCP (porneste tcpdump inainte
de noduri), altfel reconstructia batch-urilor Zenoh nu se poate alinia.


CE MA ASTEPT SA VAD (predictii de verificat cu instrumentul acesta)
-------------------------------------------------------------------
CycloneDDS 0.10.5, implicit (FragmentSize=1344, MaxMessageSize=14720,
MaxRexmitMessageSize=1456), esantion de 64 KB, MTU 1500:

    fragmente RTPS / esantion .............. 49   (48 x 1344 + 1 x 1028)
    submesaje DATA_FRAG / esantion .........  5   (fragmentsInSubmessage = 10,
                                                   10, 10, 10, 9)
    datagrame UDP / esantion ...............  5   (sarcina UDP 13536, 13524,
                                                   13524, 13524, 11868)
    fragmente IP (= cadre) / esantion ...... 49   (10+10+10+10+9)
    octeti L2 / esantion ................... 67682  (44 x 1514 + 258 + 3 x 246
                                                     + 70), adica ~3.3% peste
    din cele 49 cadre, doar 5 au offset IP zero si se decodeaza ca UDP/RTPS.

  Asimetrie importanta: RETRANSMISIILE nu urmeaza tiparul. Sunt limitate de
  MaxRexmitMessageSize=1456 si ies ca datagrame de 1416 B, un fragment RTPS
  fiecare, deci UN cadru de 1458 B fara fragmentare IP. Daca in raport
  "datagrame_per_esantion" arata mai mult de 5, aproape sigur sunt
  retransmisii; campul rtps.data_frag.esantioane_cu_retransmisii le separa.

Zenoh (rmw_zenoh_cpp 0.2.9 peste zenoh-c 1.6.2), transport TCP, MTU 1500:

    batch-uri Zenoh / esantion .............  2   (49152 si 16475 octeti,
                                                   plafon real 48 KiB)
    octeti de sarcina TCP / esantion ....... 65627 (CDR 65545 + 82)
    segmente TCP / esantion ................ 46   (45 x MSS 1448 + 467)
    octeti IP / esantion ................... 68019 (+ ACK-uri pe sensul invers)
    octeti L2 / esantion ................... 68663

  Zenoh nu produce fragmentare IP: transportul e TCP, iar scouting-ul
  multicast UDP e dezactivat explicit in configul implicit. De aceea o
  comparatie corp-la-corp cu Cyclone TREBUIE sa declare ca "unitatea de fir"
  inseamna lucruri diferite: datagrame UDP fragmentate IP la Cyclone,
  segmente TCP la Zenoh. Instrumentul raporteaza si numarul de cadre, care
  este singura marime comparabila direct intre cele doua.

AVERTISMENT GSO/TSO/GRO (esential pentru Zenoh): pe masina de dezvoltare
enp2s0 are gso_max_size 64000 si wlp4s0 65536, iar gro_max_size 65536. Un
tcpdump pe EMITATOR va arata ~2 super-pachete in loc de 46 segmente, iar pe
RECEPTOR agregarea GRO face acelasi lucru. Instrumentul detecteaza cadrele
mai mari decat MTU-ul (--mtu) si raporteaza SEPARAT numarul de segmente
estimat la MTU-ul dat (sectiunea "normalizare la MTU"), marcat clar ca
estimare aritmetica, nu ca observatie.


CUM SE DISTINGE TRAFICUL DE DATE DE CEL DE DISCOVERY/CONTROL
------------------------------------------------------------
In ordinea de prioritate aplicata:

  1. explicit, daca utilizatorul da --port-date / --port-discovery;
  2. RTPS decodat (cel mai sigur): se citesc submesajele din datagrama si se
     ia entityKind-ul lui writerId/readerId. Entitatile predefinite (builtin)
     au entityKind & 0xC0 == 0xC0 -> discovery (SPDP/SEDP). DATA sau DATA_FRAG
     de la un writer definit de utilizator -> date. Datagramele care contin
     doar ACKNACK / HEARTBEAT / NACK_FRAG / GAP / INFO_* -> control;
  3. formula de porturi RTPS (DDSI 2.2, sectiunea 9.6.1.1), pentru cazul in
     care sarcina nu a fost capturata (-s mic): offset = port - (7400 + 250*D);
     offset 0 -> SPDP multicast (discovery), 1 -> user multicast (date),
     >=10 par -> meta unicast (discovery), >=11 impar -> user unicast (date).
     Criteriul se aplica DOAR daca ambele porturi ale datagramei cad in
     ACELASI domeniu D, fiindca formula singura se potriveste si pe porturi
     efemere oarecare (50000 -> domeniul 170, offset 100); --domeniu 0,7
     restrange si mai mult;
  4. altfel "neclasificat".

Pentru Zenoh NU exista o separare pe octeti: datele si controlul circula prin
ACEEASI sesiune TCP, multiplexate in acelasi batch. Instrumentul le poate
separa doar pe port (7447 = legatura catre router, restul = legaturi
peer-to-peer), si asta declara in raport. O separare reala ar cere decodarea
protocolului Zenoh, pe care acest instrument NU o face.


VERIFICARE
----------
    /usr/bin/python3 count_wire_units.py --selftest

Selftestul nu foloseste reteaua si nu cere sudo: fabrica pcap-uri octet cu
octet, cu adevar cunoscut, si verifica exact numaratoarea.
"""
import argparse
import io
import json
import math
import os
import struct
import sys

# ---------------------------------------------------------------- constante

MAGIC_PCAP = {
    b"\xd4\xc3\xb2\xa1": ("<", "us"),
    b"\xa1\xb2\xc3\xd4": (">", "us"),
    b"\x4d\x3c\xb2\xa1": ("<", "ns"),
    b"\xa1\xb2\x3c\x4d": (">", "ns"),
}
MAGIC_PCAPNG = b"\x0a\x0d\x0d\x0a"

# limita de plauzibilitate pentru lungimea unui cadru capturat (4 MiB);
# peste asta consideram fisierul corupt sau endianness-ul gresit
MAX_CADRU = 1 << 22
MAX_BLOC_PCAPNG = 1 << 26

LINKTYPES = {0: "NULL", 1: "EN10MB", 12: "RAW", 101: "RAW",
             108: "LOOP", 113: "LINUX_SLL", 276: "LINUX_SLL2"}

PROTO_UDP = 17
PROTO_TCP = 6

# submesaje RTPS (DDSI-RTPS 2.2, tabelul 8.13)
RTPS_SUBMSG = {
    0x01: "PAD", 0x06: "ACKNACK", 0x07: "HEARTBEAT", 0x08: "GAP",
    0x09: "INFO_TS", 0x0c: "INFO_SRC", 0x0d: "INFO_REPLY_IP4",
    0x0e: "INFO_DST", 0x0f: "INFO_REPLY", 0x12: "NACK_FRAG",
    0x13: "HEARTBEAT_FRAG", 0x15: "DATA", 0x16: "DATA_FRAG",
}
# submesaje care incep direct cu readerId(4) + writerId(4)
_SUBMSG_ID_LA_0 = (0x06, 0x07, 0x08, 0x12, 0x13)
# submesaje care au 4 octeti (extraFlags + octetsToInlineQos) inainte
_SUBMSG_ID_LA_4 = (0x15, 0x16)

PORT_ZENOH_IMPLICIT = 7447


class EroarePcap(Exception):
    """Captura nu poate fi parsata (format necunoscut, trunchiata, corupta)."""


# ------------------------------------------------------- citirea containerului

def _u(e, fmt, b, off=0):
    return struct.unpack_from(e + fmt, b, off)


def _antet_pcap(f):
    magic = f.read(4)
    if len(magic) < 4:
        raise EroarePcap("fisier prea scurt: %d octeti, minim 4 pentru magic"
                         % len(magic))
    if magic == MAGIC_PCAPNG:
        return None, magic
    if magic not in MAGIC_PCAP:
        raise EroarePcap(
            "magic necunoscut %s -- nu este pcap clasic si nici pcapng"
            % magic.hex())
    e, rez = MAGIC_PCAP[magic]
    rest = f.read(20)
    if len(rest) < 20:
        raise EroarePcap("antet global pcap trunchiat: %d octeti in loc de 24"
                         % (4 + len(rest)))
    vmaj, vmin, tz, sig, snaplen, link = _u(e, "HHiIII", rest)
    return dict(format="pcap", endian=e, rezolutie_ts=rez, versiune="%d.%d"
                % (vmaj, vmin), snaplen=snaplen, linktype=link,
                zona_orara=tz, sigfigs=sig), magic


def _pachete_pcap(f, meta):
    """Generator de (ts_ns, orig_len, cap_len, octeti, linktype)."""
    e = meta["endian"]
    mult = 1 if meta["rezolutie_ts"] == "ns" else 1000
    link = meta["linktype"]
    n = 0
    while True:
        h = f.read(16)
        if not h:
            return
        if len(h) < 16:
            raise EroarePcap(
                "antet de pachet trunchiat la pachetul %d: %d octeti in loc de 16"
                % (n + 1, len(h)))
        ts_s, ts_f, incl, orig = _u(e, "IIII", h)
        if incl > MAX_CADRU or orig > MAX_CADRU:
            raise EroarePcap(
                "lungime implauzibila la pachetul %d (captat=%d, fir=%d) -- "
                "fisier corupt sau endianness gresit" % (n + 1, incl, orig))
        date = f.read(incl)
        if len(date) < incl:
            raise EroarePcap(
                "date trunchiate la pachetul %d: %d octeti in loc de %d"
                % (n + 1, len(date), incl))
        n += 1
        yield (ts_s * 1000000000 + ts_f * mult, orig, incl, date, link)


def _pachete_pcapng(f, cap_initial=b""):
    """Generator peste blocurile pcapng. Suporta SHB, IDB, EPB, SPB.
    cap_initial sunt octetii de magic deja cititi din flux."""
    e = "<"
    interfete = []
    n = 0
    primul = True
    while True:
        cap = cap_initial + f.read(8 - len(cap_initial))
        cap_initial = b""
        if not cap:
            return
        if len(cap) < 8:
            raise EroarePcap("bloc pcapng trunchiat: %d octeti in loc de 8"
                             % len(cap))
        tip = cap[0:4]
        if tip == MAGIC_PCAPNG:
            # antetul de sectiune decide endianness-ul
            bom = f.read(4)
            if len(bom) < 4:
                raise EroarePcap("SHB trunchiat (lipseste byte-order magic)")
            if bom == b"\x4d\x3c\x2b\x1a":
                e = "<"
            elif bom == b"\x1a\x2b\x3c\x4d":
                e = ">"
            else:
                raise EroarePcap("byte-order magic pcapng invalid: %s"
                                 % bom.hex())
            total = _u(e, "I", cap, 4)[0]
            if total < 16 or total > MAX_BLOC_PCAPNG:
                raise EroarePcap("lungime de bloc SHB implauzibila: %d" % total)
            corp = f.read(total - 12)
            if len(corp) < total - 12:
                raise EroarePcap("SHB trunchiat: %d octeti in loc de %d"
                                 % (len(corp) + 12, total))
            interfete = []
            primul = False
            continue
        if primul:
            raise EroarePcap("fisier pcapng fara antet de sectiune (SHB) la inceput")
        tip_i = _u(e, "I", cap, 0)[0]
        total = _u(e, "I", cap, 4)[0]
        if total < 12 or total % 4 or total > MAX_BLOC_PCAPNG:
            raise EroarePcap("lungime de bloc pcapng implauzibila: %d "
                             "(tip 0x%08x)" % (total, tip_i))
        corp = f.read(total - 12)
        if len(corp) < total - 12:
            raise EroarePcap("bloc pcapng trunchiat (tip 0x%08x): %d octeti "
                             "in loc de %d" % (tip_i, len(corp) + 12, total))
        coada = f.read(4)
        if len(coada) < 4:
            raise EroarePcap("bloc pcapng fara lungimea de final (tip 0x%08x)"
                             % tip_i)
        if _u(e, "I", coada, 0)[0] != total:
            raise EroarePcap("bloc pcapng inconsistent: lungimea de final %d "
                             "difera de cea de inceput %d"
                             % (_u(e, "I", coada, 0)[0], total))
        if tip_i == 0x00000001:                     # Interface Description
            if len(corp) < 8:
                raise EroarePcap("IDB prea scurt")
            link, _rez, snap = _u(e, "HHI", corp)
            interfete.append(dict(linktype=link, snaplen=snap, rezolutie=6))
        elif tip_i == 0x00000006:                   # Enhanced Packet Block
            if len(corp) < 20:
                raise EroarePcap("EPB prea scurt")
            iid, thi, tlo, capl, origl = _u(e, "IIIII", corp)
            if capl > MAX_CADRU or origl > MAX_CADRU:
                raise EroarePcap("lungime implauzibila in EPB (captat=%d, "
                                 "fir=%d)" % (capl, origl))
            if 20 + capl > len(corp):
                raise EroarePcap("EPB trunchiat: sarcina de %d octeti nu incape"
                                 % capl)
            date = corp[20:20 + capl]
            rezol = interfete[iid]["rezolutie"] if iid < len(interfete) else 6
            link = interfete[iid]["linktype"] if iid < len(interfete) else 1
            tick = (thi << 32) | tlo
            ts_ns = tick * (10 ** (9 - rezol))
            n += 1
            yield (ts_ns, origl, capl, date, link)
        elif tip_i == 0x00000003:                   # Simple Packet Block
            if len(corp) < 4:
                raise EroarePcap("SPB prea scurt")
            origl = _u(e, "I", corp)[0]
            date = corp[4:4 + min(origl, len(corp) - 4)]
            link = interfete[0]["linktype"] if interfete else 1
            n += 1
            yield (0, origl, len(date), date, link)
        # celelalte blocuri (NRB, ISB, DSB, custom) se ignora deliberat


def deschide_captura(f):
    """Intoarce (meta, generator_de_pachete). Ridica EroarePcap la orice
    problema de format. Nu citeste tot fisierul in memorie."""
    meta, magic = _antet_pcap(f)
    if meta is None:
        return (dict(format="pcapng", endian="?", rezolutie_ts="ns",
                     linktype=None, snaplen=None),
                _pachete_pcapng(f, magic))
    return meta, _pachete_pcap(f, meta)


# ------------------------------------------------------------- straturi 2 / 3

def _strat_legatura(linktype, cadru):
    """Intoarce (ethertype, offset_l3) sau (None, None) daca nu e IP."""
    if linktype in (1, 108):                       # Ethernet (si LOOP)
        if len(cadru) < 14:
            return None, None
        et = (cadru[12] << 8) | cadru[13]
        off = 14
        while et in (0x8100, 0x88a8, 0x9100):      # VLAN / QinQ
            if len(cadru) < off + 4:
                return None, None
            et = (cadru[off + 2] << 8) | cadru[off + 3]
            off += 4
        return et, off
    if linktype == 113:                            # LINUX_SLL
        if len(cadru) < 16:
            return None, None
        return (cadru[14] << 8) | cadru[15], 16
    if linktype == 276:                            # LINUX_SLL2
        if len(cadru) < 20:
            return None, None
        return (cadru[0] << 8) | cadru[1], 20
    if linktype in (12, 101):                      # RAW IP
        if not cadru:
            return None, None
        v = cadru[0] >> 4
        return (0x0800 if v == 4 else 0x86dd if v == 6 else None), 0
    if linktype == 0:                              # BSD loopback / NULL
        if len(cadru) < 4:
            return None, None
        for e in ("<", ">"):
            fam = _u(e, "I", cadru)[0]
            if fam == 2:
                return 0x0800, 4
            if fam in (10, 23, 24, 28, 30):
                return 0x86dd, 4
        return None, None
    return None, None


def _parse_ipv4(b, off):
    if len(b) < off + 20:
        return None
    vihl = b[off]
    if (vihl >> 4) != 4:
        return None
    ihl = (vihl & 0x0F) * 4
    if ihl < 20:
        return None
    total = (b[off + 2] << 8) | b[off + 3]
    ident = (b[off + 4] << 8) | b[off + 5]
    fo_w = (b[off + 6] << 8) | b[off + 7]
    mf = bool(fo_w & 0x2000)
    frag_off = (fo_w & 0x1FFF) * 8
    proto = b[off + 9]
    src = ".".join(str(x) for x in b[off + 12:off + 16])
    dst = ".".join(str(x) for x in b[off + 16:off + 20])
    lung_util = max(0, total - ihl)
    return dict(ver=4, src=src, dst=dst, proto=proto, ident=ident,
                mf=mf, frag_off=frag_off, ip_hdr=ihl, ip_total=total,
                lung_util=lung_util, off_l4=off + ihl)


def _parse_ipv6(b, off):
    if len(b) < off + 40:
        return None
    if (b[off] >> 4) != 6:
        return None
    plen = (b[off + 4] << 8) | b[off + 5]
    nh = b[off + 6]
    src = _ipv6_text(b[off + 8:off + 24])
    dst = _ipv6_text(b[off + 24:off + 40])
    cur = off + 40
    consumat = 0
    ident, mf, frag_off = 0, False, 0
    while nh in (0, 43, 44, 60, 51):
        if len(b) < cur + 8:
            return None
        if nh == 44:                                # Fragment Header
            w = (b[cur + 2] << 8) | b[cur + 3]
            frag_off = (w >> 3) * 8
            mf = bool(w & 1)
            ident = _u(">", "I", b, cur + 4)[0]
            nh = b[cur]
            cur += 8
            consumat += 8
            break
        ln = 8 if nh == 51 else (b[cur + 1] + 1) * 8
        if nh == 51:
            ln = (b[cur + 1] + 2) * 4
        nh_nou = b[cur]
        cur += ln
        consumat += ln
        nh = nh_nou
    return dict(ver=6, src=src, dst=dst, proto=nh, ident=ident, mf=mf,
                frag_off=frag_off, ip_hdr=40 + consumat, ip_total=40 + plen,
                lung_util=max(0, plen - consumat), off_l4=cur)


def _ipv6_text(b):
    parti = ["%x" % ((b[i] << 8) | b[i + 1]) for i in range(0, 16, 2)]
    return ":".join(parti)


# ------------------------------------------------ reasamblarea datagramelor IP

class _Grup(object):
    """Un datagram IP: unul sau mai multe fragmente cu acelasi
    (src, dst, proto, identificator)."""
    __slots__ = ("ver", "src", "dst", "proto", "ident", "bucati", "offsets",
                 "suma", "total", "n_cadre", "n_dupl", "octeti_l2", "octeti_ip",
                 "ts_ns", "fragmentat", "are_prim", "indice_prim")

    def __init__(self, ip, ts_ns):
        self.ver = ip["ver"]
        self.src = ip["src"]
        self.dst = ip["dst"]
        self.proto = ip["proto"]
        self.ident = ip["ident"]
        self.bucati = []
        self.offsets = set()
        self.suma = 0
        self.total = None
        self.n_cadre = 0
        self.n_dupl = 0
        self.octeti_l2 = 0
        self.octeti_ip = 0
        self.ts_ns = ts_ns
        self.fragmentat = False
        self.are_prim = False
        self.indice_prim = None

    def adauga(self, ip, orig_len, sarcina, indice):
        self.n_cadre += 1
        self.octeti_l2 += orig_len
        self.octeti_ip += ip["ip_total"]
        if ip["mf"] or ip["frag_off"]:
            self.fragmentat = True
        if ip["frag_off"] == 0:
            self.are_prim = True
            if self.indice_prim is None:
                self.indice_prim = indice
        if ip["frag_off"] in self.offsets:
            self.n_dupl += 1
            return
        self.offsets.add(ip["frag_off"])
        self.suma += ip["lung_util"]
        if not ip["mf"]:
            self.total = ip["frag_off"] + ip["lung_util"]
        if sarcina is not None:
            self.bucati.append((ip["frag_off"], sarcina))

    @property
    def complet(self):
        return self.total is not None and self.suma >= self.total

    def octeti_l4(self):
        """Lungimea sarcinii L4 (antet L4 inclus), din campurile IP."""
        return self.total if self.total is not None else self.suma

    def reasambleaza(self):
        """Octetii L4 disponibili, in ordine. Poate fi mai scurt decat
        octeti_l4() daca s-a capturat cu snaplen mic sau daca bugetul de
        memorie a oprit retinerea."""
        if not self.bucati:
            return b""
        n = self.octeti_l4()
        buf = bytearray(n)
        acoperit = 0
        for off, b in sorted(self.bucati):
            if off >= n:
                continue
            taiat = b[:n - off]
            buf[off:off + len(taiat)] = taiat
            if off == acoperit:
                acoperit = off + len(taiat)
        return bytes(buf[:acoperit])


# ----------------------------------------------------------------- RTPS

def _entitate_builtin(eid):
    """entityKind (ultimul octet) cu bitii 0xC0 setati -> entitate predefinita."""
    return len(eid) == 4 and (eid[3] & 0xC0) == 0xC0


def parse_rtps(p):
    """Descompune un mesaj RTPS. Intoarce None daca nu incepe cu 'RTPS'."""
    if len(p) < 20 or p[0:4] != b"RTPS":
        return None
    rez = dict(versiune="%d.%d" % (p[4], p[5]), vendor=p[6:8].hex(),
               guid_prefix=p[8:20].hex(), submesaje=[], trunchiat=False)
    off = 20
    while off + 4 <= len(p):
        sid = p[off]
        flags = p[off + 1]
        e = "<" if (flags & 1) else ">"
        onh = _u(e, "H", p, off + 2)[0]
        corp_off = off + 4
        lung = (len(p) - corp_off) if onh == 0 else onh
        corp = p[corp_off:corp_off + lung]
        s = dict(id=sid, nume=RTPS_SUBMSG.get(sid, "0x%02x" % sid),
                 flags=flags, endian=e, lung=lung)
        if sid in _SUBMSG_ID_LA_0 and len(corp) >= 8:
            s["reader_id"] = corp[0:4]
            s["writer_id"] = corp[4:8]
        elif sid in _SUBMSG_ID_LA_4 and len(corp) >= 12:
            s["reader_id"] = corp[4:8]
            s["writer_id"] = corp[8:12]
            if len(corp) >= 20:
                hi, lo = _u(e, "iI", corp, 12)
                s["writer_sn"] = (hi << 32) | lo
            if sid == 0x16 and len(corp) >= 32:
                # fragmentStartingNum(4) fragmentsInSubmessage(2)
                # fragmentSize(2) sampleSize(4)
                s["fragment_start"] = _u(e, "I", corp, 20)[0]
                s["fragmente_in_submesaj"] = _u(e, "H", corp, 24)[0]
                s["fragment_size"] = _u(e, "H", corp, 26)[0]
                s["sample_size"] = _u(e, "I", corp, 28)[0]
        rez["submesaje"].append(s)
        if onh == 0:
            break
        off = corp_off + lung
        if lung == 0 and sid == 0x01:
            off = corp_off
            break
    if off < len(p) - 3:
        rez["trunchiat"] = True
    return rez


def _clasa_rtps(r):
    """'date' / 'discovery' / 'control' dupa submesajele decodate."""
    are_date_user = False
    are_date_builtin = False
    for s in r["submesaje"]:
        if s["id"] in (0x15, 0x16):
            w = s.get("writer_id")
            if w is None:
                continue
            if _entitate_builtin(w):
                are_date_builtin = True
            else:
                are_date_user = True
    if are_date_user:
        return "date"
    if are_date_builtin:
        return "discovery"
    return "control"


def clasa_port_rtps(port, domenii=None):
    """Formula de porturi DDSI 2.2 (9.6.1.1) cu valorile implicite
    PB=7400, DG=250, d0=0, d1=10, d2=1, d3=11.

    Atentie: formula singura NU este un criteriu suficient. Aproape orice
    port efemer de peste 7400 se potriveste pe ea (50000 -> domeniul 170,
    offset 100, adica 'meta unicast'). De aceea apelantul trebuie sa ceara
    ca AMBELE porturi ale datagramei sa cada in ACELASI domeniu, si
    optional sa restranga domeniile acceptate."""
    if port is None or port < 7400:
        return None
    d, o = divmod(port - 7400, 250)
    if d > 232:
        return None
    if domenii and d not in domenii:
        return None
    if o == 0:
        return ("discovery", d, "SPDP multicast")
    if o == 1:
        return ("date", d, "user multicast")
    if o >= 10 and o % 2 == 0:
        return ("discovery", d, "meta unicast")
    if o >= 11 and o % 2 == 1:
        return ("date", d, "user unicast")
    return None


# ------------------------------------------------------- batch-uri Zenoh (TCP)

class _FluxTcp(object):
    __slots__ = ("cheie", "baza", "bucati", "octeti", "segmente", "cu_date",
                 "are_syn", "octeti_retinuti", "inainte_de_baza")

    def __init__(self, cheie):
        self.cheie = cheie
        self.baza = None
        self.bucati = {}
        self.octeti = 0
        self.segmente = 0
        self.cu_date = 0
        self.are_syn = False
        self.octeti_retinuti = 0
        self.inainte_de_baza = 0


def _reasambleaza_tcp(flux):
    """Intoarce octetii contigui de la baza fluxului (se opreste la prima gaura)."""
    if not flux.bucati:
        return b""
    out = bytearray()
    poz = 0
    for off in sorted(flux.bucati):
        if off > poz:
            break                                   # gaura
        b = flux.bucati[off]
        if off + len(b) <= poz:
            continue                                # retransmisie completa
        out.extend(b[poz - off:])
        poz = off + len(b)
    return bytes(out)


def numara_batchuri_zenoh(octeti):
    """Parcurge un flux TCP Zenoh dupa prefixul de lungime u16 little-endian.
    Fiecare batch pe fir este: len(u16 LE) + len octeti de sarcina; lungimea
    NU se numara pe sine. Intoarce (lista_de_dimensiuni_totale, stare)."""
    dim = []
    poz = 0
    n = len(octeti)
    while poz + 2 <= n:
        L = octeti[poz] | (octeti[poz + 1] << 8)
        if L == 0:
            return dim, "lungime zero la offsetul %d (dezaliniat)" % poz
        if poz + 2 + L > n:
            return dim, "batch partial la final (%d octeti din %d)" % (n - poz - 2, L)
        dim.append(2 + L)
        poz += 2 + L
    if poz == n:
        return dim, "aliniat"
    return dim, "rest de %d octeti sub 2 (prefix incomplet)" % (n - poz)


# ------------------------------------------------------------------- optiuni

class Optiuni(object):
    """Optiunile analizei; valorile implicite sunt cele folosite si de main()."""

    def __init__(self, **kw):
        self.filtru_port = set()
        self.exclude_port = set()
        self.filtru_gazda = set()
        self.exclude_gazda = set()
        self.port_date = set()
        self.port_discovery = set()
        self.port_zenoh = {PORT_ZENOH_IMPLICIT}
        self.domenii = None
        self.numar_esantioane = None
        self.esantion_octeti = 65536
        self.mtu = 1500
        self.mss = 1448
        self.buget_mib = 64
        self.batch_zenoh = "auto"
        self.max_esantioane_rtps = 20000
        self.eticheta = None
        for k, v in kw.items():
            if not hasattr(self, k):
                raise ValueError("optiune necunoscuta: %r" % k)
            setattr(self, k, v)

    @property
    def buget_octeti(self):
        return int(self.buget_mib) * 1024 * 1024


def _parse_porturi(s):
    out = set()
    if not s:
        return out
    for tok in str(s).replace(";", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if "-" in tok[1:]:
            a, b = tok.split("-", 1)
            a, b = int(a), int(b)
            if b < a:
                a, b = b, a
            if b - a > 65535:
                raise ValueError("interval de porturi prea mare: %r" % tok)
            out.update(range(a, b + 1))
        else:
            out.add(int(tok))
    for p in out:
        if not 0 <= p <= 65535:
            raise ValueError("port in afara intervalului: %d" % p)
    return out


def _parse_gazde(s):
    if not s:
        return set()
    return set(t.strip() for t in str(s).replace(";", ",").split(",") if t.strip())


# ------------------------------------------------------------------- analiza

def _histograma(d):
    return dict((str(k), v) for k, v in sorted(d.items()))


def _mod(d):
    if not d:
        return None
    return max(sorted(d.items()), key=lambda kv: kv[1])[0]


def analizeaza_flux(f, opt):
    """Analiza completa peste un obiect fisier binar deschis. Intoarce dict."""
    meta, pachete = deschide_captura(f)

    grupuri_deschise = {}
    datagrame = []
    cadre_total = 0
    cadre_ne_ip = 0
    octeti_ne_ip = 0
    octeti_total = 0
    linktypes = {}
    buget = opt.buget_octeti
    buget_epuizat = False

    # ---- pasul 1: citirea cadrelor si gruparea fragmentelor IP
    for idx, (ts_ns, orig_len, cap_len, cadru, link) in enumerate(pachete):
        cadre_total += 1
        octeti_total += orig_len
        linktypes[link] = linktypes.get(link, 0) + 1
        et, off = _strat_legatura(link, cadru)
        ip = None
        if et == 0x0800:
            ip = _parse_ipv4(cadru, off)
        elif et == 0x86dd:
            ip = _parse_ipv6(cadru, off)
        if ip is None:
            cadre_ne_ip += 1
            octeti_ne_ip += orig_len
            continue

        sarcina = cadru[ip["off_l4"]:]
        # se pastreaza mereu antetul L4 (necesar pentru porturi); restul
        # doar in limita bugetului de memorie
        if len(sarcina) > 40:
            if buget - len(sarcina) < 0:
                buget_epuizat = True
                sarcina = sarcina[:40]
            else:
                buget -= len(sarcina)
        retinut = sarcina if sarcina else None

        cheie = (ip["ver"], ip["src"], ip["dst"], ip["proto"], ip["ident"])
        if not (ip["mf"] or ip["frag_off"]):
            g = _Grup(ip, ts_ns)
            g.adauga(ip, orig_len, retinut, idx)
            datagrame.append(g)
            continue
        g = grupuri_deschise.get(cheie)
        if g is not None and g.complet:
            g = None
        if g is None:
            g = _Grup(ip, ts_ns)
            grupuri_deschise[cheie] = g
            datagrame.append(g)
        g.adauga(ip, orig_len, retinut, idx)

    # ---- pasul 2: porturi, clasificare, filtre
    rez_udp = dict(datagrame=0, datagrame_fragmentate=0, cadre=0,
                   fragmente_ip=0, cadre_prim_fragment=0, octeti_l2=0,
                   octeti_ip=0, octeti_payload=0, incomplete=0, duplicate=0)
    rez_tcp = dict(segmente=0, segmente_cu_date=0, segmente_fara_date=0,
                   cadre=0, fragmente_ip=0, octeti_l2=0, octeti_ip=0,
                   octeti_payload=0, incomplete=0)
    rez_alt = dict(datagrame=0, cadre=0, octeti_l2=0)
    clase = {}
    fluxuri_tcp = {}
    cadre_excluse = 0
    octeti_excluse = 0
    cadre_numarate = 0

    rtps_msg = 0
    rtps_submsg = {}
    rtps_esantioane = {}
    rtps_prea_multe = False
    df_submesaje = 0
    df_fragmente = 0
    df_hist_fis = {}
    df_hist_fsize = {}
    cadre_peste_mtu = 0
    segmente_estimate = 0
    fragmente_estimate = 0

    for g in datagrame:
        sport = dport = None
        date_l4 = g.reasambleaza()
        if g.proto in (PROTO_UDP, PROTO_TCP) and len(date_l4) >= 4:
            sport, dport = _u(">", "HH", date_l4)

        # filtre (se aplica pe DATAGRAM, nu pe cadru: fragmentele urmatoare
        # nu au antet L4, deci nu pot fi filtrate individual)
        gazde = (g.src, g.dst)
        porturi = tuple(p for p in (sport, dport) if p is not None)
        exclus = False
        if opt.filtru_gazda and not any(h in opt.filtru_gazda for h in gazde):
            exclus = True
        if opt.exclude_gazda and any(h in opt.exclude_gazda for h in gazde):
            exclus = True
        if opt.filtru_port and not any(p in opt.filtru_port for p in porturi):
            exclus = True
        if opt.exclude_port and any(p in opt.exclude_port for p in porturi):
            exclus = True
        if exclus:
            cadre_excluse += g.n_cadre
            octeti_excluse += g.octeti_l2
            continue

        cadre_numarate += g.n_cadre
        fragmente = g.n_cadre if g.fragmentat else 0

        # --- clasificare date / discovery / control
        clasa = None
        motiv = None
        if any(p in opt.port_discovery for p in porturi):
            clasa, motiv = "discovery", "port explicit (--port-discovery)"
        elif any(p in opt.port_date for p in porturi):
            clasa, motiv = "date", "port explicit (--port-date)"
        r = None
        if clasa is None and g.proto == PROTO_UDP and len(date_l4) > 8:
            r = parse_rtps(date_l4[8:])
            if r is not None:
                clasa = _clasa_rtps(r)
                motiv = "RTPS decodat (entityKind al writerId)"
        if clasa is None and g.proto == PROTO_UDP and len(porturi) == 2:
            cp = [clasa_port_rtps(p, opt.domenii) for p in porturi]
            # se cere ca AMBELE porturi sa cada in ACELASI domeniu RTPS,
            # altfel formula ar eticheta drept discovery orice port efemer
            if cp[0] and cp[1] and cp[0][1] == cp[1][1]:
                dom = cp[0][1]
                if "discovery" in (cp[0][0], cp[1][0]):
                    clasa = "discovery"
                else:
                    clasa = "date"
                motiv = ("formula de porturi RTPS, domeniul %d (%s / %s)"
                         % (dom, cp[0][2], cp[1][2]))
        if clasa is None and g.proto == PROTO_TCP:
            if any(p in opt.port_zenoh for p in porturi):
                clasa, motiv = ("neclasificat",
                                "TCP catre portul routerului Zenoh: datele si "
                                "controlul partajeaza sesiunea, nu se pot separa")
            else:
                clasa, motiv = "neclasificat", "TCP fara decodare de protocol"
        if clasa is None and g.proto == PROTO_UDP:
            clasa, motiv = ("neclasificat",
                            "UDP fara antet RTPS in captura si fara potrivire "
                            "pe formula de porturi")
        if clasa is None:
            clasa, motiv = "neclasificat", "protocol IP %d" % g.proto

        c = clase.setdefault(clasa, dict(datagrame=0, cadre=0, octeti_l2=0,
                                         octeti_payload=0, motive={}))
        c["datagrame"] += 1
        c["cadre"] += g.n_cadre
        c["octeti_l2"] += g.octeti_l2
        c["motive"][motiv] = c["motive"].get(motiv, 0) + 1

        # --- contoare pe protocol
        if g.proto == PROTO_UDP:
            payload = max(0, g.octeti_l4() - 8)
            rez_udp["datagrame"] += 1
            rez_udp["datagrame_fragmentate"] += 1 if g.fragmentat else 0
            rez_udp["cadre"] += g.n_cadre
            rez_udp["fragmente_ip"] += fragmente
            rez_udp["cadre_prim_fragment"] += 1 if g.are_prim else 0
            rez_udp["octeti_l2"] += g.octeti_l2
            rez_udp["octeti_ip"] += g.octeti_ip
            rez_udp["octeti_payload"] += payload
            rez_udp["incomplete"] += 0 if g.complet else 1
            rez_udp["duplicate"] += g.n_dupl
            c["octeti_payload"] += payload
            # estimarea fragmentarii la MTU-ul tinta (util cand captura e pe
            # lo, MTU 65536, unde nucleul NU fragmenteaza)
            util = max(1, ((opt.mtu - 20) // 8) * 8)
            fragmente_estimate += int(math.ceil(g.octeti_l4() / float(util)))
            if r is not None:
                rtps_msg += 1
                for s in r["submesaje"]:
                    rtps_submsg[s["nume"]] = rtps_submsg.get(s["nume"], 0) + 1
                    if s["id"] != 0x16 or "fragmente_in_submesaj" not in s:
                        continue
                    df_submesaje += 1
                    nf = s["fragmente_in_submesaj"]
                    df_fragmente += nf
                    df_hist_fis[nf] = df_hist_fis.get(nf, 0) + 1
                    fs = s["fragment_size"]
                    df_hist_fsize[fs] = df_hist_fsize.get(fs, 0) + 1
                    ck = (g.src, s["writer_id"], s.get("writer_sn"))
                    st = rtps_esantioane.get(ck)
                    if st is None:
                        if len(rtps_esantioane) >= opt.max_esantioane_rtps:
                            rtps_prea_multe = True
                            continue
                        st = dict(datagrame=set(), fragmente=set(), emise=0,
                                  sample_size=s["sample_size"],
                                  fragment_size=fs)
                        rtps_esantioane[ck] = st
                    st["datagrame"].add(id(g))
                    st["emise"] += nf
                    inceput = s["fragment_start"]
                    st["fragmente"].update(range(inceput, inceput + nf))
        elif g.proto == PROTO_TCP:
            hl = 20
            if len(date_l4) >= 13:
                hl = (date_l4[12] >> 4) * 4
                if hl < 20:
                    hl = 20
            payload = max(0, g.octeti_l4() - hl)
            rez_tcp["segmente"] += 1
            rez_tcp["cadre"] += g.n_cadre
            rez_tcp["fragmente_ip"] += fragmente
            rez_tcp["octeti_l2"] += g.octeti_l2
            rez_tcp["octeti_ip"] += g.octeti_ip
            rez_tcp["octeti_payload"] += payload
            rez_tcp["incomplete"] += 0 if g.complet else 1
            if payload:
                rez_tcp["segmente_cu_date"] += 1
                segmente_estimate += int(math.ceil(payload / float(opt.mss)))
            else:
                rez_tcp["segmente_fara_date"] += 1
            c["octeti_payload"] += payload
            if g.octeti_l4() > opt.mtu - 20:
                cadre_peste_mtu += 1
            fl_cheie = (g.src, sport, g.dst, dport)
            fl = fluxuri_tcp.get(fl_cheie)
            if fl is None:
                fl = _FluxTcp(fl_cheie)
                fluxuri_tcp[fl_cheie] = fl
            fl.segmente += 1
            fl.octeti += payload
            flags = date_l4[13] if len(date_l4) >= 14 else 0
            seq = _u(">", "I", date_l4, 4)[0] if len(date_l4) >= 8 else 0
            if flags & 0x02:
                fl.are_syn = True
                fl.baza = (seq + 1) & 0xFFFFFFFF
            if payload:
                fl.cu_date += 1
                corp = date_l4[hl:hl + payload]
                if fl.baza is None:
                    fl.baza = seq
                off = (seq - fl.baza) & 0xFFFFFFFF
                if off > 0x7FFFFFFF:
                    fl.inainte_de_baza += 1
                elif corp:
                    fl.bucati[off] = corp
                    fl.octeti_retinuti += len(corp)
        else:
            rez_alt["datagrame"] += 1
            rez_alt["cadre"] += g.n_cadre
            rez_alt["octeti_l2"] += g.octeti_l2

    for c in clase.values():
        c["motive"] = dict(sorted(c["motive"].items()))

    # ---- pasul 3: batch-uri Zenoh peste fluxurile TCP
    zenoh = None
    face_zenoh = (opt.batch_zenoh == "da" or
                  (opt.batch_zenoh == "auto" and rez_tcp["segmente_cu_date"] > 0))
    if face_zenoh and fluxuri_tcp:
        det = []
        total_batch = 0
        total_octeti_batch = 0
        for fl in fluxuri_tcp.values():
            octeti = _reasambleaza_tcp(fl)
            dims, stare = numara_batchuri_zenoh(octeti)
            if not fl.are_syn and stare == "aliniat":
                stare = "aliniat (dar fara SYN in captura: aliniere presupusa)"
            total_batch += len(dims)
            total_octeti_batch += sum(dims)
            hist = {}
            for d in dims:
                hist[d] = hist.get(d, 0) + 1
            det.append(dict(
                flux="%s:%s -> %s:%s" % (fl.cheie[0], fl.cheie[1],
                                         fl.cheie[2], fl.cheie[3]),
                segmente=fl.segmente, segmente_cu_date=fl.cu_date,
                octeti_payload=fl.octeti, octeti_reasamblati=len(octeti),
                are_syn=fl.are_syn, batchuri=len(dims), stare=stare,
                dimensiuni_batch=_histograma(hist)))
        det.sort(key=lambda d: -d["octeti_payload"])
        zenoh = dict(fluxuri=det, batchuri_total=total_batch,
                     octeti_in_batchuri=total_octeti_batch,
                     nota=("prefix de lungime u16 little-endian per batch; "
                           "lungimea nu se numara pe sine"))

    # ---- pasul 4: statistici RTPS pe esantion
    rtps = None
    if rtps_msg:
        h_dg, h_fr, h_ss = {}, {}, {}
        cu_retr = 0
        for st in rtps_esantioane.values():
            nd = len(st["datagrame"])
            nf = len(st["fragmente"])
            h_dg[nd] = h_dg.get(nd, 0) + 1
            h_fr[nf] = h_fr.get(nf, 0) + 1
            h_ss[st["sample_size"]] = h_ss.get(st["sample_size"], 0) + 1
            if st["emise"] > nf:
                cu_retr += 1
        rtps = dict(
            mesaje=rtps_msg,
            submesaje=dict(sorted(rtps_submsg.items())),
            data_frag=dict(
                submesaje=df_submesaje,
                fragmente_emise=df_fragmente,
                fragmente_in_submesaj=_histograma(df_hist_fis),
                fragment_size=_histograma(df_hist_fsize),
                esantioane=len(rtps_esantioane),
                esantioane_cu_retransmisii=cu_retr,
                datagrame_per_esantion=_histograma(h_dg),
                fragmente_unice_per_esantion=_histograma(h_fr),
                sample_size=_histograma(h_ss),
                mod_datagrame_per_esantion=_mod(h_dg),
                mod_fragmente_per_esantion=_mod(h_fr),
                depasit_limita_esantioane=rtps_prea_multe))

    # ---- pasul 5: multiplicitate
    n = opt.numar_esantioane
    unitati = dict(
        cadre=cadre_numarate,
        fragmente_ip=rez_udp["fragmente_ip"] + rez_tcp["fragmente_ip"],
        datagrame_udp=rez_udp["datagrame"],
        segmente_tcp=rez_tcp["segmente_cu_date"],
        batchuri_zenoh=(zenoh["batchuri_total"] if zenoh else None),
        octeti_l2=octeti_total - octeti_excluse - octeti_ne_ip,
        octeti_payload=rez_udp["octeti_payload"] + rez_tcp["octeti_payload"])
    mult = None
    if n:
        mult = {}
        for k, v in unitati.items():
            mult[k + "_per_esantion"] = (None if v is None else round(v / float(n), 4))
        util = n * float(opt.esantion_octeti)
        mult["suprasarcina_l2_procent"] = round(
            100.0 * (unitati["octeti_l2"] - util) / util, 3) if util else None

    avert = []
    # GARDA: --numar-esantioane e DECLARAT de om, iar RTPS masoara singur cate esantioane
    # distincte a vazut pe fir. Cand cele doua nu coincid, tot blocul 'multiplicitate' e
    # calculat pe un numitor gresit -- si tocmai el produce cifra care ajunge in articol.
    # Pana acum tabelul afisa ambele numere fara sa spuna ca se contrazic; defectul a iesit
    # la iveala fiindca un fixture de test declara 3 esantioane peste o captura care
    # continea unul singur repetat de trei ori, iar nimeni nu observase.
    # LIMITA CUNOSCUTA a acestei garzi (revizie adversariala, 2026-08-13): RTPS se
    # decodeaza doar cand clasificarea nu a fost deja fixata de --port-date/--port-discovery
    # (linia ~860). Cu una din acele optiuni date, 'rtps' ramane None si garda TACE. Deci
    # garda protejeaza drumul implicit -- cel pe care va rula campania -- dar NU e o
    # garantie generala. De reparat odata cu C3 din raportul de revizie.
    if n and rtps and rtps.get("data_frag", {}).get("esantioane"):
        masurat = rtps["data_frag"]["esantioane"]
        if masurat != n:
            avert.append("numar de esantioane DECLARAT (%d, prin --numar-esantioane) "
                         "difera de cel MASURAT din RTPS (%d writerSN distincte). Blocul "
                         "'multiplicitate' e impartit la %d, deci cifrele per esantion NU "
                         "sunt de incredere; ori captura contine retransmisii/duplicate, "
                         "ori numarul declarat e gresit." % (n, masurat, n))
    if buget_epuizat:
        avert.append("bugetul de memorie (%d MiB) s-a epuizat: sarcinile mari "
                     "nu au fost retinute integral, analiza RTPS/Zenoh acopera "
                     "doar inceputul capturii (creste --buget-mib)" % opt.buget_mib)
    if rez_udp["incomplete"] or rez_tcp["incomplete"]:
        avert.append("%d datagrame incomplete (fragmente lipsa sau captura "
                     "inceputa/oprita in mijlocul unui datagram)"
                     % (rez_udp["incomplete"] + rez_tcp["incomplete"]))
    if cadre_peste_mtu:
        avert.append("%d segmente TCP mai mari decat MTU %d: aproape sigur "
                     "GSO/TSO pe emitator sau GRO pe receptor. Numarul REAL de "
                     "segmente pe fir nu se vede in aceasta captura; vezi "
                     "'segmente estimate la MTU'. Dezactiveaza offload-ul "
                     "(ethtool -K tso off gso off gro off lro off) si repeta."
                     % (cadre_peste_mtu, opt.mtu))
    nefrag_mari = rez_udp["datagrame"] - rez_udp["datagrame_fragmentate"]
    if rez_udp["datagrame"] and fragmente_estimate > rez_udp["cadre"] and nefrag_mari:
        avert.append("exista datagrame UDP nefragmentate mai mari decat MTU %d: "
                     "captura pare facuta pe o interfata cu MTU mare (lo are "
                     "65536). Pe banc, la MTU %d, ar rezulta %d fragmente IP."
                     % (opt.mtu, opt.mtu, fragmente_estimate))
    if rez_udp["duplicate"]:
        avert.append("%d fragmente IP duplicate (retransmisii sau captura "
                     "dubla pe aceeasi interfata)" % rez_udp["duplicate"])

    return dict(
        eticheta=opt.eticheta,
        container=dict(format=meta["format"], endian=meta.get("endian"),
                       rezolutie_ts=meta.get("rezolutie_ts"),
                       snaplen=meta.get("snaplen"),
                       linktype=(sorted(linktypes) or [None])[0],
                       linktype_nume=LINKTYPES.get((sorted(linktypes) or [None])[0],
                                                   "necunoscut"),
                       cadre_pe_linktype=_histograma(linktypes)),
        cadre=dict(total=cadre_total, ne_ip=cadre_ne_ip,
                   excluse_de_filtre=cadre_excluse, numarate=cadre_numarate),
        octeti=dict(total_l2=octeti_total, ne_ip=octeti_ne_ip,
                    excluse_de_filtre=octeti_excluse,
                    numarate_l2=octeti_total - octeti_excluse - octeti_ne_ip,
                    nota="fara preambul (8 B) si FCS (4 B) per cadru, ca tcpdump"),
        udp=rez_udp, tcp=rez_tcp, alte_protocoale=rez_alt,
        clase=clase, rtps=rtps, zenoh=zenoh,
        normalizare_mtu=dict(
            mtu=opt.mtu, mss=opt.mss,
            fragmente_ip_estimate_udp=fragmente_estimate,
            segmente_tcp_estimate=segmente_estimate,
            cadre_peste_mtu=cadre_peste_mtu,
            nota=("estimare aritmetica pornind de la lungimile reale "
                  "(RFC 791 pentru UDP, MSS pentru TCP), NU o observatie; "
                  "utila cand captura e pe lo sau cu GSO/GRO active")),
        unitati_de_fir=unitati,
        numar_esantioane=n,
        multiplicitate=mult,
        avertismente=avert)


def analizeaza(cale, opt):
    with open(cale, "rb") as f:
        rez = analizeaza_flux(f, opt)
    rez["fisier"] = os.path.abspath(cale)
    return rez


def analizeaza_octeti(date, opt):
    return analizeaza_flux(io.BytesIO(date), opt)


# -------------------------------------------------------------------- raport

def _linie(eticheta, valoare, per=None):
    v = "%s" % valoare
    if per is None:
        return "  %-34s %14s" % (eticheta, v)
    return "  %-34s %14s   %10s /esantion" % (eticheta, v, per)


def formateaza_tabel(r):
    n = r["numar_esantioane"]
    m = r["multiplicitate"] or {}

    def pe(cheie):
        if not n:
            return None
        v = m.get(cheie + "_per_esantion")
        return "-" if v is None else ("%.4g" % v)

    L = []
    A = L.append
    lat = 76
    A("=" * lat)
    A("count_wire_units -- unitati de fir per esantion de aplicatie")
    A("=" * lat)
    c = r["container"]
    A("  fisier      : %s" % r.get("fisier", "(flux in memorie)"))
    if r.get("eticheta"):
        A("  eticheta    : %s" % r["eticheta"])
    A("  container   : %s, endian %s, ts %s, linktype %s (%s)"
      % (c["format"], c["endian"], c["rezolutie_ts"], c["linktype"],
         c["linktype_nume"]))
    f = r["cadre"]
    A("  cadre       : %d total | %d non-IP | %d excluse de filtre | %d numarate"
      % (f["total"], f["ne_ip"], f["excluse_de_filtre"], f["numarate"]))
    A("  esantioane  : %s" % (n if n else "necunoscut (da --numar-esantioane)"))
    A("-" * lat)

    u = r["udp"]
    if u["datagrame"]:
        A("UDP (datagrame reconstruite din fragmente IP)")
        A(_linie("datagrame UDP", u["datagrame"], pe("datagrame_udp")))
        A(_linie("  din care fragmentate", u["datagrame_fragmentate"]))
        A(_linie("  incomplete", u["incomplete"]))
        A(_linie("cadre (fragmente IP)", u["cadre"], pe("cadre")))
        A(_linie("  cu offset IP zero (decodate UDP)", u["cadre_prim_fragment"]))
        A(_linie("  fragmente duplicate", u["duplicate"]))
        A(_linie("octeti L2", u["octeti_l2"]))
        A(_linie("octeti sarcina UDP", u["octeti_payload"]))
        A("-" * lat)

    t = r["tcp"]
    if t["segmente"]:
        A("TCP (fiecare segment este o unitate de fir; nu exista reasamblare)")
        A(_linie("segmente cu date", t["segmente_cu_date"], pe("segmente_tcp")))
        A(_linie("segmente fara date (ACK/SYN/FIN)", t["segmente_fara_date"]))
        A(_linie("cadre", t["cadre"]))
        A(_linie("octeti L2", t["octeti_l2"]))
        A(_linie("octeti sarcina TCP", t["octeti_payload"]))
        A("-" * lat)

    z = r["zenoh"]
    if z:
        A("Zenoh (batch-uri reconstruite din fluxul TCP, prefix u16 LE)")
        A(_linie("batch-uri", z["batchuri_total"], pe("batchuri_zenoh")))
        A(_linie("octeti in batch-uri", z["octeti_in_batchuri"]))
        for d in z["fluxuri"][:6]:
            A("    %s" % d["flux"])
            A("      segmente=%d cu_date=%d octeti=%d batchuri=%d syn=%s"
              % (d["segmente"], d["segmente_cu_date"], d["octeti_payload"],
                 d["batchuri"], "da" if d["are_syn"] else "nu"))
            A("      stare reasamblare: %s" % d["stare"])
            A("      dimensiuni batch: %s" % d["dimensiuni_batch"])
        A("-" * lat)

    rt = r["rtps"]
    if rt:
        A("RTPS (decodat din sarcina UDP)")
        A(_linie("mesaje RTPS", rt["mesaje"]))
        A(_linie("submesaje", ", ".join("%s=%d" % kv
                                        for kv in rt["submesaje"].items())))
        df = rt["data_frag"]
        if df["submesaje"]:
            A(_linie("submesaje DATA_FRAG", df["submesaje"]))
            A(_linie("fragmente RTPS emise", df["fragmente_emise"]))
            A(_linie("fragmente/submesaj", df["fragmente_in_submesaj"]))
            A(_linie("FragmentSize (per submesaj)", df["fragment_size"]))
            A(_linie("sampleSize (per esantion)", df["sample_size"]))
            A(_linie("esantioane RTPS distincte", df["esantioane"]))
            A(_linie("  cu retransmisii", df["esantioane_cu_retransmisii"]))
            A(_linie("datagrame/esantion (histograma)",
                     df["datagrame_per_esantion"]))
            A(_linie("fragmente unice/esantion", df["fragmente_unice_per_esantion"]))
            A("  >>> MULTIPLICITATE RTPS MASURATA: %s datagrame si %s fragmente "
              "per esantion" % (df["mod_datagrame_per_esantion"],
                                df["mod_fragmente_per_esantion"]))
        A("-" * lat)

    if r["clase"]:
        A("Clasificare date / discovery / control")
        for nume in ("date", "discovery", "control", "neclasificat"):
            cl = r["clase"].get(nume)
            if not cl:
                continue
            A("  %-14s datagrame=%-7d cadre=%-7d octeti_L2=%-10d"
              % (nume, cl["datagrame"], cl["cadre"], cl["octeti_l2"]))
            for mot, k in cl["motive"].items():
                A("      criteriu: %s (x%d)" % (mot, k))
        A("-" * lat)

    nm = r["normalizare_mtu"]
    A("Normalizare la MTU %d / MSS %d (ESTIMARE aritmetica, nu observatie)"
      % (nm["mtu"], nm["mss"]))
    A(_linie("fragmente IP daca UDP s-ar fragmenta", nm["fragmente_ip_estimate_udp"]))
    A(_linie("segmente TCP la MSS", nm["segmente_tcp_estimate"]))
    A(_linie("cadre mai mari decat MTU (GSO/GRO?)", nm["cadre_peste_mtu"]))
    A("-" * lat)

    A("UNITATI DE FIR")
    un = r["unitati_de_fir"]
    for cheie, et in (("cadre", "cadre pe fir"),
                      ("fragmente_ip", "fragmente IP"),
                      ("datagrame_udp", "datagrame UDP"),
                      ("segmente_tcp", "segmente TCP cu date"),
                      ("batchuri_zenoh", "batch-uri Zenoh"),
                      ("octeti_l2", "octeti L2"),
                      ("octeti_payload", "octeti sarcina L4")):
        v = un[cheie]
        if v is None:
            continue
        A(_linie(et, v, pe(cheie)))
    if n and m.get("suprasarcina_l2_procent") is not None:
        A(_linie("suprasarcina L2 fata de %d B utili" % r.get("_eo", 65536),
                 "%.3f %%" % m["suprasarcina_l2_procent"]))
    A("=" * lat)

    if r["avertismente"]:
        A("AVERTISMENTE")
        for a in r["avertismente"]:
            A("  - %s" % a)
        A("=" * lat)
    return "\n".join(L)


# ------------------------------------------------------------------ selftest

def _suma_internet(b):
    if len(b) % 2:
        b = b + b"\x00"
    s = 0
    for i in range(0, len(b), 2):
        s += (b[i] << 8) | b[i + 1]
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _ip4(txt):
    return bytes(int(x) for x in txt.split("."))


def _fab_ipv4(src, dst, proto, ident, off_octeti, mf, sarcina, ttl=64):
    total = 20 + len(sarcina)
    fo = (off_octeti // 8) & 0x1FFF
    if mf:
        fo |= 0x2000
    h = struct.pack(">BBHHHBBH", 0x45, 0, total, ident, fo, ttl, proto, 0)
    h += _ip4(src) + _ip4(dst)
    h = h[:10] + struct.pack(">H", _suma_internet(h)) + h[12:]
    return h + sarcina


def _fab_udp(sport, dport, sarcina):
    return struct.pack(">HHHH", sport, dport, 8 + len(sarcina), 0) + sarcina


def _fab_tcp(sport, dport, seq, sarcina, flags=0x18, optiuni=b""):
    if len(optiuni) % 4:
        optiuni += b"\x00" * (4 - len(optiuni) % 4)
    do = (20 + len(optiuni)) // 4
    h = struct.pack(">HHIIBBHHH", sport, dport, seq, 0, do << 4, flags,
                    65535, 0, 0)
    return h + optiuni + sarcina


def _fab_eth(sarcina, ethertype=0x0800):
    return (b"\x02\x00\x00\x00\x00\x02" + b"\x02\x00\x00\x00\x00\x01"
            + struct.pack(">H", ethertype) + sarcina)


def _fragmenteaza(src, dst, proto, ident, sarcina_l4, mtu=1500):
    """Taie o sarcina L4 in fragmente IP, ca nucleul (RFC 791)."""
    util = ((mtu - 20) // 8) * 8
    out = []
    off = 0
    while off < len(sarcina_l4):
        bucata = sarcina_l4[off:off + util]
        mf = (off + len(bucata)) < len(sarcina_l4)
        out.append(_fab_eth(_fab_ipv4(src, dst, proto, ident, off, mf, bucata)))
        off += len(bucata)
    return out


def _fab_pcap(cadre, linktype=1, endian="<", nano=False):
    magic = 0xa1b23c4d if nano else 0xa1b2c3d4
    out = [struct.pack(endian + "IHHiIII", magic, 2, 4, 0, 0, 262144, linktype)]
    for i, c in enumerate(cadre):
        frac = (i * 1000) if nano else i
        out.append(struct.pack(endian + "IIII", 1700000000 + i, frac,
                               len(c), len(c)))
        out.append(c)
    return b"".join(out)


def _fab_pcapng(cadre, linktype=1):
    shb_corp = struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1) + struct.pack("<HH", 0, 0)
    shb = (struct.pack("<II", 0x0A0D0D0A, 12 + len(shb_corp)) + shb_corp
           + struct.pack("<I", 12 + len(shb_corp)))
    idb_corp = struct.pack("<HHI", linktype, 0, 262144) + struct.pack("<HH", 0, 0)
    idb = (struct.pack("<II", 1, 12 + len(idb_corp)) + idb_corp
           + struct.pack("<I", 12 + len(idb_corp)))
    out = [shb, idb]
    for i, c in enumerate(cadre):
        pad = (-len(c)) % 4
        corp = (struct.pack("<IIIII", 0, 0, 1700000000 + i, len(c), len(c))
                + c + b"\x00" * pad + struct.pack("<HH", 0, 0))
        out.append(struct.pack("<II", 6, 12 + len(corp)) + corp
                   + struct.pack("<I", 12 + len(corp)))
    return b"".join(out)


def _fab_rtps(guid, submesaje):
    out = [b"RTPS" + bytes([2, 2]) + b"\x01\x10" + guid]
    out.extend(submesaje)
    return b"".join(out)


def _fab_submsg(sid, corp):
    return struct.pack("<BBH", sid, 0x01, len(corp)) + corp


def _fab_data_frag(reader, writer, sn, start, n_frag, frag_size, sample_size,
                   octeti_utili):
    corp = struct.pack("<HH", 0, 16) + reader + writer
    corp += struct.pack("<iI", sn >> 32, sn & 0xFFFFFFFF)
    corp += struct.pack("<IHHI", start, n_frag, frag_size, sample_size)
    corp += octeti_utili
    return _fab_submsg(0x16, corp)


def _fab_heartbeat(reader, writer, first, last, count):
    corp = reader + writer
    corp += struct.pack("<iI", first >> 32, first & 0xFFFFFFFF)
    corp += struct.pack("<iI", last >> 32, last & 0xFFFFFFFF)
    corp += struct.pack("<I", count)
    return _fab_submsg(0x07, corp)


def _selftest():
    v = 0

    # ---- 1. un datagram UDP mic: exact 1 cadru, 1 datagram, 0 fragmente
    cadre = [_fab_eth(_fab_ipv4("10.0.0.1", "10.0.0.2", PROTO_UDP, 111, 0,
                                False, _fab_udp(7411, 7411, b"x" * 100)))]
    r = analizeaza_octeti(_fab_pcap(cadre), Optiuni())
    assert r["cadre"]["total"] == 1, r["cadre"]
    assert r["udp"]["datagrame"] == 1, r["udp"]
    assert r["udp"]["datagrame_fragmentate"] == 0, r["udp"]
    assert r["udp"]["fragmente_ip"] == 0, r["udp"]
    assert r["udp"]["octeti_payload"] == 100, r["udp"]
    assert r["udp"]["incomplete"] == 0, r["udp"]
    assert r["octeti"]["numarate_l2"] == 14 + 20 + 8 + 100
    v += 6

    # ---- 2. un datagram UDP de ~64 KB fragmentat in 45 de fragmente IP.
    #        Nota: un esantion de 65536 B NU incape intr-un singur datagram
    #        UDP (campul totalLength din IP e pe 16 biti, deci maximul absolut
    #        e 65535 - 20 - 8 = 65507 B de sarcina UDP). Exact de aceea RTPS
    #        fragmenteaza el insusi, la nivel DDSI, inainte de UDP.
    sarcina = _fab_udp(7411, 7411, b"A" * 65507)          # 65515 B L4
    assert len(sarcina) == 65515
    fr = _fragmenteaza("10.0.0.1", "10.0.0.2", PROTO_UDP, 222, sarcina)
    assert len(fr) == 45, len(fr)
    r = analizeaza_octeti(_fab_pcap(fr), Optiuni(numar_esantioane=1))
    assert r["cadre"]["total"] == 45
    assert r["udp"]["datagrame"] == 1, r["udp"]["datagrame"]
    assert r["udp"]["datagrame_fragmentate"] == 1
    assert r["udp"]["fragmente_ip"] == 45, r["udp"]["fragmente_ip"]
    assert r["udp"]["cadre_prim_fragment"] == 1
    assert r["udp"]["octeti_payload"] == 65507, r["udp"]["octeti_payload"]
    assert r["udp"]["incomplete"] == 0
    assert r["multiplicitate"]["datagrame_udp_per_esantion"] == 1.0
    assert r["multiplicitate"]["cadre_per_esantion"] == 45.0
    v += 8

    # ---- 3. doua fluxuri intercalate: gruparea dupa (src,dst,proto,ID)
    #        cazul greu: ACELASI IP ID pe amandoua, doar gazdele difera
    a = _fragmenteaza("10.0.0.1", "10.0.0.2", PROTO_UDP, 777,
                      _fab_udp(7411, 7411, b"a" * 4000))
    b = _fragmenteaza("10.0.0.3", "10.0.0.4", PROTO_UDP, 777,
                      _fab_udp(7411, 7411, b"b" * 4000))
    assert len(a) == 3 and len(b) == 3
    inter = [a[0], b[0], a[1], b[1], a[2], b[2]]
    r = analizeaza_octeti(_fab_pcap(inter), Optiuni())
    assert r["udp"]["datagrame"] == 2, r["udp"]["datagrame"]
    assert r["udp"]["fragmente_ip"] == 6
    assert r["udp"]["incomplete"] == 0, r["udp"]["incomplete"]
    assert r["udp"]["octeti_payload"] == 8000, r["udp"]["octeti_payload"]
    v += 4

    # ---- 3b. acelasi IP ID, ACEEASI pereche de gazde, secvential (reuz de ID)
    c1 = _fragmenteaza("10.0.0.1", "10.0.0.2", PROTO_UDP, 900,
                       _fab_udp(7411, 7411, b"c" * 4000))
    r = analizeaza_octeti(_fab_pcap(c1 + c1), Optiuni())
    assert r["udp"]["datagrame"] == 2, r["udp"]["datagrame"]
    assert r["udp"]["incomplete"] == 0
    v += 2

    # ---- 4. un flux TCP cu segmente
    seg = []
    seq = 1000
    seg.append(_fab_eth(_fab_ipv4("10.0.0.1", "10.0.0.2", PROTO_TCP, 1, 0,
                                  False, _fab_tcp(40000, 7447, seq, b"",
                                                  flags=0x02))))
    seq += 1
    for i in range(5):
        corp = bytes([65 + i]) * 1448
        seg.append(_fab_eth(_fab_ipv4("10.0.0.1", "10.0.0.2", PROTO_TCP, 2 + i,
                                      0, False, _fab_tcp(40000, 7447, seq, corp))))
        seq += len(corp)
    r = analizeaza_octeti(_fab_pcap(seg), Optiuni())
    assert r["tcp"]["segmente"] == 6, r["tcp"]
    assert r["tcp"]["segmente_cu_date"] == 5, r["tcp"]
    assert r["tcp"]["segmente_fara_date"] == 1
    assert r["tcp"]["octeti_payload"] == 5 * 1448
    assert r["udp"]["datagrame"] == 0
    v += 5

    # ---- 5. endianness inversat: aceleasi cifre exact
    r_le = analizeaza_octeti(_fab_pcap(fr, endian="<"), Optiuni())
    r_be = analizeaza_octeti(_fab_pcap(fr, endian=">"), Optiuni())
    assert r_le["container"]["endian"] == "<"
    assert r_be["container"]["endian"] == ">"
    assert r_le["udp"] == r_be["udp"], (r_le["udp"], r_be["udp"])
    assert r_le["octeti"]["numarate_l2"] == r_be["octeti"]["numarate_l2"]
    v += 4

    # ---- 5b. marci de timp in nanosecunde si container pcapng
    r_ns = analizeaza_octeti(_fab_pcap(fr, nano=True), Optiuni())
    assert r_ns["container"]["rezolutie_ts"] == "ns"
    assert r_ns["udp"] == r_le["udp"]
    r_ng = analizeaza_octeti(_fab_pcapng(fr), Optiuni())
    assert r_ng["container"]["format"] == "pcapng", r_ng["container"]
    assert r_ng["udp"]["datagrame"] == 1 and r_ng["udp"]["fragmente_ip"] == 45
    assert r_ng["octeti"]["numarate_l2"] == r_le["octeti"]["numarate_l2"]
    v += 5

    # ---- 6. pcap trunchiat -> EroarePcap curata, nu exceptie oarecare
    intreg = _fab_pcap(fr)
    for taietura, ce in ((10, "antet global"), (30, "antet de pachet"),
                         (24 + 16 + 100, "date de pachet")):
        try:
            analizeaza_octeti(intreg[:taietura], Optiuni())
        except EroarePcap as ex:
            assert "trunchiat" in str(ex) or "prea scurt" in str(ex), str(ex)
        else:
            raise AssertionError("nu a ridicat EroarePcap la %s" % ce)
        v += 1
    try:
        analizeaza_octeti(b"nu-este-pcap-deloc-xxxx", Optiuni())
    except EroarePcap as ex:
        assert "magic necunoscut" in str(ex), str(ex)
    else:
        raise AssertionError("nu a ridicat EroarePcap la magic invalid")
    v += 1
    # pcapng trunchiat
    try:
        analizeaza_octeti(_fab_pcapng(fr)[:60], Optiuni())
    except EroarePcap:
        pass
    else:
        raise AssertionError("nu a ridicat EroarePcap la pcapng trunchiat")
    v += 1

    # ---- 7. filtrarea pe port si pe gazda (aplicata pe DATAGRAM, nu pe cadru,
    #        fiindca fragmentele urmatoare nu au antet UDP)
    mix = list(fr)                                   # 45 cadre pe portul 7411
    mix.append(_fab_eth(_fab_ipv4("10.0.0.9", "10.0.0.2", PROTO_TCP, 5, 0,
                                  False, _fab_tcp(50000, 22, 1, b"z" * 60))))
    mix.append(_fab_eth(_fab_ipv4("10.0.0.1", "10.0.0.2", PROTO_UDP, 6, 0,
                                  False, _fab_udp(7400, 7400, b"d" * 40))))
    r = analizeaza_octeti(_fab_pcap(mix), Optiuni(exclude_port={22}))
    assert r["tcp"]["segmente"] == 0, r["tcp"]
    assert r["cadre"]["excluse_de_filtre"] == 1
    assert r["udp"]["datagrame"] == 2
    r = analizeaza_octeti(_fab_pcap(mix), Optiuni(filtru_port=_parse_porturi("7411")))
    assert r["udp"]["datagrame"] == 1 and r["udp"]["fragmente_ip"] == 45, r["udp"]
    assert r["cadre"]["excluse_de_filtre"] == 2, r["cadre"]
    r = analizeaza_octeti(_fab_pcap(mix), Optiuni(exclude_gazda={"10.0.0.9"}))
    assert r["tcp"]["segmente"] == 0 and r["udp"]["datagrame"] == 2
    v += 7

    # ---- 8. clasificarea date / discovery pe formula de porturi RTPS
    assert clasa_port_rtps(7400)[0] == "discovery"    # domeniu 0, SPDP mcast
    assert clasa_port_rtps(7401)[0] == "date"         # user multicast
    assert clasa_port_rtps(7410)[0] == "discovery"    # meta unicast
    assert clasa_port_rtps(7411)[0] == "date"         # user unicast
    assert clasa_port_rtps(9160)[0] == "discovery" and clasa_port_rtps(9160)[1] == 7
    assert clasa_port_rtps(80) is None
    r = analizeaza_octeti(_fab_pcap(mix), Optiuni())
    assert r["clase"]["date"]["datagrame"] == 1, r["clase"]
    assert r["clase"]["discovery"]["datagrame"] == 1, r["clase"]
    v += 8

    # ---- 9. RTPS: decodarea DATA_FRAG si multiplicitatea per esantion
    #        reproduce EXACT tiparul masurat la CycloneDDS pentru 64 KB
    guid = bytes(range(12))
    reader_user = b"\x00\x00\x01\x04"                # entityKind 0x04 = user
    writer_user = b"\x00\x00\x01\x02"                # entityKind 0x02 = user
    writer_bi = b"\x00\x00\x01\xc2"                  # 0xc2 -> builtin
    sample_size = 65592
    dims = [13536, 13524, 13524, 13524, 11868]
    plan = [(1, 10), (11, 10), (21, 10), (31, 10), (41, 9)]

    def _cyc(sn):
        """Cele 49 de cadre ale unui esantion de 64 KB, ca la CycloneDDS."""
        out = []
        for i, (start, nf) in enumerate(plan):
            util = 1344 * nf if nf == 10 else 1344 * 8 + 1028
            subs = [_fab_data_frag(reader_user, writer_user, sn, start, nf,
                                   1344, sample_size, b"\x00" * util)]
            if i == len(plan) - 1:
                subs.append(_fab_heartbeat(reader_user, writer_user, 1, sn, sn))
            msg = _fab_rtps(guid, subs)
            # se completeaza pana la dimensiunea masurata pe fir a datagramei
            if len(msg) < dims[i]:
                msg += b"\x00" * (dims[i] - len(msg))
            msg = msg[:dims[i]]
            out.extend(_fragmenteaza("10.0.0.1", "10.0.0.2", PROTO_UDP,
                                     1000 + 10 * sn + i,
                                     _fab_udp(7411, 7411, msg)))
        return out

    cadre_cyc = _cyc(1)
    r = analizeaza_octeti(_fab_pcap(cadre_cyc), Optiuni(numar_esantioane=1))
    assert r["cadre"]["total"] == 49, r["cadre"]["total"]
    assert r["udp"]["datagrame"] == 5, r["udp"]["datagrame"]
    assert r["udp"]["fragmente_ip"] == 49, r["udp"]["fragmente_ip"]
    assert r["udp"]["cadre_prim_fragment"] == 5
    assert r["octeti"]["numarate_l2"] == 67682, r["octeti"]["numarate_l2"]
    df = r["rtps"]["data_frag"]
    assert r["rtps"]["mesaje"] == 5, r["rtps"]["mesaje"]
    assert df["submesaje"] == 5, df["submesaje"]
    assert df["fragmente_emise"] == 49, df["fragmente_emise"]
    assert df["esantioane"] == 1, df["esantioane"]
    assert df["mod_datagrame_per_esantion"] == 5, df
    assert df["mod_fragmente_per_esantion"] == 49, df
    assert df["esantioane_cu_retransmisii"] == 0, df
    # fragment_size se numara per submesaj DATA_FRAG (5), sample_size per
    # esantion RTPS distinct (1)
    assert df["fragment_size"] == {"1344": 5}, df["fragment_size"]
    assert df["sample_size"] == {"65592": 1}, df["sample_size"]
    assert r["rtps"]["submesaje"]["DATA_FRAG"] == 5
    assert r["rtps"]["submesaje"]["HEARTBEAT"] == 1
    assert r["clase"]["date"]["datagrame"] == 5, r["clase"]
    assert r["multiplicitate"]["cadre_per_esantion"] == 49.0
    assert r["multiplicitate"]["datagrame_udp_per_esantion"] == 5.0
    assert abs(r["multiplicitate"]["suprasarcina_l2_procent"] - 3.274) < 0.01, \
        r["multiplicitate"]["suprasarcina_l2_procent"]
    v += 18

    # ---- 9b. retransmisia: acelasi esantion, alt fragment -> se vede
    rex = _fab_rtps(guid, [_fab_data_frag(reader_user, writer_user, 1, 5, 1,
                                          1344, sample_size, b"\x00" * 1344)])
    cadre_rex = cadre_cyc + _fragmenteaza("10.0.0.1", "10.0.0.2", PROTO_UDP,
                                          2000, _fab_udp(7411, 7411, rex))
    r2 = analizeaza_octeti(_fab_pcap(cadre_rex), Optiuni(numar_esantioane=1))
    df2 = r2["rtps"]["data_frag"]
    assert df2["fragmente_emise"] == 50, df2["fragmente_emise"]
    assert df2["mod_fragmente_per_esantion"] == 49, df2
    assert df2["mod_datagrame_per_esantion"] == 6, df2
    assert df2["esantioane_cu_retransmisii"] == 1, df2
    assert r2["udp"]["datagrame"] == 6
    v += 5

    # ---- 9c. DATA_FRAG de la un writer builtin -> discovery, nu date
    bi = _fab_rtps(guid, [_fab_data_frag(reader_user, writer_bi, 1, 1, 1, 1344,
                                         1344, b"\x00" * 1344)])
    r3 = analizeaza_octeti(
        _fab_pcap([_fab_eth(_fab_ipv4("10.0.0.1", "10.0.0.2", PROTO_UDP, 3, 0,
                                      False, _fab_udp(7410, 7410, bi)))]),
        Optiuni())
    assert r3["clase"]["discovery"]["datagrame"] == 1, r3["clase"]
    assert "RTPS decodat" in list(r3["clase"]["discovery"]["motive"])[0]
    # datagram doar cu HEARTBEAT -> control
    hb = _fab_rtps(guid, [_fab_heartbeat(reader_user, writer_user, 1, 5, 3)])
    r4 = analizeaza_octeti(
        _fab_pcap([_fab_eth(_fab_ipv4("10.0.0.2", "10.0.0.1", PROTO_UDP, 4, 0,
                                      False, _fab_udp(7411, 7411, hb)))]),
        Optiuni())
    assert r4["clase"]["control"]["datagrame"] == 1, r4["clase"]
    v += 4

    # ---- 10. Zenoh: 2 batch-uri (49152 + 16475) taiate in 46 segmente TCP
    b1 = struct.pack("<H", 49150) + b"\x01" * 49150
    b2 = struct.pack("<H", 16473) + b"\x02" * 16473
    flux = b1 + b2
    assert len(flux) == 65627, len(flux)
    ts_opt = b"\x01\x01\x08\x0a" + struct.pack(">II", 1, 2)   # NOP NOP TS
    cadre_z = [_fab_eth(_fab_ipv4("10.0.0.1", "10.0.0.2", PROTO_TCP, 1, 0,
                                  False, _fab_tcp(40000, 7447, 1000, b"",
                                                  flags=0x02)))]
    seq = 1001
    poz = 0
    while poz < len(flux):
        corp = flux[poz:poz + 1448]
        cadre_z.append(_fab_eth(_fab_ipv4(
            "10.0.0.1", "10.0.0.2", PROTO_TCP, 2 + poz // 1448, 0, False,
            _fab_tcp(40000, 7447, seq, corp, optiuni=ts_opt))))
        seq += len(corp)
        poz += len(corp)
    assert len(cadre_z) == 47, len(cadre_z)
    r = analizeaza_octeti(_fab_pcap(cadre_z), Optiuni(numar_esantioane=1))
    assert r["tcp"]["segmente_cu_date"] == 46, r["tcp"]
    assert r["tcp"]["octeti_payload"] == 65627, r["tcp"]["octeti_payload"]
    assert r["udp"]["datagrame"] == 0
    assert r["octeti"]["numarate_l2"] == 45 * 1514 + 533 + 54, \
        r["octeti"]["numarate_l2"]
    assert r["octeti"]["numarate_l2"] - 47 * 14 == 68019 + 40, \
        r["octeti"]["numarate_l2"]
    z = r["zenoh"]
    assert z["batchuri_total"] == 2, z
    assert z["fluxuri"][0]["stare"] == "aliniat", z["fluxuri"][0]
    assert z["fluxuri"][0]["are_syn"] is True
    assert z["fluxuri"][0]["dimensiuni_batch"] == {"16475": 1, "49152": 1}, \
        z["fluxuri"][0]["dimensiuni_batch"]
    assert r["multiplicitate"]["segmente_tcp_per_esantion"] == 46.0
    assert r["multiplicitate"]["batchuri_zenoh_per_esantion"] == 2.0
    assert r["normalizare_mtu"]["cadre_peste_mtu"] == 0, r["normalizare_mtu"]
    v += 12

    # ---- 10b. captura cu GSO: 2 super-pachete in loc de 46 -> avertisment
    #           si estimarea corecta la MSS
    cadre_g = []
    seq = 1001
    for corp in (flux[:49152], flux[49152:]):
        cadre_g.append(_fab_eth(_fab_ipv4(
            "10.0.0.1", "10.0.0.2", PROTO_TCP, 7, 0, False,
            _fab_tcp(40000, 7447, seq, corp, optiuni=ts_opt))))
        seq += len(corp)
    r = analizeaza_octeti(_fab_pcap(cadre_g), Optiuni(numar_esantioane=1))
    assert r["tcp"]["segmente_cu_date"] == 2, r["tcp"]
    assert r["tcp"]["octeti_payload"] == 65627
    assert r["normalizare_mtu"]["cadre_peste_mtu"] == 2
    assert r["normalizare_mtu"]["segmente_tcp_estimate"] == 46, \
        r["normalizare_mtu"]
    assert any("GSO" in a for a in r["avertismente"]), r["avertismente"]
    assert r["zenoh"]["batchuri_total"] == 2
    assert r["zenoh"]["fluxuri"][0]["are_syn"] is False
    assert "fara SYN" in r["zenoh"]["fluxuri"][0]["stare"]
    v += 8

    # ---- 10c. flux TCP cu gaura (segment lipsa) -> reasamblare oprita curat
    cadre_h = [c for i, c in enumerate(cadre_z) if i != 3]
    r = analizeaza_octeti(_fab_pcap(cadre_h), Optiuni())
    assert r["tcp"]["segmente_cu_date"] == 45
    assert r["zenoh"]["batchuri_total"] == 0, r["zenoh"]
    assert "dezaliniat" in r["zenoh"]["fluxuri"][0]["stare"] or \
        "partial" in r["zenoh"]["fluxuri"][0]["stare"], r["zenoh"]["fluxuri"][0]
    v += 3

    # ---- 11. captura pe lo (MTU 65536): datagram nefragmentat de 64 KB;
    #          instrumentul trebuie sa prezica cele 45 de fragmente la MTU 1500
    lo = [_fab_eth(_fab_ipv4("127.0.0.1", "127.0.0.1", PROTO_UDP, 42, 0, False,
                             sarcina))]
    r = analizeaza_octeti(_fab_pcap(lo), Optiuni(numar_esantioane=1))
    assert r["udp"]["datagrame"] == 1 and r["udp"]["fragmente_ip"] == 0
    assert r["cadre"]["total"] == 1
    assert r["normalizare_mtu"]["fragmente_ip_estimate_udp"] == 45, \
        r["normalizare_mtu"]
    assert any("MTU mare" in a for a in r["avertismente"]), r["avertismente"]
    v += 4

    # ---- 12. linktype-uri alternative: LINUX_SLL2 (tcpdump -i any) si RAW
    cadru_ip = _fab_ipv4("10.0.0.1", "10.0.0.2", PROTO_UDP, 50, 0, False,
                         _fab_udp(7411, 7411, b"q" * 30))
    sll2 = struct.pack(">HHIHBB", 0x0800, 0, 2, 1, 0, 6) + b"\x00" * 8 + cadru_ip
    r = analizeaza_octeti(_fab_pcap([sll2], linktype=276), Optiuni())
    assert r["udp"]["datagrame"] == 1 and r["cadre"]["ne_ip"] == 0, r["udp"]
    r = analizeaza_octeti(_fab_pcap([cadru_ip], linktype=101), Optiuni())
    assert r["udp"]["datagrame"] == 1 and r["udp"]["octeti_payload"] == 30
    sll = struct.pack(">HHH", 0, 1, 6) + b"\x00" * 8 + b"\x08\x00" + cadru_ip
    r = analizeaza_octeti(_fab_pcap([sll], linktype=113), Optiuni())
    assert r["udp"]["datagrame"] == 1
    v += 4

    # ---- 13. cadre non-IP (ARP) si VLAN
    arp = _fab_eth(b"\x00" * 28, ethertype=0x0806)
    vlan = (b"\x02\x00\x00\x00\x00\x02" + b"\x02\x00\x00\x00\x00\x01"
            + struct.pack(">HHH", 0x8100, 0x0064, 0x0800) + cadru_ip)
    r = analizeaza_octeti(_fab_pcap([arp, vlan]), Optiuni())
    assert r["cadre"]["ne_ip"] == 1, r["cadre"]
    assert r["udp"]["datagrame"] == 1, r["udp"]
    v += 2

    # ---- 14. IPv6 simplu (routerul Zenoh asculta pe tcp/[::]:7447)
    udp6 = _fab_udp(7447, 40000, b"w" * 12)              # 20 B L4
    ip6 = (struct.pack(">IHBB", 6 << 28, len(udp6), PROTO_UDP, 64)
           + b"\x00" * 15 + b"\x01" + b"\x00" * 15 + b"\x02" + udp6)
    r = analizeaza_octeti(_fab_pcap([_fab_eth(ip6, ethertype=0x86dd)]), Optiuni())
    assert r["udp"]["datagrame"] == 1, r["udp"]
    assert r["udp"]["octeti_payload"] == 12, r["udp"]
    assert r["udp"]["fragmente_ip"] == 0
    v += 3

    # ---- 14b. IPv6 cu antet de extensie Fragment (next header 44)
    l4_6 = _fab_udp(7447, 40000, b"y" * 1992)            # 2000 B L4
    cadre6 = []
    for off, mf in ((0, True), (1232, False)):
        bucata = l4_6[off:off + 1232]
        # offsetul din antetul Fragment IPv6 e in unitati de 8 octeti, pe
        # bitii de sus; bitul 0 este M (more fragments)
        fh = struct.pack(">BBHI", PROTO_UDP, 0,
                         ((off // 8) << 3) | (1 if mf else 0), 4242)
        cadre6.append(_fab_eth(
            struct.pack(">IHBB", 6 << 28, 8 + len(bucata), 44, 64)
            + b"\x00" * 15 + b"\x01" + b"\x00" * 15 + b"\x02" + fh + bucata,
            ethertype=0x86dd))
    r = analizeaza_octeti(_fab_pcap(cadre6), Optiuni())
    assert r["udp"]["datagrame"] == 1, r["udp"]
    assert r["udp"]["fragmente_ip"] == 2, r["udp"]
    assert r["udp"]["octeti_payload"] == 1992, r["udp"]
    assert r["udp"]["incomplete"] == 0, r["udp"]
    v += 4

    # ---- 15. multiplicitatea cu mai multe esantioane si tabelul se formeaza
    # Fixture-ul foloseste TREI writerSN distincte, nu aceiasi octeti de trei ori: altfel
    # RTPS vede corect un singur esantion purtat de 15 datagrame, iar testul ar pretinde
    # ca verifica 'mai multe esantioane' verificand de fapt unul replayat. Vezi 15b.
    cadre_3 = _cyc(1) + _cyc(2) + _cyc(3)
    r = analizeaza_octeti(_fab_pcap(cadre_3), Optiuni(numar_esantioane=3))
    assert r["multiplicitate"]["cadre_per_esantion"] == 49.0
    assert r["multiplicitate"]["datagrame_udp_per_esantion"] == 5.0
    assert r["rtps"]["data_frag"]["esantioane"] == 3, r["rtps"]["data_frag"]
    assert r["rtps"]["data_frag"]["mod_datagrame_per_esantion"] == 5
    assert r["rtps"]["data_frag"]["mod_fragmente_per_esantion"] == 49
    tab = formateaza_tabel(r)
    assert "MULTIPLICITATE RTPS MASURATA: 5 datagrame si 49 fragmente" in tab
    # declaratul si masuratul coincid -> NICIUN avertisment de nepotrivire
    assert not any("DECLARAT" in a for a in r["avertismente"]), r["avertismente"]
    assert isinstance(json.dumps(r), str)
    v += 8

    # ---- 15b. CONTROL NEGATIV pentru garda: acelasi esantion replayat de trei ori, dar
    # declarat ca trei. Asta era exact fixture-ul vechi, si tocmai el a ascuns defectul:
    # blocul 'multiplicitate' imparte la 3 desi pe fir exista un singur esantion, deci
    # scoate 5 datagrame/esantion cand adevarul RTPS e 15. Fara avertisment, cifra ar fi
    # plecat linistita spre articol.
    r_rep = analizeaza_octeti(_fab_pcap(cadre_cyc * 3), Optiuni(numar_esantioane=3))
    assert r_rep["rtps"]["data_frag"]["esantioane"] == 1, r_rep["rtps"]["data_frag"]
    assert r_rep["multiplicitate"]["datagrame_udp_per_esantion"] == 5.0
    assert r_rep["rtps"]["data_frag"]["mod_datagrame_per_esantion"] == 15
    nepotriviri = [a for a in r_rep["avertismente"] if "DECLARAT" in a]
    assert len(nepotriviri) == 1, r_rep["avertismente"]
    assert "MASURAT din RTPS (1" in nepotriviri[0], nepotriviri[0]
    assert "DECLARAT (3" in nepotriviri[0], nepotriviri[0]
    # si avertismentul chiar ajunge in tabel, nu doar in JSON
    assert "DECLARAT" in formateaza_tabel(r_rep)
    v += 7

    # ---- 16. main() cu fisier trunchiat: cod de iesire, fara traceback
    import tempfile
    d = tempfile.mkdtemp(prefix="cwu_")
    try:
        p_ok = os.path.join(d, "ok.pcap")
        p_rau = os.path.join(d, "rau.pcap")
        with open(p_ok, "wb") as fo:
            fo.write(_fab_pcap(cadre_cyc))
        with open(p_rau, "wb") as fo:
            fo.write(_fab_pcap(cadre_cyc)[:200])
        p_json = os.path.join(d, "out.json")
        cod = main([p_ok, "--numar-esantioane", "1", "--json", p_json,
                    "--liniste"])
        assert cod == 0, cod
        with open(p_json) as fj:
            jr = json.load(fj)
        assert jr["udp"]["datagrame"] == 5 and jr["cadre"]["total"] == 49
        cod = main([p_rau, "--liniste"])
        assert cod == 2, cod
        cod = main([os.path.join(d, "nu_exista.pcap"), "--liniste"])
        assert cod == 2, cod
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    v += 5

    print("SELFTEST count_wire_units OK (%d verificari: pcap/pcapng, ambele "
          "endianness, us+ns, trunchiere, fragmentare IP si grupare dupa "
          "(src,dst,proto,ID), TCP, batch-uri Zenoh, DATA_FRAG RTPS, filtre, "
          "clasificare, normalizare MTU/GSO)." % v)


# ---------------------------------------------------------------------- main

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(
        prog="count_wire_units.py",
        description="Numara unitatile de fir (cadre, fragmente IP, datagrame "
                    "UDP, segmente TCP, batch-uri Zenoh) per esantion de "
                    "aplicatie, dintr-o captura tcpdump.",
        epilog="Exemplu: count_wire_units.py c1.pcap --numar-esantioane 1000 "
               "--filtru-port 7400-7499 --json out.json")
    ap.add_argument("pcap", nargs="?", help="fisier .pcap sau .pcapng")
    ap.add_argument("--numar-esantioane", type=int, default=None,
                    help="cate esantioane a trimis bench_client (pentru multiplicitate)")
    ap.add_argument("--esantion-octeti", type=int, default=65536,
                    help="octeti utili per esantion, pentru procentul de suprasarcina")
    ap.add_argument("--filtru-port", default=None,
                    help="pastreaza doar datagramele cu acest port sursa sau "
                         "destinatie (lista si intervale: 7400-7499,7447)")
    ap.add_argument("--exclude-port", default=None,
                    help="elimina datagramele cu aceste porturi (ex: 22 pentru ssh)")
    ap.add_argument("--filtru-gazda", default=None,
                    help="pastreaza doar datagramele care ating aceste adrese IP")
    ap.add_argument("--exclude-gazda", default=None, help="elimina aceste adrese IP")
    ap.add_argument("--port-date", default=None,
                    help="porturi declarate explicit ca trafic de date")
    ap.add_argument("--port-discovery", default=None,
                    help="porturi declarate explicit ca discovery/control")
    ap.add_argument("--port-zenoh", default=str(PORT_ZENOH_IMPLICIT),
                    help="portul routerului Zenoh (implicit 7447)")
    ap.add_argument("--domeniu", default=None,
                    help="restrange formula de porturi RTPS la aceste "
                         "ROS_DOMAIN_ID (ex: 0,7); implicit oricare 0-232, "
                         "dar mereu cu ambele porturi in acelasi domeniu")
    ap.add_argument("--mtu", type=int, default=1500,
                    help="MTU pentru estimarile normalizate (implicit 1500)")
    ap.add_argument("--mss", type=int, default=1448,
                    help="MSS TCP pentru estimari (implicit 1448: MTU 1500 cu "
                         "optiunea timestamps activa)")
    ap.add_argument("--buget-mib", type=int, default=64,
                    help="memorie maxima pentru sarcinile retinute (implicit 64)")
    ap.add_argument("--batch-zenoh", choices=("auto", "da", "nu"), default="auto",
                    help="reconstruieste batch-urile Zenoh din fluxul TCP")
    ap.add_argument("--eticheta", default=None,
                    help="eticheta libera copiata in JSON (ex: cyclonedds/loss_15)")
    ap.add_argument("--json", default=None,
                    help="scrie raportul JSON in acest fisier ('-' = stdout)")
    ap.add_argument("--liniste", action="store_true",
                    help="fara tabel pe stdout (util cu --json)")
    ap.add_argument("--selftest", action="store_true",
                    help="ruleaza autotestul (fara retea, fara sudo) si iese")
    a = ap.parse_args(argv)

    if a.selftest:
        _selftest()
        return 0
    if not a.pcap:
        ap.error("lipseste fisierul de captura (sau foloseste --selftest)")

    try:
        opt = Optiuni(
            filtru_port=_parse_porturi(a.filtru_port),
            exclude_port=_parse_porturi(a.exclude_port),
            filtru_gazda=_parse_gazde(a.filtru_gazda),
            exclude_gazda=_parse_gazde(a.exclude_gazda),
            port_date=_parse_porturi(a.port_date),
            port_discovery=_parse_porturi(a.port_discovery),
            port_zenoh=_parse_porturi(a.port_zenoh),
            domenii=(_parse_porturi(a.domeniu) or None),
            numar_esantioane=a.numar_esantioane,
            esantion_octeti=a.esantion_octeti,
            mtu=a.mtu, mss=a.mss, buget_mib=a.buget_mib,
            batch_zenoh=a.batch_zenoh, eticheta=a.eticheta)
    except ValueError as ex:
        print("count_wire_units: argument invalid: %s" % ex, file=sys.stderr)
        return 2

    try:
        rez = analizeaza(a.pcap, opt)
    except EroarePcap as ex:
        print("count_wire_units: captura nevalida (%s): %s" % (a.pcap, ex),
              file=sys.stderr)
        return 2
    except (IOError, OSError) as ex:
        print("count_wire_units: nu pot citi %s: %s" % (a.pcap, ex),
              file=sys.stderr)
        return 2

    rez["_eo"] = a.esantion_octeti
    if not a.liniste:
        print(formateaza_tabel(rez))
    if a.json:
        rez.pop("_eo", None)
        text = json.dumps(rez, indent=2, sort_keys=False)
        if a.json == "-":
            print(text)
        else:
            with open(a.json, "w") as f:
                f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
