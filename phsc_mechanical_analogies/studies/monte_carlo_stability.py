#!/usr/bin/env python3
"""
monte_carlo_stability.py
Monte Carlo pentru pragul de stabilitate, cu bare de eroare.

Fata de varianta propusa, trei schimbari de fond:

1. Testeaza TOATE CELE TREI conditii (fara compensare / naiv / Smith), nu
   doar Smith. Afirmatia care are nevoie de suport statistic este ABLATIA
   ('naiv e mai rau decat nimic'), nu doar pragul lui Smith.
2. Incercari PERECHE: la un tau dat, toate cele trei conditii primesc exact
   aceleasi trageri (stare initiala, parametri fizici, zgomot pe latenta).
   Comparatia devine pe perechi, ceea ce da mult mai multa putere statistica
   decat trei esantioane independente.
3. Interval de incredere Wilson pe proportii, nu doar procentul brut. Cu
   N=50 si p=1.0, Wilson da [0.929, 1.0] -- onest; 'stabil 100%' fara
   interval ar fi inselator.

Detalii de implementare care conteaza pentru corectitudine:
- planta e integrata la 1 ms, controllerul la 100 Hz (separate, ca in nodul
  ROS); daca ambele ar rula la 10 ms, cifrele n-ar mai fi comparabile cu
  rezultatele rundelor anterioare
- masele si lungimile trase aleator sunt limitate la valori pozitive
  rezonabile: o tragere M<=0 ar da impartire la zero in dinamica
- canalul de latenta foloseste un buffer marginit, altfel interpolarea pe
  istoric creste O(n^2) si rularea devine inutil de lenta
"""

import sys
import time

import numpy as np

import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel

DT_SIM = 0.001      # integrare planta
DT_CTRL = 0.01      # controller 100 Hz
T_END = 5.0
FAIL = np.pi / 2
N_PRED = 20
U_MAX = 100.0
BUF_MAX = 1500


def wilson(k, n, z=1.96):
    """Interval de incredere Wilson pentru o proportie (95% implicit)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def interp_cmd(buf_t, buf_u, t):
    """Comanda emisa la momentul t (interpolare liniara, clamp la capete)."""
    if not buf_t or t <= buf_t[0]:
        return 0.0
    if t >= buf_t[-1]:
        return buf_u[-1]
    return float(np.interp(t, buf_t, buf_u))


def run_trial(mode, tau_nom, theta0, M, m, L, b, seed):
    """
    Un singur trial. Intoarce (timp_cadere sau T_END, stabil).

    mode: 'none' | 'naive' | 'smith'
    tau_nom: latenta nominala, si totodata ce CREDE controllerul ca e latenta
    """
    rng = np.random.default_rng(seed)

    # Planta are parametrii TRASI; controllerul cunoaste doar valorile
    # NOMINALE. Asta e cazul realist: pe hardware nu stii masa exacta.
    # Varianta in care ambele folosesc aceiasi parametri masoara doar
    # variatia punctului de operare, nu robustetea la nepotrivire de model,
    # si da praguri optimiste.
    plant = CartPoleModel(M=M, m=m, L=L, b=b)
    model = CartPoleModel(M=1.0, m=0.1, L=0.5, b=0.1)   # nominal
    K = model.lqr_gain()

    # Latenta reala: nominala + oscilatie lenta + zgomot; mereu pozitiva
    n_steps = int(T_END / DT_SIM)
    jitter = rng.normal(0.0, 0.002, size=n_steps)
    def tau_real(i):
        t = i * DT_SIM
        return max(0.001, tau_nom + 0.005 * np.sin(2.0 * t) + jitter[i])

    x = np.array([0.0, 0.0, theta0, 0.0])
    buf_t, buf_u = [], []      # comenzi emise (canal)
    u_cmd = 0.0
    t_next = 0.0

    for i in range(n_steps):
        t = i * DT_SIM

        if t >= t_next - 1e-12:
            if mode == 'none':
                xh = x
            elif mode == 'naive':
                xh = model.predict_state_delay(x, 0.0, tau_nom, N_PRED)
            elif mode == 'smith':
                xh = model.predict_state_smith(
                    x, tau_nom, list(zip(buf_t, buf_u)), t, N_PRED)
            else:
                raise ValueError(mode)

            u_cmd = float(np.clip(-(K @ xh)[0], -U_MAX, U_MAX))
            buf_t.append(t)
            buf_u.append(u_cmd)
            if len(buf_t) > BUF_MAX:
                del buf_t[:-BUF_MAX]
                del buf_u[:-BUF_MAX]
            t_next = t + DT_CTRL

        # canalul aplica comanda emisa cu tau_real in urma
        u_app = interp_cmd(buf_t, buf_u, t - tau_real(i))
        x = plant.dynamics_rk4(x, u_app, DT_SIM)

        if abs(x[2]) > FAIL or not np.isfinite(x[2]):
            return t, False

    return T_END, (abs(x[2]) < np.radians(5))


def draw_params(rng):
    """Trageri fizice, limitate la valori pozitive rezonabile."""
    return dict(
        theta0=rng.uniform(0.05, 0.15),
        M=float(np.clip(rng.normal(1.0, 0.10), 0.6, 1.5)),
        m=float(np.clip(rng.normal(0.10, 0.01), 0.06, 0.15)),
        L=float(np.clip(rng.normal(0.50, 0.05), 0.35, 0.70)),
        b=float(np.clip(rng.normal(0.10, 0.01), 0.05, 0.15)),
    )


def main(n_trials=50):
    # Grila fina intre 20 si 100 ms: acolo se separa 'none' de 'naiv'
    # (studiul determinist a dat 50-80 ms vs 20-50 ms). O grila grosiera
    # ar arata ambele sarind de la 100% la 0% intre aceleasi doua puncte.
    taus = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10,
            0.15, 0.20, 0.25, 0.30]
    modes = ['none', 'naive', 'smith']
    res = {mo: {} for mo in modes}

    print("=" * 78)
    print(f"MONTE CARLO -- N={n_trials} incercari perechi per valoare de tau")
    print(f"planta {1/DT_SIM:.0f} Hz, controller {1/DT_CTRL:.0f} Hz, "
          f"{T_END:.0f} s, prag cadere {np.degrees(FAIL):.0f} grade")
    print("planta cu parametri trasi, controller pe model NOMINAL (nepotrivire reala)")
    print("theta0 U(0.05,0.15), M/m/L/b normali +/-10%, "
          "jitter 2 ms pe latenta")
    print("=" * 78)

    t0 = time.time()
    for tau in taus:
        counts = {mo: 0 for mo in modes}
        falls = {mo: [] for mo in modes}
        for k in range(n_trials):
            # aceleasi trageri pentru toate cele trei conditii (perechi)
            p = draw_params(np.random.default_rng(10_000 + k))
            for mo in modes:
                tf, ok = run_trial(mo, tau, seed=20_000 + k, **p)
                counts[mo] += int(ok)
                if not ok:
                    falls[mo].append(tf)
        line = f"  tau={tau*1000:5.0f} ms |"
        for mo in modes:
            lo, hi = wilson(counts[mo], n_trials)
            res[mo][tau] = {
                'p': counts[mo] / n_trials, 'lo': lo, 'hi': hi,
                'k': counts[mo], 'n': n_trials,
                'mean_fall': float(np.mean(falls[mo])) if falls[mo] else None,
            }
            line += f" {mo}: {counts[mo]/n_trials:5.0%} [{lo:.2f},{hi:.2f}] |"
        print(line, flush=True)

    print("-" * 78)
    print(f"durata: {time.time()-t0:.0f} s")
    print()

    # praguri: ultimul tau cu P>=0.95, si interpolarea liniara la P=0.5
    print("=" * 78)
    print("PRAGURI")
    print("=" * 78)
    for mo in modes:
        ps = [res[mo][t]['p'] for t in taus]
        t95 = [t for t, p in zip(taus, ps) if p >= 0.95]
        t50 = [t for t, p in zip(taus, ps) if p >= 0.50]
        s95 = f"{max(t95)*1000:.0f} ms" if t95 else "niciun tau"
        s50 = f"{max(t50)*1000:.0f} ms" if t50 else "niciun tau"
        # interpolare liniara pentru P=0.5
        cross = None
        for i in range(len(taus) - 1):
            if ps[i] >= 0.5 > ps[i + 1]:
                f = (ps[i] - 0.5) / (ps[i] - ps[i + 1])
                cross = taus[i] + f * (taus[i + 1] - taus[i])
                break
        sc = f"{cross*1000:.0f} ms" if cross else "in afara intervalului"
        print(f"  {mo:<6}: P>=95% pana la {s95:>12} | P>=50% pana la {s50:>12}"
              f" | incrucisare P=50%: {sc}")
    print("=" * 78)

    # test pe perechi: e 'naiv' mai rau decat 'none'?
    print()
    print("Ablatia, pe perechi (aceleasi trageri): naiv vs fara compensare")
    for tau in taus:
        a, bb = res['none'][tau]['p'], res['naive'][tau]['p']
        if a == bb:
            verdict = "egal"
        else:
            verdict = "naiv MAI RAU" if bb < a else "naiv mai bun"
        print(f"  tau={tau*1000:5.0f} ms: none {a:5.0%} vs naiv {bb:5.0%}  -> {verdict}")

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5.5))
        col = {'none': '#d62728', 'naive': '#ff7f0e', 'smith': '#2ca02c'}
        lab = {'none': 'Fara compensare', 'naive': 'Predictie naiva (u=0)',
               'smith': 'Predictie Smith (buffer)'}
        tm = np.array(taus) * 1000
        for mo in modes:
            p = np.array([res[mo][t]['p'] for t in taus])
            lo = np.array([res[mo][t]['lo'] for t in taus])
            hi = np.array([res[mo][t]['hi'] for t in taus])
            ax.plot(tm, p, 'o-', color=col[mo], label=lab[mo], lw=2, ms=6)
            ax.fill_between(tm, lo, hi, color=col[mo], alpha=0.18)
        ax.axhline(0.95, color='k', ls='--', alpha=0.4, lw=1)
        ax.axhline(0.50, color='k', ls=':', alpha=0.4, lw=1)
        ax.text(tm[-1], 0.96, '95%', ha='right', va='bottom', fontsize=8)
        ax.text(tm[-1], 0.51, '50%', ha='right', va='bottom', fontsize=8)
        ax.set_xlabel('Latenta nominala tau [ms]')
        ax.set_ylabel('P(stabil)')
        ax.set_ylim(-0.03, 1.05)
        ax.set_title(f'Monte Carlo, N={n_trials} incercari perechi '
                     f'(banda = interval Wilson 95%)')
        ax.legend(loc='center left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('monte_carlo_stability.png', dpi=150)
        print("\nSalvat: monte_carlo_stability.png")
    except Exception as exc:
        print(f"\n(figura nu a putut fi generata: {exc})")

    return res


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    main(n)
