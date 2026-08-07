#!/usr/bin/env python3
"""uds.py -- canal peste socket UNIX de tip SOCK_SEQPACKET.

DE CE SEQPACKET SI NU STREAM
SOCK_STREAM ar cere framing propriu (lungime pe 4 octeti, apoi citire in bucla pana se
completeaza cadrul) -- adica exact clasa de bug-uri in care un mesaj de 65 KB soseste in
doua bucati si al doilea mesaj se lipeste de coada primului. SOCK_SEQPACKET pastreaza
GRANITELE mesajelor si ordinea, la fel ca un datagram, dar pe conexiune si cu livrare
garantata. Framing-ul e al nucleului, nu al nostru: un send = un recv.

MOARTEA PERECHII e gratuita aici: cand celalalt capat se inchide (sau moare), recv()
intoarce zero octeti (EOF), iar send() ridica BrokenPipeError/ConnectionResetError.
Detectia e imediata si vine de la nucleu, nu dintr-un heartbeat inventat de noi -- diferenta
fata de shm.py, si unul din motivele pentru care comparatia dintre cele doua nu e doar
despre latenta.
"""
import os
import socket
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
if AICI not in sys.path:
    sys.path.insert(0, AICI)

from channel import Canal, CanalInchis, MAX_PAYLOAD_IMPLICIT   # noqa: E402

DIR_SOCKET = "/tmp"


def cale_socket(nume):
    return os.path.join(DIR_SOCKET, "c3_%s.sock" % nume)


class CanalUDS(Canal):
    def __init__(self, nume, rol, max_payload=MAX_PAYLOAD_IMPLICIT):
        Canal.__init__(self, nume, rol, max_payload)
        self._cale = cale_socket(nume)
        self._ascultator = None
        self._sock = None
        if rol == "gazda":
            # legarea se face in constructor, ca oaspetele sa gaseasca socketul chiar
            # daca porneste imediat dupa; altfel ar exista o cursa la pornire
            try:
                os.unlink(self._cale)
            except OSError:
                pass
            self._ascultator = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            self._ascultator.bind(self._cale)
            self._ascultator.listen(1)

    def conecteaza(self, timeout=5.0):
        if self.rol == "gazda":
            self._ascultator.settimeout(timeout)
            try:
                self._sock, _ = self._ascultator.accept()
            except socket.timeout:
                raise TimeoutError("niciun oaspete in %.1f s pe %s" % (timeout, self._cale))
        else:
            from channel import acum
            t0 = acum()
            ultima = None
            while acum() - t0 < timeout:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
                try:
                    s.connect(self._cale)
                    self._sock = s
                    break
                except (FileNotFoundError, ConnectionRefusedError) as e:
                    ultima = e
                    s.close()
                    import time
                    time.sleep(0.01)
            if self._sock is None:
                raise TimeoutError("gazda nu a aparut in %.1f s pe %s (%s)"
                                   % (timeout, self._cale, ultima))
        # bufferele nucleului: un mesaj de 64 KB trebuie sa incapa intreg
        marime = max(self.max_payload * 4, 262144)
        for opt in (socket.SO_SNDBUF, socket.SO_RCVBUF):
            try:
                self._sock.setsockopt(socket.SOL_SOCKET, opt, marime)
            except OSError:
                pass
        return True

    def _send(self, cadru):
        if self._sock is None:
            raise CanalInchis("neconectat")
        # Timeout-ul socketului e STARE LIPICIOASA: un recv(timeout=0) anterior l-a lasat
        # neblocant, iar sendall-ul de aici ar primi EAGAIN si l-am lua drept moarte. Se
        # pune explicit, la fiecare operatie.
        self._sock.settimeout(1.0)
        try:
            self._sock.sendall(cadru)
        except (socket.timeout, BlockingIOError):
            # buffer plin: perechea nu consuma. Nu e moarte -- e contrapresiune, acelasi
            # inteles ca 'inel plin' la shm.
            raise CanalInchis("send blocat 1 s (perechea nu consuma)")
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            self._marcheaza_mort("send: %s" % type(e).__name__)
            raise CanalInchis("perechea a murit la send: %s" % e)

    def _recv(self, timeout):
        if self._sock is None:
            return None
        self._sock.settimeout(timeout)
        try:
            cadru = self._sock.recv(self.max_payload + 64)
        except (socket.timeout, BlockingIOError):
            # BlockingIOError apare la timeout=0 (socket neblocant) si inseamna 'nimic
            # ACUM', nu 'perechea a murit'. E subclasa de OSError, deci trebuie prinsa
            # INAINTE de ramura de mai jos -- altfel o simpla sondare fara asteptare
            # declara canalul mort.
            return None
        except (ConnectionResetError, OSError) as e:
            self._marcheaza_mort("recv: %s" % type(e).__name__)
            return None
        if not cadru:
            # zero octeti pe SEQPACKET = celalalt capat s-a inchis. Detectie de la nucleu.
            self._marcheaza_mort("eof (perechea a inchis)")
            return None
        return cadru

    def _close(self):
        for s in (self._sock, self._ascultator):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        self._sock = self._ascultator = None
        if self.rol == "gazda":
            try:
                os.unlink(self._cale)
            except OSError:
                pass


def _selftest():
    from channel import verifica_conformitate
    verifica_conformitate("uds")
    print("SELFTEST uds OK (SEQPACKET, framing de nucleu, EOF = pereche moarta).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
