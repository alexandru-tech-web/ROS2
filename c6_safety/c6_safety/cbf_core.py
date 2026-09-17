#!/usr/bin/env python3
"""cbf_core.py -- filtrul de siguranta CBF-QP, in timp discret. Fara ROS.

NOTATIE (ASCII)
  stare    x = (px, py, theta, v)
  intrare  u = (v_cmd, omega)
  punct de control  p_c = p + l * (cos theta, sin theta)
  h(x) = ||p_c - o_hat|| - r_eff,   r_eff = r + d_fr(v) + marja_extra
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

QP:  min ||u - u_op||^2
     s.t.  a_v v_cmd + a_w omega >= b          (CBF, liniara in u)
           |v_cmd| <= v_max,  |omega| <= omega_max,  |v_cmd - v_k| <= a_max dt
Solver: OSQP direct (P, q, A, l, u), NU cvxpy in bucla -- viteza conteaza la
20 Hz. Infezabil -> u = (0, 0), n_inf += 1.

Liniarizarea e pe modelul cu clamp; VEHICULUL real (rover_dyn) are tau_act si
integreaza pozitia cu v_{k+1}. Diferenta e exact ce masoara selftestul (c):
invariantul pe modelul REAL, cu cel mai mic reziduu raportat, nu presupus.

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


def _desfa(x):
    if hasattr(x, "x"):
        return x.x, x.y, x.theta, x.v
    return float(x[0]), float(x[1]), float(x[2]), float(x[3])


class SafetyFilter(object):
    def __init__(self, params, gamma=None):
        self.p = params
        self.gamma = GAMMA_IMPLICIT if gamma is None else float(gamma)
        self.n_inf = 0
        self._P = sp.csc_matrix(2.0 * np.eye(2))

    def constrangere_cbf(self, x, o_hat, marja_extra=0.0):
        """(a_v, a_w, b) astfel incat a_v v_cmd + a_w omega >= b este DT-CBF liniarizata."""
        px, py, th, v = _desfa(x)
        p = self.p
        h, n, _ = h_val(x, o_hat, p, marja_extra)
        dfr = v / p.a_max + p.tau_act                        # d_fr'(v)
        c_pos = n[0] * v * math.cos(th) + n[1] * v * math.sin(th)
        a_w = p.dt * (n[0] * (-p.l * math.sin(th)) + n[1] * (p.l * math.cos(th)))
        a_v = -dfr
        # h + dt*c_pos + a_w*omega - dfr*(v_cmd - v) >= (1-gamma) h
        b = -self.gamma * h - p.dt * c_pos - dfr * v
        return a_v, a_w, b, h

    def apply(self, x, u_op, o_hat, marja_extra=0.0):
        """(u, info). info = {h, h_next_pred, feasible, obj, kkt_res}."""
        p = self.p
        px, py, th, v = _desfa(x)
        a_v, a_w, b, h = self.constrangere_cbf(x, o_hat, marja_extra)

        A = sp.csc_matrix(np.array([[a_v, a_w],
                                    [1.0, 0.0],
                                    [0.0, 1.0],
                                    [1.0, 0.0]]))
        lo = np.array([b, -p.v_max, -p.omega_max, v - p.a_max * p.dt])
        hi = np.array([INF, p.v_max, p.omega_max, v + p.a_max * p.dt])
        q = -2.0 * np.array([float(u_op[0]), float(u_op[1])])

        m = osqp.OSQP()
        m.setup(P=self._P, q=q, A=A, l=lo, u=hi, verbose=False,
                eps_abs=1e-7, eps_rel=1e-7, polish=True, max_iter=20000)
        r = m.solve()
        st = r.info.status.lower()
        feasible = st.startswith("solved")
        if not feasible:
            self.n_inf += 1
            u = (0.0, 0.0)
            obj, kkt = None, None
        else:
            u = (float(r.x[0]), float(r.x[1]))
            obj = float((u[0] - u_op[0]) ** 2 + (u[1] - u_op[1]) ** 2)
            kkt = float(max(abs(r.info.prim_res), abs(r.info.dual_res)))
        # Constrangerea e a_v v + a_w w >= b  <=>  h_pred >= (1-gamma) h; deci
        # h_pred = (1-gamma) h + (a_v v + a_w w - b) e ce prezice liniarizarea.
        h_next = (1.0 - self.gamma) * h + (a_v * u[0] + a_w * u[1] - b) if feasible else None
        return u, {"h": h, "h_next_pred": h_next, "feasible": feasible,
                   "obj": obj, "kkt_res": kkt}


def ca_safety_filter(sf, marja_extra=0.0, o_hat=None):
    """Adaptor la semnatura din episode.py: (st, cmd, params) -> (cmd, info_dict, infez)."""
    def f(st, cmd, params):
        o = o_hat if o_hat is not None else params.obst
        u, info = sf.apply(st, cmd, o, marja_extra)
        return u, info, (not info["feasible"])
    return f


# --- selftest ------------------------------------------------------------
def _ruleaza(params, gamma, seed=1):
    import channel_core
    import episode
    import models
    random.seed(seed)
    sf = SafetyFilter(params, gamma)
    m, tr = episode.run_episode(params, models.Unicycle(), channel_core.IdealChannel(params),
                                safety_filter=ca_safety_filter(sf))
    m["n_inf"] = sf.n_inf
    return m, tr, sf


def _selftest(dir_iesire=None):
    """Ruleaza TOATE cazurile si raporteaza tabelul; iese 1 daca pica unul obligatoriu.
    Un selftest care se opreste la prima aserziune ascunde restul diagnosticului."""
    from c6_params import Params
    import channel_core
    import episode
    import io_core
    import models
    P = Params()
    rez = []          # (caz, verdict, cifre)

    m0, _ = episode.run_episode(P, models.Unicycle(), channel_core.IdealChannel(P))
    m, tr, sf = _ruleaza(P, GAMMA_IMPLICIT)

    # (a) V = 0, n_inf = 0, T_G finit
    ok = (m["V"] == 0 and m["n_inf"] == 0 and m["T_G"] is not None)
    rez.append(("a", "PASS" if ok else "FAIL",
                "V=%d n_inf=%d T_G=%s (fara filtru: T_G=%.2f) B=%.3f"
                % (m["V"], m["n_inf"], m["T_G"], m0["T_G"], m["B"])))

    # (b) a intervenit si a tinut distanta
    ok = (m["J_int"] > 0 and m["d_min"] >= P.r - 0.01)
    rez.append(("b", "PASS" if ok else "FAIL",
                "J_int=%.4f d_min=%.4f (fara filtru: %.3f)" % (m["J_int"], m["d_min"], m0["d_min"])))

    # (c) invariant pe modelul real
    hs = [q["h"] for q in tr]
    rz = [hs[k + 1] - (1.0 - GAMMA_IMPLICIT) * hs[k] for k in range(len(hs) - 1)]
    rmin = min(rz)
    rez.append(("c", "PASS" if rmin >= -1e-6 else "FAIL",
                "%d pasi, reziduu minim %.3e" % (len(rz), rmin)))

    # (d) optimalitate vs grila
    rng = random.Random(7)
    sf2 = SafetyFilter(P, GAMMA_IMPLICIT)
    worst, n_cmp, ok = -1.0, 0, True
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
                best = min(best, (vc - u_op[0]) ** 2 + (w - u_op[1]) ** 2)
        if best < float("inf"):
            n_cmp += 1
            worst = max(worst, info["obj"] - best)
            ok = ok and info["obj"] <= best + 1e-3
    rez.append(("d", "PASS" if ok else "FAIL",
                "%d stari comparate, max(obj_osqp - obj_grila) = %.2e" % (n_cmp, worst)))

    # (e) determinism
    _, tr2, _ = _ruleaza(P, GAMMA_IMPLICIT)
    h1, h2 = episode._hash_trace(tr), episode._hash_trace(tr2)
    rez.append(("e", "PASS" if h1 == h2 else "FAIL", "sha256 %s" % h1[:16]))

    # (f) gamma 1.0 vs 0.3, observatie
    m10, _, _ = _ruleaza(P, 1.0)
    rez.append(("f", "RAPORTAT", "J_int(1.0)=%.4f vs J_int(0.3)=%.4f; T_G(1.0)=%s"
                % (m10["J_int"], m["J_int"], m10["T_G"])))

    for c, v, cif in rez:
        print("  (%s) %-8s %s" % (c, v, cif))
    if dir_iesire:
        io_core.scrie(dir_iesire, m, tr, "s2a_filtru")
        print("  urme scrise in %s" % dir_iesire)
    picate = [c for c, v, _ in rez if v == "FAIL" and c in ("a", "c", "d", "e")]
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
