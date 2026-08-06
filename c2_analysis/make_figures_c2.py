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
    Iesirea ramane in repo, c2_analysis/figuri_c2/, cu ACELEASI nume ca la v1.1 (deci
    figurile vechi sunt inlocuite, nu dublate); pe langa PNG (300 dpi) se scrie si PDF,
    pentru includere in LaTeX fara pierdere de calitate.
  v2.1 (2026-08-04): LEGENDE ONESTE. Regula unica: fiecare intrare de legenda e ori chiar
    artefactul desenat, ori un proxy IDENTIC ca proprietati (forma, plin-vs-gol, grosime).
    O legenda care promite altceva decat exista in panou e un BUG, nu o scapare estetica:
    cititorul isi calibreaza ochiul dupa cheie. Ce s-a corectat:
      - F4: proxy-urile de statistica erau NEGRE (nimic negru nu se deseneaza). Acum sunt
        GRI-neutru, cu acelasi fill-state si aceeasi marime ca in plot (max = cerc PLIN,
        p95 = romb GOL marit); culoarea o explica primele doua intrari, cele de RMW.
        Adnotarile rosii '0' au disparut -- markerul asezat la 0 pe symlog spune acelasi
        lucru fara sa adauge un al doilea limbaj vizual.
      - F3: markerele referintei C1 se deseneaza REAL goale (facecolors='none', contur mai
        gros, +30% marime) si legenda primeste EXACT acel scatter ca handle, nu o copie.
      - F2: proxy-urile de sarcina utila erau cercuri/romburi GOALE, desi in panou sunt
        PLINE; acum sunt gri PLINE.
      - F1: liniuta 'median' era neagra (in panou e colorata pe RMW) -> gri; iar cheia
        falsa cu marker-text '$k/N$' a fost scoasa din legenda (nu exista niciun marker
        de tipul asta in panou) si inlocuita cu o nota, in exact rosul textului desenat.
    Selftestul verifica acum PE PROPRIETATI: pentru fiecare intrare de legenda cauta un
    artefact desenat cu aceeasi amprenta de forma (calea markerului, normalizata) si
    acelasi fill-state; culoarea are voie sa fie fie a artefactului, fie griul neutru.
"""
import os
import statistics as st
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_tables_c2 import delivery, bursts, ROOT4, ROOT64, ROOTCOMBO, ROOTC1

# Paleta EXACTA din make_figures_c1_en.py (Tol):
COLOR_CDDS = "#4477AA"
COLOR_ZENOH = "#AA3377"
COLOR = {"cyclonedds": COLOR_CDDS, "zenoh": COLOR_ZENOH}
LABEL = {"cyclonedds": "rmw_cyclonedds", "zenoh": "rmw_zenoh"}
RECV0 = "#7A0000"
# gri NEUTRU pentru cheile care explica FORMA, nu apartenenta la un RMW (v2.1). Nu e negru:
# negrul ar sugera o a treia serie desenata, griul se citeste ca 'oricare dintre culori'.
GRI = "#555555"
DPI = 300
RMWS = ("cyclonedds", "zenoh")
HOME = os.path.expanduser("~")
# Figurile stau IN REPO, langa codul care le genereaza (regula de igiena a datelor:
# datele brute NU intra in git, dar sumarele si FIGURILE da). Numele sunt cele istorice,
# deci v2.0 suprascrie exact fisierele v1.1.
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figuri_c2")
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "legend.fontsize": 7})

JITTER = 0.08          # semi-latimea benzii de puncte
N0_Y = -0.13           # pozitia benzii n0, in fractiuni de axa (NEGATIV = sub panou)


def _jitter(n):
    """Deviatii deterministe in [-JITTER, +JITTER], bine imprastiate si NEmonotone
    (secventa cu pas de sectiune de aur). Determinist = figura identica la fiecare rulare."""
    if n <= 1:
        return [0.0]
    return [((i * 0.6180339887) % 1.0 - 0.5) * 2 * JITTER for i in range(n)]


def strip_cell(ax, x_center, values, color, marker="o", hollow=False, size=13,
               linewidth=0.9, alpha=0.8):
    """TOATE rularile unei celule, ca puncte cu jitter, plus mediana ca liniuta lata.
    Fara medie si fara deviatie standard: la distributii bimodale ele mint.
    Intoarce SCATTER-ul desenat (v2.1: ca sa poata fi dat direct legendei drept handle,
    fara proxy care ar putea diverge de el); None pe celula fara nicio rulare."""
    if not values:
        return None
    xs = [x_center + d for d in _jitter(len(values))]
    sc = ax.scatter(xs, values, marker=marker, s=size, alpha=alpha, zorder=4,
                    facecolors="none" if hollow else color,
                    edgecolors=color, linewidths=linewidth)
    med = st.median(values)
    # liniuta medianei se leaga de latimea norului de puncte, nu e o constanta: la
    # figurile cu sloturi apropiate (F2, 0.18 intre sloturi) o liniuta fixa mai lata
    # decat slotul intra peste vecin si cele doua mediane par una singura
    w = JITTER * 1.15
    ax.plot([x_center - w, x_center + w], [med, med], lw=1.9, color=color,
            solid_capstyle="butt", zorder=6)
    return sc


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


def _handle(rmw, marker="o", ms=4.5):
    """Proxy pentru o serie RMW: cerc PLIN in culoarea RMW -- exact ce se deseneaza."""
    return Line2D([0], [0], marker=marker, ls="none", color=COLOR[rmw], label=LABEL[rmw],
                  ms=ms)


def _handle_forma(marker, label, hollow, ms=4.5, mew=1.0):
    """Proxy care explica FORMA, nu culoarea: gri neutru, dar cu fill-state IDENTIC cu al
    artefactului desenat (v2.1 -- un proxy gol pentru un marker plin e o minciuna mica,
    dar exact genul care il face pe cititor sa caute in figura ceva ce nu exista)."""
    return Line2D([0], [0], marker=marker, ls="none", ms=ms, mew=mew, label=label,
                  mfc="none" if hollow else GRI, mec=GRI)


# --------------------------------------------------------------------------- F1
def _build_delivery_vs_B(root4):
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
    # liniuta medianei: gri neutru (in panou e colorata pe RMW), NU neagra
    manere.append(Line2D([0], [0], color=GRI, lw=1.9, label="median"))
    leg = fig.legend(handles=manere, loc="outside upper center", ncol=3, frameon=False,
                     fontsize=7)
    # 'k/N' e TEXT sub axa, nu un marker: se explica printr-o nota in exact culoarea in
    # care e desenat, nu printr-o cheie de legenda care ar promite un simbol inexistent
    fig.text(0.5, -0.06, "k/N under the axis = runs with zero delivery (out of N)",
             ha="center", va="top", fontsize=6, color=RECV0)
    return fig, list(axes), leg


def fig_delivery_vs_B(root4, out=None):
    fig, _, _ = _build_delivery_vs_B(root4)
    return salveaza(fig, "fig_c2_delivery_vs_B", out)


# --------------------------------------------------------------------------- F2
def _build_64k_inversion(root4, root64):
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
    # cheile de sarcina utila: gri PLINE, fiindca in panou markerele sunt PLINE
    manere = [_handle(r) for r in RMWS] + [
        _handle_forma("o", "4 KB payload", hollow=False),
        _handle_forma("D", "64 KB payload", hollow=False)]
    leg = ax.legend(handles=manere, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=4,
                    frameon=False, fontsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    return fig, [ax], leg


def fig_64k_inversion(root4, root64, out=None):
    fig, _, _ = _build_64k_inversion(root4, root64)
    return salveaza(fig, "fig_c2_64k_inversion", out)


# --------------------------------------------------------------------------- F3
def _build_combo_context(root4, rootcombo, rootc1, marker_c1="s"):
    """F3: contextul combinatiei latenta+rafala. Patru conditii, toate ca strip-uri;
    referinta C1 (alta campanie, protocol byte-identic) are markere GOALE, ca sa nu fie
    citita ca masuratoare C2. Etichetele x pe doua randuri; figura cu 30% mai lata decat
    formatul 1-coloana, altfel etichetele se calca.
    v2.1: marker PATRAT gol, nu cerc gol. Datele C1 stau toate in banda 97.5-99.5%, iar
    cercurile goale suprapuse acolo se citesc ca un bloc plin (verificat pe figura
    randata); patratul pastreaza distinctia si cand punctele se ating. Legenda primeste
    chiar acest scatter, deci nu poate ramane in urma daca markerul se schimba iar."""
    sets = [("bern_15", "C2 4KB", root4, "bern_15", 4096, False),
            ("ge_15_8", "C2 4KB", root4, "ge_15_8", 4096, False),
            ("lat200_jit50", "C1 SIL ref", rootc1, "lat200_jit50", 4096, True),
            ("lat+ge_15_8", "C2 combo", rootcombo, "lat200_jit50_ge_15_8", 4096, False)]
    fig, ax = plt.subplots(figsize=(3.4 * 1.3, 2.6))
    dx = 0.17
    sc_c1 = None
    for x, (_, _, root, cond, pay, hollow) in enumerate(sets):
        for i, rmw in enumerate(RMWS):
            dv, r0, _ = delivery(root, rmw, cond, pay)
            xc = x + (i - 0.5) * 2 * dx
            # referinta C1: goala DE-ADEVARATELEA -- contur mai gros, +30% marime si fara
            # transparenta, altfel un cluster stramt de cercuri goale se citeste ca plin
            sc = strip_cell(ax, xc, dv, COLOR[rmw],
                            marker=(marker_c1 if hollow else "o"), hollow=hollow,
                            size=(13 * 1.3 if hollow else 13),
                            linewidth=(1.4 if hollow else 0.9),
                            alpha=(1.0 if hollow else 0.8))
            if hollow and sc is not None:
                sc_c1 = sc                      # HANDLE-ul real, nu o copie
            if r0:
                n0_band(ax, xc, r0, len(dv))
    ax.set_ylim(-3, 105)
    ax.set_xlim(-0.5, len(sets) - 0.5)
    ax.set_ylabel("delivery ratio [%]")
    ax.set_xticks(range(len(sets)))
    ax.set_xticklabels(["%s\n%s" % (s[0], s[1]) for s in sets], fontsize=6.8)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    manere = [_handle(r) for r in RMWS]
    if sc_c1 is not None:
        sc_c1.set_label("C1 reference (hollow)")
        manere.append(sc_c1)                    # chiar artefactul desenat
    leg = ax.legend(handles=manere, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3,
                    frameon=False, fontsize=6.5)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    return fig, [ax], leg


def fig_combo_context(root4, rootcombo, rootc1, out=None, marker_c1="s"):
    fig, _, _ = _build_combo_context(root4, rootcombo, rootc1, marker_c1)
    return salveaza(fig, "fig_c2_combo_context", out)


# --------------------------------------------------------------------------- F4
def _build_longest_burst(root4):
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
            # zeroul NU se mai adnoteaza: markerul asezat la 0 pe symlog il arata deja,
            # iar textul rosu introducea un al doilea limbaj vizual (rosul = esec total)
            # peste o valoare care aici inseamna 'nicio rafala', adica opusul
    ax.set_yscale("symlog", linthresh=1)
    ax.set_ylim(0, 400)
    ax.set_ylabel("longest failure burst [pkts]", fontsize=8)
    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels(conds, rotation=45, ha="right", fontsize=7)
    ax.set_xlim(-0.5, len(conds) - 0.5)
    ax.grid(True, axis="y", ls=":", lw=0.4, alpha=0.6)
    axa_secundara_secunde(ax)
    # cheile de statistica: gri neutru, cu FORMA, FILL-ul si MARIMEA din panou
    manere = [_handle(r) for r in RMWS] + [
        _handle_forma("o", "max over N runs", hollow=False, ms=3.8),
        _handle_forma("D", "p95 over N runs", hollow=True, ms=7.0)]
    leg = ax.legend(handles=manere, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=4,
                    frameon=False, fontsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    return fig, [ax], leg


def fig_longest_burst(root4, out=None):
    fig, _, _ = _build_longest_burst(root4)
    return salveaza(fig, "fig_c2_longest_burst", out)


# ------------------------------------------------- verificarea legenda-vs-plot (v2.1)
def _amprenta_forma(path):
    """Amprenta NORMALIZATA a formei unui marker (centrata si scalata la caseta unitate),
    ca sa fie comparabila intre un scatter si un proxy Line2D: matplotlib le stocheaza in
    sisteme diferite (calea lui 'D' e un patrat, rotatia sta in transformarea markerului)."""
    v = [(float(x), float(y)) for x, y in path.vertices]
    xs = [p[0] for p in v]
    ys = [p[1] for p in v]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    r = max(max(xs) - min(xs), max(ys) - min(ys)) / 2.0 or 1.0
    return (len(v), tuple(sorted((round((x - cx) / r, 2), round((y - cy) / r, 2))
                                 for x, y in v)))


def _cale_marker(m):
    ms = MarkerStyle(m)
    return ms.get_transform().transform_path(ms.get_path())


def _clasa_culoare(c):
    """Clasa de culoare: cdds / zenoh / gri-neutru / altceva. Proxy-urile au voie sa fie
    gri (explica forma, nu seria); orice alta culoare care nu apare in panou e o eroare."""
    if c is None:
        return "niciuna"
    rgba = mcolors.to_rgba(c)
    for nume, ref in (("cdds", COLOR_CDDS), ("zenoh", COLOR_ZENOH), ("gri", GRI),
                      ("recv0", RECV0)):
        if all(abs(a - b) < 0.02 for a, b in zip(rgba[:3], mcolors.to_rgba(ref)[:3])):
            return nume
    return "alta(%s)" % mcolors.to_hex(rgba)


def _proprietati(artefact):
    """(amprenta_forma, plin, clasa_culoare) pentru un scatter sau un Line2D cu marker.
    None daca artefactul nu poarta marker (linii simple, texte)."""
    if hasattr(artefact, "get_paths"):                       # PathCollection (scatter)
        caiuri = artefact.get_paths()
        if not caiuri:
            return None
        fc = artefact.get_facecolors()
        ec = artefact.get_edgecolors()
        plin = len(fc) > 0
        culoare = (ec[0] if len(ec) else (fc[0] if plin else None))
        return (_amprenta_forma(caiuri[0]), plin, _clasa_culoare(culoare))
    m = artefact.get_marker() if hasattr(artefact, "get_marker") else None
    if m in (None, "", " ", "None"):
        return None
    mfc = artefact.get_markerfacecolor()
    plin = mfc not in ("none", "None", None)
    return (_amprenta_forma(_cale_marker(m)), plin, _clasa_culoare(artefact.get_markeredgecolor()))


def _artefacte_desenate(axes):
    """Toate artefactele cu marker de pe axele date (scatter + linii cu marker)."""
    out = []
    for ax in axes:
        for coll in ax.collections:
            p = _proprietati(coll)
            if p:
                out.append(p)
        for ln in ax.lines:
            p = _proprietati(ln)
            if p:
                out.append(p)
    return out


def verifica_legenda(axes, leg):
    """Regula v2.1: fiecare intrare de legenda cu marker trebuie sa aiba un artefact
    desenat cu ACEEASI forma si ACELASI fill-state; culoarea are voie sa fie a
    artefactului sau griul neutru. Intoarce lista de probleme (goala = totul e onest)."""
    desenate = _artefacte_desenate(axes)
    manere = getattr(leg, "legend_handles", None) or getattr(leg, "legendHandles", [])
    etichete = [t.get_text() for t in leg.get_texts()]
    probleme = []
    for h, et in zip(manere, etichete):
        p = _proprietati(h)
        if p is None:                       # cheie fara marker (ex. liniuta medianei)
            culoare = getattr(h, "get_color", lambda: None)()
            if _clasa_culoare(culoare).startswith("alta"):
                probleme.append("'%s': culoare %s inexistenta in panou"
                                % (et, _clasa_culoare(culoare)))
            continue
        forma, plin, clasa = p
        potriviri = [d for d in desenate if d[0] == forma and d[1] == plin]
        if not potriviri:
            probleme.append("'%s': forma/fill (%s) nu exista desenat in panou"
                            % (et, "plin" if plin else "gol"))
            continue
        if clasa != "gri" and clasa not in {d[2] for d in potriviri}:
            probleme.append("'%s': culoarea %s nu apare pe niciun artefact cu forma asta"
                            % (et, clasa))
    return probleme


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

        # strip_cell: intoarce ARTEFACTUL desenat (v2.1), deseneaza punctele + mediana
        fig, ax = plt.subplots()
        sc = strip_cell(ax, 1.0, [10.0, 20.0, 60.0], COLOR["zenoh"])
        assert sc in ax.collections, "strip_cell nu a intors scatter-ul desenat"
        assert len(sc.get_offsets()) == 3, sc.get_offsets()
        assert any(abs(ln.get_ydata()[0] - 20.0) < 1e-9 for ln in ax.lines), "mediana lipseste"
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

        # --- v2.1: LEGENDA vs PLOT, pe proprietati, pentru FIECARE figura
        constructori = [
            ("F1 delivery_vs_B", lambda: _build_delivery_vs_B(root)),
            ("F2 64k_inversion", lambda: _build_64k_inversion(root, root)),
            ("F3 combo_context", lambda: _build_combo_context(root, root, root)),
            ("F4 longest_burst", lambda: _build_longest_burst(root)),
        ]
        for nume, ctor in constructori:
            f, axs, lg = ctor()
            assert lg is not None, "%s: fara legenda" % nume
            probleme = verifica_legenda(axs, lg)
            assert not probleme, "%s: %s" % (nume, probleme)
            plt.close(f)

        # verificatorul PRINDE divergentele (altfel testul de mai sus nu dovedeste nimic):
        f, ax = plt.subplots()
        ax.scatter([0], [0], marker="o", facecolors=COLOR_CDDS, edgecolors=COLOR_CDDS)
        rele = [
            (Line2D([0], [0], marker="o", ls="none", mfc="none", mec=GRI, label="gol-fals"),
             "fill"),                                   # in panou e PLIN, cheia zice gol
            (Line2D([0], [0], marker="D", ls="none", color=GRI, label="forma-falsa"),
             "forma"),                                  # niciun romb desenat
            (Line2D([0], [0], marker="o", ls="none", color="black", label="culoare-falsa"),
             "culoare"),                                # negru: nu exista in panou
        ]
        for h, fel in rele:
            lg = ax.legend(handles=[h], labels=[h.get_label()])
            assert verifica_legenda([ax], lg), "verificatorul NU a prins divergenta de %s" % fel
        # iar cheia CORECTA trece
        lg = ax.legend(handles=[Line2D([0], [0], marker="o", ls="none", color=COLOR_CDDS,
                                       label="buna")], labels=["buna"])
        assert verifica_legenda([ax], lg) == [], verifica_legenda([ax], lg)
        plt.close(f)
        assert _amprenta_forma(_cale_marker("D")) != _amprenta_forma(_cale_marker("s"))
        assert _clasa_culoare(GRI) == "gri" and _clasa_culoare("black").startswith("alta")

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
        print("SELFTEST make_figures_c2 OK (24 verificari, date sintetice in /tmp; "
              "banda n0 verificata geometric sub panou; legenda fiecarei figuri "
              "confruntata pe proprietati cu artefactele desenate).")
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
