#!/usr/bin/env python3
"""sonda_canal.py -- sonda de CANAL: masoara (L,B) INJECTATE, nu (L,B) vazute prin transport.

PROBLEMA PE CARE O REPARA
Pana la etapa 3.5, estimatorul gateway-ului era hranit de ecourile care se intorceau PRIN
transport. Numai ca tabela de politica e indexata pe (L,B) pe care netem le INJECTEAZA in
canal, si cele doua marimi nu sunt aceeasi marime. Cu QoS RELIABLE, middleware-ul o
transforma: CycloneDDS retransmite si recupereaza o parte din pierderi, Zenoh le amplifica
(documentat in c2_analysis/probe_udp.py, motivul pentru care exista sonda UDP din C2 --
si masurat acolo: tabelul app-level e REZULTAT, nu calibrare).

Consecinta era un bias SISTEMATIC si, mai rau, cu semn dependent de transportul activ: pe
cyclonedds canalul parea mai bun decat e, pe zenoh mai rau. Adica exact estimarea care
alege transportul depindea de transportul deja ales. Cautare in tabela cu o cheie
contaminata de raspuns.

CE FACE IN SCHIMB
UDP brut, best-effort, in afara ROS, exact tiparul sondei validate in C2 (C2_PROBE_20260719):
un pachet = magic + seq, o singura directie. Nicio retransmisie, niciun middleware, nimic
intre netem si contorul de secvente. Ce vede sonda E ce a injectat netem.

DE CE ONE-WAY SI NU DUS-INTORS
Dus-intors ar fi fost mai simplu de implementat (un singur proces stie tot), dar ar fi
masurat 1-(1-L)^2 in loc de L, si ar fi amestecat rafalele celor doua sensuri. Ar fi cerut
apoi o inversare cu ipoteza de simetrie si independenta -- adica exact genul de ipoteza
nemasurata pe care corectia asta o elimina. Asa ca pierderea se numara ACOLO UNDE SE VEDE,
la receptor, iar receptorul trimite inapoi estimarea gata facuta, intr-un raport mic si rar.
Daca un raport se pierde, gateway-ul pastreaza ultima valoare si stie de cand o are
(campul 'varsta'); nu inventeaza nimic.

DE CE 20 Hz (derivare, nu preferinta)
Rata sondei fixeaza dwell-time-ul, fiindca acum ea si numai ea hraneste estimatorul:
    dwell = ASEZARE_ESANTIOANE / rata = 171 / rata     (171 = mediana masurata la etapa 3)
Doua margini o incadreaza:
  - JOS: dwell-ul e timpul cat gateway-ul e legat la maini dupa o comutare. La 10 Hz ar fi
    17.1 s -- pe un link degradat, o jumatate de minut de orbire dupa fiecare decizie.
  - SUS: sonda costa pachete, iar pe o retea degradata pachetele sunt resursa rara (vezi
    core/overhead.py). La 50 Hz sonda ar adauga ~15% la numarul de pachete al fluxului de
    4 KB, adica ar degrada chiar canalul pe care pretinde ca il masoara.
La 20 Hz: dwell = 8.55 s si overhead 6.8% in pachete / 0.22% in octeti la 4 KB (calculat
in core/overhead.py, nu estimat din ochi). Rata e ALEASA, dar consecintele ei sunt masurate,
si oricare alta rata se recalculeaza cu aceleasi doua formule.

Roluri:
  --rol reflector   ruleaza pe masina cealalta: numara golurile si trimite inapoi raportul
  --rol emitator    trimite sonde si tipareste rapoartele (pentru probe manuale)
Gateway-ul nu porneste un proces separat: foloseste ClientSondaCanal din acest modul.
"""
import argparse
import os
import select
import socket
import struct
import sys
import time

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
for _p in (os.path.join(PACHET, "core"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from estimator import EstimatorLink                             # noqa: E402
from switching import HZ_SONDA_CANAL                            # noqa: E402

MAGIC_SONDA = b"C3PR"
MAGIC_RAPORT = b"C3RP"
SONDA = struct.Struct(">4sQ")                    # magic + seq = 12 octeti (ca in C2)
RAPORT = struct.Struct(">4sddQQB")               # magic+L+B+n+goluri+stabil = 37 octeti
PORT_IMPLICIT = 47311
HZ_RAPORT = 2.0


def acum():
    return time.clock_gettime(time.CLOCK_MONOTONIC)


class Raport(object):
    """Ce a vazut receptorul. Poarta si varsta, fiindca un raport vechi nu e o masuratoare
    proaspata si nimeni nu are voie sa il confunde cu una."""

    __slots__ = ("L", "B", "n", "goluri", "stabil", "t_primit")

    def __init__(self, L, B, n, goluri, stabil, t_primit):
        self.L, self.B, self.n = L, B, n
        self.goluri, self.stabil, self.t_primit = goluri, stabil, t_primit

    def varsta(self, t=None):
        return (acum() if t is None else t) - self.t_primit

    def __repr__(self):
        return ("Raport(L=%.4f, B=%.2f, n=%d, goluri=%d, stabil=%s, varsta=%.1f s)"
                % (self.L, self.B, self.n, self.goluri, self.stabil, self.varsta()))


# --------------------------------------------------------------------------- reflector
class Reflector(object):
    """Ruleaza pe masina de la celalalt capat. Primeste sonde, numara golurile din seq,
    trimite inapoi estimarea. NU raspunde la fiecare sonda: ar dubla traficul degeaba."""

    def __init__(self, port=PORT_IMPLICIT, hz_raport=HZ_RAPORT, pierdere=None, seed=1):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(("0.0.0.0", port))
        # NEBLOCANT, si asta nu e un detaliu. Cu settimeout(0.2), bucla de drenare de mai
        # jos nu se mai termina devreme: sonda trimite la 20 Hz, deci un pachet apare
        # intotdeauna inainte sa expire cele 0.2 s, iar cele 256 de iteratii se consuma
        # pana la capat -- 12.8 s in care nu se trimite niciun raport. Masurat exact asa in
        # testul de integrare: rapoarte la t=12.87, 25.67, 38.47, cu n = 256, 512, 768.
        # Un socket neblocant transforma bucla in ceea ce trebuia sa fie: 'ia ce e acum'.
        self.s.setblocking(False)
        self.est = EstimatorLink()
        self.hz_raport = float(hz_raport)
        self.t_ultim_raport = 0.0
        self.n_primite = 0
        self.sursa = None          # ultima adresa cunoscuta; un pas fara pachete nu o uita
        self.canal = None
        if pierdere is not None:
            # Pierdere SINTETICA, aplicata la RECEPTIE -- unde apare si cea a lui netem.
            # Exista doar pentru testul offline (o singura masina, fara tc): in HIL nu se
            # foloseste, acolo netem e cel care arunca pachetele.
            sys.path.insert(0, os.path.join(PACHET, "core"))
            from canal_ge import CanalGE
            self.canal = CanalGE.from_LB_pct(pierdere[0], pierdere[1], seed=seed)

    def pas(self):
        """Un pas de bucla: consuma ce e ACUM in socket, trimite raportul daca i-a venit
        randul. Nu blocheaza niciodata; asteptarea o face apelantul, cu select."""
        for _ in range(256):
            try:
                date, adresa = self.s.recvfrom(2048)
            except (BlockingIOError, socket.timeout):
                break
            except OSError:
                break
            if len(date) < SONDA.size:
                continue
            magic, seq = SONDA.unpack_from(date, 0)
            if magic != MAGIC_SONDA:
                continue
            self.sursa = adresa
            if self.canal is not None and not self.canal.esantion():
                continue                       # 'pierdut pe drum' -- gaura in sirul de seq
            self.n_primite += 1
            self.est.observa(seq)
        t = acum()
        if self.sursa is not None and t - self.t_ultim_raport >= 1.0 / self.hz_raport:
            self.t_ultim_raport = t
            e = self.est.estimare()
            try:
                self.s.sendto(RAPORT.pack(MAGIC_RAPORT, e.L, e.B, e.n_samples, e.n_goluri,
                                          1 if e.stable else 0), self.sursa)
            except OSError:
                pass
        return self.sursa

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------- emitator
class ClientSondaCanal(object):
    """Capatul din gateway. NU are fir de executie propriu si nu blocheaza niciodata:
    gateway-ul il bate din timerele lui ROS (trimite() la rata sondei, citeste() des).
    Un fir separat ar fi insemnat un lock peste estimare, adica o sursa de jitter chiar in
    calea deciziei."""

    def __init__(self, gazda, port=PORT_IMPLICIT, payload=0):
        self.adresa = (gazda, int(port))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setblocking(False)
        self.seq = 0
        self.n_trimise = 0
        self.n_rapoarte = 0
        self.umplutura = b"x" * max(0, int(payload))
        self.ultim = None

    def octeti_sonda(self):
        return SONDA.size + len(self.umplutura)

    def trimite(self):
        self.seq += 1
        pachet = SONDA.pack(MAGIC_SONDA, self.seq) + self.umplutura
        try:
            self.s.sendto(pachet, self.adresa)
            self.n_trimise += 1
        except OSError:
            pass                                # link cazut: e chiar informatia cautata
        return self.seq

    def citeste(self):
        """Consuma rapoartele sosite. Intoarce numarul de rapoarte noi."""
        noi = 0
        for _ in range(16):
            try:
                date, _adresa = self.s.recvfrom(256)
            except (BlockingIOError, socket.timeout):
                break
            except OSError:
                break
            if len(date) < RAPORT.size:
                continue
            magic, L, B, n, goluri, stabil = RAPORT.unpack_from(date, 0)
            if magic != MAGIC_RAPORT:
                continue
            self.ultim = Raport(L, B, n, goluri, bool(stabil), acum())
            self.n_rapoarte += 1
            noi += 1
        return noi

    def estimare(self, varsta_maxima=None):
        """Ultimul raport, ca obiect Estimare (ce asteapta nucleul). None daca nu a venit
        inca niciunul sau daca cel avut e mai vechi decat varsta_maxima."""
        from estimator import Estimare
        if self.ultim is None:
            return None
        if varsta_maxima is not None and self.ultim.varsta() > varsta_maxima:
            return None
        r = self.ultim
        # sigma_L nu vine prin fir: se recalculeaza local din aceleasi formule ca in
        # estimator.py, pe (L,B) raportate. E o functie deterministica de (L,B,alpha),
        # deci nu e nevoie sa fie transmisa -- si asa nu poate ajunge desincronizata.
        return Estimare(r.L, r.B, _sigma_L(r.L, r.B), r.n, r.goluri, r.stabil)

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


def _sigma_L(L, B):
    """Aceeasi formula ca EstimatorLink.sigma_L, aplicata pe (L,B) raportate."""
    import math

    from estimator import ALPHA_L
    if L <= 0.0 or L >= 1.0 or B <= 0.0:
        return 0.0
    r = 1.0 / B
    p = L * r / (1.0 - L) if L < 1.0 else 1.0
    rho = max(0.0, min(0.999, 1.0 - p - r))
    var = L * (1.0 - L) * (ALPHA_L / (2.0 - ALPHA_L)) * ((1.0 + rho) / (1.0 - rho))
    return math.sqrt(max(0.0, var))


# ---------------------------------------------------------------------------- selftest
def _selftest():
    # 1. formatele sunt exact cele promise in docstring
    assert SONDA.size == 12, SONDA.size
    assert RAPORT.size == 37, RAPORT.size

    # 2. dus-intors pe loopback, FARA pierdere: reflectorul trebuie sa raporteze L=0
    refl = Reflector(port=0, hz_raport=50.0)
    port = refl.s.getsockname()[1]
    cli = ClientSondaCanal("127.0.0.1", port)
    try:
        for _ in range(120):
            cli.trimite()
        time.sleep(0.05)
        refl.pas()
        time.sleep(0.05)
        cli.citeste()
        assert cli.ultim is not None, "niciun raport primit pe loopback curat"
        assert cli.ultim.L < 1e-6, cli.ultim
        assert cli.ultim.n >= 100, cli.ultim
    finally:
        cli.close()
        refl.close()

    # 3. CU pierdere injectata: sonda trebuie sa o VADA. Asta e proprietatea care conteaza
    # -- o sonda care nu vede pierderea injectata nu masoara nimic. 30% e departe de zero
    # cu orice toleranta rezonabila, deci testul nu e sensibil la seed.
    refl2 = Reflector(port=0, hz_raport=50.0, pierdere=(30, 1), seed=4)
    port2 = refl2.s.getsockname()[1]
    cli2 = ClientSondaCanal("127.0.0.1", port2)
    try:
        for k in range(3000):
            cli2.trimite()
            if k % 500 == 0:
                refl2.pas()
                time.sleep(0.01)
        time.sleep(0.05)
        refl2.pas()
        time.sleep(0.05)
        cli2.citeste()
        assert cli2.ultim is not None, "niciun raport la rularea cu pierdere"
        L = cli2.ultim.L
        assert 0.15 < L < 0.45, ("sonda nu vede pierderea injectata de 30%%: L=%.3f" % L)
    finally:
        cli2.close()
        refl2.close()

    # 4. varsta unui raport creste, si estimare(varsta_maxima) refuza sa serveasca unul
    # invechit. Fara asta, un link cazut ar arata sanatos la nesfarsit: ultimul raport bun
    # ar ramane in memorie si nimeni nu ar observa ca nu mai vine nimic.
    cli3 = ClientSondaCanal("127.0.0.1", 1)
    cli3.ultim = Raport(0.1, 2.0, 500, 20, True, acum() - 30.0)
    assert cli3.estimare() is not None
    assert cli3.estimare(varsta_maxima=5.0) is None, "raport de 30 s a trecut de filtru"
    assert cli3.estimare(varsta_maxima=60.0) is not None
    cli3.close()

    # 5. CADENTA RAPOARTELOR sub trafic continuu. Testul asta exista fiindca varianta
    # anterioara pica exact aici: cu socket blocant si 0.2 s de timeout, bucla de drenare
    # nu se termina cat timp sonda tot trimite, si rapoartele ieseau la 12.8 s in loc de
    # 0.5 s. Nu se poate prinde cu pachete deja in buffer -- trebuie trafic care PICURA,
    # ca in realitate. 1.2 s la 20 Hz trebuie sa dea cel putin 2 rapoarte la 2 Hz.
    refl3 = Reflector(port=0, hz_raport=2.0)
    port3 = refl3.s.getsockname()[1]
    cli4 = ClientSondaCanal("127.0.0.1", port3)
    try:
        t_final = acum() + 1.2
        urmator = acum()
        while acum() < t_final:
            if acum() >= urmator:
                cli4.trimite()
                urmator += 0.05                       # 20 Hz
            refl3.pas()
            cli4.citeste()
            time.sleep(0.002)
        assert cli4.n_rapoarte >= 2, (
            "reflectorul a trimis %d rapoarte in 1.2 s la 2 Hz -- bucla de drenare "
            "blocheaza din nou" % cli4.n_rapoarte)
        assert refl3.n_primite >= 15, refl3.n_primite
    finally:
        cli4.close()
        refl3.close()

    # 6. rata implicita e cea din care s-a derivat dwell-ul; daca cineva o schimba intr-un
    # loc si uita in celalalt, dwell-ul ar deveni o cifra fara acoperire
    assert HZ_SONDA_CANAL == 20.0, HZ_SONDA_CANAL

    print("SELFTEST sonda_canal OK (formate, loopback curat, pierdere vazuta, varsta).")


# -------------------------------------------------------------------------------- main
def main(argv):
    ap = argparse.ArgumentParser(description="Sonda de canal C3 (vezi docstringul).")
    ap.add_argument("--rol", choices=("emitator", "reflector"), default=None)
    ap.add_argument("--catre", default="127.0.0.1", help="gazda reflectorului (emitator)")
    ap.add_argument("--port", type=int, default=PORT_IMPLICIT)
    ap.add_argument("--hz", type=float, default=HZ_SONDA_CANAL)
    ap.add_argument("--hz-raport", type=float, default=HZ_RAPORT)
    ap.add_argument("--durata", type=float, default=0.0, help="0 = pana la Ctrl-C")
    ap.add_argument("--pierdere", default=None,
                    help="'L_pct,B' -- pierdere sintetica la receptie (DOAR test offline)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return 0
    if a.rol is None:
        print(__doc__.strip())
        return 0

    t0 = acum()
    if a.rol == "reflector":
        pierdere = None
        if a.pierdere:
            L, _, B = a.pierdere.partition(",")
            pierdere = (float(L), float(B))
        r = Reflector(a.port, a.hz_raport, pierdere, a.seed)
        print("sonda_canal: reflector pe portul %d%s"
              % (a.port, " (pierdere sintetica %s)" % a.pierdere if pierdere else ""),
              flush=True)
        try:
            while a.durata <= 0 or acum() - t0 < a.durata:
                select.select([r.s], [], [], 0.05)
                r.pas()
        except KeyboardInterrupt:
            pass
        finally:
            e = r.est.estimare()
            print("reflector: primite=%d L=%.4f B=%.2f goluri=%d stabil=%s"
                  % (r.n_primite, e.L, e.B, e.n_goluri, e.stable), flush=True)
            r.close()
        return 0

    c = ClientSondaCanal(a.catre, a.port)
    print("sonda_canal: emitator -> %s:%d la %.1f Hz" % (a.catre, a.port, a.hz), flush=True)
    perioada = 1.0 / a.hz
    urmator = acum()
    try:
        while a.durata <= 0 or acum() - t0 < a.durata:
            t = acum()
            if t >= urmator:
                c.trimite()
                urmator += perioada
            if c.citeste():
                print("  %s" % c.ultim, flush=True)
            time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        print("emitator: trimise=%d rapoarte=%d ultim=%s"
              % (c.n_trimise, c.n_rapoarte, c.ultim), flush=True)
        c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
