#!/usr/bin/env python3
"""Bateria de verificari a emulatorului de articulatie (fara ROS/fier)."""
import math
import csv
import os
import tempfile
import zipfile
from types import SimpleNamespace
from xml.etree import ElementTree

from joint_core import (ImpedanceLaw, VirtualLimb, VirtualStopLaw, DelayLine,
                        PairSim, EnergyMonitor, SafetyGate, run_equilibrium,
                        simulation_substeps)
from drive_iface import SimBackend

OK = 0


def ck(cond, msg):
    global OK
    assert cond, msg
    OK += 1
    print(f"[ok]   {msg}")


# ---- legea de impedanta ----
law = ImpedanceLaw(k_nm_rad=10, b_nms_rad=0.5, tau_max=1.5)
ck(law.torque(0.0, 0.0) == 0.0, "impedanta: zero la echilibru")
ck(law.torque(0.2, 0.0) < 0, "impedanta: se opune deplasarii pozitive")
ck(law.torque(-0.2, 0.0) > 0, "impedanta: se opune deplasarii negative")
ck(abs(law.torque(10.0, 0.0)) == 1.5, "impedanta: clamp la tau_max")
law_db = ImpedanceLaw(k_nm_rad=10, deadband_rad=0.05)
ck(law_db.torque(0.03, 0.0) == 0.0, "impedanta: deadband ignora eroarea mica")
law_r = ImpedanceLaw(k_nm_rad=100, tau_max=5, ramp_nm_s=10)
t1 = law_r.torque(1.0, 0.0, dt=0.01)
ck(abs(t1) <= 0.1 + 1e-9, "impedanta: rampa limiteaza saltul de cuplu")

# ---- pacientul virtual (catch spastic) ----
limb = VirtualLimb(k=2, b=0.2, catch_om=1.0, catch_gain=5)
lent = abs(limb.torque(0.1, 0.5))
rapid = abs(limb.torque(0.1, 1.5))
ck(rapid > lent * 2, "limb: rezistenta creste brusc peste viteza-prag (catch)")
ck(abs(limb.torque(5, 5)) <= limb.tau_max, "limb: clamp la tau_max")

stop = VirtualStopLaw(k=20, b=0.8, contact_angle_rad=0.05)
ck(stop.torque(0.04, 1.0) == 0.0,
   "contact: fara reactie in zona libera")
ck(stop.torque(0.1, 0.0) < 0.0 and stop.torque(-0.1, 0.0) > 0.0,
   "contact: opune cuplu in ambele sensuri")
ck(stop.torque(0.1, 1.0) < stop.torque(0.1, -1.0),
   "contact: amortizeaza doar patrunderea, nu retragerea")
ck(abs(stop.torque(10.0, 1.0)) == stop.tau_max,
   "contact: cuplul ramane limitat")
try:
    VirtualStopLaw(k=-1.0)
except ValueError:
    invalid_contact_rejected = True
else:
    invalid_contact_rejected = False
ck(invalid_contact_rejected,
   "contact: rigiditatea negativa este respinsa")
s_contact, _, _ = run_equilibrium(
    lambda t: 1.0 if t >= 0.2 else 0.0,
    VirtualStopLaw(k=20, b=0.8, contact_angle_rad=0.05),
    dt=0.001, t_end=4.0)
ck(abs(s_contact.th - 0.10) < 0.01 and abs(s_contact.om) < 0.02,
   "contact: echilibru la prag + tau/K")

steps, inner_dt = simulation_substeps(200.0)
ck(steps == 10 and abs(inner_dt - 0.0005) < 1e-12,
   "SIM: 200 Hz ROS inseamna 10 subpasi de 0.5 ms")

# ---- intarzierea ----
dl = DelayLine(0.01, dt=0.001, initial=0.0)
outs = [dl.push(float(i)) for i in range(15)]
ck(outs[0] == 0.0 and outs[10] == 0.0 and outs[11] == 1.0,
   "delay: 10 ms = 10 esantioane la 1 kHz")

# ---- fizica perechii: B tine echilibrul sub treapta lui A ----
sim, mon, tr = run_equilibrium(
    lambda t: 0.5 if t > 0.2 else 0.0,
    ImpedanceLaw(k_nm_rad=10, b_nms_rad=0.6, tau_max=2.0), t_end=4.0)
th_fin = sim.th
ck(abs(th_fin - 0.05) < 0.01,
   f"echilibru: th_final~=tau/K (={th_fin:.3f} rad la 0.5 Nm / 10 Nm/rad)")
ck(abs(sim.om) < 0.02, "echilibru: viteza finala ~0 (amortizat)")
ck(tr[-1][3] > 0.0 and tr[-1][4] < 0.0,
   "pereche A/B: cuplul B se opune cuplului pozitiv al lui A")

# ---- pasivitate: fara intarziere energia B e marginita ----
ck(mon.e_max < 0.05, f"pasivitate: energia injectata de B marginita ({mon.e_max:.4f} J)")

# ---- CARLIGUL TEZEI: intarzierea destabilizeaza aceeasi lege ----
def energie_la(delay_ms):
    _, m, _ = run_equilibrium(
        lambda t: 0.5 if t > 0.2 else 0.0,
        ImpedanceLaw(k_nm_rad=40, b_nms_rad=1.2, tau_max=8.0),
        dt=0.001, t_end=3.0, delay_s=delay_ms / 1000.0)
    return m.e_max

e0, e20, e60 = energie_la(0), energie_la(20), energie_la(60)
ck(e0 < 0.05, f"stabil la 0 ms (E={e0:.3f} J)")
ck(e60 > 10 * max(e0, 1e-6), f"instabil la 60 ms (E={e60:.1f} J >> E0)")
ck(e60 > e20, f"degradare monotona cu intarzierea ({e20:.3f} -> {e60:.1f} J)")

# ---- siguranta: watchdog -> cuplu zero ----
g = SafetyGate(timeout_s=0.05, tau_max=2.0)
g.feed(0.0)
ck(g.gate(0.02, 1.0) == 1.0, "watchdog: trece cand masura e proaspata")
ck(g.gate(0.2, 1.0) == 0.0 and g.tripped, "watchdog: cuplu ZERO cand encoderul tace")
ck(g.gate(0.21, -5.0) == 0.0, "watchdog: ramane declansat")

# ---- backend-ul simulat respecta contractul ----
hw = SimBackend(n_pairs=3)
hw.enable(0); hw.enable(1)            # perechea 0: A=0, B=1
hw.set_torque(0, 0.5)
law_b = ImpedanceLaw(k_nm_rad=10, b_nms_rad=0.6, tau_max=2.0)
for _ in range(3000):
    hw.step()
    t, th, om = hw.read(1)
    hw.set_torque(1, law_b.torque(th, om, 0.001))
ck(abs(th - 0.05) < 0.012, f"backend sim: aceeasi fizica prin interfata ({th:.3f} rad)")
t2, th2, _ = hw.read(3)               # perechea 1 neatinsa
ck(abs(th2) < 1e-9, "backend sim: perechile sunt independente")

# Citirea este observatie pura: nu avanseaza nici perechea citita, nici restul.
t0 = [hw.read(2 * k)[0] for k in range(3)]
for _ in range(10):
    for mid in range(6):
        hw.read(mid)
t_read = [hw.read(2 * k)[0] for k in range(3)]
ck(t_read == t0, "backend sim: read este fara efecte secundare")

# Un pas avanseaza toate perechile exact o data si cu acelasi dt.
hw.step(0.005)
t_step = [hw.read(2 * k)[0] for k in range(3)]
ck(all(abs((after - before) - 0.005) < 1e-12
       for before, after in zip(t0, t_step)),
   "backend sim: step avanseaza toate perechile exact o data")
ck(max(t_step) - min(t_step) < 1e-12,
   "backend sim: toate perechile au acelasi timestamp")

try:
    hw.step(0.0)
except ValueError:
    invalid_dt_rejected = True
else:
    invalid_dt_rejected = False
ck(invalid_dt_rejected, "backend sim: respinge dt nul sau negativ")
hw.estop()
ck(not any(any(e) for e in hw.enabled), "estop: dezarmeaza tot")
position_at_stop = [hw.read(2 * k)[1] for k in range(3)]
old_speed = hw.pairs[0].om
hw.pairs[0].om = 0.1
try:
    hw.rearm()
except ValueError:
    fast_reset_rejected = True
else:
    fast_reset_rejected = False
ck(fast_reset_rejected and not any(any(e) for e in hw.enabled),
   "reset SIM: refuza rearmarea cand o axa inca se misca")
hw.pairs[0].om = old_speed
hw.rearm()
ck(all(all(e) for e in hw.enabled) and
   all(tau == [0.0, 0.0] for tau in hw.tau),
   "reset SIM: rearmeaza cu toate comenzile de cuplu zero")
ck([hw.read(2 * k)[1] for k in range(3)] == position_at_stop,
   "reset SIM: nu teleporteaza pozitia axelor")


# ---- tele-impedanta: canalul degradat + legea adaptiva ----
from teleimpedance import DegradedMeasure, AdaptiveImpedance, run_teleimpedance

lk = DegradedMeasure(ms=50, seed=1)
lk.push(0.0, 0.7, 0.1)
ck(lk.latest(0.02) is None, "link: nimic livrat inainte de latenta")
th_m, om_m, age = lk.latest(0.06)
ck(th_m == 0.7 and 0.055 < age < 0.065, "link: livrare dupa 50 ms, varsta corecta")
lk2 = DegradedMeasure(loss=1.0, seed=1)
lk2.push(0.0, 1.0, 0.0)
ck(lk2.latest(1.0) is None, "link: loss=1 nu livreaza nimic")

lk_multi = DegradedMeasure()
lk_multi.set_from_dict({"lat_ms": {"op-rob": 27.0},
                        "jit_ms": {"op-rob": 3.0},
                        "loss": {"op-rob": 0.2}, "down": []})
ck((lk_multi.ms, lk_multi.jit, lk_multi.loss, lk_multi.down) ==
   (27.0, 3.0, 0.2, False),
   "link: accepta fara crash schema multi-link a roverului")

lk_clamp = DegradedMeasure()
lk_clamp.set_from_dict({"ms": -5, "jit": -2, "loss": 4})
ck((lk_clamp.ms, lk_clamp.jit, lk_clamp.loss) == (0.0, 0.0, 1.0),
   "link: limiteaza parametrii la domeniul fizic")

TAU = lambda t: 0.5 if t > 0.2 else 0.0
law_ad = AdaptiveImpedance(k0=40, b0=1.2, tau_max=8.0)
s_ad, m_ad, _ = run_teleimpedance(law_ad, DegradedMeasure(ms=60, seed=42),
                                  TAU, t_end=4.0, adaptive=True)
ck(m_ad.e_max < 0.01, f"adaptiv+amortizare locala: pasiv la 60 ms (E={m_ad.e_max:.4f} J)")
ck(abs(s_ad.th - 0.5 / law_ad.k_ef) < 0.01,
   f"adaptiv: echilibru la tau/K_ef ({s_ad.th:.3f} rad, K_ef={law_ad.k_ef:.1f})")
s_120, m_120, _ = run_teleimpedance(AdaptiveImpedance(k0=40, b0=1.2, tau_max=8.0),
                                    DegradedMeasure(ms=120, seed=42),
                                    TAU, t_end=4.0, adaptive=True)
ck(m_120.e_max < 0.01, f"adaptiv: ramane pasiv si la 120 ms (E={m_120.e_max:.4f} J)")
law_fx = ImpedanceLaw(k_nm_rad=40, b_nms_rad=1.2, tau_max=8.0)
_, m_fx, _ = run_teleimpedance(law_fx, DegradedMeasure(ms=60, seed=42),
                               TAU, t_end=4.0)
ck(m_fx.e_max > 1000 * max(m_ad.e_max, 1e-6),
   f"duelul: fixul-total-remote explodeaza unde adaptivul rezista "
   f"({m_fx.e_max:.0f} J vs {m_ad.e_max:.4f} J)")

# Regresie pentru configuratia care oscila in GUI la 200 Hz / 16 ms.
s_safe, _, tr_safe = run_teleimpedance(
    AdaptiveImpedance(k0=23.67, b0=1.3, tau_max=2.0),
    DegradedMeasure(ms=16, seed=1),
    lambda t: 0.882 if t >= 0.5 else 0.0,
    dt=inner_dt, t_end=6.0, adaptive=True)
tail_safe = [row for row in tr_safe if row[0] >= 5.0]
ck(max(abs(row[2]) for row in tail_safe) < 0.05 and
   max(row[3] for row in tail_safe) - min(row[3] for row in tail_safe) < 0.1,
   "SIM: 16 ms si B=1.3 raman stabile la subpasul de 0.5 ms")


# ---- stratul de encoder: cuantizare + estimator ----
from encoder_core import (EncoderModel, NaiveDiff, KinematicEstimator,
                          EncoderLogger, MotorEncoderBank, MotorEncoderLogger)

enc = EncoderModel(counts_per_rev=4096)
ck(abs(enc.step - 2 * math.pi / 4096) < 1e-12, "encoder: pasul = 2pi/cpr")
ck(enc.read(0.0) == 0.0 and abs(enc.read(enc.step * 3.4) - enc.step * 3) < 1e-12,
   "encoder: cuantizare la cel mai apropiat pas")

A, F = 0.5, 1.0
W = 2 * math.pi * F
nd, ke = NaiveDiff(), KinematicEstimator()
dt = 0.001
e_n, e_k, e_a = [], [], []
t = 0.0
while t < 3.0:
    th_m = enc.read(A * math.sin(W * t))
    om_n, _ = nd.step(th_m, dt)
    _, om_k, acc_k = ke.step(th_m, dt)
    if t > 0.5:
        e_n.append((om_n - A * W * math.cos(W * t)) ** 2)
        e_k.append((om_k - A * W * math.cos(W * t)) ** 2)
        e_a.append((acc_k + A * W * W * math.sin(W * t)) ** 2)
    t += dt
rms = lambda e: (sum(e) / len(e)) ** 0.5
ck(rms(e_k) < 0.05, f"estimator: viteza filtrata RMS={rms(e_k):.3f} rad/s (<1.6% din varf)")
ck(rms(e_n) > 10 * rms(e_k),
   f"estimator: de >10x mai curat decat derivata bruta ({rms(e_n):.2f} vs {rms(e_k):.3f})")
ck(rms(e_a) < 0.15 * A * W * W,
   f"estimator: acceleratia RMS={rms(e_a):.2f} (<15% din varful {A*W*W:.1f})")
ke2 = KinematicEstimator()
for _ in range(2000):
    ke2.step(0.7, 0.001)
ck(abs(ke2.th - 0.7) < 1e-3 and abs(ke2.om) < 1e-3 and abs(ke2.acc) < 0.05,
   "estimator: pe pozitie constanta converge la om=0, acc=0")

bank = MotorEncoderBank(n_pairs=3, counts_per_rev=0,
                        signs=[1, -1, 1, -1, 1, -1])
a0 = bank.sample(0, 0.0, 0.2)
b0 = bank.sample(1, 0.0, -0.2)
ck(abs(a0["th"] - b0["th"]) < 1e-12 and
   bank.sample(2, 0.0, 0.3)["th"] == 0.3,
   "6 encodere: A/B aliniate, perechile independente")
ck(bank.sample(0, 0.0, 0.4) is None,
   "6 encodere: timestamp duplicat ignorat")
bank_quant = MotorEncoderBank(n_pairs=3, counts_per_rev=4096)
qa = bank_quant.sample(0, 0.0, 0.1)
qb = bank_quant.sample(1, 0.0, 0.1)
ck(qa["counts"] == qb["counts"] and qa["th_raw"] == qb["th_raw"],
   "6 encodere: axul rigid da citiri identice in SIM ideal")
with tempfile.TemporaryDirectory(prefix="joint_motor_test_") as tmp:
    path = os.path.join(tmp, "motor.csv")
    motor_log = MotorEncoderLogger(path)
    motor_log.row(0, "A", qa)
    motor_log.row(0, "B", qb)
    motor_log.close()
    with open(path, newline="", encoding="utf-8") as stream:
        motor_rows = list(csv.DictReader(stream))
    ck(len(motor_rows) == 2 and
       [row["motor_id"] for row in motor_rows] == ["0", "1"],
       "6 encodere: jurnalul CSV pastreaza motorul si latura")

# --- margine de stabilitate glisanta (fereastra 1s) + ESTOP ---
em = EnergyMonitor(window_s=1.0, estop_energy=0.5)
for _ in range(500):
    em.step(2.0, 0.5, 0.001)          # putere tau*om = 1.0 W timp de 0.5 s -> 0.5 J
ck(abs(em.win_energy - 0.5) < 0.02 and not em.estopped,
   f"EnergyMonitor: energie pe fereastra ~0.5J, fara ESTOP ({em.win_energy:.2f})")
for _ in range(1500):
    em.step(0.0, 0.0, 0.001)          # fereastra gliseaza peste putere 0
ck(em.win_energy < 0.05, f"EnergyMonitor: fereastra gliseaza, energia scade ({em.win_energy:.3f})")
em2 = EnergyMonitor(window_s=1.0, estop_energy=0.5)
for _ in range(800):
    em2.step(3.0, 0.5, 0.001)         # 1.5 W * 0.8 s = 1.2 J > prag 0.5
ck(em2.estopped, "EnergyMonitor: energie pe fereastra peste prag -> ESTOP declansat")
em2.reset_estop()
ck(not em2.estopped, "EnergyMonitor: reset_estop curata flag-ul")

# ---- exportul CSV din panou: datele plotate, fara interpolare ----
from panel_export import export_panel_csv

with tempfile.TemporaryDirectory(prefix="joint_panel_test_") as tmp:
    path = os.path.join(tmp, "graph.csv")
    count = export_panel_csv([
        {"th": [(1.0, 0.1)], "tau_a_cmd": [(1.0, 0.5)],
         "tau_b": [(1.0, -0.5)], "om": [(1.02, 0.0)],
         "th_a": [(1.0, 0.1)], "th_b": [(1.0, 0.099)],
         "delta_th": [(1.0, 0.001)]},
        {"th": [(1.0, -0.2)]},
    ], path)
    with open(path, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    ck(count == 3 and len(rows) == 3 and
       rows[0]["theta_rad"] == "0.1" and
       rows[0]["tau_a_cmd_nm"] == "0.5" and
       rows[0]["tau_b_cmd_nm"] == "-0.5" and
       rows[0]["theta_a_rad"] == "0.1" and
       rows[0]["theta_b_rad"] == "0.099" and
       rows[0]["delta_theta_a_b_rad"] == "0.001" and
       rows[1]["theta_rad"] == "-0.2" and
       rows[2]["omega_rad_s"] == "0.0",
       "CSV HMI: exporta perechi si semnale la timestampurile lor")
    try:
        export_panel_csv([], path)
    except FileExistsError:
        no_overwrite = True
    else:
        no_overwrite = False
    ck(no_overwrite, "CSV HMI: nu suprascrie un export existent")

# ---- jurnalul complet al sesiunii si exportul Excel ----
from session_export import (SessionEventLogger, SessionStateLogger,
                            checked_session_id, export_session_xlsx,
                            session_path, write_config)

with tempfile.TemporaryDirectory(prefix="joint_session_test_") as tmp:
    sid = "test_20260919T090000Z"
    write_config(session_path(tmp, sid, "sim_config"), {"rate_hz": 200})
    write_config(session_path(tmp, sid, "encoder_config"),
                 {"counts_per_rev": 4096})
    first = "2026-09-19T09:00:00.000+00:00"
    later = "2026-09-19T09:00:01.000+00:00"
    state_log = SessionStateLogger(session_path(tmp, sid, "states"))
    event_log = SessionEventLogger(session_path(tmp, sid, "events"))
    common_log = EncoderLogger(os.path.join(tmp, f"encoders_{sid}.csv"))
    motor_log = MotorEncoderLogger(os.path.join(tmp,
                                                 f"motor_encoders_{sid}.csv"))
    law = SimpleNamespace(k=20.0, b=0.8, th0=0.0)
    link = SimpleNamespace(ms=10.0, jit=0.0, loss=0.0, down=False)
    state = {"t": 0.0, "th": 0.0, "om": 0.0,
             "motors": {"A": {"th": 0.0, "om": 0.0, "source": "sim"},
                        "B": {"th": 0.0, "om": 0.0, "source": "sim"}},
             "tau_a_cmd": 0.0, "tau_b": 0.0, "k_ef": 20.0,
             "win_energy": 0.0, "estopped": False,
             "reaction_mode": "impedance", "contact_angle_deg": 5.0,
             "reset_status": ""}
    state_log.row(0, state, law, link, time_utc=first)
    event_log.row(0.0, "start", time_utc=first)
    common_log.row(0.0, 0, 0.0, 0.0, 0.0, 0.0, time_utc=first)
    sample = {"t": 0.0, "counts": 0, "th_raw": 0.0, "th": 0.0,
              "om": 0.0, "acc": 0.0, "om_raw": 0.0}
    motor_log.row(0, "A", sample, time_utc=first, source="sim")
    motor_log.row(0, "B", sample, time_utc=first, source="sim")
    state["t"] = 1.0
    state["tau_a_cmd"] = 1.0
    state_log.row(0, state, law, link, time_utc=later)
    event_log.row(1.0, "cmd_a", pair=0, tau_a_cmd_nm=1.0, time_utc=later)
    common_log.row(1.0, 0, 0.0, 0.0, 0.0, 0.0, time_utc=later)
    motor_log.row(0, "A", {**sample, "t": 1.0},
                  time_utc=later, source="sim")
    state_log.stream.flush(); event_log.stream.flush()
    common_log.f.flush(); motor_log.f.flush()

    book = export_session_xlsx(tmp, sid,
                               export_time_utc="2026-09-19T09:00:00.500+00:00")
    with zipfile.ZipFile(book) as archive:
        good_zip = archive.testzip() is None
        sheets = []
        for index in range(1, 6):
            root = ElementTree.fromstring(
                archive.read(f"xl/worksheets/sheet{index}.xml"))
            sheets.append(root.findall(
                ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"))
        workbook = archive.read("xl/workbook.xml").decode("utf-8")
    ck(good_zip and len(sheets) == 5 and
       [len(sheet) for sheet in sheets] == [2, 3, 2, 2, 16] and
       "Encodere_6" in workbook,
       "Excel: patru jurnale si metadate, pana la timestampul exportului")
    state_log.close(); event_log.close(); common_log.close(); motor_log.close()
    with open(state_log.path, newline="", encoding="utf-8") as stream:
        state_rows = list(csv.DictReader(stream))
    with open(motor_log.f.name, newline="", encoding="utf-8") as stream:
        motor_rows = list(csv.DictReader(stream))
    ck(len(state_rows) == 2 and state_rows[0]["time_s"] == "0.0" and
       state_rows[0]["time_utc"] == first and
       state_rows[1]["tau_a_cmd_nm"] == "1.0" and
       motor_rows[0]["time_utc"] == first and
       motor_rows[0]["source"] == "sim" and
       motor_rows[0]["om_raw"] == "0.00000",
       "Jurnale: t=0, UTC, cuplu comandat si encoder brut/filtrat")
    try:
        export_session_xlsx(tmp, "../invalid")
    except ValueError:
        invalid_id_rejected = True
    else:
        invalid_id_rejected = False
    ck(invalid_id_rejected and checked_session_id(sid) == sid,
       "Excel: ID sesiune validat, fara traversare de directoare")

# ---- geometria: trei A in stanga, trei B in dreapta, axuri cu suruburi ----
from tools.gen_bench_model import geometrie, PAIRS

shapes = geometrie()
motor_a = [v for v in shapes if v["link"] == "base_link" and
           v["kind"] == "box" and v["sz"] == (0.20, 0.14, 0.13) and
           v["c"] == "motor_a"]
motor_b = [v for v in shapes if v["link"] == "base_link" and
           v["kind"] == "box" and v["sz"] == (0.20, 0.14, 0.13) and
           v["c"] == "negru"]
ck(len(motor_a) == len(motor_b) == 3 and
   all(v["xyz"][0] < 0 for v in motor_a) and
   all(v["xyz"][0] > 0 for v in motor_b),
   "geometrie: 3 motoare A albastre stanga, 3 motoare B negre dreapta")
ck(len(PAIRS) == 3 and
   all(a["xyz"][1] == b["xyz"][1] == PAIRS[k][1]
       for k, (a, b) in enumerate(zip(motor_a, motor_b))),
   "geometrie: A si B din fiecare pereche sunt aliniate pe acelasi ax")
ck(all(sum(v["kind"] == "cyl" and v.get("r") == 0.0035
           for v in shapes if v["link"] == f"shaft{k}") == 6
       for k in range(3)),
   "geometrie: fiecare flansa are 6 suruburi prinse de axul rotitor")

print(f"\n=== {OK}/{OK} verificari trecute ===")
