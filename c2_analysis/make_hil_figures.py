#!/usr/bin/env python3
"""make_hil_figures.py -- figurile v1.0 ale campaniei HIL (Wi-Fi, doua masini).

READ-ONLY pe date (arhivele sunt sigilate a-w). Scrie EXCLUSIV in
~/DATE_CAMPANIE/ANALIZA_C2/fig/ -- PNG la 300 dpi si PDF pentru fiecare figura.
matplotlib PUR (fara seaborn), paleta si regulile de casa din make_figures_c2.py:
Tol (#4477AA cdds / #AA3377 zenoh), rosu inchis pentru esec total, legende DEASUPRA
axelor, grid punctat, latimi fizice IEEE (7.16in 2-coloane / 3.4in 1-coloana), EN.

Statisticile vin din make_hil_tables.py, deci figurile si tabelele NU pot diverge:
mediana pe rularile SUPRAVIETUITOARE (n>0), esecul separat ca n0=k/N.

Figuri:
  F1 fig_hil_heatmap_mirror  -- FIGURA CENTRALA: doua panouri oglinda (cdds | zenoh),
     L={5,15,30}% x B={1,3,8}, culoare = mediana livrarii pe supravietuitori, fiecare
     celula adnotata cu n0=k/10. B=1 e randul Bernoulli (bern_L, memoryless).
  F2 fig_hil_delivery_vs_B   -- livrare vs B, un panou per L, ambele RMW, banda min-max
     pe supravietuitori; celulele 10/10 moarte marcate explicit (nu lipsesc in tacere).
  F3 fig_hil_discovery_prefix-- prefixul de discovery: first_seq median vs L (4KB),
     cdds ca si curba, zenoh ca referinta; L=0 e conditia 'ideal'.
  F4 fig_hil_sil_vs_hil_zenoh-- zenoh 4KB, perechi de bare SIL vs HIL pe conditiile comune.

Uz:
  python3 make_hil_figures.py [ARH_4K] [ARH_64K] [--out DIR]
  python3 make_hil_figures.py --selftest     # date sintetice, fara arhive reale
"""
import os
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_hil_tables import (ARH_4K_DEFAULT, ARH_64K_DEFAULT, OUT_DEFAULT, PAY_4K,
                             RMWS, SIL_4K_TIPARE, celula, comune, descopera_arhive)

COLOR = {"cyclonedds": "#4477AA", "zenoh": "#AA3377"}
LABEL = {"cyclonedds": "rmw_cyclonedds", "zenoh": "rmw_zenoh"}
RECV0 = "#7A0000"
DPI = 300
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "legend.fontsize": 7})

LS = [5, 15, 30]
BS = [1, 3, 8]


def cond_LB(L, B):
    """Numele conditiei pentru (L, B). B=1 = Bernoulli (memoryless), altfel Gilbert."""
    return "bern_%d" % L if B == 1 else "ge_%d_%d" % (L, B)


def legend_above(ax, ncol=2):
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=ncol,
              frameon=False, fontsize=7, handletextpad=0.4, columnspacing=1.2)


def salveaza(fig, out, nume):
    """PNG (300 dpi) + PDF, aceeasi figura."""
    caiuri = []
    for ext in ("png", "pdf"):
        p = os.path.join(out, "%s.%s" % (nume, ext))
        fig.savefig(p, dpi=DPI, bbox_inches="tight")
        caiuri.append(p)
    plt.close(fig)
    return caiuri


def grila(root, payload=PAY_4K):
    """{(rmw, L, B): celula} pentru toata grila L x B."""
    return {(rmw, L, B): celula(root, rmw, cond_LB(L, B), payload)
            for rmw in RMWS for L in LS for B in BS}


# ------------------------------------------------------------------------ figuri
def fig_heatmap(G, out):
    """F1: doua panouri oglinda; culoarea = mediana livrarii pe supravietuitori.
    Celula fara niciun supravietuitor nu are mediana -> se hasureaza si se scrie 'n0=10/10'
    (un 0 colorat ar sugera fals ca 'a livrat 0%', cand de fapt NU exista masuratoare)."""
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.9))
    for ax, rmw in zip(axes, RMWS):
        M = [[G[(rmw, L, B)]["liv_med"] for B in BS] for L in LS]
        im = ax.imshow([[(v if v is not None else float("nan")) for v in row] for row in M],
                       cmap="viridis", vmin=0, vmax=100, aspect="auto", origin="upper")
        for i, L in enumerate(LS):
            for j, B in enumerate(BS):
                c = G[(rmw, L, B)]
                if c["liv_med"] is None:
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=True,
                                               facecolor="#DDDDDD", hatch="xx",
                                               edgecolor=RECV0, linewidth=0.6))
                    # eticheta pe fundal opac: altfel hasura o face ilizibila
                    ax.text(j, i, "no data\nn0=%d/%d" % (c["n0"], c["N"]), ha="center",
                            va="center", fontsize=6.5, color=RECV0, fontweight="bold",
                            bbox=dict(facecolor="white", edgecolor=RECV0, linewidth=0.4,
                                      boxstyle="round,pad=0.25", alpha=0.95))
                else:
                    alb = c["liv_med"] < 55
                    ax.text(j, i, "%.1f%%" % c["liv_med"], ha="center", va="bottom",
                            fontsize=7.5, color="white" if alb else "black")
                    ax.text(j, i, "n0=%d/%d" % (c["n0"], c["N"]), ha="center", va="top",
                            fontsize=6,
                            color=(RECV0 if c["n0"] else ("white" if alb else "black")))
        ax.set_xticks(range(len(BS)))
        ax.set_xticklabels(["B=1\n(bern)" if b == 1 else "B=%d" % b for b in BS], fontsize=7)
        ax.set_yticks(range(len(LS)))
        ax.set_yticklabels(["L=%d%%" % L for L in LS], fontsize=7)
        ax.set_title(LABEL[rmw])
        ax.set_xlabel("mean burst length B [pkts]", fontsize=7.5)
    axes[0].set_ylabel("mean loss L", fontsize=7.5)
    cb = fig.colorbar(im, ax=axes, fraction=0.035, pad=0.02)
    cb.set_label("median delivery ratio over SURVIVING runs [%]", fontsize=7)
    fig.suptitle("HIL Wi-Fi, 4 KB payload, N=10 per cell "
                 "(median conditioned on survivors; n0 = runs with zero samples)",
                 fontsize=8, y=1.06)
    return salveaza(fig, out, "fig_hil_heatmap_mirror")


def fig_delivery_vs_B(G, out):
    """F2: livrare vs B, cate un panou per L; banda min-max pe supravietuitori."""
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.5), sharey=True)
    for ax, L in zip(axes, LS):
        for rmw in RMWS:
            cs = [G[(rmw, L, B)] for B in BS]
            xs = [B for B, c in zip(BS, cs) if c["liv_med"] is not None]
            ys = [c["liv_med"] for c in cs if c["liv_med"] is not None]
            lo = [c["liv_min"] for c in cs if c["liv_med"] is not None]
            hi = [c["liv_max"] for c in cs if c["liv_med"] is not None]
            if xs:
                ax.fill_between(xs, lo, hi, color=COLOR[rmw], alpha=0.18, linewidth=0)
                ax.plot(xs, ys, marker="o", ms=4, lw=1.3, color=COLOR[rmw],
                        label=LABEL[rmw])
            for B, c in zip(BS, cs):
                if c["liv_med"] is None:            # celula 10/10 moarta: marcata EXPLICIT
                    ax.scatter([B], [0], marker="x", s=28, color=RECV0, zorder=6)
                    ax.text(B, 3, "%d/%d dead" % (c["n0"], c["N"]), color=RECV0,
                            fontsize=6, ha="center", va="bottom", rotation=90)
                elif c["n0"]:
                    ax.text(B, c["liv_med"] + 4, "n0=%d/%d" % (c["n0"], c["N"]),
                            color=RECV0, fontsize=6, ha="center", va="bottom")
        ax.set_title("mean loss L=%d%%" % L)
        ax.set_xlabel("mean burst length B [pkts]", fontsize=8)
        ax.set_xticks(BS)
        ax.set_xticklabels(["1\n(bern)" if b == 1 else "%d" % b for b in BS], fontsize=7)
        ax.set_ylim(-3, 105)
        ax.grid(True, ls=":", lw=0.4, alpha=0.6)
    axes[0].set_ylabel("delivery ratio [%]", fontsize=8)
    # legenda de FIGURA, deasupra titlurilor de panou (altfel se suprapune peste cel din
    # mijloc), si auto-explicativa: banda si crucea sunt explicate acolo, nu in axa Y
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    manere = [Line2D([0], [0], color=COLOR[r], marker="o", ms=4, lw=1.3, label=LABEL[r])
              for r in RMWS]
    manere.append(Patch(facecolor="#888888", alpha=0.3, label="min-max over survivors"))
    manere.append(Line2D([0], [0], color=RECV0, marker="x", ls="none", ms=6,
                         label="all N runs dead"))
    fig.legend(handles=manere, loc="upper center", bbox_to_anchor=(0.5, 1.11), ncol=4,
               frameon=False, fontsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return salveaza(fig, out, "fig_hil_delivery_vs_B")


def fig_discovery(root, out):
    """F3: prefixul de discovery = first_seq median vs L. L=0 este conditia 'ideal'.
    Linia = mediana peste conditiile de la acel L (bern, ge_3, ge_8); punctele mici =
    celulele individuale, ca un outlier (o singura conditie cu prefix urias) sa fie VIZIBIL,
    nu inghitit de mediana. Scala log: valorile se intind pe doua ordine de marime."""
    xs = [0] + LS
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    for rmw in RMWS:
        ys, pts_x, pts_y = [], [], []
        for L in xs:
            if L == 0:
                v = [celula(root, rmw, "ideal", PAY_4K)["first_seq_med"]]
            else:
                v = [celula(root, rmw, cond_LB(L, B), PAY_4K)["first_seq_med"] for B in BS]
            v = [x for x in v if x is not None]
            ys.append(statistics.median(v) if v else float("nan"))
            for x in v:
                pts_x.append(L)
                pts_y.append(x)
        ax.scatter(pts_x, pts_y, s=9, color=COLOR[rmw], alpha=0.45, zorder=4,
                   edgecolors="none")
        ax.plot(xs, ys, marker="o", ms=4, lw=1.3, color=COLOR[rmw], label=LABEL[rmw],
                zorder=5)
    ax.axhline(11, color="black", lw=0.8, ls="--")
    ax.set_yscale("log")
    ax.set_yticks([11, 20, 50, 100, 200, 500, 1000])
    ax.set_yticklabels(["11", "20", "50", "100", "200", "500", "1000"], fontsize=7)
    ax.set_ylim(9, 1400)
    # nota in coltul liber din stanga-sus, ca sa nu treaca peste curbe
    ax.text(-1, 700, "dashed: seq 11 = first eligible\n(10 warm-up samples ignored)",
            fontsize=5.5, va="top", ha="left")
    ax.set_xticks(xs)
    ax.set_xticklabels(["0\n(ideal)"] + ["%d" % L for L in LS], fontsize=7)
    ax.set_xlim(-2, 33)
    ax.set_xlabel("mean loss L [%]", fontsize=8)
    ax.set_ylabel("first delivered seq\n(line = median over B; dots = cells)", fontsize=7)
    ax.grid(True, ls=":", lw=0.4, alpha=0.6)
    legend_above(ax, ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    return salveaza(fig, out, "fig_hil_discovery_prefix")


def fig_sil_vs_hil(perechi, out):
    """F4: zenoh 4KB, perechi de bare SIL vs HIL pe conditiile comune."""
    p = [(c, s, h) for c, rmw, s, h, *_ in perechi if rmw == "zenoh"]
    fig, ax = plt.subplots(figsize=(7.16, 2.6))
    x = list(range(len(p)))
    w = 0.38
    for i, (eticheta, cheie, culoare, hatch) in enumerate(
            [("SIL (loopback)", 1, "#BBBBBB", None), ("HIL (Wi-Fi)", 2, COLOR["zenoh"], None)]):
        ys = [(t[cheie]["liv_med"] if t[cheie]["liv_med"] is not None else 0.0) for t in p]
        xs = [xi + (i - 0.5) * w for xi in x]
        ax.bar(xs, ys, width=w, color=culoare, edgecolor="black", linewidth=0.4,
               hatch=hatch, label=eticheta)
        # adnotarile stau VERTICAL, fiecare peste bara ei: barele sunt inguste si doua
        # etichete orizontale vecine se lipeau intre ele ('n0=5' + '10/10 dead')
        for xi, t in zip(xs, p):
            c = t[cheie]
            if c["liv_med"] is None:
                ax.text(xi, 2, "%d/%d dead" % (c["n0"], c["N"]), color=RECV0, fontsize=5.5,
                        ha="center", va="bottom", rotation=90)
            elif c["n0"]:
                ax.text(xi, c["liv_med"] + 2, "n0=%d" % c["n0"], color=RECV0, fontsize=5.5,
                        ha="center", va="bottom", rotation=90)
    ax.set_ylim(-3, 125)
    ax.set_ylabel("median delivery ratio [%]\n(survivors only)", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels([t[0] for t in p], rotation=45, ha="right", fontsize=7)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    ax.set_title("rmw_zenoh, 4 KB: same conditions, two environments", fontsize=8)
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.10), ncol=2, frameon=False,
               fontsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return salveaza(fig, out, "fig_hil_sil_vs_hil_zenoh")


def genereaza(arh4, arh64, out):
    """Toate figurile; intoarce lista de cai scrise."""
    os.makedirs(out, exist_ok=True)
    G = grila(arh4)
    caiuri = []
    caiuri += fig_heatmap(G, out)
    caiuri += fig_delivery_vs_B(G, out)
    caiuri += fig_discovery(arh4, out)
    sil4 = descopera_arhive(SIL_4K_TIPARE)      # grila + combo
    if sil4:
        caiuri += fig_sil_vs_hil(comune(sil4, arh4, PAY_4K), out)
    else:
        print("  (F4 sarita: nu am gasit arhiva SIL 4KB pe disc)")
    return caiuri


# ------------------------------------------------------------------------ selftest
def _selftest():
    """Date SINTETICE (nicio arhiva reala citita): se construieste un arbore minimal cu
    grila completa L x B + ideal, cu o celula 10/10 moarta, si se verifica DOAR mecanica:
    fisierele apar, au continut, iar celula moarta nu inventeaza valori."""
    import json
    import shutil
    import tempfile
    baza = tempfile.mkdtemp(prefix="hil_figuri_selftest_")
    root = os.path.join(baza, "ARH")
    out = os.path.join(baza, "fig")
    try:
        def scrie_cond(rmw, cond, livrari, first=11):
            """livrari: lista de procente (0 = rulare moarta)."""
            for k, pct in enumerate(livrari, 1):
                rd = os.path.join(root, rmw, cond, "rep%d" % k)
                os.makedirs(rd)
                n = int(round(pct))
                with open(os.path.join(rd, "transport_p4096.csv"), "w") as f:
                    f.write("seq,rtt_ms\n")
                    for s in range(first, first + n):
                        f.write("%d,1.0\n" % s)
                with open(os.path.join(rd, "transport_p4096_summary.json"), "w") as f:
                    json.dump({"n": n, "sent": 100, "received": n}, f)

        for rmw in RMWS:
            scrie_cond(rmw, "ideal", [100] * 10)
            for L in LS:
                for B in BS:
                    if rmw == "zenoh" and L == 30:
                        scrie_cond(rmw, cond_LB(L, B), [0] * 10)      # celula moarta
                    else:
                        scrie_cond(rmw, cond_LB(L, B), [100 - L] * 8 + [100 - L - 5, 0],
                                   first=11 + L)
        G = grila(root)
        moarta = G[("zenoh", 30, 8)]
        assert moarta["liv_med"] is None and moarta["n0"] == 10, moarta
        vie = G[("cyclonedds", 5, 3)]
        assert vie["n0"] == 1 and vie["liv_med"] == 95.0, vie

        os.makedirs(out)
        caiuri = fig_heatmap(G, out) + fig_delivery_vs_B(G, out) + fig_discovery(root, out)
        assert len(caiuri) == 6, caiuri                    # 3 figuri x (png + pdf)
        for p in caiuri:
            assert os.path.isfile(p) and os.path.getsize(p) > 1000, p
        assert sorted(os.path.basename(p) for p in caiuri) == [
            "fig_hil_delivery_vs_B.pdf", "fig_hil_delivery_vs_B.png",
            "fig_hil_discovery_prefix.pdf", "fig_hil_discovery_prefix.png",
            "fig_hil_heatmap_mirror.pdf", "fig_hil_heatmap_mirror.png"], caiuri
        # F4 pe perechi sintetice SIL/HIL
        perechi = [("bern_15", "zenoh", G[("zenoh", 15, 1)], G[("zenoh", 15, 3)]),
                   ("ge_30_8", "zenoh", G[("zenoh", 15, 8)], G[("zenoh", 30, 8)])]
        c4 = fig_sil_vs_hil(perechi, out)
        assert len(c4) == 2 and all(os.path.getsize(p) > 1000 for p in c4), c4
        assert cond_LB(15, 1) == "bern_15" and cond_LB(15, 8) == "ge_15_8"
        print("SELFTEST make_hil_figures OK (12 verificari, date sintetice in /tmp).")
    finally:
        shutil.rmtree(baza, ignore_errors=True)


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    poz = [a for a in argv if not a.startswith("--")]
    out = os.path.join(OUT_DEFAULT, "fig")
    if "--out" in argv:
        out = os.path.expanduser(argv[argv.index("--out") + 1])
    arh4 = os.path.expanduser(poz[0]) if len(poz) > 0 else ARH_4K_DEFAULT
    arh64 = os.path.expanduser(poz[1]) if len(poz) > 1 else ARH_64K_DEFAULT
    if not os.path.isdir(arh4):
        print("arhiva inexistenta: %s" % arh4)
        return 2
    print("ARH 4K : %s" % arh4)
    print("iesire : %s" % out)
    for p in genereaza(arh4, arh64, out):
        print("  scris %s (%d octeti)" % (p, os.path.getsize(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
