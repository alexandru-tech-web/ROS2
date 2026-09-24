#!/usr/bin/env python3
"""test_s5.py -- testele unitatii S5 (bratele A4, A5 si scenariul schimba_directia), SCRISE INAINTE DE COD.

Ordinea e deliberata: acest fisier se comite INAINTE de implementare si, in acel moment, t1-t6 PICA.
Un test scris dupa cod ajunge sa descrie ce face codul; unul scris inainte descrie ce trebuie sa faca.

  t1  A4: marja = |v|*mean(A) + v_max*k_sigma*std(A) pe fereastra de 30 de RAPOARTE (serii sintetice de A).
  t2  A5: pe pericol cu viteza constanta, eroarea de predictie e 0 (pana la epsilon numeric).
  t3  A5: pe schimbare de directie, eroarea de predictie MASURATA, comparata cu marginea Lemei 1 (v_o*A)
      si cu marginea triunghiului (2*v_o*A). Asta e testul care arata de ce A2 ramane necesar.
  t4  certificatul pe A4/A5: (ii) se verifica pe marja BRATULUI (r_eff din urma == formula bratului),
      (i) pe h_true, pe obstacolul ADEVARAT, ca la toate bratele.
  t5  run_c6 --dry-run pe planul de 340: verifica bratele si scenariile din plan CONTRA codului;
      cu control negativ (un plan care cere un brat inexistent TREBUIE respins).
  t6  redare offline a 2 episoade per brat nou, din trace-uri existente, FARA ROS si fara netem.

Rulare: python3 test/test_s5.py            (cod 0 = toate trec)
        python3 test/test_s5.py --lista    (doar numele testelor)
DOAR stdlib + numpy/osqp din .venv_c6 (prin cbf_core).
"""
import math
import os
import statistics
import subprocess
import sys
import tempfile

_AICI = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.join(os.path.dirname(_AICI), "c6_safety")
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

RADACINA = os.path.abspath(os.path.join(_AICI, "..", "..", ".."))
TOOLS = os.path.join(RADACINA, "ORGANIZARE", "DOC", "BORD", "tools")
PLAN = os.path.join(RADACINA, "ORGANIZARE", "DOC", "CAIETE", "run_plan_c6.csv")
CAMPANIE = os.path.join(RADACINA, "DATE", "C6", "S4_2026-09-23_CANONIC", "runs")
VENV = os.path.join(RADACINA, ".venv_c6", "bin", "python")

EPS = 1e-9


def _ok(cond, mesaj):
    return ("PASS" if cond else "FAIL"), mesaj


# ---------------------------------------------------------------- t1
def t1_marja_a4():
    """marja = |v|*mean(A) + v_max*k_sigma*std(A), pe ULTIMELE `fereastra` rapoarte.

    std = abaterea standard de POPULATIE (pstdev): definita si pentru un singur raport (0.0),
    deci marja nu sare cand fereastra are un element. Fereastra numara RAPOARTE, nu pasi.
    """
    import brate
    from c6_params import Params
    P = Params()
    K = P.A4_k_sigma
    F = P.A4_fereastra

    # (a) serie constanta: std = 0, deci marja = |v| * A
    m = brate.MarjaIntarziere(fereastra=F, k_sigma=K, v_max=P.v_max)
    for _ in range(F):
        m.observa(0.1)
    astept = 0.7 * 0.1 + P.v_max * K * 0.0
    if abs(m.marja(0.7) - astept) > 1e-12:
        return _ok(False, "(a) serie constanta 0.1: marja %.9f, asteptat %.9f" % (m.marja(0.7), astept))

    # (b) serie alternanta: mean si pstdev calculate independent, aici
    serie = [0.1, 0.3] * (F // 2)
    m = brate.MarjaIntarziere(fereastra=F, k_sigma=K, v_max=P.v_max)
    for a in serie:
        m.observa(a)
    mu, sd = statistics.fmean(serie), statistics.pstdev(serie)
    astept = abs(-0.4) * mu + P.v_max * K * sd
    if abs(m.marja(-0.4) - astept) > 1e-12:
        return _ok(False, "(b) serie alternanta: marja %.9f, asteptat %.9f (mean %.4f std %.4f)"
                   % (m.marja(-0.4), astept, mu, sd))

    # (c) FEREASTRA: al 31-lea raport trebuie sa il scoata pe primul
    m = brate.MarjaIntarziere(fereastra=F, k_sigma=K, v_max=P.v_max)
    for _ in range(F):
        m.observa(5.0)                      # valori mari, care trebuie sa iasa din fereastra
    for _ in range(F):
        m.observa(0.2)
    if abs(m.marja(1.0) - (1.0 * 0.2)) > 1e-12:
        return _ok(False, "(c) fereastra de %d nu a uitat valorile vechi: marja %.9f, asteptat %.9f"
                   % (F, m.marja(1.0), 0.2))

    # (d) CONTROL NEGATIV: fara niciun raport nu exista statistica, deci marja nu are voie sa fie
    #     un numar inventat; se cere 0.0 explicit (si bratul nu porneste pe ea -- vezi A4 in brate.py)
    m = brate.MarjaIntarziere(fereastra=F, k_sigma=K, v_max=P.v_max)
    if m.n != 0 or m.marja(1.0) != 0.0:
        return _ok(False, "(d) fara rapoarte: n=%d marja=%s, asteptat 0 si 0.0" % (m.n, m.marja(1.0)))

    # (e) derivata dupa v, folosita de QP: d(marja)/dv = sign(v) * mean(A)
    m = brate.MarjaIntarziere(fereastra=F, k_sigma=K, v_max=P.v_max)
    for a in (0.1, 0.2, 0.3):
        m.observa(a)
    mu = statistics.fmean((0.1, 0.2, 0.3))
    if abs(m.dmarja_dv(0.5) - mu) > 1e-12 or abs(m.dmarja_dv(-0.5) + mu) > 1e-12:
        return _ok(False, "(e) dmarja_dv: %+.6f / %+.6f, asteptat %+.6f / %+.6f"
                   % (m.dmarja_dv(0.5), m.dmarja_dv(-0.5), mu, -mu))

    return _ok(True, "A4: marja = |v|*mean(A) + v_max*%.1f*std(A) pe %d rapoarte; fereastra uita, "
                     "fara rapoarte marja 0, dmarja_dv = sign(v)*mean" % (K, F))


# ---------------------------------------------------------------- t2
def t2_predictor_viteza_constanta():
    """A5 pe pericol cu viteza constanta: eroarea de predictie trebuie sa fie 0."""
    import brate
    v_o, dt_rap = 0.5, 0.2                        # pericol pe +y cu 0.5 m/s, raport la 5 Hz
    pr = brate.PredictorVitezaConstanta()
    o_de = lambda t: (6.0, -2.0 + v_o * t)        # noqa: E731  adevarul
    erori = []
    for k in range(1, 40):
        t_tx = k * dt_rap
        pr.observa(o_de(t_tx), t_tx)
        for A in (0.0, 0.05, 0.1, 0.35, 0.8):     # varste la care se cere predictia
            p = pr.prezice(o_de(t_tx), A)
            if p is None:
                continue
            ad = o_de(t_tx + A)
            erori.append(math.hypot(p[0] - ad[0], p[1] - ad[1]))
    if not erori:
        return _ok(False, "predictorul nu a produs nicio predictie")
    e = max(erori)
    return _ok(e <= 1e-9, "A5 pe viteza constanta: eroare max de predictie %.3e (prag 1e-9), "
                          "%d predictii" % (e, len(erori)))


# ---------------------------------------------------------------- t3
def t3_predictor_pe_schimbare_de_directie():
    """A5 la schimbarea de directie: se MASOARA eroarea si se compara cu marginile.

    Marginea Lemei 1 (ce acopera A2, fara niciun model al miscarii): ||o_true(t) - o_hat|| <= v_o*A.
    Marginea triunghiului pentru un predictor cu |v_hat| <= v_o: eroarea <= 2*v_o*A -- pentru ca
    predictia poate arata exact in sens opus fata de miscarea reala.
    Testul cere (1) sa treaca de 0, adica predictia chiar CEDEAZA aici, si (2) sa nu depaseasca
    marginea triunghiului. Raportul relatie fata de v_o*A e MASURAT si scris, nu presupus.
    """
    import brate
    import episode
    from c6_params import Params
    P = Params(scenariu="schimba_directia")
    hz = episode.Hazard(P)
    v_o, dt_rap = P.v_o_max, 1.0 / P.f_haz
    pr = brate.PredictorVitezaConstanta()
    raport = []
    for k in range(1, int(round(P.T_max / dt_rap))):
        t_tx = k * dt_rap
        o = hz.o_true(t_tx)
        pr.observa(o, t_tx)
        for A in (0.2, 0.5, 1.0):
            p = pr.prezice(o, A)
            if p is None:
                continue
            ad = hz.o_true(t_tx + A)
            e = math.hypot(p[0] - ad[0], p[1] - ad[1])
            raport.append((e, A, t_tx))
    if not raport:
        return _ok(False, "niciun raport de predictie")
    e_max, A_max_e, t_max_e = max(raport)
    peste_lema1 = [x for x in raport if x[0] > v_o * x[1] + 1e-9]
    peste_triunghi = [x for x in raport if x[0] > 2.0 * v_o * x[1] + 1e-9]
    ok = (e_max > 1e-6) and not peste_triunghi
    return _ok(ok, "A5 pe schimba_directia: eroare max %.4f m la A=%.2f s (t_tx=%.2f); "
                   "peste marginea Lemei 1 (v_o*A) in %d din %d puncte; peste 2*v_o*A in %d -- "
                   "deci predictia cedeaza, iar marja pe varsta (A2) ramane cea care acopera cazul"
               % (e_max, A_max_e, t_max_e, len(peste_lema1), len(raport), len(peste_triunghi)))


# ---------------------------------------------------------------- t4
def t4_certificat_pe_brate_noi():
    """(ii) pe marja BRATULUI (r_eff din urma == formula bratului), (i) pe h_true, ca la toate."""
    import brate
    import certif_core
    import channel_core
    import rover_dyn
    from c6_params import Params
    P = Params()
    detalii = []
    for b in ("A4", "A5"):
        canal = channel_core.DelayLossChannel(0.2, 0.05, 0.15, seed=3, T_hold=P.T_hold)
        m, tr, c = brate.ruleaza_brat(b, P, 3, canal=canal)
        # (i): incalcarile pe obstacolul ADEVARAT, recalculate independent din urma
        inc_i = 0
        hmin = float("inf")
        for q in tr:
            cx = q["x"] + P.l * math.cos(q["theta"])
            cy = q["y"] + P.l * math.sin(q["theta"])
            ht = math.hypot(cx - q["o_true_x"], cy - q["o_true_y"]) - P.r
            hmin = min(hmin, ht)
            if ht < 0:
                inc_i += 1
        if inc_i != c["incalcari_i"]:
            return _ok(False, "%s: (i) recalculat %d != certificat %d" % (b, inc_i, c["incalcari_i"]))
        if abs(round(hmin, 6) - c["min_h_true"]) > 1e-6:
            return _ok(False, "%s: min_h_true recalculat %.6f != certificat %.6f"
                       % (b, hmin, c["min_h_true"]))
        # (ii): r_eff din urma trebuie sa fie chiar marja bratului, nu a altuia
        pasi = [q for q in tr if q.get("r_eff") is not None and q.get("h") is not None]
        if not pasi:
            return _ok(False, "%s: niciun pas cu r_eff in urma" % b)
        q = pasi[len(pasi) // 2]
        d_hat = math.hypot(q["x"] + P.l * math.cos(q["theta"]) - q["o_hat_x"],
                           q["y"] + P.l * math.sin(q["theta"]) - q["o_hat_y"])
        # h = ||p_c - o_hat_folosit|| - r_eff; pentru A5 o_hat_folosit e PREDICTIA, deci h + r_eff
        # nu trebuie sa dea distanta la o_hat brut -- de aceea se verifica identitatea pe h, nu pe d.
        rest = q["h"] + q["r_eff"]
        if b == "A4" and abs(rest - d_hat) > 1e-6:
            return _ok(False, "A4: h + r_eff = %.6f != ||p_c - o_hat|| = %.6f" % (rest, d_hat))
        if b == "A5" and abs(rest - d_hat) < 1e-9:
            return _ok(False, "A5: h + r_eff coincide cu distanta la o_hat BRUT -- predictia nu e folosita")
        detalii.append("%s V=%d cert=%s (i)=%d (ii)=%d n_inf=%d n_ws=%d min_h_true=%.4f"
                       % (b, m["V"], c["verdict"], c["incalcari_i"], c["incalcari_ii"],
                          m["n_inf"], m["n_ws"], c["min_h_true"]))
    return _ok(True, "certificat pe brate noi -- " + " | ".join(detalii))


# ---------------------------------------------------------------- t5
def t5_dry_run_verifica_bratele():
    """--dry-run pe planul de 340 + CONTROL NEGATIV: un plan cu brat inexistent trebuie respins."""
    if not os.path.exists(PLAN):
        return _ok(False, "planul %s lipseste" % PLAN)
    py = VENV if os.path.exists(VENV) else sys.executable
    r = subprocess.run([py, os.path.join(TOOLS, "run_c6.py"), "--dry-run", "--plan", PLAN],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return _ok(False, "dry-run pe planul real a iesit cu %d: %s"
                   % (r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:]))
    if "brate" not in r.stdout:
        return _ok(False, "dry-run nu raporteaza bratele")
    # control negativ: plan cu un brat care nu exista in cod
    with open(PLAN, encoding="utf-8") as f:
        linii = f.read().splitlines()
    stricat = [linii[0]] + [linii[1].replace(",A0,", ",A9,").replace(",A1,", ",A9,")
                            .replace(",A2,", ",A9,").replace(",A4,", ",A9,").replace(",A5,", ",A9,")]
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("\n".join(stricat) + "\n")
        p_rau = f.name
    try:
        r2 = subprocess.run([py, os.path.join(TOOLS, "run_c6.py"), "--dry-run", "--plan", p_rau],
                            capture_output=True, text=True)
        if r2.returncode == 0:
            return _ok(False, "CONTROL NEGATIV PICAT: dry-run accepta un plan cu bratul A9")
        if "A9" not in r2.stdout + r2.stderr:
            return _ok(False, "dry-run respinge planul, dar nu spune ca A9 e vinovatul")
        # control negativ 2: scenariu inexistent
        stricat2 = [linii[0], linii[1].replace(",traversare,", ",zbor_liber,")]
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f2:
            f2.write("\n".join(stricat2) + "\n")
            p_rau2 = f2.name
        try:
            r3 = subprocess.run([py, os.path.join(TOOLS, "run_c6.py"), "--dry-run", "--plan", p_rau2],
                                capture_output=True, text=True)
            if r3.returncode == 0:
                return _ok(False, "CONTROL NEGATIV PICAT: dry-run accepta scenariul zbor_liber")
        finally:
            os.unlink(p_rau2)
    finally:
        os.unlink(p_rau)
    linie = [x for x in r.stdout.splitlines() if x.startswith("dry-run: plan")]
    return _ok(True, "dry-run 340 OK si respinge brat/scenariu inexistent -- %s"
               % (linie[0] if linie else "?"))


# ---------------------------------------------------------------- t6
def t6_redare_brate_noi():
    """2 episoade per brat nou, redate offline din trace-uri existente. Fara ROS, fara netem."""
    import glob
    if not os.path.isdir(CAMPANIE):
        return _ok(False, "campania %s lipseste" % CAMPANIE)
    sys.path.insert(0, TOOLS)
    try:
        import redare_s41
    except ImportError as e:
        return _ok(False, "redare_s41 nu se importa: %s" % e)
    dosare = []
    for tinta in ("*-r012", "*-r111"):                     # ideal si lat200_jit50, ambele A2 in original
        g = sorted(glob.glob(os.path.join(CAMPANIE, tinta)))
        if g:
            dosare.append(g[0])
    if len(dosare) < 2:
        return _ok(False, "nu gasesc cele doua rulari de redat (r012, r111)")
    detalii = []
    for b in ("A4", "A5"):
        for d in dosare:
            try:
                q = redare_s41.redda(d, "plafon", brat=b)
            except TypeError:
                return _ok(False, "redare_s41.redda nu accepta inca parametrul brat=")
            if q["n_pasi"] <= 0 or q["verdict"] not in ("PASS", "FAIL"):
                return _ok(False, "%s pe %s: redare fara certificat (n_pasi=%s verdict=%s)"
                           % (b, os.path.basename(d), q["n_pasi"], q["verdict"]))
            detalii.append("%s/%s V=%d cert=%s (ii)=%d n_inf=%d n_ws=%d d_min=%.3f"
                           % (b, os.path.basename(d)[-4:], q["V"], q["verdict"],
                              q["inc_ii"], q["n_inf"], q["n_ws"], q["d_min"]))
    return _ok(True, "redare offline 2 episoade x 2 brate -- " + " | ".join(detalii))


TESTE = (("t1", t1_marja_a4), ("t2", t2_predictor_viteza_constanta),
         ("t3", t3_predictor_pe_schimbare_de_directie), ("t4", t4_certificat_pe_brate_noi),
         ("t5", t5_dry_run_verifica_bratele), ("t6", t6_redare_brate_noi))


def main(argv):
    if "--lista" in argv:
        for n, f in TESTE:
            print("%s  %s" % (n, (f.__doc__ or "").splitlines()[0]))
        return 0
    rez = []
    for n, f in TESTE:
        try:
            v, mesaj = f()
        except Exception as e:                                    # noqa: BLE001 -- inainte de cod, asta e starea normala
            v, mesaj = "FAIL", "%s: %s" % (type(e).__name__, e)
        rez.append((n, v, mesaj))
        print("  (%s) %-5s %s" % (n, v, mesaj))
    picate = [n for n, v, _ in rez if v != "PASS"]
    print("TEST S5 %s (%d teste%s)"
          % ("OK" if not picate else "ESUAT: " + ", ".join(picate), len(rez),
             "" if not picate else ", %d picate" % len(picate)))
    return 0 if not picate else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
