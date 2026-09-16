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
    """Fara intarziere, fara pierdere. AoI_cmd = 0 la fiecare pas."""

    def __init__(self, params=None):
        self.params = params

    def trimite(self, cmd, t_tx):
        self._ultim = (cmd, t_tx)

    def primeste(self, t_now):
        cmd, t_tx = self._ultim
        return cmd, t_now - t_tx


class DelayLossChannel(object):
    """Intarziere + jitter + pierdere, in proces. Determinist la seed fix."""

    def __init__(self, delay_s, jitter_s, p_loss, seed=1, T_hold=0.5):
        self.delay_s, self.jitter_s, self.p_loss = delay_s, jitter_s, p_loss
        self.T_hold = T_hold
        self.rng = random.Random(seed)
        self.in_zbor = []          # [(t_sosire, cmd, t_tx)]
        self.ultim = None          # (cmd, t_tx) livrata cel mai recent

    def trimite(self, cmd, t_tx):
        if self.rng.random() < self.p_loss:
            return                                  # pachet pierdut
        j = self.rng.uniform(-self.jitter_s, self.jitter_s)
        self.in_zbor.append((t_tx + max(0.0, self.delay_s + j), cmd, t_tx))

    def primeste(self, t_now):
        """Ce e in aer si a ajuns pana acum. Reordonarea e rezolvata pastrand
        comanda cu t_tx cel mai NOU, nu ultima sosita: un pachet intarziat care
        soseste dupa unul mai proaspat nu are voie sa intoarca starea inapoi."""
        ramase = []
        for t_s, cmd, t_tx in self.in_zbor:
            if t_s <= t_now:
                if self.ultim is None or t_tx > self.ultim[1]:
                    self.ultim = (cmd, t_tx)
            else:
                ramase.append((t_s, cmd, t_tx))
        self.in_zbor = ramase
        if self.ultim is None:
            return (0.0, 0.0), None                 # nimic nu a ajuns inca
        cmd, t_tx = self.ultim
        aoi = t_now - t_tx
        if aoi > self.T_hold:
            return (0.0, 0.0), aoi                  # prea veche: oprire
        return cmd, aoi
