#!/usr/bin/env python3
"""make_figures_c2.py -- figurile analizei SIL C2 (read-only pe date, fara ROS/retea).
UN script, EN, paleta identica cu make_figures_c1_en (Tol). Regenerabil din date.

changelog:
  v1.0 (2026-07-19): F1 delivery vs B; F2 longest burst; F3 64KB inversion; F4 combo.
  v1.1 (2026-07-19): reguli de casa -- legende DEASUPRA axelor (ncol=2, frameon=False);
    dispersie peste tot cu whiskere taiate la [0,100]; conventie recv0 "n0=k/10" (rosu
    inchis, orizontal, la baza); dimensiuni fizice IEEE (F1/F2 2-col 7.16in, F3/F4 1-col
    3.4in), DPI=300. F2: zero-uri explicite + p95 suprapus + axa secundara in secunde.
    F3: hatch pe 64KB + erori. F4: ordine bern->ge->C1->combo, C1 hatch+eticheta, puncte
    individuale (bimodalitate) pe combo.
  v2.0 (2026-08-04): ARATA TOATE RULARILE. Media+-std a fost inlocuita peste tot cu
    STRIP-uri: fiecare repetitie e un punct (jitter determinist +-0.08, alpha 0.8), iar
    mediana e o liniuta orizontala lata. Motivul: la N=10 cu distributii bimodale (o parte
    din rulari livreaza, alta parte cade la zero) media si deviatia descriu o populatie
    care nu exista; punctele arata forma reala, iar cititorul vede si dispersia si
    outlierii. Consecinte de asezare:
      - eticheta n0 ("k/N", rulari cu received=0) sta SUB axa, in banda proprie -- niciodata
        in interiorul panoului, unde ar fi acoperit puncte;
      - F1: x CATEGORIAL (B=1,3,8 la pozitii egale), fara linii de legatura -- B nu e o
        scala continua si o linie ar sugera interpolare intre valori masurate;
      - F2 (64KB): forma markerului codifica sarcina utila, culoarea RMW-ul; fara error bars;
      - F4: lollipop pe symlog, max plin + p95 romb gol, cu axa secundara in secunde.
    Iesirea s-a mutat in ~/DATE_CAMPANIE/ANALIZA_C2/fig/ (langa restul analizei), cu
    ACELEASI nume de fisier; se scriu PNG (300 dpi) si PDF.
"""
import os
import statistics as st
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_tables_c2 import delivery, bursts, ROOT4, ROOT64, ROOTCOMBO, ROOTC1

# Paleta EXACTA din make_figures_c1_en.py (Tol):
COLOR_CDDS = "#4477AA"
COLOR_ZENOH = "#AA3377"
COLOR = {"cyclonedds": COLOR_CDDS, "zenoh": COLOR_ZENOH}
LABEL = {"cyclonedds": "rmw_cyclonedds", "zenoh": "rmw_zenoh"}
RECV0 = "#7A0000"
DPI = 300
RMWS = ("cyclonedds", "zenoh")
HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, "DATE_CAMPANIE", "ANALIZA_C2", "fig")
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "legend.fontsize": 7})

JITTER = 0.08          # semi-latimea benzii de puncte
N0_Y = -0.13           # pozitia benzii n0, in fractiuni de axa (NEGATIV = sub panou)


def _jitter(n):
    """Deviatii deterministe in [-JITTER, +JITTER], bine imprastiate si NEmonotone
    (secventa cu pas de sectiune de aur). Determinist = figura identica la fiecare rulare."""
    if n <= 1:
        return [0.0]
    return [((i * 0.6180339887) % 1.0 - 0.5) * 2 * JITTER for i in range(n)]


def strip_cell(ax, x_center, values, color, marker="o", hollow=False, size=13):
    """TOATE rularile unei celule, ca puncte cu jitter, plus mediana ca liniuta lata.
    Fara medie si fara deviatie standard: la distributii bimodale ele mint.
    Intoarce mediana (None pe celula fara nicio rulare)."""
    if not values:
        return None
    xs = [x_center + d for d in _jitter(len(values))]
    ax.scatter(xs, values, marker=marker, s=size, alpha=0.8, zorder=4,
               facecolors="none" if hollow else color,
               edgecolors=color, linewidths=0.9)
    med = st.median(values)
    # liniuta medianei se leaga de latimea norului de puncte, nu e o constanta: la
    # figurile cu sloturi apropiate (F2, 0.18 intre sloturi) o liniuta fixa mai lata
    # decat slotul intra peste vecin si cele doua mediane par una singura
    w = JITTER * 1.15
    ax.plot([x_center - w, x_center + w], [med, med], lw=1.9, color=color,
            solid_capstyle="butt", zorder=6)
    return med


def n0_band(ax, x, k, N):
    """Eticheta 'k/N' (rulari cu received=0) in BANDA DE SUB AXA: x in coordonate de date,
    y in fractiuni de axa (negativ), clip_on=False ca sa nu fie taiata de panou.
    NU se deseneaza niciodata in interiorul axelor -- acolo ar acoperi exact punctele pe
    care figura vrea sa le arate. Apelantul decide cand o cheama (de regula doar k>0).
    Intoarce obiectul Text, ca sa poata fi verificat geometric in selftest."""
    return ax.text(x, N0_Y, "%d/%d" % (k, N), transform=ax.get_xaxis_transform(),
                   ha="center", va="top", fontsize=5.8, color=RECV0, clip_on=False)


def salveaza(fig, nume, out=None):
    """PNG (300 dpi) + PDF, acelasi continut. Intoarce caile scrise."""
    out = out or OUT
    os.makedirs(out, exist_ok=True)
    caiuri = []
    for ext in ("png", "pdf"):
        p = os.path.join(out, "%s.%s" % (nume, ext))
        fig.savefig(p, dpi=DPI, bbox_inches="tight")
        caiuri.append(p)
    plt.close(fig)
    return caiuri


def axa_secundara_secunde(ax, hz=50.0):
    """Axa din dreapta: ACELEASI valori, citite in secunde (la rata fixa de esantionare).
    Scala se impune EXPLICIT identica cu a parintelui (symlog): axa secundara construita
    din functii ramane altfel LINIARA, iar gradatiile ei ar cadea la inaltimi care nu
    corespund valorilor de pe stanga (verificat: eticheta '2 s' ajungea la 25% din
    inaltime in loc de dreptul lui 100 pkts). Alinierea e blocata de selftest."""
    sec = ax.secondary_yaxis("right", functions=(lambda p: p / hz, lambda s: s * hz))
    sec.set_yscale("symlog", linthresh=1.0 / hz)
    sec.set_yticks([0, 1 / hz, 10 / hz, 100 / hz, 400 / hz])
    sec.set_yticklabels(["0", "0.02", "0.2", "2", "8"], fontsize=7)
    sec.set_ylabel("gap duration [s] @ %g Hz" % hz, fontsize=7.5)
    return sec


def _handle(rmw):
    return Line2D([0], [0], marker="o", ls="none", color=COLOR[rmw], label=LABEL[rmw],
                  ms=4.5)


# --------------------------------------------------------------------------- F1
def fig_delivery_vs_B(root4, out=None):
    """F1: livrare vs B, un panou per L. x CATEGORIAL (B=1,3,8 la pozitii egale) si
    FARA linii de legatura: B ia trei valori discrete, iar o linie ar sugera ca stim ce
    se intampla intre ele. Doua strip-uri per B (cdds, zenoh)."""
    Ls = [(5, ["bern_5", "ge_5_3", "ge_5_8"]), (15, ["bern_15", "ge_15_3", "ge_15_8"]),
          (30, ["bern_30", "ge_30_3", "ge_30_8"])]
    B = [1, 3, 8]
    xpos = [0, 1, 2]                        # pozitii EGALE, categoriale
    dx = 0.17
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.7), sharey=True,
                             constrained_layout=True)
    for ax, (L, conds) in zip(axes, Ls):
        for i, rmw in enumerate(RMWS):
            for x, c in zip(xpos, conds):
                dv, r0, _ = delivery(root4, rmw, c)
                xc = x + (i - 0.5) * 2 * dx
                strip_cell(ax, xc, dv, COLOR[rmw])
                if r0:
                    n0_band(ax, xc, r0, len(dv))
        ax.set_title("mean loss L=%d%%" % L)
        ax.set_xlabel("mean burst length B [pkts]", fontsize=8)
        ax.set_xticks(xpos)
        ax.set_xticklabels(["1\n(bern)", "3", "8"], fontsize=7.5)
        ax.set_xlim(-0.5, 2.5)
        ax.set_ylim(-3, 105)
        ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    axes[0].set_ylabel("delivery ratio [%]")
    manere = [_handle(r) for r in RMWS]
    manere.append(Line2D([0], [0], color="black", lw=1.9, label="median"))
    manere.append(Line2D([0], [0], marker="$k/N$", ls="none", color=RECV0, ms=11,
                         label="runs with zero delivery (below axis)"))
    fig.legend(handles=manere, loc="outside upper center", ncol=4, frameon=False,
               fontsize=7)
    return salveaza(fig, "fig_c2_delivery_vs_B", out)


# --------------------------------------------------------------------------- F2
def fig_64k_inversion(root4, root64, out=None):
    """F2: 4KB vs 64KB pe {bern_15, ge_15_8}. Forma markerului = sarcina utila
    (cerc 4KB, romb 64KB), culoarea = RMW. Fara error bars: se vad toate rularile."""
    conds = ["bern_15", "ge_15_8"]
    fig, ax = plt.subplots(figsize=(7.16, 2.7))
    slots = [("cyclonedds", 4096, -0.27, "o"), ("cyclonedds", 65536, -0.09, "D"),
             ("zenoh", 4096, 0.09, "o"), ("zenoh", 65536, 0.27, "D")]
    for x, c in enumerate(conds):
        for rmw, pay, off, mk in slots:
            root = root64 if pay == 65536 else root4
            dv, r0, _ = delivery(root, rmw, c, pay)
            xc = x + off
            strip_cell(ax, xc, dv, COLOR[rmw], marker=mk, size=15)
            if r0:
                n0_band(ax, xc, r0, len(dv))
    ax.set_ylim(-3, 105)
    ax.set_xlim(-0.5, len(conds) - 0.5)
    ax.set_ylabel("delivery ratio [%]")
    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels(conds, fontsize=8)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    manere = [_handle(r) for r in RMWS] + [
        Line2D([0], [0], marker="o", ls="none", mfc="none", mec="black", ms=4.5,
               label="4 KB payload"),
        Line2D([0], [0], marker="D", ls="none", mfc="none", mec="black", ms=4.5,
               label="64 KB payload")]
    ax.legend(handles=manere, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=4,
              frameon=False, fontsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    return salveaza(fig, "fig_c2_64k_inversion", out)


# --------------------------------------------------------------------------- F3
def fig_combo_context(root4, rootcombo, rootc1, out=None):
    """F3: contextul combinatiei latenta+rafala. Patru conditii, toate ca strip-uri;
    referinta C1 (alta campanie, protocol byte-identic) are markere GOALE, ca sa nu fie
    citita ca masuratoare C2. Etichetele x pe doua randuri; figura cu 30% mai lata decat
    formatul 1-coloana, altfel etichetele se calca."""
    sets = [("bern_15", "C2 4KB", root4, "bern_15", 4096, False),
            ("ge_15_8", "C2 4KB", root4, "ge_15_8", 4096, False),
            ("lat200_jit50", "C1 SIL ref", rootc1, "lat200_jit50", 4096, True),
            ("lat+ge_15_8", "C2 combo", rootcombo, "lat200_jit50_ge_15_8", 4096, False)]
    fig, ax = plt.subplots(figsize=(3.4 * 1.3, 2.6))
    dx = 0.17
    for x, (_, _, root, cond, pay, hollow) in enumerate(sets):
        for i, rmw in enumerate(RMWS):
            dv, r0, _ = delivery(root, rmw, cond, pay)
            xc = x + (i - 0.5) * 2 * dx
            strip_cell(ax, xc, dv, COLOR[rmw], hollow=hollow)
            if r0:
                n0_band(ax, xc, r0, len(dv))
    ax.set_ylim(-3, 105)
    ax.set_xlim(-0.5, len(sets) - 0.5)
    ax.set_ylabel("delivery ratio [%]")
    ax.set_xticks(range(len(sets)))
    ax.set_xticklabels(["%s\n%s" % (s[0], s[1]) for s in sets], fontsize=6.8)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    manere = [_handle(r) for r in RMWS] + [
        Line2D([0], [0], marker="o", ls="none", mfc="none", mec="black", ms=4.5,
               label="C1 reference (hollow)")]
    ax.legend(handles=manere, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3,
              frameon=False, fontsize=6.5)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    return salveaza(fig, "fig_c2_combo_context", out)


# --------------------------------------------------------------------------- F4
def fig_longest_burst(root4, out=None):
    """F4: cea mai lunga rafala de esec. Lollipop pe symlog: tija de la 0, marker plin =
    maximul peste repetitii, romb GOL = p95. Zerourile raman la 0 si se vad ca atare
    (un zero e REZULTAT, nu date lipsa). Axa secundara: aceleasi valori in secunde."""
    conds = ["bern_5", "ge_5_3", "ge_5_8", "bern_15", "ge_15_3", "ge_15_8",
             "bern_30", "ge_30_3", "ge_30_8"]
    fig, ax = plt.subplots(figsize=(7.16, 2.7))
    dx = 0.18
    for x, c in enumerate(conds):
        for i, rmw in enumerate(RMWS):
            b = bursts(root4, rmw, c)
            xc = x + (i - 0.5) * 2 * dx
            ax.vlines(xc, 0, b["longest_max"], color=COLOR[rmw], lw=1.1, alpha=0.85,
                      zorder=3)
            # p95 = romb GOL, mai mare; max = cerc plin, DEASUPRA. La N=10 p95 coincide
            # des cu maximul: asa cercul ramane vizibil INAUNTRUL rombului, in loc sa fie
            # acoperit de el (altfel 'max' dispare din figura exact unde conteaza).
            ax.plot([xc], [b["longest_p95"]], marker="D", ms=7.0, mfc="none",
                    mec=COLOR[rmw], mew=1.0, zorder=5)
            ax.plot([xc], [b["longest_max"]], marker="o", ms=3.8, color=COLOR[rmw],
                    zorder=7)
            if b["longest_max"] == 0:
                ax.text(xc, 0.06, "0", color=RECV0, fontsize=6, ha="center", va="bottom")
    ax.set_yscale("symlog", linthresh=1)
    ax.set_ylim(0, 400)
    ax.set_ylabel("longest failure burst [pkts]", fontsize=8)
    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels(conds, rotation=45, ha="right", fontsize=7)
    ax.set_xlim(-0.5, len(conds) - 0.5)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    axa_secundara_secunde(ax)
    manere = [_handle(r) for r in RMWS] + [
        Line2D([0], [0], marker="o", ls="none", color="black", ms=4.5,
               label="max over N runs"),
        Line2D([0], [0], marker="D", ls="none", mfc="none", mec="black", ms=4.5,
               label="p95 over N runs")]
    ax.legend(handles=manere, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=4,
              frameon=False, fontsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    return salveaza(fig, "fig_c2_longest_burst", out)


# --------------------------------------------------------------------------- test
def _selftest():
    """Date SINTETICE in /tmp (nicio arhiva reala citita). Include o celula n0=9/10 si
    verifica GEOMETRIC ca banda n0 cade SUB panou, nu in interiorul lui."""
    import json
    import shutil
    import tempfile
    baza = tempfile.mkdtemp(prefix="figuri_c2_selftest_")
    root, out = os.path.join(baza, "ARH"), os.path.join(baza, "fig")
    try:
        def scrie(rmw, cond, livrari, payload=4096, seq0=11):
            for k, pct in enumerate(livrari, 1):
                rd = os.path.join(root, rmw, cond, "rep%d" % k)
                os.makedirs(rd, exist_ok=True)   # aceeasi repetitie poate avea 2 payload-uri
                n = int(round(pct))
                with open(os.path.join(rd, "transport_p%d.csv" % payload), "w") as f:
                    f.write("seq,rtt_ms\n")
                    for s in range(seq0, seq0 + n):
                        f.write("%d,1.0\n" % (s * 2))      # goluri => rafale nenule
                with open(os.path.join(rd, "transport_p%d_summary.json" % payload), "w") as f:
                    json.dump({"n": n, "sent": 100, "received": n}, f)

        conds4 = ["bern_5", "ge_5_3", "ge_5_8", "bern_15", "ge_15_3", "ge_15_8",
                  "bern_30", "ge_30_3", "ge_30_8"]
        for rmw in RMWS:
            for c in conds4:
                scrie(rmw, c, [80, 75, 70, 65, 60, 55, 50, 45, 40, 35])
            scrie(rmw, "lat200_jit50", [90] * 10)
            scrie(rmw, "lat200_jit50_ge_15_8", [30] * 10)
            for c in ("bern_15", "ge_15_8"):
                scrie(rmw, c, [20] * 10, payload=65536)
        # celula cu 9 rulari moarte din 10 -- cazul care trebuie sa produca banda n0
        shutil.rmtree(os.path.join(root, "zenoh", "ge_30_8"))
        scrie("zenoh", "ge_30_8", [0] * 9 + [12])

        dv, r0, _ = delivery(root, "zenoh", "ge_30_8")
        assert r0 == 9 and len(dv) == 10, (r0, dv)

        # strip_cell: puncte + mediana, jitter in banda ceruta, determinist
        fig, ax = plt.subplots()
        med = strip_cell(ax, 1.0, [10.0, 20.0, 60.0], COLOR["zenoh"])
        assert med == 20.0, med
        assert strip_cell(ax, 0.0, [], COLOR["zenoh"]) is None
        j = _jitter(10)
        assert all(abs(x) <= JITTER + 1e-9 for x in j), j
        assert j == _jitter(10) and len(set(j)) == 10, "jitter nedeterminist sau repetat"
        assert _jitter(1) == [0.0]
        plt.close(fig)

        # n0_band: SUB axa (y negativ in fractiuni de axa), netaiata de panou
        fig, ax = plt.subplots()
        t = n0_band(ax, 1.0, 9, 10)
        assert t.get_text() == "9/10", t.get_text()
        assert t.get_position()[1] < 0, t.get_position()
        assert t.get_clip_on() is False
        fig.canvas.draw()
        y_disp = t.get_transform().transform(t.get_position())[1]
        assert y_disp < ax.get_window_extent().y0, "banda n0 a intrat in panou"
        plt.close(fig)

        # axa secundara in secunde: TREBUIE sa fie aliniata cu cea in pachete, altfel
        # figura minte (vezi axa_secundara_secunde)
        fig, ax = plt.subplots()
        ax.set_yscale("symlog", linthresh=1)
        ax.set_ylim(0, 400)
        sec = axa_secundara_secunde(ax)
        fig.canvas.draw()
        for pkt in (1, 10, 100):
            y_pkt = ax.transData.transform((0, pkt))[1]
            y_sec = sec.transData.transform((0, pkt / 50.0))[1]
            assert abs(y_pkt - y_sec) < 0.5, (pkt, y_pkt, y_sec)
        plt.close(fig)

        os.makedirs(out)
        caiuri = (fig_delivery_vs_B(root, out) + fig_64k_inversion(root, root, out)
                  + fig_combo_context(root, root, root, out) + fig_longest_burst(root, out))
        assert len(caiuri) == 8, caiuri                     # 4 figuri x (png + pdf)
        assert sorted(os.path.basename(p) for p in caiuri) == [
            "fig_c2_64k_inversion.pdf", "fig_c2_64k_inversion.png",
            "fig_c2_combo_context.pdf", "fig_c2_combo_context.png",
            "fig_c2_delivery_vs_B.pdf", "fig_c2_delivery_vs_B.png",
            "fig_c2_longest_burst.pdf", "fig_c2_longest_burst.png"], caiuri
        for p in caiuri:
            assert os.path.getsize(p) > 1000, p

        # in figura REALA: eticheta 9/10 exista si e sub axele panoului ei
        fig, axes = plt.subplots(1, 3, sharey=True)
        for ax, conds in zip(axes, (["bern_5", "ge_5_3", "ge_5_8"],
                                    ["bern_15", "ge_15_3", "ge_15_8"],
                                    ["bern_30", "ge_30_3", "ge_30_8"])):
            for x, c in enumerate(conds):
                dv, r0, _ = delivery(root, "zenoh", c)
                strip_cell(ax, x, dv, COLOR["zenoh"])
                if r0:
                    n0_band(ax, x, r0, len(dv))
        fig.canvas.draw()
        gasite = [(ax, t) for ax in axes for t in ax.texts if t.get_text() == "9/10"]
        assert len(gasite) == 1, [t.get_text() for ax in axes for t in ax.texts]
        ax, t = gasite[0]
        assert t.get_transform().transform(t.get_position())[1] < ax.get_window_extent().y0
        plt.close(fig)
        print("SELFTEST make_figures_c2 OK (18 verificari, date sintetice in /tmp; "
              "banda n0 verificata geometric ca fiind sub panou).")
    finally:
        shutil.rmtree(baza, ignore_errors=True)


def main(argv=()):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    os.makedirs(OUT, exist_ok=True)
    caiuri = (fig_delivery_vs_B(ROOT4) + fig_64k_inversion(ROOT4, ROOT64)
              + fig_combo_context(ROOT4, ROOTCOMBO, ROOTC1) + fig_longest_burst(ROOT4))
    for p in caiuri:
        print("  scris %s (%d octeti)" % (p, os.path.getsize(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
