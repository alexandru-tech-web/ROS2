#!/usr/bin/env python3
"""test_podea.py -- niciun punct al piciorului nu coboara sub podea. INVARIANT.

DE CE EXISTA
Pe 22 aug 2026 omul a vazut in simulare ca picioarele trec prin placa metalica.
Diagnosticul: sub axa soldului erau 0.42 m pana la placa, dar piciorul avea 0.80 m.
Nu o cota prost aleasa, ci o imposibilitate dimensionala pe care nimic nu o verifica.
Argumentul care a rezultat de acolo -- un scaun nu poate fi mai inalt decat piciorul
care atarna din el -- a decis conventia articulara (DECIZII.md, D1). Un argument care
decide o conventie nu are voie sa ramana o amintire dintr-un raport: aici devine test
care ruleaza la fiecare build.

CE SE BALEIAZA
Configuratiile LEGALE, adica cele pe care limitele URDF chiar le permit: grila pe
cursele soldului si genunchiului, capetele gleznei, si intervalul COMPLET de reglaj
al lungimilor (push rod 306 si 403). Un model corect doar la lungimea nominala ar
cadea pe primul pacient mai inalt.

CE SE VERIFICA: cele patru colturi ale placii de talpa, plus axele gleznei si
genunchiului. Colturile conteaza: centrul poate fi deasupra podelei in timp ce un
colt e dedesubt.

POSTURA SEZUT PICA INTENTIONAT. Banda ei a fost TRANSPORTATA mecanic din conventia
veche (DECIZII.md, corectia 3) si cade integral sub orizontala. Testul aserteaza ca
pica, fiindca exact asta e dovada ca plasarea veche era gresita. Cand banda se
rejustifica (punctul 5), asertia se inverseaza -- deliberat, printr-o modificare
vizibila a acestui fisier, nu prin tacere.

Rulare: python3 test/test_podea.py
"""
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

AICI = os.path.dirname(os.path.abspath(__file__))
PACHET = os.path.dirname(AICI)
sys.path.insert(0, os.path.join(PACHET, "scripts"))
XACRO = os.path.join(PACHET, "urdf", "rehab_exo.urdf.xacro")

import geometrie_core as gc                                        # noqa: E402

PARTI = ("left", "right")
# Nu e destul ca nimic sa nu ATINGA podeaua: intre "nu atinge" si "are margine" e
# diferenta dintre o coincidenta si o proiectare. Marginea ceruta vine din
# geometrie_core, ca sa nu existe doua valori.


def _urdf(*arg):
    f = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    f.close()
    p = subprocess.run(["xacro", XACRO] + list(arg) + ["-o", f.name],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("xacro a picat: %s" % p.stderr[:400])
    return f.name


def _rpy2R(r):
    x, y, z = r
    cx, sx, cy, sy, cz, sz = (math.cos(x), math.sin(x), math.cos(y),
                              math.sin(y), math.cos(z), math.sin(z))
    return np.array([[cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
                     [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
                     [-sy, cy * sx, cy * cx]])


def _model(cale):
    r = ET.parse(cale).getroot()
    J, lim = [], {}
    for j in r.findall("joint"):
        o, ax, li = j.find("origin"), j.find("axis"), j.find("limit")
        J.append(dict(
            name=j.get("name"), typ=j.get("type"),
            par=j.find("parent").get("link"), chi=j.find("child").get("link"),
            xyz=np.array([float(v) for v in (o.get("xyz", "0 0 0")).split()])
            if o is not None else np.zeros(3),
            rpy=[float(v) for v in (o.get("rpy", "0 0 0")).split()]
            if o is not None else [0.0, 0.0, 0.0],
            axis=np.array([float(v) for v in ax.get("xyz").split()])
            if ax is not None else np.array([0.0, 0.0, 1.0])))
        if li is not None:
            lim[j.get("name")] = (float(li.get("lower")), float(li.get("upper")))
    return J, lim


def _fk(J, q):
    T = {"world": (np.zeros(3), np.eye(3))}
    for _ in range(6):
        for j in J:
            if j["par"] in T and j["chi"] not in T:
                p, R = T[j["par"]]
                Rj = R @ _rpy2R(j["rpy"])
                pj = p + R @ j["xyz"]
                v = q.get(j["name"], 0.0)
                if j["typ"] == "revolute":
                    a = j["axis"] / np.linalg.norm(j["axis"])
                    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
                    Rj = Rj @ (np.eye(3) + math.sin(v) * K + (1 - math.cos(v)) * K @ K)
                elif j["typ"] == "prismatic":
                    pj = pj + Rj @ (j["axis"] * v)
                T[j["chi"]] = (pj, Rj)
    return T


def _puncte_critice(T, c):
    """(nume, z) pentru punctele care pot atinge podeaua primele."""
    out = []
    L, W = c["talpa_lungime"], 0.130
    for p in PARTI:
        Rf, pf = T["%s_foot" % p][1], T["%s_foot" % p][0]
        # cele patru colturi ale placii, in cadrul tapei: +X e in lungul gambei
        # (sub axa), +Z inainte, +Y lateral
        for dz in (-L / 4.0, 3.0 * L / 4.0):
            for dy in (-W / 2.0, W / 2.0):
                col = pf + Rf @ np.array([c["glezna_offset"], dy, dz])
                out.append(("%s talpa colt" % p, float(col[2])))
        out.append(("%s glezna" % p, float(pf[2])))
        out.append(("%s genunchi" % p, float(T["%s_shank" % p][0][2])))
    return out


def _baleiaza(J, lim, c, pasi=5):
    """Cel mai jos punct atins pe toata grila legala. Intoarce (z_min, descriere)."""
    def gama(nume, n):
        lo, hi = lim[nume]
        return [lo] if abs(hi - lo) < 1e-12 else [lo + (hi - lo) * k / (n - 1.0)
                                                 for k in range(n)]
    solduri = gama("left_hip_joint", pasi)
    genunchi = gama("left_knee_joint", pasi)
    glezne = list(lim["left_ankle_joint"])
    ext_c = [0.0, c["coapsa_cursa"]]
    ext_g = [0.0, c["gamba_cursa"]]
    z_min, unde, n = 1e9, None, 0
    for s in solduri:
        for g in genunchi:
            for a in glezne:
                for ec in ext_c:
                    for eg in ext_g:
                        q = {}
                        for p in PARTI:
                            q["%s_hip_joint" % p] = s
                            q["%s_knee_joint" % p] = g
                            q["%s_ankle_joint" % p] = a
                            q["%s_thigh_ext_joint" % p] = ec
                            q["%s_shank_ext_joint" % p] = eg
                        n += 1
                        for nume, z in _puncte_critice(_fk(J, q), c):
                            if z < z_min:
                                z_min, unde = z, (
                                    "%s la sold %.1f, genunchi %.1f, glezna %.1f grade, "
                                    "reglaj %+.3f/%+.3f"
                                    % (nume, math.degrees(s), math.degrees(g),
                                       math.degrees(a), ec, eg))
    return z_min, unde, n


def main(argv):
    n = [0]

    def ok(cond, m):
        if not cond:
            print("ESEC: %s" % m)
            raise SystemExit(1)
        n[0] += 1

    c = gc.cote()

    # --- 1. POSTURA CULCAT: nimic sub podea, nicaieri pe grila legala
    J, lim = _model(_urdf("controllers:=%s" % os.path.join(PACHET, "config",
                                                           "controllers.yaml")))
    z_min, unde, cate = _baleiaza(J, lim, c)
    print("  culcat: %d configuratii legale, cel mai jos punct z = %+.4f m" % (cate, z_min))
    print("          (%s)" % unde)
    ok(z_min >= c["margine_podea"],
       "cel mai jos punct e la %.4f m, sub marginea ceruta de %.3f m: %s"
       % (z_min, c["margine_podea"], unde))

    # SENSIBILITATE, scrisa aici ca sa nu produca panica peste sase luni.
    # Testul trece cu circa 0.7 mm PESTE marginea ceruta, si asta NU e o slabiciune:
    # inaltimea talpii a fost aleasa exact ca marginea sa fie atinsa, deci cazul cel
    # mai defavorabil sta PE marja prin CONSTRUCTIE, nu cu rezerva peste ea.
    # Consecinta practica: orice retus de cota (segmente, offset de glezna, lungimea
    # tapei) basculeaza invariantul, si asta e comportamentul dorit -- inseamna ca
    # testul chiar mai are dinti. Daca se doreste rezerva reala, se creste
    # MARGINE_PODEA in geometrie_core, NU se slabeste asertia de aici.
    rezerva = z_min - c["margine_podea"]
    print("  rezerva peste marginea ceruta: %+.4f m (asteptat: mic, prin constructie)"
          % rezerva)
    ok(rezerva < 0.010,
       "rezerva de %.4f m e mai mare decat se astepta: inseamna ca inaltimea talpii "
       "nu mai e stransa pe invariant si comentariul de mai sus a devenit fals"
       % rezerva)
    n[0] += cate

    # --- 2. LA REPAUS talpa se aseaza EXACT pe inaltimea derivata a suportului.
    # Verificarea care leaga geometria de derivare: daca cele doua se despart, una
    # din ele a fost schimbata fara cealalta.
    T = _fk(J, {"%s_knee_joint" % p: math.pi / 2 for p in PARTI})
    pf, Rf = T["left_foot"][0], T["left_foot"][1]
    centru = pf + Rf @ np.array([c["glezna_offset"], 0.0, c["talpa_lungime"] / 4.0])
    ok(abs(centru[2] - c["talpa_inaltime"]) < 1e-6,
       "la repaus centrul tapei e la %.4f m, dar cota derivata zice %.4f"
       % (centru[2], c["talpa_inaltime"]))
    ok(abs(T["left_shank"][0][2] - T["left_thigh"][0][2]) < 1e-9,
       "la sold zero coapsa nu e orizontala")

    # --- 3. CONTROLUL NEGATIV: conventia VECHE, adica soldul rotit cu 90 de grade in
    # jos, trebuie sa pice. Asta e argumentul care a decis D1, verificat aici pe
    # geometria reala si nu pe o aritmetica facuta pe hartie.
    q_jos = {}
    for p in PARTI:
        q_jos["%s_hip_joint" % p] = -math.pi / 2      # coapsa in jos
        q_jos["%s_knee_joint" % p] = 0.0
    z_jos = min(z for _, z in _puncte_critice(_fk(J, q_jos), c))
    ok(z_jos < 0.0,
       "cu coapsa rotita in jos piciorul ar trebui sa treaca sub podea, dar z=%.4f"
       % z_jos)
    print("  control negativ: cu coapsa in jos, cel mai jos punct z = %+.4f m" % z_jos)

    # ... si ramane adevarat si la reglajul MINIM al lungimilor, adica argumentul nu
    # depinde de pacientul ales.
    z_jos_min = min(z for _, z in _puncte_critice(_fk(J, q_jos), c))
    ok(z_jos_min < 0.0, "argumentul podelei trebuie sa tina si la lungimea minima")

    # --- 4. POSTURA SEZUT: banda transportata pica INTENTIONAT. Vezi antetul.
    J2, lim2 = _model(_urdf("postura:=sezut",
                            "controllers:=%s" % os.path.join(PACHET, "config",
                                                             "controllers.yaml")))
    lo2, hi2 = lim2["left_hip_joint"]
    ok(hi2 <= 1e-9,
       "banda de sezut transportata ar trebui sa fie integral sub orizontala, dar "
       "urca la %.2f grade" % math.degrees(hi2))
    z2, unde2, _ = _baleiaza(J2, lim2, c, pasi=3)
    ok(z2 < 0.0,
       "banda de sezut TRANSPORTATA ar trebui sa pice invariantul podelei; daca a "
       "inceput sa treaca, inseamna ca a fost rejustificata (punctul 5) si asertia "
       "asta trebuie INVERSATA deliberat, nu stearsa")
    print("  sezut (banda transportata, IMPOSIBILA): cel mai jos punct z = %+.4f m" % z2)
    print("          %s" % unde2)

    print("test_podea: %d verificari OK (grila legala culcat curata, repausul "
          "coincide cu derivarea, sezutul transportat pica asa cum trebuie)." % n[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
