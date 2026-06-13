#!/usr/bin/env python3
"""campaign_stats.py -- rigoare statistica pentru campaniile de benchmark.

ADITIV: sta langa analyze_campaign.py, NU il inlocuieste. Raspunde la ce cere
un recenzent peste o singura rulare:
  - intervale de incredere (bootstrap) pe percentile (p50/p95/p99) -- bare de eroare;
  - test Kolmogorov-Smirnov pe doua esantioane (zenoh vs cyclonedds) -- diferenta
    de distributii e semnificativa?
  - CDF empiric cu banda de incredere (bootstrap + alternativa DKW, fara distributie)
    -- sustine afirmatia "CDF-urile se incruciseaza".

Nucleul (percentile, bootstrap, KS, benzi) e Python PUR (random + math), testabil
izolat: ruleaza `python3 campaign_stats.py --selftest`. Se aplica la orice campanie
(C1, M, adaptiv-vs-static) fiindca lucreaza pe liste de masuratori RTT grupate pe
(rmw, conditie).

Intrare (trei moduri):
  --demo                  date sintetice (vezi imediat fluxul + figurile)
  --csv FISIER            CSV lung: coloane rmw,condition[,rep],rtt_ms
  --results-dir DIR       arborele run_campaign.py: DIR/{rmw}/{conditie}/rep*/<glob>
                          (autodetecteaza coloana RTT; vezi --rtt-col / --glob)

Iesire (in --out, implicit ./stats_out):
  stats_summary.csv       per (rmw, conditie): n, p50, p95 [CI], p99, pierdere
  stats_compare.csv       per conditie: KS D + p (zenoh vs dds), CI pe diferenta p95
  fig_cdf_band_<cond>.png CDF ambele RMW cu benzi (conditia cea mai diferita, auto)
  fig_p95_ci.png          p95 per conditie, ambele RMW, cu bare de eroare (CI)
"""
import argparse
import bisect
import csv
import glob as globmod
import math
import os
import random
import sys

# ============================ NUCLEU PUR (testabil) ============================

def percentile(xs, q):
    """Percentila q in [0,100] (interpolare liniara). Lista goala -> 0."""
    if not xs:
        return 0.0
    s = sorted(xs)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (q / 100.0)
    lo = math.floor(k); hi = math.ceil(k)
    if lo == hi:
        return float(s[int(k)])
    return s[lo] * (hi - k) + s[hi] * (k - lo)


def _cdf_at(sorted_xs, x):
    """F(x) empiric = fractia de esantioane <= x."""
    n = len(sorted_xs)
    return bisect.bisect_right(sorted_xs, x) / n if n else 0.0


def bootstrap_percentile_ci(xs, q, B=1000, alpha=0.05, rng=None, cap=20000):
    """Punct + interval de incredere (1-alpha) pentru percentila q, prin bootstrap
    (reesantionare cu inlocuire). Pentru viteza, esantioane > cap se subesantioneaza."""
    rng = rng or random.Random(0)
    xs = list(xs)
    if len(xs) > cap:
        xs = [xs[rng.randrange(len(xs))] for _ in range(cap)]
    n = len(xs)
    point = percentile(xs, q)
    if n < 2:
        return point, point, point
    boot = []
    for _ in range(B):
        sample = [xs[rng.randrange(n)] for _ in range(n)]
        boot.append(percentile(sample, q))
    return point, percentile(boot, 100 * alpha / 2), percentile(boot, 100 * (1 - alpha / 2))


def bootstrap_diff_ci(a, b, q, B=1000, alpha=0.05, rng=None, cap=20000):
    """CI pe diferenta percentilelor: percentile(a,q) - percentile(b,q).
    Daca intervalul nu contine 0, diferenta e semnificativa la nivelul alpha."""
    rng = rng or random.Random(0)
    a = list(a); b = list(b)
    if len(a) > cap:
        a = [a[rng.randrange(len(a))] for _ in range(cap)]
    if len(b) > cap:
        b = [b[rng.randrange(len(b))] for _ in range(cap)]
    na, nb = len(a), len(b)
    point = percentile(a, q) - percentile(b, q)
    if na < 2 or nb < 2:
        return point, point, point
    boot = []
    for _ in range(B):
        sa = [a[rng.randrange(na)] for _ in range(na)]
        sb = [b[rng.randrange(nb)] for _ in range(nb)]
        boot.append(percentile(sa, q) - percentile(sb, q))
    return point, percentile(boot, 100 * alpha / 2), percentile(boot, 100 * (1 - alpha / 2))


def _q_ks(lam):
    """Distributia Kolmogorov Q(lam) = 2 sum_{j>=1} (-1)^{j-1} exp(-2 j^2 lam^2).
    Forma Numerical Recipes: convergenta relativa; intoarce 1.0 cand seria nu
    converge (cazul lam mic, unde Q -> 1)."""
    if lam <= 0:
        return 1.0
    a2 = -2.0 * lam * lam
    fac = 2.0
    s = 0.0
    termbf = 0.0
    for j in range(1, 101):
        term = fac * math.exp(a2 * j * j)
        s += term
        if abs(term) <= 1e-3 * termbf or abs(term) <= 1e-8 * s:
            return max(0.0, min(1.0, s))
        fac = -fac
        termbf = abs(term)
    return 1.0


def ks_2samp(a, b):
    """Testul Kolmogorov-Smirnov pe doua esantioane.
    Intoarce (D, p): D = sup|F_a - F_b|; p = probabilitatea ca o diferenta >= D
    sa apara daca esantioanele vin din aceeasi distributie (mic = diferite)."""
    a = sorted(a); b = sorted(b)
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    i = j = 0
    d = 0.0
    while i < n1 and j < n2:
        x = a[i] if a[i] <= b[j] else b[j]
        while i < n1 and a[i] <= x:
            i += 1
        while j < n2 and b[j] <= x:
            j += 1
        d = max(d, abs(i / n1 - j / n2))
    ne = math.sqrt(n1 * n2 / (n1 + n2))
    return d, _q_ks((ne + 0.12 + 0.11 / ne) * d)


def cdf_band_bootstrap(xs, grid, B=500, alpha=0.05, rng=None, cap=20000):
    """Banda de incredere (1-alpha) pentru CDF la punctele din grid, prin bootstrap."""
    rng = rng or random.Random(0)
    xs = list(xs)
    if len(xs) > cap:
        xs = [xs[rng.randrange(len(xs))] for _ in range(cap)]
    n = len(xs)
    cols = [[] for _ in grid]
    for _ in range(B):
        sample = sorted(xs[rng.randrange(n)] for _ in range(n))
        for k, g in enumerate(grid):
            cols[k].append(_cdf_at(sample, g))
    lo = [percentile(c, 100 * alpha / 2) for c in cols]
    hi = [percentile(c, 100 * (1 - alpha / 2)) for c in cols]
    return lo, hi


def cdf_band_dkw(xs, grid, alpha=0.05):
    """Banda CDF fara distributie (Dvoretzky-Kiefer-Wolfowitz): F +/- eps, cu
    eps = sqrt(ln(2/alpha) / (2n)). Garantata prin constructie, conservatoare."""
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return [0.0] * len(grid), [0.0] * len(grid), [0.0] * len(grid)
    eps = math.sqrt(math.log(2.0 / alpha) / (2.0 * n))
    F = [_cdf_at(s, g) for g in grid]
    return F, [max(0.0, f - eps) for f in F], [min(1.0, f + eps) for f in F]


# ================================ SELFTEST ================================

def _selftest():
    ok = 0; fail = []
    def check(name, cond, extra=""):
        nonlocal ok
        if cond: ok += 1
        else: fail.append(f"{name} {extra}")

    # percentila
    check("p95 lista goala = 0", percentile([], 95) == 0.0)
    check("p95 constanta", abs(percentile([5, 5, 5], 95) - 5) < 1e-9)
    check("p50 = mediana", abs(percentile([1, 2, 3, 4], 50) - 2.5) < 1e-9)

    rng = random.Random(42)
    # bootstrap CI: contine punctul; se ingusteaza cu n mai mare
    small = [rng.gauss(100, 15) for _ in range(40)]
    big = [rng.gauss(100, 15) for _ in range(800)]
    ps, ls, hs = bootstrap_percentile_ci(small, 50, B=400, rng=random.Random(1))
    pb, lb, hb = bootstrap_percentile_ci(big, 50, B=400, rng=random.Random(1))
    check("CI bootstrap contine punctul", ls <= ps <= hs)
    check("CI se ingusteaza cu n mai mare", (hb - lb) < (hs - ls),
          f"lat n_mic={hs-ls:.2f}, n_mare={hb-lb:.2f}")

    # diferenta de percentile: aceeasi distributie -> CI contine 0;
    # distributii separate -> CI exclude 0
    a = [rng.gauss(100, 10) for _ in range(300)]
    b = [rng.gauss(100, 10) for _ in range(300)]
    c = [rng.gauss(200, 10) for _ in range(300)]
    _, lo0, hi0 = bootstrap_diff_ci(a, b, 95, B=400, rng=random.Random(2))
    _, lo1, hi1 = bootstrap_diff_ci(a, c, 95, B=400, rng=random.Random(2))
    check("diff CI contine 0 cand distributiile sunt egale", lo0 <= 0 <= hi0,
          f"[{lo0:.1f},{hi0:.1f}]")
    check("diff CI exclude 0 cand distributiile difera", hi1 < 0,
          f"[{lo1:.1f},{hi1:.1f}]")

    # Q_ks: ~1 la argument mic, ~0 la argument mare, descrescator
    check("Q_ks(0.01)~1", _q_ks(0.01) > 0.99)
    check("Q_ks(3)~0", _q_ks(3.0) < 0.01)
    check("Q_ks descrescator", _q_ks(0.5) > _q_ks(1.5))

    # KS: identice -> D=0,p mare; separate -> D=1,p mic; moderat -> 0<D<1
    d_id, p_id = ks_2samp(list(range(100)), list(range(100)))
    d_sep, p_sep = ks_2samp(list(range(100)), list(range(200, 300)))
    d_mod, p_mod = ks_2samp([rng.gauss(0, 1) for _ in range(300)],
                            [rng.gauss(0.6, 1) for _ in range(300)])
    check("KS identice: D=0, p mare", d_id == 0.0 and p_id > 0.5, f"D={d_id},p={p_id:.3f}")
    check("KS separate: D=1, p mic", d_sep == 1.0 and p_sep < 0.01, f"D={d_sep},p={p_sep:.4f}")
    check("KS moderat: 0<D<1", 0.0 < d_mod < 1.0, f"D={d_mod:.3f}")

    # benzi CDF: DKW contine F prin constructie; bootstrap contine F la mediana
    xs = [rng.gauss(50, 8) for _ in range(400)]
    grid = [percentile(xs, q) for q in range(5, 96, 10)]
    F, lo, hi = cdf_band_dkw(xs, grid, alpha=0.05)
    check("DKW: lo<=F<=hi peste tot", all(lo[k] <= F[k] <= hi[k] for k in range(len(grid))))
    check("DKW: banda in [0,1]", all(0 <= lo[k] and hi[k] <= 1 for k in range(len(grid))))
    blo, bhi = cdf_band_bootstrap(xs, grid, B=300, rng=random.Random(3))
    s = sorted(xs)
    contained = sum(blo[k] <= _cdf_at(s, grid[k]) <= bhi[k] for k in range(len(grid)))
    check("bootstrap: banda contine F la majoritatea punctelor",
          contained >= 0.8 * len(grid), f"{contained}/{len(grid)}")
    check("bootstrap: banda valida 0<=lo<=hi<=1",
          all(0 <= blo[k] <= bhi[k] <= 1 for k in range(len(grid))))

    print(f"[selftest] {ok} verificari trecute" + (f", {len(fail)} ESUATE:" if fail else ", toate OK"))
    for f in fail:
        print("   FAIL:", f)
    return not fail


# ============================ INCARCAREA DATELOR ============================

RTT_COL_CANDIDATES = ["rtt_ms", "rtt", "rtt_us", "value", "latency_ms", "latency"]


def _detect_rtt_col(header):
    low = [h.strip().lower() for h in header]
    for cand in RTT_COL_CANDIDATES:
        if cand in low:
            return header[low.index(cand)]
    return None


def load_long_csv(path, rmw_col="rmw", cond_col="condition", rtt_col=None, rep_col=None):
    """CSV lung: o linie per esantion, coloane rmw, condition[, rep], rtt."""
    data = {}
    with open(path, newline="") as f:
        rdr = csv.DictReader(f)
        rtt_col = rtt_col or _detect_rtt_col(rdr.fieldnames or [])
        if rtt_col is None:
            sys.exit(f"[eroare] nu gasesc coloana RTT in {path}; antet: {rdr.fieldnames}\n"
                     f"         da-mi-o cu --rtt-col NUME")
        for row in rdr:
            try:
                key = (row[rmw_col].strip(), row[cond_col].strip())
                data.setdefault(key, []).append(float(row[rtt_col]))
            except (KeyError, ValueError):
                continue
    return data


def load_results_dir(root, glob_pat="transport_*.csv", rtt_col=None):
    """Arborele run_campaign.py: root/{rmw}/{conditie}/rep*/<glob>.
    Autodetecteaza coloana RTT din antet (sau o iei cu --rtt-col)."""
    data = {}
    pattern = os.path.join(root, "*", "*", "*", glob_pat)
    files = sorted(globmod.glob(pattern))
    if not files:
        # incearca si fara nivelul rep*
        files = sorted(globmod.glob(os.path.join(root, "*", "*", glob_pat)))
    if not files:
        sys.exit(f"[eroare] niciun fisier {glob_pat} sub {root}\n"
                 f"         structura asteptata: {root}/<rmw>/<conditie>/rep*/{glob_pat}\n"
                 f"         (sau da-mi --glob si lipeste-mi antetul unui CSV de transport)")
    for path in files:
        parts = path.split(os.sep)
        # rmw si conditia: doua niveluri sub root
        try:
            rel = os.path.relpath(path, root).split(os.sep)
            rmw, cond = rel[0], rel[1]
        except Exception:
            continue
        with open(path, newline="") as f:
            rdr = csv.DictReader(f)
            col = rtt_col or _detect_rtt_col(rdr.fieldnames or [])
            if col is None:
                continue
            for row in rdr:
                try:
                    data.setdefault((rmw, cond), []).append(float(row[col]))
                except (KeyError, ValueError):
                    continue
    if not data:
        sys.exit(f"[eroare] am gasit fisiere dar n-am putut citi coloana RTT.\n"
                 f"         lipeste-mi antetul unui {glob_pat} si dau --rtt-col corect.")
    return data


# o ordine canonica a conditiilor C1 (pentru tabele/figuri lizibile)
COND_ORDER = ["ideal", "loss_5", "loss_15", "loss_30", "lat200_jit50", "lat200_l15"]


def _sorted_conds(conds):
    known = [c for c in COND_ORDER if c in conds]
    extra = sorted(c for c in conds if c not in COND_ORDER)
    return known + extra


def demo_data(rng=None):
    """Date sintetice care imita calitativ povestea C1 (DOAR pentru demo):
    cyclonedds = fiabil (mediana mica, coada grea sub pierdere/latenta);
    zenoh = mediana rapida, coada proprie. NU sunt date reale."""
    rng = rng or random.Random(7)
    def mix(n, base, base_sd, tail_frac, tail_lo, tail_hi):
        out = []
        for _ in range(n):
            if rng.random() < tail_frac:
                out.append(rng.uniform(tail_lo, tail_hi))
            else:
                out.append(max(0.1, rng.gauss(base, base_sd)))
        return out
    N = 1500
    return {
        ("cyclonedds", "ideal"): mix(N, 1.5, 0.4, 0.0, 0, 0),
        ("zenoh", "ideal"):      mix(N, 1.7, 0.4, 0.0, 0, 0),
        ("cyclonedds", "loss_15"): mix(N, 6, 2, 0.18, 200, 1100),   # coada de retransmisii
        ("zenoh", "loss_15"):      mix(N, 5, 2, 0.06, 150, 760),
        ("cyclonedds", "loss_30"): mix(N, 7, 3, 0.30, 400, 2400),
        ("zenoh", "loss_30"):      mix(N, 5, 2, 0.14, 300, 3700),
        ("cyclonedds", "lat200_l15"): mix(N, 205, 20, 0.30, 800, 2600),
        ("zenoh", "lat200_l15"):      mix(N, 203, 25, 0.18, 600, 4200),
    }


# ============================ RAPORT + FIGURI ============================

def write_summary(data, out, boot, alpha):
    rng = random.Random(0)
    rmws = sorted({k[0] for k in data})
    conds = _sorted_conds({k[1] for k in data})

    path = os.path.join(out, "stats_summary.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rmw", "condition", "n", "p50_ms", "p95_ms",
                    f"p95_lo{int((1-alpha)*100)}", f"p95_hi{int((1-alpha)*100)}", "p99_ms"])
        for cond in conds:
            for rmw in rmws:
                xs = data.get((rmw, cond))
                if not xs:
                    continue
                p95, lo, hi = bootstrap_percentile_ci(xs, 95, B=boot, alpha=alpha, rng=rng)
                w.writerow([rmw, cond, len(xs), round(percentile(xs, 50), 2),
                            round(p95, 2), round(lo, 2), round(hi, 2),
                            round(percentile(xs, 99), 2)])
    print(f"  [csv] {path}")

    # comparatie per conditie: KS + CI pe diferenta p95 (zenoh - cyclonedds)
    if "zenoh" in rmws and "cyclonedds" in rmws:
        path2 = os.path.join(out, "stats_compare.csv")
        with open(path2, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["condition", "ks_D", "ks_p", "dp95_zenoh_minus_dds",
                        "dp95_lo", "dp95_hi", "diferit_semnificativ"])
            for cond in conds:
                za = data.get(("zenoh", cond)); ca = data.get(("cyclonedds", cond))
                if not za or not ca:
                    continue
                D, p = ks_2samp(za, ca)
                dp, lo, hi = bootstrap_diff_ci(za, ca, 95, B=boot, alpha=alpha, rng=rng)
                sig = "da" if (lo > 0 or hi < 0) else "nu"
                w.writerow([cond, round(D, 3), round(p, 4), round(dp, 1),
                            round(lo, 1), round(hi, 1), sig])
        print(f"  [csv] {path2}")


def _pick_most_different(data):
    """Conditia cu cel mai mare D (KS) intre zenoh si cyclonedds -- cea mai
    interesanta pentru CDF."""
    best, bestD = None, -1.0
    for cond in {k[1] for k in data}:
        za = data.get(("zenoh", cond)); ca = data.get(("cyclonedds", cond))
        if za and ca:
            D, _ = ks_2samp(za, ca)
            if D > bestD:
                best, bestD = cond, D
    return best


def plot_cdf(data, cond, out, boot, alpha):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("  (matplotlib indisponibil - sar peste figura CDF)"); return
    za = data.get(("zenoh", cond)); ca = data.get(("cyclonedds", cond))
    if not za or not ca:
        return
    lo_x = min(min(za), min(ca)); hi_x = max(percentile(za, 99), percentile(ca, 99))
    grid = [lo_x + (hi_x - lo_x) * i / 200.0 for i in range(201)]

    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=130)
    for xs, name, col in ((ca, "CycloneDDS", "#C0504D"), (za, "Zenoh", "#1C7293")):
        s = sorted(xs)
        F = [_cdf_at(s, g) for g in grid]
        blo, bhi = cdf_band_bootstrap(xs, grid, B=max(200, boot // 3), alpha=alpha,
                                      rng=random.Random(11))
        ax.plot(grid, [f * 100 for f in F], color=col, lw=2.2, label=name)
        ax.fill_between(grid, [b * 100 for b in blo], [b * 100 for b in bhi],
                        color=col, alpha=0.18, linewidth=0)
    D, p = ks_2samp(za, ca)
    ax.set_xlabel("RTT [ms]"); ax.set_ylabel("CDF [%]")
    ax.set_title(f"CDF RTT cu banda de incredere {int((1-alpha)*100)}% -- conditia {cond}\n"
                 f"KS: D={D:.3f}, p={p:.3g}")
    ax.grid(alpha=0.3); ax.legend(loc="lower right")
    path = os.path.join(out, f"fig_cdf_band_{cond}.png")
    fig.savefig(path, bbox_inches="tight"); print(f"  [figura] {path}")


def plot_p95_ci(data, out, boot, alpha):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("  (matplotlib indisponibil - sar peste figura p95)"); return
    rng = random.Random(0)
    conds = _sorted_conds({k[1] for k in data})
    rmws = [r for r in ("cyclonedds", "zenoh") if any(k[0] == r for k in data)]
    cols = {"cyclonedds": "#C0504D", "zenoh": "#1C7293"}
    x = list(range(len(conds))); w = 0.36

    fig, ax = plt.subplots(figsize=(8.4, 4.6), dpi=130)
    for idx, rmw in enumerate(rmws):
        ys, los, his = [], [], []
        for cond in conds:
            xs = data.get((rmw, cond))
            if xs:
                p, lo, hi = bootstrap_percentile_ci(xs, 95, B=boot, alpha=alpha, rng=rng)
            else:
                p = lo = hi = 0.0
            ys.append(p); los.append(max(0, p - lo)); his.append(max(0, hi - p))
        off = (idx - (len(rmws) - 1) / 2) * w
        ax.bar([xi + off for xi in x], ys, width=w, color=cols.get(rmw, "#888"),
               label=rmw, yerr=[los, his], capsize=3,
               error_kw=dict(ecolor="#333", lw=1))
    ax.set_xticks(x); ax.set_xticklabels(conds, rotation=20, ha="right")
    ax.set_ylabel("RTT p95 [ms]")
    ax.set_title(f"RTT p95 per conditie cu interval de incredere {int((1-alpha)*100)}% "
                 f"(bootstrap)")
    ax.grid(alpha=0.3, axis="y"); ax.legend()
    path = os.path.join(out, "fig_p95_ci.png")
    fig.savefig(path, bbox_inches="tight"); print(f"  [figura] {path}")


def main():
    ap = argparse.ArgumentParser(description="Statistica pentru campaniile de benchmark.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("results_dir", nargs="?", help="arborele run_campaign.py")
    src.add_argument("--csv", help="CSV lung: rmw,condition[,rep],rtt_ms")
    src.add_argument("--demo", action="store_true", help="date sintetice (demonstratie)")
    ap.add_argument("--selftest", action="store_true", help="ruleaza testele nucleului si iese")
    ap.add_argument("--out", default="stats_out", help="directorul de iesire")
    ap.add_argument("--glob", default="transport_*.csv", help="tiparul fisierelor de transport")
    ap.add_argument("--rtt-col", default=None, help="numele coloanei RTT (daca autodetectia esueaza)")
    ap.add_argument("--boot", type=int, default=1000, help="repetitii bootstrap")
    ap.add_argument("--alpha", type=float, default=0.05, help="1-alpha = nivelul de incredere")
    ap.add_argument("--cdf-cond", default=None, help="conditia pentru figura CDF (implicit: cea mai diferita)")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if _selftest() else 1)

    if args.demo:
        data = demo_data()
        print("[demo] date sintetice (NU reale) -- doar pentru a vedea fluxul si figurile")
    elif args.csv:
        data = load_long_csv(args.csv, rtt_col=args.rtt_col)
    elif args.results_dir:
        data = load_results_dir(args.results_dir, glob_pat=args.glob, rtt_col=args.rtt_col)
    else:
        ap.error("alege o sursa: --demo, --csv FISIER, sau directorul rezultatelor")

    os.makedirs(args.out, exist_ok=True)
    print(f"[date] {len(data)} celule (rmw x conditie); "
          f"esantioane: {sum(len(v) for v in data.values())}")
    write_summary(data, args.out, args.boot, args.alpha)
    cond = args.cdf_cond or _pick_most_different(data)
    if cond:
        plot_cdf(data, cond, args.out, args.boot, args.alpha)
    plot_p95_ci(data, args.out, args.boot, args.alpha)
    print(f"[gata] rezultate in {args.out}/")


if __name__ == "__main__":
    main()
