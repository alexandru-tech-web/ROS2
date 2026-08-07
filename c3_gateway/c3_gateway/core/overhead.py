#!/usr/bin/env python3
"""overhead.py -- costul sondelor, in octeti SI IN PACHETE. NUCLEU PUR.

DE CE UN MODUL SEPARAT, SI DE CE PACHETE
La etapa 3 overhead-ul sondei a fost raportat ca '338.4 octeti/s = 0.201% din trafic'.
Cifra avea doua defecte:

  1. NUMITOR NEDECLARAT. 338.4 / 0.201% da 168 kB/s, dar fluxul de referinta (4096 B la
     50 Hz) e 204800 B/s, unde aceiasi 338.4 dau 0.165%. Diferenta venea din faptul ca
     numitorul era traficul MASURAT in jurnal (mesaje care chiar s-au intors, cu antetele
     IPC incluse), nu fluxul nominal. Nici una din cifre nu era gresita; nedeclarat era
     CARE dintre ele. Aici numitorul e intotdeauna explicit: fiecare procent vine insotit
     de numele si valoarea bazei fata de care s-a calculat.

  2. OCTETII SUNT UNITATEA GRESITA pentru intrebarea care conteaza. Pe o retea degradata,
     pierderea si timpul de antena se consuma PER PACHET, nu per octet: netem arunca
     pachete, nu kiloocteti, iar un mesaj de 4096 B nu e un pachet, ci trei. O sonda de
     12 B si un mesaj de 4096 B costa la fel de mult in numar de pachete pe cablu, desi
     raportul lor in octeti e de 1 la 341. Pentru configuratia C3 la 4 KB, cifrele
     calculate mai jos sunt 0.22% in octeti dar 6.8% in pachete -- de 30 de ori mai mult,
     si pachetele sunt cele care se pierd.

MODELUL DE FRAGMENTARE (declarat, ca sa poata fi contestat)
Se numara fragmente IP ale unei datagrame UDP: IP payload = util + 8 (antet UDP), fiecare
fragment duce cel mult MTU - 20 octeti de IP payload. E o APROXIMARE pentru caile ROS:
CycloneDDS si Zenoh isi fragmenteaza singure esantioanele mari la nivel RTPS/Zenoh, nu
lasa IP-ul s-o faca. Numarul de pachete iese insa comparabil (ambele taie la MTU), iar
pentru sonda de canal -- UDP brut, sub MTU -- modelul e exact, nu aproximativ.
"""
import sys

MTU_IMPLICIT = 1500
ANTET_IP = 20                   # IPv4 fara optiuni
ANTET_UDP = 8


def pachete_udp(octeti_util, mtu=MTU_IMPLICIT):
    """Cate pachete IP pleaca pentru o datagrama UDP cu octeti_util octeti de payload."""
    if octeti_util < 0:
        raise ValueError("payload negativ")
    util_ip = octeti_util + ANTET_UDP
    per_fragment = mtu - ANTET_IP
    return max(1, -(-util_ip // per_fragment))       # ceil


def octeti_pe_fir(octeti_util, mtu=MTU_IMPLICIT):
    """Octeti chiar pusi pe fir: payload + UDP + un antet IP per fragment."""
    return octeti_util + ANTET_UDP + ANTET_IP * pachete_udp(octeti_util, mtu)


class Flux(object):
    """Un flux unidirectional: nume, rata, payload. Obiect de date."""

    __slots__ = ("nume", "hz", "octeti", "sonda")

    def __init__(self, nume, hz, octeti, sonda=False):
        self.nume = nume
        self.hz = float(hz)
        self.octeti = int(octeti)
        self.sonda = bool(sonda)

    def pachete_s(self, mtu=MTU_IMPLICIT):
        return self.hz * pachete_udp(self.octeti, mtu)

    def octeti_s(self, mtu=MTU_IMPLICIT):
        return self.hz * octeti_pe_fir(self.octeti, mtu)


def bilant(fluxuri, mtu=MTU_IMPLICIT):
    """Overhead-ul sondelor fata de traficul total, in AMBELE unitati, cu numitorul
    declarat. Intoarce un dict; nimic nu se rotunjeste aici (rotunjirea e treaba
    raportului, nu a calculului)."""
    tot_p = sum(f.pachete_s(mtu) for f in fluxuri)
    tot_o = sum(f.octeti_s(mtu) for f in fluxuri)
    son_p = sum(f.pachete_s(mtu) for f in fluxuri if f.sonda)
    son_o = sum(f.octeti_s(mtu) for f in fluxuri if f.sonda)
    app_p, app_o = tot_p - son_p, tot_o - son_o
    return {
        "mtu": mtu,
        "numitor": "trafic total pe fir (aplicatie + sonde), ambele sensuri",
        "pachete_s_total": tot_p, "pachete_s_sonda": son_p, "pachete_s_app": app_p,
        "octeti_s_total": tot_o, "octeti_s_sonda": son_o, "octeti_s_app": app_o,
        "overhead_pachete_pct": 100.0 * son_p / tot_p if tot_p else 0.0,
        "overhead_octeti_pct": 100.0 * son_o / tot_o if tot_o else 0.0,
        "fluxuri": [(f.nume, f.hz, f.octeti, f.pachete_s(mtu), f.octeti_s(mtu), f.sonda)
                    for f in fluxuri],
    }


def _selftest():
    # 1. fragmentarea: cifrele pe care se sprijina tot raportul
    assert pachete_udp(12) == 1, pachete_udp(12)          # sonda: un pachet
    assert pachete_udp(32) == 1
    assert pachete_udp(1472) == 1                          # exact la limita MTU 1500
    assert pachete_udp(1473) == 2                          # un octet peste -> doua
    assert pachete_udp(4096) == 3, pachete_udp(4096)       # (4096+8)/1480 = 2.77 -> 3
    assert pachete_udp(65536) == 45, pachete_udp(65536)    # (65536+8)/1480 = 44.3 -> 45
    assert pachete_udp(0) == 1                             # datagrama goala e tot un pachet

    # 2. octetii pe fir includ un antet IP PER FRAGMENT, nu unul singur
    assert octeti_pe_fir(4096) == 4096 + 8 + 60, octeti_pe_fir(4096)
    assert octeti_pe_fir(12) == 40

    # 3. bilantul: exemplul care arata de ce contau pachetele. Aceleasi doua sonde,
    # acelasi flux de aplicatie: in octeti overhead-ul e sub 1%, in pachete e de ordinul
    # zecilor de ori mai mare. Daca vreodata cele doua procente ies egale, ceva e rupt.
    f = [Flux("app_tx", 50, 4096), Flux("app_rx", 50, 4096),
         Flux("sonda_canal", 20, 12, sonda=True),
         Flux("raport_sonda", 2, 40, sonda=True)]
    b = bilant(f)
    assert abs(b["pachete_s_app"] - 300.0) < 1e-9, b        # 2 x 50 x 3 fragmente
    assert abs(b["pachete_s_sonda"] - 22.0) < 1e-9, b
    assert b["overhead_pachete_pct"] > 15 * b["overhead_octeti_pct"], b
    assert 6.0 < b["overhead_pachete_pct"] < 7.0, b["overhead_pachete_pct"]
    assert 0.2 < b["overhead_octeti_pct"] < 0.3, b["overhead_octeti_pct"]

    # 4. la 64 KB raportul se INVERSEAZA ca ordin de marime: fluxul de aplicatie devine
    # 45 de pachete per mesaj, deci sonda se pierde in el. Cifra de overhead NU e una
    # singura -- depinde de payload, si de aceea se raporteaza pe fiecare.
    f64 = [Flux("app_tx", 50, 65536), Flux("app_rx", 50, 65536),
           Flux("sonda_canal", 20, 12, sonda=True),
           Flux("raport_sonda", 2, 40, sonda=True)]
    b64 = bilant(f64)
    assert b64["overhead_pachete_pct"] < b["overhead_pachete_pct"] / 10.0, (b64, b)

    # 5. MTU-ul e parametru, nu constanta ascunsa
    assert pachete_udp(4096, mtu=9000) == 1                 # jumbo frames
    assert pachete_udp(4096, mtu=576) == 8                  # MTU minim IPv4

    print("SELFTEST overhead OK (fragmentare, octeti pe fir, bilant in ambele unitati).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
