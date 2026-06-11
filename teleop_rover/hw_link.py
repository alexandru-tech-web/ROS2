#!/usr/bin/env python3
"""hw_link.py — puntea HARDWARE-IN-THE-LOOP a roverului (nucleu PUR).

Protocol serial in stil NMEA, lizibil si verificabil cu suma de control XOR:
    PC -> MCU:   $CMD,<v m/s>,<w rad/s>*<CK>\\n
    MCU -> PC:   $POS,<x>,<y>,<th>,<seq>*<CK>\\n
CK = XOR-ul octetilor dintre '$' si '*', in hex pe 2 cifre.

Trei piese, toate testabile FARA hardware (test_hw_link.py):
  - encode_cmd / encode_pos + FrameParser (taie cadrele din fluxul de octeti,
    tolereaza fragmentare si zgomot, respinge sumele de control gresite);
  - LoopbackRover: un "microcontroler" software care integreaza cinematica
    si raspunde cu $POS — HIL complet, in bucla, fara niciun fir;
  - HwLink: aceeasi interfata peste loopback (port="loop") sau peste un
    port serial real (port="/dev/ttyUSB0", cere pyserial) — robot_node
    nu stie si nu-i pasa care din ele e dedesubt.

Important de proiectare: stratul de siguranta (SafetyGate) ramane in
robot_node, IN AMONTE de punte — pe hardware nu pleaca niciodata o comanda
veche sau orfana; in plus, firmware-ul de referinta are propriul watchdog
(aparare in adancime).
"""
import time


def checksum(payload: str) -> int:
    ck = 0
    for b in payload.encode():
        ck ^= b
    return ck


def _frame(payload: str) -> bytes:
    return f"${payload}*{checksum(payload):02X}\n".encode()


def encode_cmd(v: float, w: float) -> bytes:
    return _frame(f"CMD,{v:.3f},{w:.3f}")


def encode_pos(x: float, y: float, th: float, seq: int) -> bytes:
    return _frame(f"POS,{x:.3f},{y:.3f},{th:.4f},{seq}")


class FrameParser:
    """Reasambleaza cadrele din fluxul de octeti (fragmentare, zgomot)."""

    def __init__(self):
        self.buf = b""
        self.bad = 0          # cadre respinse (suma de control / format)

    def feed(self, data: bytes):
        out = []
        self.buf += data
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            s = line.decode(errors="replace").strip()
            if not s.startswith("$") or "*" not in s:
                if s:
                    self.bad += 1
                continue
            payload, _, ck = s[1:].rpartition("*")
            try:
                ok = int(ck, 16) == checksum(payload)
            except ValueError:
                ok = False
            if not ok:
                self.bad += 1
                continue
            f = payload.split(",")
            try:
                if f[0] == "CMD" and len(f) == 3:
                    out.append({"k": "CMD", "v": float(f[1]), "w": float(f[2])})
                elif f[0] == "POS" and len(f) == 5:
                    out.append({"k": "POS", "x": float(f[1]), "y": float(f[2]),
                                "th": float(f[3]), "seq": int(f[4])})
                else:
                    self.bad += 1
            except ValueError:
                self.bad += 1
        return out


class LoopbackRover:
    """„MCU" software: primeste $CMD, integreaza cinematica, emite $POS.
    Permite HIL cap-coada fara hardware (si testele automate de aici)."""

    def __init__(self):
        from rover_core import DiffDrive
        self.rover = DiffDrive()
        self.parser = FrameParser()
        self.v = self.w = 0.0
        self.seq = 0
        self.t = time.monotonic()
        self.rx = b""

    def write(self, data: bytes):
        for f in self.parser.feed(data):
            if f["k"] == "CMD":
                self.v, self.w = f["v"], f["w"]

    def read(self) -> bytes:
        now = time.monotonic()
        self.rover.step(self.v, self.w, min(0.2, now - self.t))
        self.t = now
        self.seq += 1
        out, self.rx = self.rx, b""
        return out + encode_pos(self.rover.x, self.rover.y,
                                self.rover.th, self.seq)


class HwLink:
    """Interfata unica a robotului catre hardware: loopback sau serial real."""

    def __init__(self, port: str = "loop", baud: int = 115200):
        self.parser = FrameParser()
        self.pose = None                      # (x, y, th) ultima valida
        if port == "loop":
            self.dev = LoopbackRover()
        else:                                  # hardware REAL (netestat aici)
            import serial                      # pip install pyserial
            self.dev = serial.Serial(port, baud, timeout=0)

    def send_cmd(self, v: float, w: float):
        self.dev.write(encode_cmd(v, w))

    def poll(self):
        """Citeste tot ce e disponibil; intoarce ultima poza valida sau None."""
        data = self.dev.read() if isinstance(self.dev, LoopbackRover) \
            else self.dev.read(4096)
        for f in self.parser.feed(data or b""):
            if f["k"] == "POS":
                self.pose = (f["x"], f["y"], f["th"])
        return self.pose
