#!/usr/bin/env python3
"""protocol.py -- ce inseamna octetii care trec prin canalul local. FARA ROS, fara retea.

Canalul (channel.py) duce (payload, seq) si nu vrea sa stie ce sunt. Aici se decide ce pune
gateway-ul in payload, ca agentul sa stie ce sa faca:

    [tip:1][topic:1][util...]

  tip   'A' = mesaj de aplicatie, 'P' = sonda, 'E' = ecou (raspunsul agentului)
  topic indexul topicului (deciziile sunt PER-TOPIC, deci agentul trebuie sa stie pe care
        sa publice; un octet ajunge, nu avem sute de topicuri)
  util  sarcina utila propriu-zisa

SECVENTELE: gateway-ul tine un contor PER CALE si il incrementeaza la fiecare mesaj trimis
pe acea cale, fie el de aplicatie sau de sonda. Agentul intoarce acelasi seq in ecou. Asa,
estimatorul caii primeste un sir de numere consecutive din care golurile SUNT pierderile --
exact conventia din C2 (bench_client / burst_metrics), deci cifrele raman comparabile.
Consecinta utila: pe calea activa estimatorul e hranit de aplicatie SI de sonda (55 Hz), pe
cea inactiva doar de sonda (5 Hz).
"""
import struct
import sys

TIP_APP = b"A"
TIP_SONDA = b"P"
TIP_ECOU = b"E"
TIPURI = (TIP_APP, TIP_SONDA, TIP_ECOU)

ANTET = struct.Struct("<cB")


def impacheteaza(tip, topic, util=b""):
    if tip not in TIPURI:
        raise ValueError("tip necunoscut: %r" % (tip,))
    if not (0 <= topic <= 255):
        raise ValueError("indexul de topic trebuie in 0..255: %r" % (topic,))
    return ANTET.pack(tip, topic) + util


def despacheteaza(cadru):
    if len(cadru) < ANTET.size:
        raise ValueError("cadru prea scurt: %d octeti" % len(cadru))
    tip, topic = ANTET.unpack_from(cadru, 0)
    if tip not in TIPURI:
        raise ValueError("tip necunoscut pe fir: %r" % (tip,))
    return tip, topic, cadru[ANTET.size:]


def _selftest():
    for tip in TIPURI:
        for topic in (0, 1, 255):
            for util in (b"", b"x" * 4096):
                t, tp, u = despacheteaza(impacheteaza(tip, topic, util))
                assert (t, tp, u) == (tip, topic, util), (tip, topic, len(util))
    assert ANTET.size == 2, ANTET.size
    # antetul e MIC intentionat: la sonda de 32 de octeti, 2 octeti in plus inseamna 6%
    # din payload -- vizibil in cifra de overhead, deci nu se umfla degeaba
    for rea in ((b"X", 0), (TIP_APP, 256), (TIP_APP, -1)):
        try:
            impacheteaza(*rea)
            raise AssertionError("acceptat: %r" % (rea,))
        except ValueError:
            pass
    for scurt in (b"", b"A"):
        try:
            despacheteaza(scurt)
            raise AssertionError("cadru scurt acceptat: %r" % scurt)
        except ValueError:
            pass
    try:
        despacheteaza(b"Z\x00date")
        raise AssertionError("tip necunoscut acceptat")
    except ValueError:
        pass
    print("SELFTEST protocol OK (impachetare/despachetare, validari).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
