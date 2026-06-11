#!/usr/bin/env python3
"""test_plugins.py — verificari automate pentru toate modulele pure.
Ruleaza fara ROS2; fiecare CHECK afiseaza [ok]/[FAIL] si scriptul iese
cu cod != 0 daca ceva pica."""
import math
import random
import sys

sys.path.insert(0, ".")

from channel import DegradedChannel
from radio_link import LogDistanceRadioLink, make_link
from coverage import CoverageGrid
from victims import VictimField
from battery import BatteryModel
from guard import ObstacleGuard
from predictor import DeadReckoningPredictor, unicycle_step

N_OK = 0
N_FAIL = 0


def check(name, cond, detail=""):
    global N_OK, N_FAIL
    if cond:
        N_OK += 1
        print(f"[ok]   {name}")
    else:
        N_FAIL += 1
        print(f"[FAIL] {name}  {detail}")


# ============================ DegradedChannel ============================
print("--- channel.DegradedChannel ---")
ch = DegradedChannel(ms=100, jit_ms=0, loss=0.0, seed=1)
ch.push(0.0, "a")
check("canal: nimic livrat inainte de scadenta", ch.pop_ready(0.05) == [])
out = ch.pop_ready(0.11)
check("canal: livrare la t >= ms", len(out) == 1 and out[0][1] == "a"
      and abs(out[0][0] - 0.1) < 1e-9)

ch = DegradedChannel(ms=0, jit_ms=0, loss=0.5, seed=42)
n = 20000
sent_ok = sum(ch.push(0.0, i) for i in range(n))
ratio = sent_ok / n
check("canal: pierderea statistica ~50%", abs(ratio - 0.5) < 0.02,
      f"ratio={ratio:.3f}")
check("canal: statistici coerente",
      ch.stats()["dropped"] == n - sent_ok and ch.stats()["sent"] == n)

ch = DegradedChannel(ms=50, jit_ms=30, loss=0.0, monotonic=True, seed=7)
for i in range(500):
    ch.push(i * 0.01, i)
deliv = ch.pop_ready(1e9)
ts = [t for t, _ in deliv]
order = [p for _, p in deliv]
check("canal: livrare monotona in timp",
      all(ts[i] <= ts[i + 1] for i in range(len(ts) - 1)))
check("canal: FIFO pastrat in mod monoton (fara reordonare)",
      order == sorted(order))

ch = DegradedChannel(ms=0, jit_ms=0, loss=0.0, down=True)
check("canal: down blocheaza tot", ch.push(0, "x") is False
      and ch.stats()["dropped"] == 1)
ch.set_from_dict({"down": False, "ms": 10})
check("canal: set_from_dict (schema linkstate)",
      ch.down is False and ch.ms == 10)

# ========================= LogDistanceRadioLink ==========================
print("--- radio_link.LogDistanceRadioLink ---")
rl = LogDistanceRadioLink(shadow_sigma_db=0.0)
s10 = rl.state_for_distance(10)
s100 = rl.state_for_distance(100)
s400 = rl.state_for_distance(400)
check("radio: SNR scade cu distanta", s10["snr"] > s100["snr"] > s400["snr"])
check("radio: pierderea creste cu distanta",
      s10["loss"] <= s100["loss"] <= s400["loss"])
check("radio: aproape de GCS legatura e curata",
      s10["loss"] < 0.01 and not s10["down"],
      f"loss={s10['loss']}")
check("radio: latenta creste cu pierderea", s400["ms"] > s100["ms"] >= s10["ms"])

# monotonie stricta pe o plaja larga (fara umbra)
ds = [1, 5, 10, 20, 50, 100, 150, 200, 300, 400, 600, 800]
losses = [rl.state_for_distance(d)["loss"] for d in ds]
check("radio: monotonie loss(d) pe 1..800 m",
      all(losses[i] <= losses[i + 1] + 1e-12 for i in range(len(losses) - 1)))

rl2 = LogDistanceRadioLink(shadow_sigma_db=0.0, d_max=300)
check("radio: cutoff dur d_max", rl2.state_for_distance(301)["down"] is True
      and rl2.state_for_distance(299)["down"] in (True, False))

states = rl.states_for_positions((0, 0), {"d1": (30, 40), "d2": (300, 400)})
check("radio: states_for_positions (3-4-5 => d=50)",
      abs(states["d1"]["d"] - 50.0) < 1e-6 and abs(states["d2"]["d"] - 500.0) < 1e-6)
check("radio: schema linkstate completa",
      all(k in states["d1"] for k in ("ms", "jit", "loss", "down")))

rlu = make_link("urban_rubble", shadow_sigma_db=0.0)
rlo = make_link("open_field", shadow_sigma_db=0.0)
check("radio: profil urban mai sever decat camp deschis la 150 m",
      rlu.state_for_distance(150)["loss"] > rlo.state_for_distance(150)["loss"])

# reproducibilitate cu seed (umbra log-normala)
ra = LogDistanceRadioLink(shadow_sigma_db=3.0, seed=5)
rb = LogDistanceRadioLink(shadow_sigma_db=3.0, seed=5)
sa = [ra.state_for_distance(100)["loss"] for _ in range(5)]
sb = [rb.state_for_distance(100)["loss"] for _ in range(5)]
check("radio: umbra reproductibila cu seed", sa == sb)

# ============================= CoverageGrid =============================
print("--- coverage.CoverageGrid ---")
cg = CoverageGrid(0, 100, 0, 100, cell=1.0)
check("acoperire: porneste de la 0%", cg.percent() == 0.0)
cg.mark_disc(50, 50, 10, t=1.0)
area_pct = 100.0 * math.pi * 10 ** 2 / (100 * 100)
check("acoperire: disc ~ pi*r^2", abs(cg.percent() - area_pct) < 0.6,
      f"{cg.percent():.2f} vs {area_pct:.2f}")
cg.mark_disc(50, 50, 10, t=2.0)
check("acoperire: marcarea repetata nu dubleaza",
      abs(cg.percent() - area_pct) < 0.6)
cg2 = CoverageGrid(0, 60, 0, 60, cell=0.5)
# traseu lawnmower cu pas <= 2*r intre linii => acoperire aproape totala
r = 4.0
y = r
pts = []
while y < 60:
    pts += [(x, y) for x in [i * 0.5 for i in range(0, 121)]]
    y += 1.5 * r
cg2.mark_path(pts, r, t=10.0)
check("acoperire: lawnmower acopera > 95%", cg2.percent() > 95.0,
      f"{cg2.percent():.1f}%")
check("acoperire: jaloane t-pana-la-X% inregistrate",
      cg2.time_to(90) == 10.0 and 50 in cg2.milestones())
check("acoperire: marcare in afara ariei nu crapa",
      (cg2.mark_disc(-500, -500, 3) or True) and cg2.percent() <= 100.0)
row = cg2.csv_row(12.0)
check("acoperire: rand CSV valid", row.startswith("12.00,")
      and row.count(",") == 3)

# ============================= VictimField ==============================
print("--- victims.VictimField ---")
vf = VictimField(6, 0, 60, 0, 60, seed=3, min_sep=5.0)
check("victime: N plasate", vf.n_total == 6)
ok_sep = all((ax - bx) ** 2 + (ay - by) ** 2 >= 25.0 - 1e-9
             for i, (ax, ay) in enumerate(vf.victims)
             for (bx, by) in vf.victims[i + 1:])
check("victime: separatie minima respectata", ok_sep)
vfa = VictimField(6, 0, 60, 0, 60, seed=3)
vfb = VictimField(6, 0, 60, 0, 60, seed=3)
check("victime: pozitii reproductibile cu seed", vfa.victims == vfb.victims)

# detectie determinista: drona fix peste victima, p_detect imens
vx, vy = vf.victims[0]
ev = vf.step(5.0, {"d1": (vx, vy)}, sensor_r=2.0, p_detect=1e9, dt=0.1)
check("victime: detectie la suprapunere", len(ev) == 1
      and ev[0]["victim"] == 0 and vf.n_detected == 1)
ev2 = vf.step(6.0, {"d1": (vx, vy)}, sensor_r=2.0, p_detect=1e9, dt=0.1)
check("victime: nu detecteaza de doua ori", ev2 == [])
far = (vx + 50, vy + 50)
ev3 = vf.step(7.0, {"d1": far}, sensor_r=2.0, p_detect=1e9, dt=0.1)
check("victime: in afara razei nu detecteaza", ev3 == [])
check("victime: t_first corect", vf.first_detection_t() == 5.0)
check("victime: t_all None cat timp raman nedetectate",
      vf.last_detection_t() is None)

# ============================= BatteryModel =============================
print("--- battery.BatteryModel ---")
b = BatteryModel(capacity_wh=60, p_hover_w=120, k_v_w=8,
                 soc_rtl=0.30, soc_land=0.10)
check("baterie: SOC initial 100%", b.soc() == 1.0 and b.state == "NORMAL")
# la punct fix: 60 Wh / 120 W = 0.5 h pana la 0% => la soc 30% au trecut 21 min
t = 0.0
dt = 1.0
while b.state == "NORMAL" and t < 4000:
    t += dt
    b.update(dt, speed=0.0, t=t)
check("baterie: RTL declansat la pragul static",
      b.state == "RTL" and abs(b.soc() - 0.30) < 0.01,
      f"soc={b.soc():.3f} t={t}")
expect_t_rtl = 0.70 * 60 / 120 * 3600
check("baterie: momentul RTL ~ teoretic (21 min)",
      abs(t - expect_t_rtl) <= 2.0, f"t={t} vs {expect_t_rtl}")
while b.state == "RTL" and t < 8000:
    t += dt
    b.update(dt, speed=4.0, t=t)
check("baterie: LAND la pragul critic",
      b.state == "LAND" and abs(b.soc() - 0.10) < 0.01)
u = b.used_wh
b.update(10.0, speed=4.0, t=t + 10)
check("baterie: dupa LAND nu mai consuma", b.used_wh == u)

b2 = BatteryModel(capacity_wh=60, p_hover_w=120, k_v_w=8, soc_rtl=0.05,
                  soc_land=0.02, v_rtl=4.0, dynamic_margin=1.5)
# la 1000 m de baza: energia intoarcerii = 1.5*(120+32)*(250 s)/3600 ~ 15.8 Wh
# => RTL trebuie sa se declanseze cu mult inainte de pragul static de 5%
b2.update(1.0, speed=0.0, t=0.0, dist_home=1000.0)
soc_when = None
t2 = 0.0
while b2.state == "NORMAL" and t2 < 4000:
    t2 += 1.0
    b2.update(1.0, speed=0.0, t=t2, dist_home=1000.0)
    if b2.state == "RTL":
        soc_when = b2.soc()
check("baterie: prag RTL dinamic dupa distanta",
      soc_when is not None and soc_when > 0.20, f"soc_rtl_din={soc_when}")
check("baterie: endurance scade cu viteza",
      BatteryModel().endurance_s(8.0) < BatteryModel().endurance_s(0.0))

# ============================= ObstacleGuard ============================
print("--- guard.ObstacleGuard ---")
g = ObstacleGuard(d_stop=0.6, d_slow=1.5, sector_deg=70)
# scanare sintetica: 360 raze, obstacol la 0.4 m drept in fata (unghi 0)
n = 360
amin, ainc = -math.pi, 2 * math.pi / n
ranges = [10.0] * n
ranges[n // 2] = 0.4                  # unghiul ~0 (fata)
d = g.min_front(ranges, amin, ainc)
check("garda: gaseste minimul frontal", abs(d - 0.4) < 1e-9)
v, w, info = g.filter_cmd(0.8, 0.3)
check("garda: blocheaza inaintarea sub d_stop", v == 0.0 and info["blocked"])
check("garda: rotatia ramane permisa", w == 0.3)
v, w, _ = g.filter_cmd(-0.5, 0.0)
check("garda: mersul inapoi ramane permis", v == -0.5)
# obstacol doar in spate => nu afecteaza
ranges = [10.0] * n
ranges[0] = 0.3                       # unghi -pi (spate)
g2 = ObstacleGuard(d_stop=0.6, d_slow=1.5, sector_deg=70)
g2.min_front(ranges, amin, ainc)
v, _, info = g2.filter_cmd(0.8, 0.0)
check("garda: obstacolul din spate nu blocheaza fata", v == 0.8
      and not info["blocked"])
# franare progresiva la 1.0 m: scale = (1.0-0.6)/(1.5-0.6) = 0.444
g3 = ObstacleGuard(d_stop=0.6, d_slow=1.5, sector_deg=70)
v, _, info = g3.filter_cmd(0.9, 0.0, dmin=1.0)
check("garda: franare progresiva in zona d_slow",
      abs(v - 0.9 * (0.4 / 0.9)) < 1e-9, f"v={v}")
# histerezis: blocat la 0.55, NU elibereaza la 0.65 (<0.75), DA la 0.8
g4 = ObstacleGuard(d_stop=0.6, d_slow=1.5, release_factor=1.25)
g4.filter_cmd(0.5, 0, dmin=0.55)
v, _, i1 = g4.filter_cmd(0.5, 0, dmin=0.65)
check("garda: histerezis tine blocat sub prag*factor",
      v == 0.0 and i1["blocked"])
v, _, i2 = g4.filter_cmd(0.5, 0, dmin=0.80)
exp = 0.5 * (0.80 - 0.6) / (1.5 - 0.6)   # eliberat, dar inca in zona d_slow
check("garda: histerezis elibereaza peste prag*factor",
      not i2["blocked"] and abs(v - exp) < 1e-9, f"v={v} exp={exp:.4f}")
# scanare 0..2*pi (stil gz) cu obstacol frontal la unghiul 0
g5 = ObstacleGuard(sector_deg=70)
ranges = [10.0] * n
ranges[0] = 0.5                       # unghi 0 in scanare 0..2pi
d = g5.min_front(ranges, 0.0, 2 * math.pi / n)
check("garda: accepta si scanari 0..2*pi", abs(d - 0.5) < 1e-9)
# inf/nan ignorate
g6 = ObstacleGuard()
d = g6.min_front([float("inf"), float("nan"), 0.0], -0.1, 0.1)
check("garda: inf/nan/0 ignorate => fara obstacol",
      math.isinf(d) and g6.filter_cmd(1.0, 0)[0] == 1.0)

# ========================== DeadReckoningPredictor ======================
print("--- predictor.DeadReckoningPredictor ---")
# adevar-teren: uniciclu condus de o secventa de comenzi cunoscute
random.seed(11)
cmds = []
t = 0.0
for k in range(120):                   # 12 s de comenzi la 10 Hz
    v = 0.8 + 0.2 * math.sin(k / 7)
    w = 0.6 * math.sin(k / 9)
    cmds.append((t, v, w))
    t += 0.1
LAT = 0.30                             # latenta legaturii [s]


def true_pose(t_q):
    x = y = th = 0.0
    for i, (tc, v, w) in enumerate(cmds):
        t_next = cmds[i + 1][0] if i + 1 < len(cmds) else t_q
        if tc >= t_q:
            break
        x, y, th = unicycle_step(x, y, th, v, w, min(t_next, t_q) - tc)
    return x, y, th


pr = DeadReckoningPredictor()
err_pred, err_naiv = [], []
for (tc, v, w) in cmds:
    pr.on_cmd_sent(tc, v, w)
    t_now = tc + 0.05
    if t_now - LAT >= 0:               # poza care SOSEsTE acum a fost emisa
        tp = t_now - LAT               # la t_now - LAT
        xp, yp, thp = true_pose(tp)
        pr.on_pose(tp, xp, yp, thp)
        xt, yt, _ = true_pose(t_now)
        res = pr.predict(t_now)
        xq, yq, _, age, _ = res
        err_pred.append(math.hypot(xq - xt, yq - yt))
        err_naiv.append(math.hypot(xp - xt, yp - yt))
mp, mn = sum(err_pred) / len(err_pred), sum(err_naiv) / len(err_naiv)
check("predictor: eroarea predictiei << eroarea pozei intarziate",
      mp < 0.25 * mn, f"pred={mp:.4f} m vs naiv={mn:.4f} m")
check("predictor: varsta pozei raportata ~ latenta",
      abs(age - LAT) < 0.06, f"age={age:.3f}")
res0 = DeadReckoningPredictor().predict(1.0)
check("predictor: fara poza => None", res0 is None)
pe = DeadReckoningPredictor(max_extrapolation_s=0.5)
pe.on_pose(0.0, 0, 0, 0)
pe.on_cmd_sent(0.0, 1.0, 0.0)
x_, y_, th_, age_, ex_ = pe.predict(3.0)
check("predictor: extrapolarea e plafonata",
      ex_ == 0.5 and abs(x_ - 0.5) < 1e-9, f"x={x_} extrap={ex_}")
# pasul exact pe arc: v=1, w=pi/2, dt=1 => sfert de cerc de raza 2/pi
x_, y_, th_ = unicycle_step(0, 0, 0, 1.0, math.pi / 2, 1.0)
check("predictor: integrarea exacta pe arc",
      abs(x_ - 2 / math.pi) < 1e-12 and abs(y_ - 2 / math.pi) < 1e-12
      and abs(th_ - math.pi / 2) < 1e-12)

# ================================ bilant ================================
print(f"\n=== {N_OK}/{N_OK + N_FAIL} verificari trecute ===")
sys.exit(0 if N_FAIL == 0 else 1)
