#!/usr/bin/env python3
"""modbus_backend.py -- SCHELETUL backend-ului real pentru drive-urile ABB
"seria 300" prin Modbus (RTU pe RS-485 sau TCP). NU e functional inca:
harta de registre din CONFIG se completeaza DIN MANUALUL drive-ului dupa
citirea placutei exacte. Aceeasi interfata ca SimBackend -- nimic de
schimbat deasupra.

ARHITECTURA RECOMANDATA (lectia din teste -- vezi figs/joint_sweep.png):
  [laptop/GCS] --(Zenoh/DDS, legatura degradata: doar K, th0, comenzi)-->
  [Raspberry Pi LANGA banc] --(Modbus, bucla locala 50-100 Hz)--> [drive]
Bucla rapida (amortizarea + watchdog + limita de cuplu) traieste pe Pi.
Modbus RTU realist face ~50-100 Hz pe registru -- suficient LOCAL, fatal
daca incerci sa inchizi bucla prin internet.

REGULI: drive in mod CUPLU (torque reference); limita de curent setata
IN drive (bariera independenta de software); estop() scrie zero si
dezactiveaza, neconditionat.
"""
import time

# === DE COMPLETAT DIN MANUAL (dupa placuta exacta a drive-ului) ===
CONFIG = {
    "metoda": "rtu",            # "rtu" (RS-485) sau "tcp"
    "port": "/dev/ttyUSB0",     # adaptor USB->RS485 pe Pi
    "baud": 19200, "parity": "E", "stopbits": 1,
    "unit_ids": [1, 2, 3, 4, 5, 6],   # adresele celor 6 drive-uri
    # registre (PLACEHOLDER -- adresele reale din manual!):
    "REG_TORQUE_REF": None,     # ex: 0x????  referinta de cuplu
    "REG_POSITION":   None,     # ex: 0x????  pozitia (encoder)
    "REG_VELOCITY":   None,     # ex: 0x????  viteza
    "REG_ENABLE":     None,     # ex: coil/holding pentru armare
    "SCALE_TORQUE":   None,     # Nm per unitate de registru
    "SCALE_POS":      None,     # rad per unitate
    "SCALE_VEL":      None,     # rad/s per unitate
}


class ModbusBackend:
    """Implementarea contractului drive_iface peste pymodbus.
    Refuza sa porneasca pana cand CONFIG e completat -- intentionat."""

    def __init__(self, cfg=CONFIG):
        missing = [k for k, v in cfg.items() if v is None]
        if missing:
            raise SystemExit(
                "[X] ModbusBackend necompletat: lipsesc "
                f"{missing}.\n    Trimite placuta drive-ului -> completam "
                "harta de registre din manual si abia apoi armam fierul.")
        try:
            from pymodbus.client import ModbusSerialClient, ModbusTcpClient
        except ImportError:
            raise SystemExit("[X] pip install pymodbus (pe Pi)")
        self.cfg = cfg
        if cfg["metoda"] == "rtu":
            self.cli = ModbusSerialClient(port=cfg["port"],
                                          baudrate=cfg["baud"],
                                          parity=cfg["parity"],
                                          stopbits=cfg["stopbits"])
        else:
            self.cli = ModbusTcpClient(cfg["port"])
        assert self.cli.connect(), "[X] nu ma pot conecta la drive-uri"

    def _uid(self, mid):
        return self.cfg["unit_ids"][mid]

    def enable(self, mid):
        self.cli.write_register(self.cfg["REG_ENABLE"], 1,
                                device_id=self._uid(mid))

    def disable(self, mid):
        self.set_torque(mid, 0.0)
        self.cli.write_register(self.cfg["REG_ENABLE"], 0,
                                device_id=self._uid(mid))

    def read(self, mid):
        uid = self._uid(mid)
        pos = self.cli.read_holding_registers(self.cfg["REG_POSITION"], 
                                              count=1, device_id=uid)
        vel = self.cli.read_holding_registers(self.cfg["REG_VELOCITY"], 
                                              count=1, device_id=uid)
        th = pos.registers[0] * self.cfg["SCALE_POS"]
        om = vel.registers[0] * self.cfg["SCALE_VEL"]
        return time.time(), th, om

    def set_torque(self, mid, tau):
        raw = int(tau / self.cfg["SCALE_TORQUE"])
        self.cli.write_register(self.cfg["REG_TORQUE_REF"], raw & 0xFFFF,
                                device_id=self._uid(mid))

    def estop(self):
        for mid in range(len(self.cfg["unit_ids"])):
            try:
                self.disable(mid)
            except Exception:
                pass
