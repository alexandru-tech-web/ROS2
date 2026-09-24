#!/usr/bin/env python3
"""cbf_core.py -- filtrul de siguranta CBF-QP, in timp discret. Fara ROS.

NOTATIE (ASCII)
  stare    x = (px, py, theta, v)
  intrare  u = (v_cmd, omega)
  punct de control  p_c = p + l * (cos theta, sin theta)
  h(x) = ||p_c - o_hat|| - r_eff,   r_eff = r + d_fr(v) + marja_extra + delta_DT
         delta_DT = (v_o dt_r + eps_lin)/gamma, rezerva de fezabilitate (ERATA 5, Lema 3)
         dt_r = dt_max_admis (S4.1, implicit), NU dt nominal si NU maximul observat
         d_fr(v) = v^2 / (2 a_max) + v tau_act          (rover_dyn.d_fr)
         marja_extra e PARAMETRU: 0 in S2; v_o * AoI in S2b.

CONDITIA DT-CBF:  h_{k+1} >= (1 - gamma) h_k, gamma in (0, 1].
Liniarizata pe pas:  h_k + dt * (dh/dx . f(x_k, u)) >= (1 - gamma) h_k,
cu f(x, u) = (v cos th, v sin th, omega, (v_cmd - v)/dt). Ultimul termen e
modelul cu clamp din nota M0; in interiorul cutiei |v_cmd - v| <= a_max dt
clamp-ul nu actioneaza, deci acolo f e exact liniar in u.

  dh/dp     = n = (p_c - o_hat) / ||p_c - o_hat||
  dh/dtheta = n . (l * (-sin th, cos th))
  dh/dv     = -d_fr'(v) = -(v / a_max + tau_act)

QP (v0.2, 17.09):
     min (u - u_op)^T W (u - u_op),  W = diag(1/v_max^2, 1/omega_max^2)
     s.t.  h_lin,k+1 >= (1 - gamma) h_k + eps_lin      (CBF, liniara in u)
           |v_cmd| <= v_max,  |omega| <= omega_max,  |v_cmd - v_k| <= a_max dt
W normalizeaza intrarile la [-1, 1]: fara ea, o unitate de omega si o unitate de
v_cmd costau la fel, iar franarea (coeficient ~ -0.2) batea intotdeauna virajul
(coeficient ~ dt*l ~ 0.01) -- blocajul din S2.

LEMA 2 (marginea de liniarizare). h(x) = ||p_c - o|| - r_eff. Distanta d(p) =
||p - o|| are Hessiana cu norma <= 1/d (curbura sferei de raza d). Pe un pas,
p_c se muta cu cel mult (v_max + l*omega_max)*dt =: s. Restul Taylor de ordin 2
al distantei este atunci <= s^2 / (2 d) <= s^2 / (2 r) cat timp d >= r. Deci
    h_real,k+1 >= h_lin,k+1 - eps_lin,   eps_lin = s^2 / (2 r).
Cerand h_lin,k+1 >= (1-gamma) h_k + eps_lin obtinem h_real,k+1 >= (1-gamma) h_k
pe modelul REAL, nu doar pe liniarizare. eps_lin se calculeaza din Params si
se scrie in info la fiecare pas.
Solver: OSQP direct (P, q, A, l, u), NU cvxpy in bucla -- viteza conteaza la
20 Hz. Infezabil -> u = (0, 0), n_inf += 1.

Liniarizarea e pe modelul cu clamp; VEHICULUL real (rover_dyn) are tau_act si
integreaza pozitia cu v_{k+1}. Diferenta e exact ce masoara selftestul (c):
invariantul pe modelul REAL, cu cel mai mic reziduu raportat, nu presupus.

S4.1 (24.09.2026) -- REZERVA PE PLAFONUL ADMIS. Bugetul de varsta si rezerva de
fezabilitate se iau din dt_max_admis (= 3 dt nominal = 0.150 s), CONSTANT, nu din
maximul observat pana la pasul curent. Motivul, masurat: cu mod_dt="max" bugetul e
monoton crescator, deci la PRIMUL pas mai lung decat toate cele dinainte (un
"pas-record") compensarea marjei ramane in urma cu cel mult v_o*(dt_nou - dt_max_vazut)
si conditia (ii) a certificatului poate fi incalcata cu atat. S-a intamplat in S4 lot 1
in 3 din 60 de rulari A2 (RAPORT_S4_LOT1 sec. 1b si 1c). Pe plafon, compensarea acopera
prin constructie orice pas ADMIS, fiindca un pas peste plafon nu mai e pas de control:
acolo filtrul intoarce u = (0, 0) si numara n_dt (neschimbat). Pretul e o marja mai mare,
marginita si stiuta dinainte: v_o * dt_max_admis, adica 7.5 cm la v_o = 0.5 si 22.5 cm la
v_o = 1.5. mod_dt="max" si "pas" raman in cod, ca sa se poata reproduce comportamentul
de dinainte (S4 lot 1); implicitul e "plafon".

Rulare: python3 cbf_core.py --selftest
"""
import math
import os
import random
import sys

import numpy as np
import osqp
import scipy.sparse as sp

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)
import rover_dyn                                             # noqa: E402

GAMMA_IMPLICIT = 0.3
INF = 1e20


def h_val(x, o_hat, params, marja_extra=0.0):
    """h(x) si vectorul unitar n. x = Stare sau (px, py, theta, v)."""
    px, py, th, v = _desfa(x)
    cx, cy = px + params.l * math.cos(th), py + params.l * math.sin(th)
    dx, dy = cx - o_hat[0], cy - o_hat[1]
    d = math.hypot(dx, dy)
    r_eff = params.r + rover_dyn.d_fr(v, params.a_max, params.tau_act) + marja_extra
    n = (dx / d, dy / d) if d > 1e-12 else (1.0, 0.0)
    return d - r_eff, n, r_eff


def marja_inchidere(v, v_o, a_max, A_ef):
    """ERATA 4 (17.09): r_eff = r + (v + v_o)^2/(2a) + v_o*A_ef, cu VITEZA DE INCHIDERE
    v + v_o (roverul franeaza, pericolul vine cu v_o spre el; ipoteza v_o < v_max).
    h_val aduna deja d_fr(v) = v^2/(2a), deci marja_extra = restul:
        (v + v_o)^2/(2a) - v^2/(2a) + v_o*A_ef = v_o*v/a + v_o^2/(2a) + v_o*A_ef.
    Fata de ERATA 3 (v_o*(A_ef + v/a)) difera cu constanta v_o^2/(2a): la retragere
    (v < 0) ERATA 3 dadea marja NEGATIVA (S3: V=2, d_min 0.9996 pe ideal), patratul nu.
    d r_eff / dv = (v + v_o)/a, acelasi ca la ERATA 3; la v_o = 0 se reduce la v^2/(2a)."""
    return (v + v_o) ** 2 / (2.0 * a_max) - v ** 2 / (2.0 * a_max) + v_o * A_ef


def _desfa(x):
    if hasattr(x, "x"):
        return x.x, x.y, x.theta, x.v
    return float(x[0]), float(x[1]), float(x[2]), float(x[3])


class SafetyFilter(object):
    def __init__(self, params, gamma=None):
        self.p = params
        self.gamma = GAMMA_IMPLICIT if gamma is None else float(gamma)
        self.n_inf = 0
        self.n_ws = 0            # stari sigure la informatie prea veche (A2, ERATA 2)
        p = params
        self.W = np.diag([1.0 / p.v_max ** 2, 1.0 / p.omega_max ** 2])
        self._P = sp.csc_matrix(2.0 * self.W)
        s_max = (p.v_max + p.l * p.omega_max) * p.dt
        self.eps_lin = s_max ** 2 / (2.0 * p.r)              # Lema 2
        # V0.1: pe hardware pasul REAL dt_k = t_k - t_{k-1} nu e dt nominal (tick 52-56 ms sub grafic incarcat).
        # Varsta informatiei creste cu dt_k, deci bugetul din Lema 3 se ia din dt_k (marginit la [0.5, 3] x dt nominal).
        self.dt_ef = p.dt
        self.n_dt_marginit = 0
        self.dt_max = p.dt
        # mod_dt: "pas" = eps_lin, delta_DT si bugetul de varsta din dt_k al pasului (V0.1 literal; masurat: r_eff se
        # misca cu v_o*ddt/gamma ~ 8 mm intre pasi si certificatul (ii) pica mai rau); "max" = bugetul de varsta din
        # dt maxim vazut pana acum (monoton, dar in urma la un pas-record: S4 lot 1, 3 incalcari (ii));
        # "plafon" (S4.1, implicit) = bugetul si rezerva din dt_max_admis, CONSTANT -- acopera prin constructie
        # orice pas admis, fiindca un pas peste plafon devine stare sigura si nu mai e pas de control.
        self.mod_dt = "plafon"                # implicit dupa S4.1 (24.09.2026); "max" / "pas" raman reproductibile
        # P0-HIL: peste dt_max_admis (implicit 3 x dt = 150 ms) pasul nu mai e un pas de control (tick pierdut,
        # proces blocat): filtrul NU intinde marginile, ci intoarce starea sigura u=(0,0) si numara n_dt
        # (separat de n_ws, care e pentru informatie prea veche pe canal). Pasul urmator se judeca normal.
        self.dt_max_admis = 3.0 * p.dt
        self.n_dt = 0

    @property
    def dt_rezerva(self):
        """Pasul pe care se DIMENSIONEAZA rezerva: plafonul admis (S4.1) sau dt nominal (modurile vechi).

        E proprietate, nu camp, fiindca rover_node suprascrie dt_max_admis DUPA constructie
        (parametru ROS): o rezerva calculata o singura data in __init__ ar ramane in urma.
        """
        return self.dt_max_admis if self.mod_dt == "plafon" else self.p.dt

    @property
    def delta_DT(self):
        """ERATA 5: rezerva de fezabilitate (Lema 3). Intre doua pachete h_A scade cu v_o*dt_r
        indiferent de u; QP-ul ramane fezabil doar daca h_A >= (v_o dt_r + eps_lin)/gamma.
        Un CBF cu gamma-decay lasa h -> 0 (S3.1: h ~ 0.005, apoi infezabil), deci pragul intra in
        r_eff: bariera h = ||p_c - o_hat|| - r_eff atinge 0 exact cand distanta reala ajunge la
        r + delta_DT, iar de acolo QP-ul are inca loc de un pas.
        S4.1: dt_r = dt_max_admis, deci rezerva acopera si cel mai lung pas ADMIS, nu doar unul nominal."""
        return (self.p.v_o_max * self.dt_rezerva + self.eps_lin) / self.gamma

    def _dt_efectiv(self, dt_masurat):
        p = self.p
        if dt_masurat is not None:
            lo, hi = 0.5 * p.dt, 3.0 * p.dt
            d = min(max(float(dt_masurat), lo), hi)
            if d != dt_masurat:
                self.n_dt_marginit += 1
            self.dt_max = max(self.dt_max, d)          # doar raportare (dt_max_vazut) in modul "plafon"
        if self.mod_dt == "plafon":
            # constant, independent de ce s-a observat: bugetul de varsta si rezerva acopera orice pas admis
            return self.dt_max_admis, self.eps_lin, self.delta_DT
        if dt_masurat is None:
            return p.dt, self.eps_lin, self.delta_DT
        if self.mod_dt == "max":
            return self.dt_max, self.eps_lin, self.delta_DT
        s_max = (p.v_max + p.l * p.omega_max) * d
        eps = s_max ** 2 / (2.0 * p.r)
        return d, eps, (p.v_o_max * d + eps) / self.gamma

    def constrangere_cbf(self, x, o_hat, marja_extra=0.0, r_eff_fix=None, dmarja_dt=0.0,
                         dmarja_dv=0.0, dt_masurat=None):
        """(a_v, a_w, b) astfel incat a_v v_cmd + a_w omega >= b este DT-CBF liniarizata.
        r_eff_fix (A3): r_eff e o CONSTANTA, deci dh/dv = 0 -- fara termenul d_fr'(v).
        dmarja_dt (A2): CBF VARIABIL IN TIMP, M0 sec. 5. Intre doua pachete varsta A creste
        cu dt pe pas, deci marja v_o*A creste cu v_o*dt si h_A SCADE cu atat, indiferent
        de u. Fara termenul asta QP-ul e optimist cu exact v_o*dt pe fiecare pas fara
        pachet -- masurat: 49 incalcari (ii) cu reziduu -0.024 = -v_o*dt la S2b."""
        px, py, th, v = _desfa(x)
        p = self.p
        dt_ef, eps_ef, delta_ef = self._dt_efectiv(dt_masurat)
        self.dt_ef, self.eps_ef, self.delta_ef = dt_ef, eps_ef, delta_ef
        if r_eff_fix is None:
            h, n, self.r_eff_ultim = h_val(x, o_hat, p, marja_extra + delta_ef)
            # ERATA 4: r_eff = r + (v + v_o)^2/(2a) + v_o*A_ef, deci
            # d r_eff / dv = (v + v_o)/a = v/a + v_o/a. Al doilea termen vine prin dmarja_dv.
            dfr = v / p.a_max + dmarja_dv
        else:
            d_, n, _ = h_val(x, o_hat, p, 0.0)
            self.r_eff_ultim = r_eff_fix + delta_ef
            h = d_ + p.r + rover_dyn.d_fr(v, p.a_max) - self.r_eff_ultim   # ||p_c-o|| - r_eff_fix
            dfr = 0.0
        c_pos = n[0] * v * math.cos(th) + n[1] * v * math.sin(th)
        a_w = p.dt * (n[0] * (-p.l * math.sin(th)) + n[1] * (p.l * math.cos(th)))
        a_v = -dfr
        # h + dt*c_pos + a_w*omega - dfr*(v_cmd - v) - dmarja_dt*dt >= (1-gamma) h + eps_lin
        # termenii cinematici (c_pos, a_w, cutia) raman pe dt nominal: plantul face un pas F de dt nominal;
        # varsta informatiei si marginile (eps_lin, delta_DT prin r_eff) sunt pe dt efectiv
        b = -self.gamma * h - p.dt * c_pos - dfr * v + eps_ef + dmarja_dt * dt_ef
        return a_v, a_w, b, h

    def apply(self, x, u_op, o_hat, marja_extra=0.0, r_eff_fix=None, dmarja_dt=0.0,
              dmarja_dv=0.0, dt_masurat=None):
        """(u, info). info = {h, h_next_pred, feasible, obj, kkt_res, eps_lin, marja_extra}."""
        p = self.p
        if dt_masurat is not None and float(dt_masurat) > self.dt_max_admis:
            self.n_dt += 1
            self.dt_max = max(self.dt_max, float(dt_masurat))
            return (0.0, 0.0), {"h": None, "h_next_pred": None, "feasible": None, "obj": None, "kkt_res": None,
                                "eps_lin": None, "marja_extra": marja_extra, "delta_DT": None,
                                "dt_ef": float(dt_masurat), "r_eff": None, "dt_depasit": True}
        px, py, th, v = _desfa(x)
        a_v, a_w, b, h = self.constrangere_cbf(x, o_hat, marja_extra, r_eff_fix, dmarja_dt, dmarja_dv, dt_masurat)

        A = sp.csc_matrix(np.array([[a_v, a_w],
                                    [1.0, 0.0],
                                    [0.0, 1.0],
                                    [1.0, 0.0]]))
        lo = np.array([b, -p.v_max, -p.omega_max, v - p.a_max * p.dt])
        hi = np.array([INF, p.v_max, p.omega_max, v + p.a_max * p.dt])
        q = -2.0 * self.W.dot(np.array([float(u_op[0]), float(u_op[1])]))

        m = osqp.OSQP()
        m.setup(P=self._P, q=q, A=A, l=lo, u=hi, verbose=False,
                eps_abs=1e-9, eps_rel=1e-9, polish=False, max_iter=50000)
        r = m.solve()
        st = r.info.status.lower()
        feasible = st.startswith("solved")
        if not feasible:
            self.n_inf += 1
            u = (0.0, 0.0)
            obj, kkt = None, None
        else:
            u = (float(r.x[0]), float(r.x[1]))
            d_ = np.array([u[0] - u_op[0], u[1] - u_op[1]])
            obj = float(d_.dot(self.W).dot(d_))
            kkt = float(max(abs(r.info.prim_res), abs(r.info.dual_res)))
        # Constrangerea e a_v v + a_w w >= b  <=>  h_pred >= (1-gamma) h; deci
        # h_pred = (1-gamma) h + (a_v v + a_w w - b) e ce prezice liniarizarea.
        h_next = ((1.0 - self.gamma) * h + self.eps_ef + (a_v * u[0] + a_w * u[1] - b)
                  if feasible else None)
        return u, {"h": h, "h_next_pred": h_next, "feasible": feasible,
                   "obj": obj, "kkt_res": kkt, "eps_lin": self.eps_ef,
                   "marja_extra": marja_extra, "delta_DT": self.delta_ef, "dt_ef": self.dt_ef,
                   "r_eff": self.r_eff_ultim}


def ca_safety_filter(sf, marja_extra=0.0, o_hat=None, marja_fn=None, r_eff_fix=None,
                     dmarja_dt=0.0):
    """Adaptor la semnatura din episode.py: (st, cmd, params, ctx) -> (u, info, infez).
    ctx (de la episode) = {"o_hat": ..., "A_haz": ...} cand exista pericol pe canal.
    marja_fn(ctx, params) -> marja_extra, pentru bratele A2/A3; altfel marja_extra fix."""
    def f(st, cmd, params, ctx=None):
        ctx = ctx or {}
        o = ctx.get("o_hat") if ctx.get("o_hat") is not None else (o_hat if o_hat is not None else params.obst)
        m = marja_fn(ctx, params) if marja_fn else marja_extra
        u, info = sf.apply(st, cmd, o, m, r_eff_fix, dmarja_dt)
        return u, info, (info["feasible"] is False)
    return f


# --- selftest ------------------------------------------------------------
def _ruleaza(params, gamma, seed=1, react=False, tau_act=0.0):
    import channel_core
    import episode
    import models
    random.seed(seed)
    sf = SafetyFilter(params, gamma)
    m, tr = episode.run_episode(params, models.Unicycle(tau_act), channel_core.IdealChannel(params),
                                safety_filter=ca_safety_filter(sf), react=react)
    m["n_inf"] = sf.n_inf
    return m, tr, sf


def _fezabilitate_la_blocaj(tr, params, sf):
    """Cerut de DoD daca (a) pica din nou: la primul pas cu v<0.05 si v_op>0.2,
    lista comenzilor fezabile pe o grila si costul lor. Raport, nu reparatie."""
    for k, q in enumerate(tr):
        if q["v"] < 0.05 and q["v_op"] > 0.2 and k > 0:
            pre = tr[k - 1]
            x = rover_dyn.Stare(x=pre["x"], y=pre["y"], theta=pre["theta"], v=pre["v"])
            u_op = (q["v_op"], q["omega_op"])
            a_v, a_w, b, h = sf.constrangere_cbf(x, params.obst, 0.0)
            fez = []
            for i in range(21):
                vc = x.v - params.a_max * params.dt + 2 * params.a_max * params.dt * i / 20.0
                for jj in range(21):
                    w = -params.omega_max + 2 * params.omega_max * jj / 20.0
                    if a_v * vc + a_w * w >= b and abs(vc) <= params.v_max:
                        dd = np.array([vc - u_op[0], w - u_op[1]])
                        fez.append((float(dd.dot(sf.W).dot(dd)), vc, w))
            fez.sort()
            print("  BLOCAJ la pasul %d, t=%.2f: h=%.4f v=%.3f u_op=(%.2f,%.2f); a_v=%.3f a_w=%.4f b=%.4f"
                  % (k, q["t"], h, x.v, u_op[0], u_op[1], a_v, a_w, b))
            print("    comenzi fezabile pe grila 21x21: %d; cele mai ieftine 3 (cost, v_cmd, omega):"
                  % len(fez))
            for c, vc, w in fez[:3]:
                print("      %.4f  (%.4f, %.4f)" % (c, vc, w))
            return
    print("  (niciun pas de blocaj gasit)")


def _selftest(dir_iesire=None):
    from c6_params import Params
    import channel_core
    import episode
    import io_core
    import models
    P = Params()
    rez = []

    m0, _ = episode.run_episode(P, models.Unicycle(), channel_core.IdealChannel(P), react=False)
    m, tr, sf = _ruleaza(P, GAMMA_IMPLICIT)
    print("  eps_lin = %.3e  (Lema 2, din Params)" % sf.eps_lin)

    ok_a = (m["V"] == 0 and m["n_inf"] == 0 and m["T_G"] is not None)
    rez.append(("a", "PASS" if ok_a else "FAIL",
                "V=%d n_inf=%d T_G=%s B=%.3f (fara filtru, orb: T_G=%s V=%d)"
                % (m["V"], m["n_inf"], m["T_G"], m["B"], m0["T_G"], m0["V"])))
    rez.append(("b", "PASS" if (m["J_int"] > 0 and m["d_min"] >= P.r - 0.01) else "FAIL",
                "J_int=%.4f d_min=%.4f (fara filtru: %.3f)" % (m["J_int"], m["d_min"], m0["d_min"])))

    hs = [q["h"] for q in tr]
    rz = [hs[k + 1] - (1.0 - GAMMA_IMPLICIT) * hs[k] for k in range(len(hs) - 1)]
    rmin = min(rz) if rz else 0.0
    rez.append(("c", "PASS" if rmin >= -1e-9 else "FAIL",
                "%d pasi, reziduu minim %.3e (prag -1e-9)" % (len(rz), rmin)))

    rng = random.Random(7)
    sf2 = SafetyFilter(P, GAMMA_IMPLICIT)
    worst, n_cmp, ok_d = -1.0, 0, True
    for _ in range(50):
        x = rover_dyn.Stare(x=rng.uniform(2.0, 6.0), y=rng.uniform(-1.5, 1.5),
                            theta=rng.uniform(-0.6, 0.6), v=rng.uniform(0.0, P.v_max))
        u_op = (rng.uniform(0.0, P.v_max), rng.uniform(-P.omega_max, P.omega_max))
        u, info = sf2.apply(x, u_op, P.obst, 0.0)
        if not info["feasible"]:
            continue
        a_v, a_w, b, _ = sf2.constrangere_cbf(x, P.obst, 0.0)
        best = float("inf")
        for i in range(41):
            vc = -P.v_max + 2 * P.v_max * i / 40.0
            if abs(vc - x.v) > P.a_max * P.dt + 1e-12:
                continue
            for jj in range(41):
                w = -P.omega_max + 2 * P.omega_max * jj / 40.0
                if a_v * vc + a_w * w < b - 1e-12:
                    continue
                dd = np.array([vc - u_op[0], w - u_op[1]])
                best = min(best, float(dd.dot(sf2.W).dot(dd)))
        if best < float("inf"):
            n_cmp += 1
            worst = max(worst, info["obj"] - best)
            ok_d = ok_d and info["obj"] <= best + 1e-3
    rez.append(("d", "PASS" if ok_d else "FAIL",
                "%d stari, cost W, max(obj_osqp - obj_grila) = %.2e" % (n_cmp, worst)))

    _, tr2, _ = _ruleaza(P, GAMMA_IMPLICIT)
    h1, h2 = episode._hash_trace(tr), episode._hash_trace(tr2)
    rez.append(("e", "PASS" if h1 == h2 else "FAIL", "sha256 %s" % h1[:16]))

    m10, _, _ = _ruleaza(P, 1.0)
    rez.append(("f", "RAPORTAT", "J_int(1.0)=%.4f vs J_int(0.3)=%.4f; T_G: %s vs %s"
                % (m10["J_int"], m["J_int"], m10["T_G"], m["T_G"])))

    mg, _, _ = _ruleaza(P, GAMMA_IMPLICIT, tau_act=0.2)
    rez.append(("g", "RAPORTAT", "plant cu lag tau=0.2, filtru pe clamp: V=%d d_min=%.3f T_G=%s "
                "(asteptat V >> 0)" % (mg["V"], mg["d_min"], mg["T_G"])))

    mh, _, _ = _ruleaza(P, GAMMA_IMPLICIT, react=True)
    rez.append(("h", "RAPORTAT", "react=True (pe blocaj): V=%d T_G=%s B=%.3f n_reactii=%d"
                % (mh["V"], mh["T_G"], mh["B"], mh["n_reactii"])))

    # (i) P0-HIL: un pas masurat de 200 ms (> dt_max_admis = 3 dt = 150 ms) injectat la k=300 intr-o traversare
    # A2 pe canal ideal (bratul din brate.py, nemodificat) -> exact un pas in stare sigura (n_dt = 1), n_ws
    # neatins, nicio incalcare (i)/(ii) in certificat. Pasul e injectat prin ctx["dt_masurat"].
    import brate
    import certif_core
    random.seed(1)
    f_b, sf_i = brate.filtru_pentru("A2", P, None, 0.0)
    hz_i = episode.Hazard(P)
    k_inj = [0]

    def f_i(st, cmd, p, ctx=None):
        ctx = dict(ctx or {})
        k_inj[0] += 1
        ctx["dt_masurat"] = 0.200 if k_inj[0] == 300 else p.dt
        return f_b(st, cmd, p, ctx)
    mi, tri = episode.run_episode(P, models.Unicycle(), channel_core.IdealChannel(P), safety_filter=f_i, hazard=hz_i)
    poz = {q["t"]: (q["o_true_x"], q["o_true_y"]) for q in tri}
    ci = certif_core.certify(tri, P, lambda t: poz.get(t, hz_i.o_true(t)), sf_i.gamma)
    ok_i = (sf_i.n_dt == 1 and sf_i.n_ws == 0 and mi["V"] == 0 and ci["incalcari_i"] == 0 and ci["incalcari_ii"] == 0
            and sf_i.n_inf == 0)
    rez.append(("i", "PASS" if ok_i else "FAIL", "pas 200 ms injectat la k=300 (dt_max_admis=%.3f): n_dt=%d n_ws=%d n_inf=%d "
                "V=%d cert (i)=%d (ii)=%d" % (sf_i.dt_max_admis, sf_i.n_dt, sf_i.n_ws, sf_i.n_inf, mi["V"],
                                              ci["incalcari_i"], ci["incalcari_ii"])))

    # (j) S4.1: bugetul de varsta folosit la pasul k trebuie sa acopere imbatranirea de pe
    # intervalul [k, k+1]. La pasul k filtrul stie doar intervalele DEJA incheiate, deci in modul
    # "max" bugetul ramane in urma exact cand intervalul urmator e un record nou -- defectul masurat
    # in S4 lot 1 (3 rulari, RAPORT_S4_LOT1 sec. 1b). CONTROL NEGATIV pe acelasi obiect: modul vechi
    # TREBUIE sa arate lipsa, modul nou TREBUIE sa nu o arate pentru niciun pas admis.
    def _lipsa_buget(mod, pasi):
        sfj = SafetyFilter(P)
        sfj.mod_dt = mod
        bugete = [sfj._dt_efectiv(d_)[0] for d_ in pasi]
        return max([pasi[k + 1] - bugete[k] for k in range(len(pasi) - 1)]), sfj
    # un sir de tick-uri admise (toate <= dt_max_admis = 0.150 s), cu trei recorduri succesive
    pasi_j = [0.0500, 0.0505, 0.0500, 0.0530, 0.0520, 0.1490, 0.0500]
    lipsa_max, sf_m = _lipsa_buget("max", pasi_j)
    lipsa_plafon, sf_p = _lipsa_buget("plafon", pasi_j)
    # rezerva se recalculeaza daca dt_max_admis e suprascris dupa constructie (parametru ROS)
    sf_p2 = SafetyFilter(P)
    sf_p2.dt_max_admis = 0.300
    d_inainte = sf_p2.delta_DT
    sf_p2.mod_dt = "max"
    ok_j = (lipsa_max > 0.0 and lipsa_plafon <= 0.0
            and sf_p.delta_DT > sf_m.delta_DT
            and abs(d_inainte - (P.v_o_max * 0.300 + sf_p2.eps_lin) / sf_p2.gamma) < 1e-12
            and abs(sf_p2.delta_DT - (P.v_o_max * P.dt + sf_p2.eps_lin) / sf_p2.gamma) < 1e-12)
    rez.append(("j", "PASS" if ok_j else "FAIL",
                "buget de varsta pe %d tick-uri admise: lipsa max(mod 'max') = %+.4f s (defectul S4), "
                "lipsa max(mod 'plafon') = %+.4f s; delta_DT %.5f m (plafon) vs %.5f m (max)"
                % (len(pasi_j), lipsa_max, lipsa_plafon, sf_p.delta_DT, sf_m.delta_DT)))

    for c, v, cif in rez:
        print("  (%s) %-8s %s" % (c, v, cif))
    if not ok_a:
        _fezabilitate_la_blocaj(tr, P, sf)
    if dir_iesire:
        io_core.scrie(dir_iesire, m, tr, "s2_1_a_filtru")
        print("  urme scrise in %s" % dir_iesire)
    picate = [c for c, v, _ in rez if v == "FAIL" and c in ("a", "c", "d", "e", "i", "j")]
    if picate:
        print("SELFTEST cbf_core: FAIL pe obligatorii %s" % picate)
        return 1
    print("SELFTEST cbf_core OK.")
    return 0


if __name__ == "__main__":
    d = sys.argv[sys.argv.index("--outputs") + 1] if "--outputs" in sys.argv else None
    if "--selftest" in sys.argv:
        sys.exit(_selftest(d))
    print(__doc__.splitlines()[0]); print("Foloseste --selftest.")
