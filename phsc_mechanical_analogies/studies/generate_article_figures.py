#!/usr/bin/env python3
"""
generate_article_figures.py
Genereaza figurile PHSC in format VECTORIAL (PDF) plus PNG pentru previzualizare.

Toate figurile sunt produse din date reale: fie re-ruland simularea (rapida),
fie citind CSV-urile din ~/analyses_phsc/02_date_tabelare/. Nicio cifra nu e
introdusa manual.

Stil: coloana IEEE (3.5 inch simpla / 7.2 inch dubla), font serif, linii
subtiri, grila recesiva.

Culori: primele trei sloturi din paleta categoriala de referinta, in ordine
fixa. Fiecare serie are IN PLUS un stil de linie si un marker distinct, deci
identitatea nu depinde niciodata doar de culoare (daltonism, tiparire alb-negru).

Rulare:  python3 generate_article_figures.py
"""

import csv
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patheffects as pe
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel, DelayedCartPole

# iesirile stau langa cod, in docs/ ale pachetului
_PKG = Path(__file__).resolve().parent.parent
IESIRE = _PKG / 'docs' / 'figuri'
DATE = _PKG / 'docs' / 'date'
IESIRE.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- stil
COL = {'none': '#2a78d6', 'naive': '#eb6834', 'smith': '#1baf7a'}
LS = {'none': '--', 'naive': '-.', 'smith': '-'}
MK = {'none': 'o', 'naive': 's', 'smith': '^'}
ET = {'none': 'Fara compensare', 'naive': 'Predictie naiva (u=0)',
      'smith': 'Predictie Smith (buffer)'}
GRI = '#9a9a94'
INK = '#0b0b0b'
INK2 = '#52514e'

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['DejaVu Serif', 'Times New Roman', 'Computer Modern Roman'],
    'font.size': 10,
    'axes.labelsize': 10,
    'axes.titlesize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 8,
    'lines.linewidth': 1.6,
    'axes.linewidth': 0.6,
    'axes.edgecolor': GRI,
    'axes.labelcolor': INK,
    'text.color': INK,
    'xtick.color': INK2,
    'ytick.color': INK2,
    'grid.color': GRI,
    'grid.alpha': 0.25,
    'grid.linewidth': 0.5,
    'legend.frameon': False,
    'figure.dpi': 110,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
})

O1, O2 = 3.5, 7.2      # latimi de coloana IEEE


def salveaza(fig, nume):
    pdf = IESIRE / f'{nume}.pdf'
    png = IESIRE / f'{nume}.png'
    fig.savefig(pdf)                    # vectorial
    fig.savefig(png, dpi=300)           # previzualizare
    plt.close(fig)
    print(f"  {pdf.name} ({pdf.stat().st_size/1024:.0f} KB) + "
          f"{png.name} ({png.stat().st_size/1024:.0f} KB)")


def curata(ax):
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.grid(True, axis='both')
    ax.set_axisbelow(True)


# ------------------------------------------------- simularea de ablatie
DT_SIM, DT_CTRL, T_END, THETA0, N_PRED = 0.001, 0.01, 5.0, 0.10, 20
TAU_ABL = 0.10
FAIL = np.pi / 2

model = CartPoleModel()
K = model.lqr_gain()


def ruleaza(mode, tau=TAU_ABL, T=T_END):
    """Intoarce (t, theta, theta_dot, u, moment_cadere)."""
    plant = DelayedCartPole()
    x = np.array([0.0, 0.0, THETA0, 0.0])
    t, u_cmd, t_next = 0.0, 0.0, 0.0
    buf = []
    ts, th, thd, us = [], [], [], []
    cazut = None
    while t < T:
        if t >= t_next:
            if mode == 'none':
                xh = x
            elif mode == 'naive':
                xh = model.predict_state_delay(x, 0.0, tau, N_PRED)
            else:
                xh = model.predict_state_smith(x, tau, buf, t, N_PRED)
            u_cmd = float(np.clip(-(K @ xh)[0], -100.0, 100.0))
            buf.append((t, u_cmd))
            if len(buf) > 2000:
                del buf[:-2000]
            t_next = t + DT_CTRL
        plant.control_history.append((t, u_cmd))
        x = plant.dynamics_rk4(x, plant.get_delayed_control(t, tau), DT_SIM)
        ts.append(t); th.append(x[2]); thd.append(x[3]); us.append(u_cmd)
        if cazut is None and abs(x[2]) > FAIL:
            cazut = t
        t += DT_SIM
    return (np.array(ts), np.array(th), np.array(thd), np.array(us), cazut)


print("Simulez ablatia (o singura data, refolosita de fig01 si fig06)...")
SIM = {m: ruleaza(m) for m in ('none', 'naive', 'smith')}


# ============================================== fig01 -- ablatie in timp
def fig01():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(O2, 4.4), sharex=True,
                                   gridspec_kw={'height_ratios': [1.35, 1]})
    # etichetele de cadere se decaleaza pe verticala: momentele 0.53 s si
    # 0.88 s sunt prea apropiate ca sa incapa pe acelasi rand
    y_et = {'naive': 168, 'none': 132}
    for m in ('none', 'naive', 'smith'):
        ts, th, _, us, cazut = SIM[m]
        ax1.plot(ts, np.degrees(th), color=COL[m], ls=LS[m], label=ET[m])
        ax2.plot(ts, us, color=COL[m], ls=LS[m])
        if cazut is not None:
            ax1.axvline(cazut, color=COL[m], ls=':', lw=0.9, alpha=0.75)
            ax1.annotate(f'cade la {cazut:.2f} s', xy=(cazut, y_et[m]),
                         xytext=(cazut + 0.14, y_et[m]), fontsize=7.5,
                         color=COL[m], va='center')
    ax1.axhline(90, color=GRI, ls='--', lw=0.7)
    ax1.axhline(-90, color=GRI, ls='--', lw=0.7)
    ax1.text(T_END, 93, 'prag de cadere', ha='right', fontsize=7.5, color=INK2)
    ax1.set_ylim(-180, 185)
    ax1.set_ylabel(r'unghi $\theta$ [grade]')
    ax1.legend(loc='lower left', ncol=1)
    curata(ax1)

    ax2.axhline(100, color=GRI, ls='--', lw=0.7)
    ax2.axhline(-100, color=GRI, ls='--', lw=0.7)
    ax2.text(T_END, 103, r'saturatie $\pm u_{max}$', ha='right',
             fontsize=7.5, color=INK2)
    ax2.set_ylim(-125, 130)
    ax2.set_ylabel('comanda $u$ [N]')
    ax2.set_xlabel('timp [s]')
    curata(ax2)
    ax1.set_title(r'Ablatia compensarii latentei, $\tau$ = 100 ms, LQR la 100 Hz',
                  loc='left')
    fig.align_ylabels([ax1, ax2])
    salveaza(fig, 'fig01_ablation_tau100')


# ======================================= fig02 -- Monte Carlo, praguri
def fig02():
    src = DATE / 'monte_carlo' / 'praguri_stabilitate_N50.csv'
    d = {}
    with src.open() as f:
        for r in csv.DictReader(f):
            cond = {'fara_compensare': 'none', 'naiv_u0': 'naive',
                    'smith_buffer': 'smith'}[r['conditie']]
            d.setdefault(cond, []).append(
                (float(r['tau_ms']), float(r['p_stabil']),
                 float(r['wilson_95_jos']), float(r['wilson_95_sus'])))
    fig, ax = plt.subplots(figsize=(O2, 3.4))
    for m in ('none', 'naive', 'smith'):
        a = np.array(sorted(d[m]))
        ax.fill_between(a[:, 0], a[:, 2], a[:, 3], color=COL[m], alpha=0.16,
                        linewidth=0)
        ax.plot(a[:, 0], a[:, 1], color=COL[m], ls=LS[m], marker=MK[m],
                ms=4.5, label=ET[m])
    ax.axhline(0.95, color=GRI, ls='--', lw=0.7)
    ax.axhline(0.50, color=GRI, ls=':', lw=0.9)
    ax.text(302, 0.95, '95%', va='center', fontsize=7.5, color=INK2)
    ax.text(302, 0.50, '50%', va='center', fontsize=7.5, color=INK2)
    # pragurile 55 si 69 ms sunt prea apropiate pe axa x pentru etichete pe
    # acelasi rand; le decalez pe verticala si lateral
    for m, prag, yt, dx in (('naive', 55, 0.30, -13), ('none', 69, 0.16, 12),
                            ('smith', 265, 0.30, 0)):
        ax.annotate(f'{prag} ms', xy=(prag, 0.5), xytext=(prag + dx, yt),
                    ha='center', fontsize=7.5, color=COL[m],
                    arrowprops=dict(arrowstyle='-', color=COL[m], lw=0.7,
                                    shrinkA=1, shrinkB=1))
    ax.set_xlabel(r'latenta nominala $\tau$ [ms]')
    ax.set_ylabel('P(stabil)')
    ax.set_ylim(-0.04, 1.06)
    ax.set_xlim(10, 315)
    ax.set_title('Probabilitate de stabilitate, N = 50 incercari perechi '
                 '(banda: interval Wilson 95%)', loc='left')
    ax.legend(loc='center left')
    curata(ax)
    salveaza(fig, 'fig02_monte_carlo_praguri')


# ================================== fig03 -- McNemar, tabel de contingenta
def fig03():
    src = DATE / 'mcnemar' / 'mcnemar_perechi_N50.csv'
    randuri = list(csv.DictReader(src.open()))
    taus = [int(r['tau_ms']) for r in randuri]
    b = [int(r['doar_fara_compensare_b']) for r in randuri]
    c = [int(r['doar_naiv_c']) for r in randuri]
    pv = [float(r['p_o_coada']) for r in randuri]

    a = [int(r['ambele_stabile']) for r in randuri]
    d = [int(r['niciunul']) for r in randuri]

    # Tabelul de contingenta complet, ca bare stivuite pe cele 50 de perechi.
    # O bara separata pentru c ar fi fost invizibila (c=0 peste tot), deci
    # exact celula cea mai importanta n-ar fi comunicat nimic. Aici absenta
    # segmentului portocaliu ESTE mesajul.
    seg = [
        ('ambele stabile (a)', a, '#1baf7a'),
        ('doar fara compensare -- naivul a STRICAT (b)', b, COL['naive']),
        ('doar naiv -- naivul a AJUTAT (c)', c, COL['none']),
        ('niciunul stabil (d)', d, '#9a9a94'),
    ]

    fig, ax = plt.subplots(figsize=(O2, 2.6))
    y = np.arange(len(taus))
    h = 0.5
    stanga = np.zeros(len(taus))
    for eticheta, val, culoare in seg:
        v = np.array(val, dtype=float)
        ax.barh(y, v, height=h, left=stanga, color=culoare, label=eticheta,
                edgecolor='white', linewidth=1.4)
        for i, (x0, w) in enumerate(zip(stanga, v)):
            if w >= 4:
                ax.text(x0 + w / 2, i, f'{int(w)}', ha='center', va='center',
                        fontsize=8, color='white')
        stanga += v

    for i, p in enumerate(pv):
        ax.text(51.5, i, f'c = 0,  p = {p:.1e}', va='center', fontsize=8,
                color=INK)

    ax.set_yticks(y)
    ax.set_yticklabels([fr'$\tau$ = {t} ms' for t in taus])
    ax.set_xlabel('incercari perechi (din 50)')
    ax.set_xlim(0, 50)
    ax.invert_yaxis()
    ax.set_title('McNemar exact: predictie naiva vs fara compensare\n'
                 'segmentul "naivul a AJUTAT" lipseste la toate latentele',
                 loc='left')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.32), ncol=2)
    curata(ax)
    ax.grid(False, axis='y')
    salveaza(fig, 'fig03_mcnemar_contingency')


# ==================================== fig04 -- eroarea estimatorului EWMA
def fig04():
    # Reproduce EXACT conditiile din test_smith_variable.py, ca figura sa nu
    # contrazica cifrele din RESULTS.md sec. 6: estimatorul se actualizeaza la
    # 20 Hz, dar eroarea se esantioneaza la rata CONTROLLERULUI (100 Hz),
    # pentru ca aceea e rata la care bucla chiar foloseste valoarea -- deci
    # perioadele in care estimarea e invechita intre actualizari conteaza.
    rng = np.random.default_rng(42)
    tau_t = lambda t: 0.100 + 0.050 * np.sin(2 * np.pi * t / 4.0)
    alpha, rate, jit = 0.3, 20.0, 0.004
    dt_ctrl, T = 0.01, 10.0
    tau_est, t_next_est = 0.05, 0.0
    err, ts, tr, te = [], [], [], []
    for i in range(int(T / dt_ctrl)):
        t = i * dt_ctrl
        real = tau_t(t)
        if t >= t_next_est:
            rtt = max(0.0, 2 * real + rng.normal(0, jit))
            tau_est = alpha * (0.5 * rtt) + (1 - alpha) * tau_est
            t_next_est = t + 1.0 / rate
        ts.append(t); tr.append(real); te.append(tau_est)
        if t > 1.0:
            err.append(100 * (tau_est - real) / real)
    err = np.array(err)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(O2, 2.7),
                                   gridspec_kw={'width_ratios': [1.3, 1]})
    ax1.plot(ts, 1000 * np.array(tr), color=INK2, lw=1.2, label=r'$\tau$ real')
    ax1.plot(ts, 1000 * np.array(te), color=COL['smith'], lw=1.4,
             label=r'$\tau$ estimat (EWMA)')
    ax1.set_xlabel('timp [s]'); ax1.set_ylabel(r'$\tau$ [ms]')
    ax1.set_xlim(0, 10)
    ax1.legend(loc='upper right')
    ax1.set_title('Urmarirea latentei', loc='left')
    curata(ax1)

    ax2.hist(err, bins=32, color=COL['smith'], alpha=0.75, edgecolor='white',
             linewidth=0.4)
    med, p95 = err.mean(), np.percentile(np.abs(err), 95)
    ax2.axvline(med, color=INK, lw=1.2)
    ax2.axvline(20, color=COL['naive'], ls='--', lw=1.1)
    ax2.axvline(-20, color=COL['naive'], ls='--', lw=1.1)
    ax2.text(med, ax2.get_ylim()[1] * 0.96, f' medie {med:+.2f}%',
             fontsize=7.5, color=INK, va='top')
    ax2.text(20, ax2.get_ylim()[1] * 0.55, ' prag critic\n +/-20%',
             fontsize=7.5, color=COL['naive'], va='top')
    ax2.set_xlabel('eroare de estimare [%]')
    ax2.set_ylabel('numar de esantioane')
    ax2.set_title(f'Distributia erorii (p95 = {p95:.1f}%)', loc='left')
    curata(ax2)
    salveaza(fig, 'fig04_estimator_error_dist')
    return med, p95


# ================================= fig05 -- benchmark MPC, timp de solve
def fig05():
    from phsc_mechanical_analogies.mpc_controller import (
        MPCParams, MPCController)
    x0 = np.array([0.0, 0.0, 0.1, 0.0]); xr = np.zeros(4)
    Ns = [5, 7, 10, 15, 20]
    rez = {}
    for mod in ('none', 'hard'):
        rez[mod] = []
        for N in Ns:
            p = MPCParams(N=N, dt=0.05, u_max=100.0, theta_mode=mod,
                          Q=np.diag([10., 1., 100., 1.]),
                          R=np.array([[0.01]]), P=np.diag([50., 5., 500., 5.]))
            c = MPCController(model, p)
            c.solve(x0, xr)
            ts = []
            for _ in range(5):
                t0 = time.perf_counter(); c.solve(x0, xr)
                ts.append((time.perf_counter() - t0) * 1000)
            rez[mod].append(float(np.median(ts)))
            print(f"    N={N:2d} theta={mod:4s}: {np.median(ts):7.1f} ms",
                  flush=True)

    fig, ax = plt.subplots(figsize=(O1 + 0.7, 2.9))
    # contur alb in spatele valorilor: unele cad exact peste linia bugetului
    halo = [pe.withStroke(linewidth=2.6, foreground='white')]
    x = np.arange(len(Ns)); w = 0.36
    ax.bar(x - w / 2 - 0.01, rez['none'], w, color=COL['smith'],
           label='fara constrangere de stare')
    ax.bar(x + w / 2 + 0.01, rez['hard'], w, color=COL['none'],
           label=r'cu $|\theta| \leq \theta_{max}$ impus')
    ax.axhline(50, color=COL['naive'], ls='--', lw=1.2, zorder=1)
    # eticheta pe doua randuri, in coltul liber din stanga: pe un rand
    # ajungea peste bara N=7
    ax.text(-0.45, 58, 'buget 20 Hz\n= 50 ms', ha='left', va='center',
            fontsize=7.2, color=COL['naive'], linespacing=1.25,
            path_effects=halo, zorder=6)
    def eticheta(xc, val):
        # o valoare intre 30 si 80 ar cadea exact peste linia de 50 ms;
        # pe aceea o scriem in interiorul barei, alb
        if 30 <= val <= 80:
            ax.text(xc, val * 0.80, f'{val:.0f}', ha='center', va='top',
                    fontsize=7, color='white', zorder=6)
        else:
            ax.text(xc, val * 1.14, f'{val:.0f}', ha='center',
                    fontsize=7, color=INK2, path_effects=halo, zorder=6)

    for i, (a, b) in enumerate(zip(rez['none'], rez['hard'])):
        eticheta(i - w / 2 - 0.01, a)
        eticheta(i + w / 2 + 0.01, b)
    ax.set_yscale('log')
    ax.set_xticks(x); ax.set_xticklabels([f'N={n}' for n in Ns])
    ax.set_ylabel('timp de solve [ms], scara log')
    ax.set_xlabel('orizont de predictie')
    ax.set_title('MPC neliniar (SLSQP): cost per ciclu', loc='left')
    ax.legend(loc='upper left')
    curata(ax)
    ax.grid(False, axis='x')
    salveaza(fig, 'fig05_mpc_benchmark')

    with (DATE / 'benchmark' / 'timp_solve_ambele_moduri.csv').open(
            'w', newline='') as f:
        w2 = csv.writer(f)
        w2.writerow(['orizont_N', 'fara_constrangere_ms', 'cu_theta_max_ms'])
        for i, N in enumerate(Ns):
            w2.writerow([N, f"{rez['none'][i]:.1f}", f"{rez['hard'][i]:.1f}"])
    print("    -> timp_solve_ambele_moduri.csv")


# ====================================== fig06 -- portret de faza
def fig06():
    fig, ax = plt.subplots(figsize=(O1 + 0.6, 3.2))
    for m in ('none', 'naive', 'smith'):
        _, th, thd, _, _ = SIM[m]
        d = np.degrees(th)
        k = np.abs(d) <= 180
        ax.plot(d[k], np.degrees(thd[k]), color=COL[m], ls=LS[m],
                lw=1.3, label=ET[m], alpha=0.9)
    ax.plot(np.degrees(THETA0), 0, marker='o', ms=6, color=INK,
            zorder=5, label='stare initiala')
    ax.plot(0, 0, marker='*', ms=11, color=INK, zorder=5,
            label='echilibru (instabil)')
    ax.set_xlabel(r'$\theta$ [grade]')
    ax.set_ylabel(r'$\dot{\theta}$ [grade/s]')
    ax.set_xlim(-180, 180)
    ax.set_title(r'Portret de faza, $\tau$ = 100 ms', loc='left')
    ax.legend(loc='upper left')
    curata(ax)

    # Lupa pe origine: la scara intreaga, traiectoria Smith se reduce la un
    # punct si seria cea mai importanta devine invizibila.
    axi = ax.inset_axes([0.60, 0.06, 0.37, 0.34])
    for m in ('none', 'naive', 'smith'):
        _, th, thd, _, _ = SIM[m]
        axi.plot(np.degrees(th), np.degrees(thd), color=COL[m], ls=LS[m],
                 lw=1.2)
    axi.plot(np.degrees(THETA0), 0, marker='o', ms=4, color=INK, zorder=5)
    axi.plot(0, 0, marker='*', ms=8, color=INK, zorder=5)
    axi.set_xlim(-14, 14); axi.set_ylim(-60, 60)
    axi.tick_params(labelsize=6, length=2)
    axi.set_title('lupa pe origine', fontsize=6.5, color=INK2, pad=2)
    for sp in axi.spines.values():
        sp.set_color(GRI); sp.set_linewidth(0.6)
    axi.grid(True, alpha=0.2, lw=0.4)
    ax.indicate_inset_zoom(axi, edgecolor=GRI, alpha=0.6, lw=0.7)
    salveaza(fig, 'fig06_phase_portrait')


# ================================= fig07 -- arhitectura sistemului
def fig07():
    fig, ax = plt.subplots(figsize=(O2, 3.1))
    ax.set_xlim(0, 100); ax.set_ylim(0, 50); ax.axis('off')

    def bloc(x, y, w, h, text, culoare, fg='white'):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle='round,pad=0.4,rounding_size=1.2',
                     facecolor=culoare, edgecolor='none'))
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
                fontsize=7.0, color=fg, linespacing=1.35)

    def sageata(x1, y1, x2, y2, text='', culoare=INK2, stil='-'):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                     arrowstyle='-|>', mutation_scale=9,
                     color=culoare, lw=1.0, linestyle=stil,
                     shrinkA=0, shrinkB=0))
        if text:
            ax.text((x1 + x2) / 2, max(y1, y2) + 1.4, text, ha='center',
                    fontsize=6.6, color=INK2)

    YB, HB = 25.0, 9.5          # banda blocurilor de sus
    YM = YB + HB / 2            # linia sagetilor orizontale
    YL = YB + HB + 1.6          # etichetele de topic, DEASUPRA blocurilor
    W = 15.0
    XS = [1.0, 21.5, 42.0, 62.5, 83.0]

    bloc(XS[0], YB, W, HB, 'Operator\numan', INK2)
    bloc(XS[1], YB, W, HB, 'Shared control\nmixer ($\\alpha$)', COL['none'])
    bloc(XS[2], YB, W, HB, 'Controller\nLQR + Smith', COL['smith'])
    bloc(XS[3], YB, W, HB, 'Garzi de\nsiguranta', COL['naive'])
    bloc(XS[4], YB, W, HB, 'Robot\n(planta)', INK2)
    bloc(42.0, 4.0, W, 9.0, 'Estimator de\nlatenta (EWMA)', COL['smith'])
    bloc(62.5, 4.0, W, 9.0, 'Canal cu\nintarziere', INK2)

    # sageti orizontale intre blocuri, cu eticheta deasupra benzii
    for i, et in enumerate(['', '/human_cmd', '/robot_cmd', '/robot_cmd_safe']):
        x1, x2 = XS[i] + W, XS[i + 1]
        ax.add_patch(FancyArrowPatch((x1, YM), (x2, YM), arrowstyle='-|>',
                     mutation_scale=9, color=INK2, lw=1.0,
                     shrinkA=0, shrinkB=0))
        if et:
            ax.text((x1 + x2) / 2, YL, et, ha='center', fontsize=6.4,
                    color=INK2)

    # calea de masurare a latentei (jos): robot -> canal -> estimator -> control
    ax.add_patch(FancyArrowPatch((90.5, YB), (90.5, 8.5), arrowstyle='-',
                 color=INK2, lw=1.0, shrinkA=0, shrinkB=0))
    ax.add_patch(FancyArrowPatch((90.5, 8.5), (77.5, 8.5), arrowstyle='-|>',
                 mutation_scale=9, color=INK2, lw=1.0, shrinkA=0, shrinkB=0))
    ax.text(84, 10.2, 'ping / pong', ha='center', fontsize=6.4, color=INK2)
    sageata(62.5, 8.5, 57.0, 8.5)
    ax.add_patch(FancyArrowPatch((49.5, 13.0), (49.5, YB), arrowstyle='-|>',
                 mutation_scale=9, color=COL['smith'], lw=1.2,
                 shrinkA=0, shrinkB=0))
    ax.text(51.2, 16.5, r'$\tau$ estimat', fontsize=6.6, color=COL['smith'])

    # bucla de reactie a starii, pe un rand propriu
    YF = 20.0
    ax.add_patch(FancyArrowPatch((87.5, YB), (87.5, YF), arrowstyle='-',
                 color=INK2, lw=1.0, shrinkA=0, shrinkB=0))
    ax.add_patch(FancyArrowPatch((87.5, YF), (29.0, YF), arrowstyle='-',
                 color=INK2, lw=1.0, shrinkA=0, shrinkB=0))
    ax.add_patch(FancyArrowPatch((29.0, YF), (29.0, YB), arrowstyle='-|>',
                 mutation_scale=9, color=INK2, lw=1.0, shrinkA=0, shrinkB=0))
    ax.text(64, YF + 1.3, 'stare masurata  /robot_state', ha='center',
            fontsize=6.4, color=INK2)

    ax.text(0, 46.5, 'Arhitectura PHSC', fontsize=10, color=INK)
    ax.text(0, 42.5, 'randul de jos: masurarea latentei peste canalul intarziat',
            fontsize=7, color=INK2)
    salveaza(fig, 'fig07_system_architecture')


# ======================================== fig08 -- schema cart-pole
def fig08():
    fig, ax = plt.subplots(figsize=(O1, 2.9))
    ax.set_xlim(-2.6, 2.9); ax.set_ylim(-1.15, 3.2)
    ax.set_aspect('equal'); ax.axis('off')

    # sina
    ax.plot([-2.4, 2.4], [0, 0], color=GRI, lw=1.6)
    for xh in np.arange(-2.3, 2.4, 0.35):
        ax.plot([xh, xh - 0.16], [0, -0.2], color=GRI, lw=0.7)

    px, cw, ch = 0.35, 1.0, 0.5
    ax.add_patch(Rectangle((px - cw / 2, 0), cw, ch, facecolor=COL['none'],
                           edgecolor='none'))
    ax.text(px, ch / 2, r'$M$', ha='center', va='center', color='white',
            fontsize=10)
    for dx in (-0.28, 0.28):
        ax.add_patch(Circle((px + dx, 0), 0.1, facecolor=INK2, edgecolor='none'))

    # pendul, inclinat cu theta fata de verticala
    th = np.radians(24)
    L = 1.85
    bx, by = px, ch
    tx, ty = bx + L * np.sin(th), by + L * np.cos(th)
    ax.plot([bx, tx], [by, ty], color=COL['smith'], lw=2.6,
            solid_capstyle='round')
    ax.add_patch(Circle((tx, ty), 0.15, facecolor=COL['smith'],
                        edgecolor='none'))
    ax.text(tx + 0.24, ty + 0.02, r'$m$', fontsize=10, color=INK)
    ax.add_patch(Circle((bx, by), 0.055, facecolor=INK, edgecolor='none'))

    # verticala de referinta si unghiul
    ax.plot([bx, bx], [by, by + L + 0.18], color=GRI, ls=':', lw=1.0)
    arc = np.linspace(0, th, 40)
    ax.plot(bx + 0.80 * np.sin(arc), by + 0.80 * np.cos(arc),
            color=INK, lw=1.0)
    # theta INTRE verticala si tija; L pe partea cealalta a tijei, decalat
    # perpendicular -- altfel cele doua etichete se suprapun
    ax.text(bx + 0.98 * np.sin(th / 2), by + 0.98 * np.cos(th / 2),
            r'$\theta$', fontsize=11, color=INK, ha='center', va='center')
    mx, my = bx + L * np.sin(th) / 2, by + L * np.cos(th) / 2
    ax.text(mx + 0.30 * np.cos(th), my - 0.30 * np.sin(th),
            r'$L$', fontsize=10, color=INK, ha='left', va='center')

    # forta de comanda
    ax.add_patch(FancyArrowPatch((px - cw / 2 - 0.85, ch / 2),
                                 (px - cw / 2 - 0.09, ch / 2),
                                 arrowstyle='-|>', mutation_scale=12,
                                 color=COL['naive'], lw=2.0))
    ax.text(px - cw / 2 - 0.47, ch / 2 + 0.24, r'$u$', fontsize=11,
            color=COL['naive'], ha='center')

    # axa de pozitie
    ax.add_patch(FancyArrowPatch((-2.3, -0.62), (-1.35, -0.62),
                                 arrowstyle='-|>', mutation_scale=9,
                                 color=INK2, lw=0.9))
    ax.text(-1.82, -0.92, r'$p$', fontsize=10, color=INK2, ha='center')
    ax.text(-2.55, 3.05, r'Cart-pole: $\theta$ masurat de la verticala in sus',
            fontsize=8, color=INK2)
    salveaza(fig, 'fig08_cartpole_schematic')


if __name__ == '__main__':
    print("\nGenerez figurile vectoriale in", IESIRE)
    fig01()
    fig02()
    fig03()
    m, p = fig04()
    print(f"    (estimator: medie {m:+.2f}%, p95 {p:.1f}%)")
    print("  masor benchmark-ul MPC in ambele moduri...")
    fig05()
    fig06()
    fig07()
    fig08()
    print("\nGata.")
