#!/usr/bin/env python3
"""measure_settling.py -- cat dureaza pana estimatorul se ASEAZA dupa o schimbare de regim.

DE CE CONTEAZA CIFRA ASTA
Dwell-time-ul (cat trebuie sa stea gateway-ul pe un transport inainte sa aiba voie sa
comute iar) era derivat, in etapa 1, din costul de repornire a unui proces (0.43 s x 10).
Derivarea aceea nu mai e valabila: in dual-path ambii agenti raman pornit permanent, deci
comutarea doar redirectioneaza octetii pe alt socket UNIX (~0.1 ms, masurat la etapa 2).
Ce ramane, si devine termenul care conteaza, e cu totul altceva: dupa ce linkul isi schimba
regimul, ESTIMATORUL are nevoie de timp ca sa afle. Daca dwell-time-ul e mai scurt decat
timpul de asezare, gateway-ul decide pe o estimare care inca descrie regimul VECHI.

DEFINITIA ASEZARII -- si de ce nu e cea evidenta
Prima varianta cerea ca estimarea sa ramana in +/-1 sigma de valoarea noua pana la capatul
ferestrei. Criteriul acela e IMPOSIBIL de indeplinit si testul a aratat-o imediat: un
estimator zgomotos iese din banda de 1 sigma in ~32% din timp, prin definitia lui sigma.
Ce ne intereseaza de fapt nu e zgomotul, ci BIASUL: cat dureaza pana estimarea nu mai
descrie sistematic regimul VECHI. Deci se masoara media de ansamblu peste seed-uri (care
elimina zgomotul, avand eroarea standard sigma/sqrt(K)) si se cauta primul esantion de la
care media ramane, pana la capat, in +/-1 sigma de valoarea noua -- si pentru L, si pentru
B. Sigma sunt cele raportate de estimator la tinta (sigma_L cu corectia de corelatie,
sigma_B din geometrica golurilor), nu praguri alese aici.
NUMARUL DE SEED-URI nu e ales din obisnuinta: media de ansamblu trebuie sa fie mult mai
precisa decat banda in care o masuram, altfel criteriul 'ramane pana la capat' pica pe
propria ei imprecizie. La 5 seed-uri (SE = 0.45 sigma) masuratoarea nici nu converge; la
10/20/40 da 91/130/137 esantioane, adica se aseaza. Implicitul e 40 (SE = 0.16 sigma).

Uz:
  python3 tools/measure_settling.py [--seeds 5] [--out FISIER]
  python3 tools/measure_settling.py --selftest
"""
import json
import os
import statistics as st
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(os.path.dirname(AICI), "c3_gateway", "core")
sys.path.insert(0, CORE)

from canal_ge import CanalGE                                  # noqa: E402
from estimator import ALPHA_B, ALPHA_L, EstimatorLink        # noqa: E402

HZ = 50.0
GRILA = [(5, 1), (5, 3), (5, 8), (15, 1), (15, 3), (15, 8), (30, 1), (30, 3), (30, 8)]
SURSE = [(0, 1), (5, 1), (30, 8)]        # de unde se vine: ideal, usor, greu
N_PRE = 3000                              # esantioane de incalzire pe regimul vechi
N_POST = 6000                             # 120 s la 50 Hz: destul pentru cele mai lente
# Prag MINIM pentru banda lui B. La B=1 rafala are lungime determinista, deci sigma_B e
# exact 0 si banda ar avea latime nula: media exponentiala coboara spre 1 asimptotic si nu
# ajunge niciodata EXACT acolo, asa ca asezarea nu s-ar declara niciodata (chiar asa au
# picat primele 3 tranzitii, toate catre B=1). Un sfert de pachet e mult sub distanta
# dintre treptele grilei (1, 3, 8), deci nu ascunde nicio diferenta care ne intereseaza.
BANDA_B_MINIMA = 0.25
OUT_IMPLICIT = os.path.join(os.path.expanduser("~"), "DATE_CAMPANIE", "ANALIZA_C3",
                            "asezare_estimator.json")


def _flux(canal, n, seq0):
    """Numerele de secventa livrate de un canal, continuand numerotarea."""
    return [seq0 + i for i in range(n) if canal.esantion()]


def _traiectorie(sursa, tinta, seed, alpha_L, alpha_B, n_pre, n_post):
    """(L_hat, B_hat) esantion cu esantion DUPA treapta, pentru un seed."""
    c_sursa = CanalGE.from_LB_pct(sursa[0], sursa[1], seed=seed)
    c_tinta = CanalGE.from_LB_pct(tinta[0], tinta[1], seed=seed + 7777)
    est = EstimatorLink(alpha_L=alpha_L, alpha_B=alpha_B)
    for s in _flux(c_sursa, n_pre, 1):
        est.observa(s)
    Ls, Bs = [], []
    seq = n_pre + 1
    for _ in range(n_post):
        if c_tinta.esantion():
            est.observa(seq)
        seq += 1
        Ls.append(est._L)
        Bs.append(est._B)
    return Ls, Bs


def masoara_o_treapta(sursa, tinta, seeds, alpha_L=ALPHA_L, alpha_B=ALPHA_B,
                      n_pre=N_PRE, n_post=N_POST):
    """Cate esantioane dupa treapta pana cand BIASUL (media peste seed-uri) intra si ramane
    in +/-1 sigma de valoarea noua. None daca nu se aseaza in fereastra data."""
    traiectorii = [_traiectorie(sursa, tinta, 1000 + 13 * k, alpha_L, alpha_B,
                                n_pre, n_post) for k in range(seeds)]
    L_t, B_t = tinta[0] / 100.0, float(tinta[1])
    # sigma la TINTA: de la un estimator asezat pe regimul nou, nu din estimarea curenta
    # (care in primele esantioane inca descrie regimul vechi)
    ref = EstimatorLink(alpha_L=alpha_L, alpha_B=alpha_B)
    ref._L, ref._B = L_t, B_t
    sig_L, sig_B = ref.sigma_L(), max(ref.sigma_B(), BANDA_B_MINIMA)

    in_banda = []
    for i in range(n_post):
        mL = sum(t[0][i] for t in traiectorii) / float(seeds)
        mB = sum(t[1][i] for t in traiectorii) / float(seeds)
        in_banda.append(abs(mL - L_t) <= sig_L and abs(mB - B_t) <= sig_B)

    ultim_afara = None
    for i in range(len(in_banda) - 1, -1, -1):
        if not in_banda[i]:
            ultim_afara = i
            break
    if ultim_afara is None:
        return 0
    if ultim_afara >= len(in_banda) - 1:
        return None                      # nu s-a asezat in fereastra
    return ultim_afara + 1


def masoara_tot(seeds=40):
    brut, per_celula = [], {}
    for tinta in GRILA:
        val = []
        for sursa in SURSE:
            if sursa == tinta:
                continue
            n = masoara_o_treapta(sursa, tinta, seeds)
            if n is not None:
                val.append(n)
                brut.append({"sursa": sursa, "tinta": tinta, "seeds": seeds,
                             "esantioane": n, "secunde": n / HZ})
        if val:
            per_celula["L%d_B%d" % tinta] = {
                "n": len(val), "mediana_esantioane": st.median(val),
                "mediana_s": st.median(val) / HZ,
                "p95_esantioane": sorted(val)[min(len(val) - 1,
                                                  int(round(0.95 * (len(val) - 1))))],
                "max_esantioane": max(val)}
    toate = [b["esantioane"] for b in brut]
    rezumat = {
        "hz": HZ, "alpha_L": ALPHA_L, "alpha_B": ALPHA_B,
        "n_tranzitii": len(toate),
        "mediana_esantioane": st.median(toate) if toate else None,
        "mediana_s": st.median(toate) / HZ if toate else None,
        "p95_esantioane": (sorted(toate)[min(len(toate) - 1,
                                             int(round(0.95 * (len(toate) - 1))))]
                           if toate else None),
        "p95_s": None,
        "esecuri": sum(1 for tinta in GRILA for sursa in SURSE
                       if sursa != tinta) - len(toate),
    }
    if rezumat["p95_esantioane"] is not None:
        rezumat["p95_s"] = rezumat["p95_esantioane"] / HZ
    return {"rezumat": rezumat, "per_celula": per_celula, "brut": brut}


def _selftest():
    # 1. treapta de la ideal la un regim usor: estimatorul TREBUIE sa se aseze
    n = masoara_o_treapta((0, 1), (15, 3), seeds=40, n_pre=500, n_post=4000)
    assert n is not None and 0 < n < 4000, n

    # 2. fara treapta (sursa == tinta) asezarea e imediata sau foarte rapida: estimatorul
    # e deja acolo, deci nu trebuie sa 'astepte' nimic
    n0 = masoara_o_treapta((15, 3), (15, 3), seeds=40, n_pre=3000, n_post=3000)
    assert n0 is not None, n0
    assert n0 < 1500, ("fara schimbare de regim nu ar trebui sa dureze mult", n0)

    # 3. Ce guverneaza asezarea NU e marimea treptei, ci cat de des primeste estimatorul
    # informatie despre B -- adica RATA GOLURILOR. Prima varianta a testului presupunea
    # monotonie in marimea treptei si a picat: treapta mare (5,1)->(30,8) se aseaza in 161
    # esantioane, iar cea mica (15,3)->(15,8) in 262, fiindca la L=30% golurile vin de ~2.4
    # ori mai des decat la L=15%. Invariantul adevarat, deci: pentru acelasi B, tinta cu L
    # mai mic (goluri mai rare) se aseaza mai INCET.
    rar = masoara_o_treapta((0, 1), (5, 8), seeds=20, n_pre=2000, n_post=6000) or 6000
    des = masoara_o_treapta((0, 1), (30, 8), seeds=20, n_pre=2000, n_post=6000) or 6000
    assert rar > des, ("la L mic golurile sunt rare, deci asezarea trebuie sa fie mai lenta",
                       rar, des)

    # 4. sigma_B exista si e pozitiv acolo unde exista rafale
    e = EstimatorLink()
    e._L, e._B = 0.15, 8.0
    assert e.sigma_B() > 0 and e.sigma_L() > 0
    e._B = 1.0
    assert e.sigma_B() == 0.0, "la B=1 rafala e determinista, deci sigma_B = 0"
    print("SELFTEST measure_settling OK (4 verificari).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    seeds = 40
    out = OUT_IMPLICIT
    if "--seeds" in argv:
        seeds = int(argv[argv.index("--seeds") + 1])
    if "--out" in argv:
        out = os.path.expanduser(argv[argv.index("--out") + 1])
    print("masor asezarea estimatorului: %d celule x %d surse x %d seed-uri, la %g Hz"
          % (len(GRILA), len(SURSE), seeds, HZ))
    r = masoara_tot(seeds)
    z = r["rezumat"]
    print("\n  %-10s %10s %10s %10s" % ("celula", "mediana", "p95", "max"))
    for k in sorted(r["per_celula"]):
        c = r["per_celula"][k]
        print("  %-10s %7.0f es %7.0f es %7.0f es   (%.1f s mediana)"
              % (k, c["mediana_esantioane"], c["p95_esantioane"], c["max_esantioane"],
                 c["mediana_s"]))
    print("\n  TOTAL: %d tranzitii | mediana %.0f esantioane (%.2f s) | p95 %.0f (%.2f s)"
          % (z["n_tranzitii"], z["mediana_esantioane"], z["mediana_s"],
             z["p95_esantioane"], z["p95_s"]))
    if z["esecuri"]:
        print("  ATENTIE: %d tranzitii nu s-au asezat in fereastra de %d esantioane"
              % (z["esecuri"], N_POST))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(r, f, indent=1)
    print("  scris %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
