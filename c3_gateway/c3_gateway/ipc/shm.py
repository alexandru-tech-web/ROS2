#!/usr/bin/env python3
"""shm.py -- canal peste memorie partajata POSIX (ring buffer) + semafoare POSIX numite.

STRUCTURA
Doua inele separate, cate unul per sens (gazda->oaspete si oaspete->gazda). Fiecare inel
are un singur producator si un singur consumator (SPSC), deci indicii de scriere si de
citire sunt fiecare scrisi de un singur proces; ordonarea o dau semafoarele, nu norocul.
    sem_liber[X]  cate sloturi libere are inelul X   (initial n_sloturi)
    sem_plin[X]   cate mesaje asteapta in inelul X   (initial 0)
    producator: wait(liber) -> scrie slot -> post(plin)
    consumator: wait(plin)  -> citeste slot -> post(liber)

SEMAFOARELE sunt cele POSIX din libc (sem_open/sem_timedwait/sem_post), chemate prin ctypes.
Nu e o dependinta exotica -- e API-ul standard al sistemului; alternativa (posix_ipc) ar fi
fost un pachet in plus pentru exact aceleasi apeluri.

MOARTEA PERECHII -- aici NU e gratuita, spre deosebire de uds.py
Memoria partajata nu are notiunea de 'celalalt capat s-a inchis': un proces care moare lasa
inelul exact cum era. Detectia se face pe doua cai, ambele explicite:
  1. PID-ul perechii nu mai exista (os.kill(pid, 0)) -- prinde procesul mort, imediat;
  2. batalia de inima s-a oprit de mai mult de TIMEOUT_BATAIE secunde -- prinde procesul
     viu dar blocat.
Bataia se actualizeaza la ORICE operatie pe canal. Un proces care nu face nimic minute in
sir trebuie sa cheme bate() explicit, altfel arata mort; e un compromis constient, iar
cifra de detectie masurata in bench_ipc.py e cu mecanismul asta, nu cu unul ideal.
"""
import ctypes
import ctypes.util
import errno
import os
import struct
import sys
import time
from multiprocessing import resource_tracker, shared_memory

AICI = os.path.dirname(os.path.abspath(__file__))
if AICI not in sys.path:
    sys.path.insert(0, AICI)

from channel import ANTET, Canal, CanalInchis, MAX_PAYLOAD_IMPLICIT, acum  # noqa: E402

MAGIC = b"C3SH"
VERSIUNE = 1
N_SLOTURI_IMPLICIT = 64
TIMEOUT_BATAIE = 0.5            # secunde fara semn de viata = pereche considerata moarta

# antetul global: magic, versiune, n_sloturi, marime_slot, idx_w[2], idx_r[2],
# pid[2], bataie[2], gata
CAP = struct.Struct("<4sIII QQ QQ qq dd I")
OFS_IDX_W = 16                  # dupa magic+versiune+n_sloturi+marime_slot
OFS_IDX_R = OFS_IDX_W + 16
OFS_PID = OFS_IDX_R + 16
OFS_BATAIE = OFS_PID + 16
OFS_GATA = OFS_BATAIE + 16
MARIME_CAP = OFS_GATA + 4

_libc = ctypes.CDLL(ctypes.util.find_library("pthread") or "libc.so.6", use_errno=True)
_libc.sem_open.restype = ctypes.c_void_p
_libc.sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
_libc.sem_post.argtypes = [ctypes.c_void_p]
_libc.sem_wait.argtypes = [ctypes.c_void_p]
_libc.sem_close.argtypes = [ctypes.c_void_p]
_libc.sem_unlink.argtypes = [ctypes.c_char_p]
SEM_FAILED = ctypes.c_void_p(-1).value
O_CREAT, O_EXCL = 0o100, 0o200


class _Timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]


_libc.sem_timedwait.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Timespec)]


class Semafor(object):
    """Semafor POSIX numit. Numele incep cu '/' si traiesc in /dev/shm/sem.*"""

    def __init__(self, nume, creeaza=False, valoare=0):
        self.nume = nume.encode() if isinstance(nume, str) else nume
        steaguri = (O_CREAT | O_EXCL) if creeaza else 0
        h = _libc.sem_open(self.nume, steaguri, 0o600, valoare)
        if h == SEM_FAILED or h is None:
            e = ctypes.get_errno()
            raise OSError(e, "sem_open(%s) a esuat: %s" % (self.nume, os.strerror(e)))
        self._h = ctypes.c_void_p(h)
        self._creator = creeaza

    def post(self):
        if _libc.sem_post(self._h) != 0:
            raise OSError(ctypes.get_errno(), "sem_post")

    def wait(self, timeout=None):
        """True daca a obtinut semaforul, False la expirare."""
        if timeout is None:
            return _libc.sem_wait(self._h) == 0
        # sem_timedwait cere un moment ABSOLUT pe CLOCK_REALTIME
        tinta = time.clock_gettime(time.CLOCK_REALTIME) + max(0.0, timeout)
        ts = _Timespec(int(tinta), int((tinta - int(tinta)) * 1e9))
        while True:
            if _libc.sem_timedwait(self._h, ctypes.byref(ts)) == 0:
                return True
            e = ctypes.get_errno()
            if e == errno.ETIMEDOUT:
                return False
            if e == errno.EINTR:
                continue                       # semnal: reincercam pana la termen
            raise OSError(e, "sem_timedwait: %s" % os.strerror(e))

    def close(self):
        if self._h is not None:
            _libc.sem_close(self._h)
            self._h = None

    def unlink(self):
        _libc.sem_unlink(self.nume)


def _ataseaza(nume):
    """Ataseaza un segment EXISTENT, fara ca procesul-oaspete sa pretinda ca e
    proprietarul lui. Python 3.13 are parametrul track=False exact pentru asta; pe 3.12
    (interpretorul ROS) se face dezinregistrarea manuala din resource_tracker. Fara una
    din cele doua, la iesirea oaspetelui trackerul fie se plange de memorie 'scursa', fie
    incearca sa stearga un nume pe care nu-l are (KeyError in procesul lui)."""
    try:
        return shared_memory.SharedMemory(name=nume, track=False)
    except TypeError:
        # Python <= 3.12: nu exista track=. NU dezinregistram aici: cache-ul trackerului
        # e o multime partajata cu procesul parinte, asa ca stergerea din oaspete face ca
        # unlink-ul de mai tarziu al GAZDEI sa loveasca un KeyError. Proprietarul (gazda)
        # elibereaza segmentul; oaspetele doar il atinge.
        return shared_memory.SharedMemory(name=nume)


def _pid_viu(pid):
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class CanalSHM(Canal):
    def __init__(self, nume, rol, max_payload=MAX_PAYLOAD_IMPLICIT,
                 n_sloturi=N_SLOTURI_IMPLICIT, timeout_bataie=TIMEOUT_BATAIE):
        Canal.__init__(self, nume, rol, max_payload)
        self.n_sloturi = int(n_sloturi)
        self.timeout_bataie = float(timeout_bataie)
        self.marime_slot = 4 + ANTET.size + self.max_payload
        self._eu = 0 if rol == "gazda" else 1          # indexul meu in campurile perechi
        self._el = 1 - self._eu
        # inelul in care SCRIU eu, si cel din care CITESC
        self._inel_scriu = 0 if rol == "gazda" else 1
        self._inel_citesc = 1 - self._inel_scriu
        self._shm = None
        self._sem = {}
        nume_shm = "c3shm_%s" % nume
        total = MARIME_CAP + 2 * self.n_sloturi * self.marime_slot
        if rol == "gazda":
            try:
                vechi = shared_memory.SharedMemory(name=nume_shm)
                vechi.close()
                vechi.unlink()                          # ramasita de la o rulare moarta
            except FileNotFoundError:
                pass
            self._shm = shared_memory.SharedMemory(name=nume_shm, create=True, size=total)
            CAP.pack_into(self._shm.buf, 0, MAGIC, VERSIUNE, self.n_sloturi,
                          self.marime_slot, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0)
            for i in (0, 1):
                for fel, val in (("liber", self.n_sloturi), ("plin", 0)):
                    n = "/c3_%s_%s%d" % (nume, fel, i)
                    try:
                        Semafor(n, creeaza=True, valoare=val).close()
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            raise
                        Semafor(n).unlink()
                        Semafor(n, creeaza=True, valoare=val).close()
            self._scrie_pid()
        else:
            self._shm = None                            # se ataseaza in conecteaza()
        self._nume_shm = nume_shm

    # ------------------------------------------------------------------- interne
    def _deschide_semafoare(self):
        for i in (0, 1):
            for fel in ("liber", "plin"):
                self._sem[(fel, i)] = Semafor("/c3_%s_%s%d" % (self.nume, fel, i))

    def _scrie_pid(self):
        struct.pack_into("<q", self._shm.buf, OFS_PID + 8 * self._eu, os.getpid())
        self.bate()

    def bate(self):
        """Semn de viata. Se cheama automat la orice operatie; un proces complet inactiv
        trebuie sa o cheme singur, altfel perechea il crede mort (vezi docstring)."""
        if self._shm is not None:
            struct.pack_into("<d", self._shm.buf, OFS_BATAIE + 8 * self._eu, acum())

    def _citeste(self, fmt, ofs):
        return struct.unpack_from(fmt, self._shm.buf, ofs)[0]

    def _verifica_pereche(self):
        if self._shm is None:
            return
        pid = self._citeste("<q", OFS_PID + 8 * self._el)
        if pid and not _pid_viu(pid):
            self._marcheaza_mort("pid %d disparut" % pid)
            return
        b = self._citeste("<d", OFS_BATAIE + 8 * self._el)
        if b > 0 and acum() - b > self.timeout_bataie:
            self._marcheaza_mort("fara bataie de %.2f s" % (acum() - b))

    def conecteaza(self, timeout=5.0):
        if self.rol == "oaspete":
            t0 = acum()
            while acum() - t0 < timeout:
                try:
                    self._shm = _ataseaza(self._nume_shm)
                    break
                except FileNotFoundError:
                    time.sleep(0.01)
            if self._shm is None:
                raise TimeoutError("segmentul %s nu a aparut in %.1f s"
                                   % (self._nume_shm, timeout))
            magic = self._citeste("<4s", 0)
            if magic != MAGIC:
                raise ValueError("segment strain (magic %r)" % (magic,))
            self._deschide_semafoare()
            self._scrie_pid()
            struct.pack_into("<I", self._shm.buf, OFS_GATA, 1)
            return True
        self._deschide_semafoare()
        t0 = acum()
        while acum() - t0 < timeout:
            if self._citeste("<I", OFS_GATA) == 1:
                self.bate()
                return True
            time.sleep(0.005)
        raise TimeoutError("niciun oaspete in %.1f s pe %s" % (timeout, self._nume_shm))

    def _ofs_slot(self, inel, idx):
        return (MARIME_CAP + (inel * self.n_sloturi + idx % self.n_sloturi)
                * self.marime_slot)

    def _send(self, cadru):
        if self._shm is None:
            raise CanalInchis("neconectat")
        self._verifica_pereche()
        if not self._viu:
            raise CanalInchis("perechea a murit: %s" % self._motiv)
        inel = self._inel_scriu
        if not self._sem[("liber", inel)].wait(timeout=1.0):
            raise CanalInchis("inel plin 1 s (perechea nu consuma)")
        idx = self._citeste("<Q", OFS_IDX_W + 8 * inel)
        o = self._ofs_slot(inel, idx)
        struct.pack_into("<I", self._shm.buf, o, len(cadru))
        self._shm.buf[o + 4:o + 4 + len(cadru)] = cadru
        struct.pack_into("<Q", self._shm.buf, OFS_IDX_W + 8 * inel, idx + 1)
        self.bate()
        self._sem[("plin", inel)].post()

    def _recv(self, timeout):
        if self._shm is None:
            return None
        inel = self._inel_citesc
        if not self._sem[("plin", inel)].wait(timeout=timeout):
            self._verifica_pereche()
            return None
        idx = self._citeste("<Q", OFS_IDX_R + 8 * inel)
        o = self._ofs_slot(inel, idx)
        n = self._citeste("<I", o)
        cadru = bytes(self._shm.buf[o + 4:o + 4 + n])
        struct.pack_into("<Q", self._shm.buf, OFS_IDX_R + 8 * inel, idx + 1)
        self.bate()
        self._sem[("liber", inel)].post()
        return cadru

    def stare(self):
        self._verifica_pereche()
        return Canal.stare(self)

    def _close(self):
        for s in self._sem.values():
            try:
                s.close()
            except OSError:
                pass
        self._sem = {}
        if self._shm is not None:
            try:
                self._shm.close()
            except (OSError, BufferError):
                pass
            if self.rol == "gazda":
                try:
                    self._shm.unlink()
                except FileNotFoundError:
                    pass
                for i in (0, 1):
                    for fel in ("liber", "plin"):
                        try:
                            Semafor("/c3_%s_%s%d" % (self.nume, fel, i)).unlink()
                        except OSError:
                            pass
            self._shm = None


def _selftest():
    from channel import verifica_conformitate
    verifica_conformitate("shm")
    print("SELFTEST shm OK (inel SPSC, semafoare POSIX, moarte prinsa prin pid+bataie).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
