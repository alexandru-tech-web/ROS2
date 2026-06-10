#!/usr/bin/env python3
"""operator_core.py — starea de comanda a operatorului (om-in-bucla).

Logica PURA (fara ROS), folosita de GCS: starea misiunii (IDLE / RUNNING /
PAUSED / ABORTED), modul fiecarei drone (AUTO / HOLD / GOTO / RTH) si
traducerea comenzilor operatorului in comenzi catre drone. Comenzile catre
drone pleaca pe acelasi canal /sar/cmd/{id} ca alocarile -> trec prin
legatura degradata (gating + latenta + store-and-forward), deci raspunsul
la comanda operatorului este MASURABIL sub degradare ("control la distanta
in timp real" — miezul tezei).

Schema comenzilor primite (JSON pe /sar/operator):
  {"type": "mission", "action": "start|pause|resume|abort"}
  {"type": "drone", "id": "d2", "action": "goto", "cell": [ci, cj]}
  {"type": "drone", "id": "d2", "action": "hold|resume|rth"}
  {"type": "fault", ...}        -> ignorat aici (tratat de fault_injector)

handle() intoarce lista de (drone_id, payload) de trimis pe /sar/cmd/{id};
payload-urile au k="op" si un cmd_id unic (pentru jurnalul sent->ack->done).
"""

AUTO, HOLD, GOTO, RTH = "AUTO", "HOLD", "GOTO", "RTH"
IDLE, RUNNING, PAUSED, ABORTED = "IDLE", "RUNNING", "PAUSED", "ABORTED"


class OperatorState:
    def __init__(self, drone_ids, autostart=True):
        self.drones = list(drone_ids)
        self.mission = RUNNING if autostart else IDLE
        self.mode = {d: AUTO for d in self.drones}
        self._next_id = 1

    def _cid(self):
        i = self._next_id
        self._next_id += 1
        return i

    def _op(self, did, action, **extra):
        payload = {"k": "op", "a": action, "cmd_id": self._cid()}
        payload.update(extra)
        return (did, payload)

    # ------------------------------------------------------------------
    def handle(self, cmd):
        """Aplica o comanda a operatorului; intoarce [(drone_id, payload)]."""
        out = []
        if not isinstance(cmd, dict):
            return out
        t = cmd.get("type")

        if t == "mission":
            a = cmd.get("action")
            if a == "start" and self.mission in (IDLE, PAUSED, ABORTED):
                if self.mission == ABORTED:        # restart complet
                    self.mode = {d: AUTO for d in self.drones}
                self.mission = RUNNING
                out += [self._op(d, "resume")
                        for d in self.drones if self.mode[d] == AUTO]
            elif a == "pause" and self.mission == RUNNING:
                self.mission = PAUSED
                out += [self._op(d, "hold")
                        for d in self.drones if self.mode[d] == AUTO]
            elif a == "resume" and self.mission == PAUSED:
                self.mission = RUNNING
                out += [self._op(d, "resume")
                        for d in self.drones if self.mode[d] == AUTO]
            elif a == "abort":
                self.mission = ABORTED
                for d in self.drones:
                    self.mode[d] = RTH
                    out.append(self._op(d, "rth"))

        elif t == "drone":
            d, a = cmd.get("id"), cmd.get("action")
            if d in self.mode:
                if a == "goto" and cmd.get("cell") is not None:
                    self.mode[d] = GOTO
                    out.append(self._op(d, "goto",
                                        cell=[int(c) for c in cmd["cell"]]))
                elif a == "hold":
                    self.mode[d] = HOLD
                    out.append(self._op(d, "hold"))
                elif a == "rth":
                    self.mode[d] = RTH
                    out.append(self._op(d, "rth"))
                elif a == "resume":
                    self.mode[d] = AUTO
                    out.append(self._op(d, "resume"))
        return out

    # ------------------------------------------------------------------
    def on_event(self, did, phase):
        """Eveniment de la drona (ack/done/fail): goto/rth incheiat -> HOLD
        (drona ramane pe loc pana operatorul o trece inapoi pe Auto)."""
        if phase in ("done", "fail") and self.mode.get(did) in (GOTO, RTH):
            self.mode[did] = HOLD

    def auto_eligible(self):
        """Dronele care primesc alocari automate de frontiere acum."""
        if self.mission != RUNNING:
            return set()
        return {d for d, m in self.mode.items() if m == AUTO}
