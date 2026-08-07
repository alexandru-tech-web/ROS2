#!/usr/bin/env python3
"""channel.py -- interfata canalului local intre gateway si agentii de transport.

DE CE EXISTA STRATUL ASTA
Gateway-ul decide ce transport foloseste (core/switching.py); agentii de transport sunt
procese separate, fiecare cu RMW-ul lui (izolarea e dovedita in FAPTE_C3.md). Intre ele
trebuie sa treaca octeti, local, cu latenta neglijabila fata de fenomenele de retea pe care
le masuram. Stratul asta e conducta -- si trebuie sa fie IDENTICA spre fiecare agent,
altfel diferenta dintre transporturi s-ar amesteca cu diferenta dintre conducte.

CONTRACT (respectat identic de toate implementarile):
    send(payload: bytes, seq: int)      pune un mesaj in conducta
    recv(timeout: float) -> Mesaj|None  ia urmatorul mesaj, None la expirare
    close()                             elibereaza resursele, idempotent
    stare() -> Stare                    ciclul de viata OBSERVABIL (pereche vie/moarta)

Mesajul poarta si momentul trimiterii (CLOCK_MONOTONIC, comparabil intre procese pe
Linux), ca latenta de handoff sa fie masurabila prin constructie, nu prin instrumentare
adaugata pe deasupra.

NUCLEUL DE DECIZIE NU STIE CE IMPLEMENTARE E ACTIVA: primeste un obiect Canal si atat.
Alegerea se face intr-un singur loc, creeaza_canal(), pe baza unui sir.
"""
import struct
import sys
import time

# antetul, identic in ambele implementari: seq (uint64) + moment trimitere (double)
ANTET = struct.Struct("<Qd")
MAX_PAYLOAD_IMPLICIT = 65536


def acum():
    """Ceas MONOTON, comparabil intre procese pe Linux (epoca = pornirea sistemului).
    NU time.perf_counter(): acela are epoca arbitrara per proces, deci diferenta dintre
    doua procese ar fi lipsita de sens -- exact greseala care ar face latenta masurata
    sa arate frumos si sa fie falsa."""
    return time.clock_gettime(time.CLOCK_MONOTONIC)


class Mesaj(object):
    __slots__ = ("payload", "seq", "t_send")

    def __init__(self, payload, seq, t_send):
        self.payload = payload
        self.seq = seq
        self.t_send = t_send

    def latenta(self, t_recv=None):
        """Timpul de handoff: de la punerea in conducta la scoaterea din ea."""
        return (acum() if t_recv is None else t_recv) - self.t_send

    def __repr__(self):
        return "Mesaj(seq=%d, %d octeti)" % (self.seq, len(self.payload))


class Stare(object):
    """Ciclul de viata, observabil din afara. 'viu' inseamna: perechea e acolo si conducta
    e utilizabila. 'motiv' spune de ce nu, cand nu."""

    __slots__ = ("viu", "motiv", "t_ultima_activitate", "n_trimise", "n_primite")

    def __init__(self, viu, motiv, t_ultima_activitate, n_trimise, n_primite):
        self.viu = viu
        self.motiv = motiv
        self.t_ultima_activitate = t_ultima_activitate
        self.n_trimise = n_trimise
        self.n_primite = n_primite

    def __repr__(self):
        return ("Stare(viu=%s, motiv=%r, trimise=%d, primite=%d)"
                % (self.viu, self.motiv, self.n_trimise, self.n_primite))


class CanalInchis(Exception):
    """Ridicata la send() pe un canal a carui pereche a murit sau care a fost inchis."""


class Canal(object):
    """Interfata. Implementarile mostenesc si completeaza _send/_recv/_close.
    Contabilitatea (numaratoare, ultima activitate) sta AICI, o singura data, ca cele doua
    implementari sa nu poata diverge in felul in care raporteaza starea."""

    def __init__(self, nume, rol, max_payload=MAX_PAYLOAD_IMPLICIT):
        if rol not in ("gazda", "oaspete"):
            raise ValueError("rol necunoscut: %r (gazda|oaspete)" % (rol,))
        self.nume = nume
        self.rol = rol
        self.max_payload = int(max_payload)
        self._viu = True
        self._motiv = ""
        self._t_activitate = acum()
        self._n_trimise = 0
        self._n_primite = 0
        self._inchis = False

    # ------------------------------------------------------------------ de completat
    def conecteaza(self, timeout=5.0):
        raise NotImplementedError

    def _send(self, cadru):
        raise NotImplementedError

    def _recv(self, timeout):
        raise NotImplementedError

    def _close(self):
        raise NotImplementedError

    # ------------------------------------------------------------------- interfata
    def send(self, payload, seq):
        if self._inchis:
            raise CanalInchis("canal inchis")
        if not self._viu:
            raise CanalInchis("perechea a murit: %s" % self._motiv)
        if len(payload) > self.max_payload:
            raise ValueError("payload %d > max %d" % (len(payload), self.max_payload))
        self._send(ANTET.pack(int(seq), acum()) + payload)
        self._n_trimise += 1
        self._t_activitate = acum()

    def recv(self, timeout=0.1):
        if self._inchis:
            return None
        cadru = self._recv(timeout)
        if cadru is None:
            return None
        seq, t_send = ANTET.unpack_from(cadru, 0)
        self._n_primite += 1
        self._t_activitate = acum()
        return Mesaj(bytes(cadru[ANTET.size:]), seq, t_send)

    def close(self):
        if self._inchis:
            return
        self._inchis = True
        self._close()

    def stare(self):
        return Stare(self._viu and not self._inchis, self._motiv, self._t_activitate,
                     self._n_trimise, self._n_primite)

    def _marcheaza_mort(self, motiv):
        if self._viu:
            self._viu = False
            self._motiv = motiv

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def creeaza_canal(tip, nume, rol, max_payload=MAX_PAYLOAD_IMPLICIT, **kw):
    """SINGURUL loc unde se alege implementarea. Restul sistemului vede doar Canal.
    Importurile sunt lenese ca sa nu tragem shm cand folosim uds si invers."""
    if tip == "uds":
        from uds import CanalUDS
        return CanalUDS(nume, rol, max_payload, **kw)
    if tip == "shm":
        from shm import CanalSHM
        return CanalSHM(nume, rol, max_payload, **kw)
    raise ValueError("tip de canal necunoscut: %r (uds|shm)" % (tip,))


TIPURI = ("uds", "shm")


# ------------------------------------------------------------------- conformitate
def verifica_conformitate(tip, eticheta=None):
    """ACELASI test pentru orice implementare. Daca uds si shm trec amandoua asta, atunci
    codul care le foloseste chiar nu poate distinge intre ele -- ceea ce e tot rostul.
    Ruleaza doua procese reale (fork), nu doua fire: un canal IPC testat in acelasi proces
    nu dovedeste nimic despre IPC."""
    import multiprocessing as mp
    import os

    eticheta = eticheta or "c3test_%s_%d" % (tip, os.getpid())
    rezultate = mp.Queue()

    SANTINELA = 999999          # mesajul care ii spune oaspetelui sa iasa

    def oaspete():
        # Oaspetele NU iese dupa un numar fix de ecouri: ramane viu pana i se cere, ca
        # gazda sa poata testa si expirarea lui recv pe canal gol CU perechea inca vie.
        # (Prima varianta iesea dupa 3 ecouri, si testul de timeout masura de fapt EOF-ul.)
        c = creeaza_canal(tip, eticheta, "oaspete")
        try:
            c.conecteaza(timeout=5.0)
            ecou = 0
            t0 = acum()
            while acum() - t0 < 15.0:
                m = c.recv(timeout=0.2)
                if m is None:
                    continue
                if m.seq == SANTINELA:
                    break
                c.send(m.payload, m.seq + 1000)
                ecou += 1
            rezultate.put(("oaspete_ecouri", ecou))
        finally:
            c.close()

    gazda = creeaza_canal(tip, eticheta, "gazda")
    proc = mp.Process(target=oaspete)
    proc.start()
    try:
        gazda.conecteaza(timeout=5.0)
        assert gazda.stare().viu is True, gazda.stare()

        # 1. mesajele ajung INTREGI si in ordine, cu seq si timp corecte
        primite = []
        for i in range(3):
            gazda.send(b"x" * (100 + i), 42 + i)
        t0 = acum()
        while len(primite) < 3 and acum() - t0 < 5.0:
            m = gazda.recv(timeout=0.5)
            if m is not None:
                primite.append(m)
        assert len(primite) == 3, "am primit %d din 3 ecouri" % len(primite)
        for i, m in enumerate(primite):
            assert m.seq == 42 + i + 1000, (i, m.seq)
            assert m.payload == b"x" * (100 + i), (i, len(m.payload))
            assert 0 <= m.latenta() < 5.0, m.latenta()

        # 2. contabilitatea starii e tinuta de clasa de baza, deci identica peste tot
        s = gazda.stare()
        assert s.n_trimise == 3 and s.n_primite == 3, s

        # 3. recv pe gol EXPIRA, nu blocheaza la nesfarsit si nu arunca
        t0 = acum()
        assert gazda.recv(timeout=0.2) is None
        dt = acum() - t0
        assert 0.1 < dt < 1.0, "timeout-ul nu e respectat: %.3f s" % dt

        # 3b. SONDARE fara asteptare (timeout=0): intoarce None si NU declara perechea
        # moarta. Pe socket, timeout=0 inseamna mod neblocant, iar exceptia de acolo e
        # subclasa de OSError -- exact tiparul care, prins gresit, omoara canalul la o
        # simpla sondare (a si facut-o, in prima varianta).
        assert gazda.recv(timeout=0.0) is None
        assert gazda.stare().viu is True, ("sondarea fara asteptare a omorat canalul",
                                           gazda.stare())
        # ... si canalul ramane UTILIZABIL dupa sondare: pe socket, timeout-ul e stare
        # lipicioasa, deci un send de dupa o sondare neblocanta pica daca nu e resetat
        gazda.send(b"dupa-sondare", 7)
        t0 = acum()
        ecou = None
        while ecou is None and acum() - t0 < 5.0:
            ecou = gazda.recv(timeout=0.5)
        assert ecou is not None and ecou.seq == 7 + 1000, ecou

        # 4. payload peste limita e REFUZAT explicit
        try:
            gazda.send(b"y" * (gazda.max_payload + 1), 1)
            raise AssertionError("payload supradimensionat acceptat")
        except ValueError:
            pass

        # 4b. SARCINA SUSTINUTA. Trei mesaje nu prind nimic: bug-ul care a costat cel mai
        # mult in etapa asta (o citire rupta a campului de bataie din memoria partajata,
        # interpretata drept 'pereche moarta') aparea abia dupa cateva sute de mesaje.
        # Deci canalul trebuie sa reziste la trafic continuu, nu doar la un salut.
        n_dus = 300
        primite_sustinut = 0
        for i in range(n_dus):
            gazda.send(b"s" * 512, 10000 + i)
            m = gazda.recv(timeout=1.0)
            if m is not None:
                primite_sustinut += 1
            assert gazda.stare().viu, ("canalul a murit sub sarcina, la mesajul %d: %s"
                                       % (i, gazda.stare().motiv))
        assert primite_sustinut >= n_dus * 0.99, (primite_sustinut, n_dus)

        # 5. abia ACUM ii cerem oaspetelui sa iasa: pana aici a fost viu si tacut, ceea ce
        # face verificarile 3 si 4 sa masoare ce trebuie
        gazda.send(b"", SANTINELA)
        proc.join(timeout=5.0)
        # PEREHEA MOARTA e detectata, si starea o spune
        t0 = acum()
        detectat = False
        while acum() - t0 < 3.0:
            gazda.recv(timeout=0.1)
            if not gazda.stare().viu:
                detectat = True
                break
        assert detectat, "moartea perechii NU a fost detectata in 3 s"
        assert gazda.stare().motiv, "moartea detectata dar fara motiv raportat"

        # 6. send dupa moarte ridica CanalInchis, nu esueaza tacut
        try:
            gazda.send(b"z", 1)
            raise AssertionError("send pe canal mort a reusit")
        except CanalInchis:
            pass

        # 7. close e idempotent
        gazda.close()
        gazda.close()
        assert gazda.stare().viu is False
    finally:
        gazda.close()
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=2.0)
    return True


def _selftest():
    for tip in TIPURI:
        verifica_conformitate(tip)
        print("  conformitate OK: %s" % tip)
    print("SELFTEST channel OK (aceeasi baterie trecuta de ambele implementari).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # Rulat direct, fisierul asta e modulul '__main__', dar uds.py/shm.py importa
    # 'channel' -- adica un AL DOILEA obiect-modul, cu ALTE clase. Un 'except CanalInchis'
    # scris aici nu ar prinde exceptia ridicata acolo, desi arata identic. De aceea ne
    # importam pe noi insine sub numele adevarat si rulam din acel exemplar.
    import channel as _acelasi_modul
    sys.exit(_acelasi_modul.main(sys.argv[1:]))
