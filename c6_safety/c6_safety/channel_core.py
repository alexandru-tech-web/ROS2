#!/usr/bin/env python3
"""channel_core.py -- canal de TEST pentru core-uri; bancul experimentului e netem pe lo (S3).

Distinctia conteaza: ce e aici e un model in-proces, determinist la seed fix, bun
ca sa exercitam lantul si sa verificam ca AoI se propaga. NU e o masuratoare de
retea si nu produce cifre care sa intre in teza.

Fiecare comanda poarta marca t_tx (cand a fost emisa). Receptorul tine ULTIMA
comanda primita cel mult T_hold; peste asta, se opreste. AoI_cmd = acum - t_tx al
comenzii aplicate, adica exact varsta informatiei pe care actioneaza vehiculul.
"""
import random


class IdealChannel(object):
    """Fara intarziere, fara pierdere. AoI = 0 la fiecare pas, pe orice flux."""

    def __init__(self, params=None):
        self.params = params
        self._ultim = {}

    def trimite(self, cmd, t_tx, flux="cmd"):
        self._ultim[flux] = (cmd, t_tx)

    def primeste(self, t_now, flux="cmd"):
        if flux not in self._ultim:
            return None, None
        cmd, t_tx = self._ultim[flux]
        return cmd, t_now - t_tx


class DelayLossChannel(object):
    """Intarziere + jitter + pierdere, in proces. Determinist la seed fix."""

    def __init__(self, delay_s, jitter_s, p_loss, seed=1, T_hold=0.5):
        self.delay_s, self.jitter_s, self.p_loss = delay_s, jitter_s, p_loss
        self.T_hold = T_hold
        self.rng = random.Random(seed)
        self.in_zbor = {}          # flux -> [(t_sosire, payload, t_tx)]
        self.ultim = {}            # flux -> (payload, t_tx) livrat cel mai recent

    def trimite(self, cmd, t_tx, flux="cmd"):
        """Al doilea flux ("haz", pericolul raportat de GCS) trece prin ACELASI
        canal: aceeasi intarziere, aceeasi pierdere, acelasi generator aleator.
        S2b, caiet v0.2, F6 = 'acelasi'."""
        if self.rng.random() < self.p_loss:
            return                                  # pachet pierdut
        j = self.rng.uniform(-self.jitter_s, self.jitter_s)
        self.in_zbor.setdefault(flux, []).append((t_tx + max(0.0, self.delay_s + j), cmd, t_tx))

    def primeste(self, t_now, flux="cmd"):
        """Ce e in aer si a ajuns pana acum. Reordonarea e rezolvata pastrand
        pachetul cu t_tx cel mai NOU, nu ultimul sosit: un pachet intarziat care
        soseste dupa unul mai proaspat nu are voie sa intoarca starea inapoi.
        Pe fluxul "cmd", peste T_hold comanda devine (0,0). Pe "haz" NU exista
        taiere: roverul tine ultimul pericol primit oricat de vechi, iar varsta
        lui e chiar A_haz din Lema 1."""
        ramase = []
        for t_s, cmd, t_tx in self.in_zbor.get(flux, []):
            if t_s <= t_now:
                if flux not in self.ultim or t_tx > self.ultim[flux][1]:
                    self.ultim[flux] = (cmd, t_tx)
            else:
                ramase.append((t_s, cmd, t_tx))
        self.in_zbor[flux] = ramase
        if flux not in self.ultim:
            return ((0.0, 0.0) if flux == "cmd" else None), None
        cmd, t_tx = self.ultim[flux]
        aoi = t_now - t_tx
        if flux == "cmd" and aoi > self.T_hold:
            return (0.0, 0.0), aoi                  # prea veche: oprire
        return cmd, aoi
