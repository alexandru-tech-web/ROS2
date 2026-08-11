#!/usr/bin/env python3
"""compara_sil_hil_64k.py -- SIL-loopback vs HIL-cablat pe celulele de 64 KB.

INTREBAREA STIINTIFICA
  Inversiunea de la 64 KB masurata pe loopback supravietuieste pe fir real cu MTU 1500,
  sau e artefact al MTU-ului de 65536 de pe 'lo'?
  'Inversiune' NU inseamna aici 'castigatorul se schimba fata de 4 KB', ci: la ACELASI
  payload (64 KB) si la ACEEASI pierdere medie (15%), semnul avantajului CycloneDDS-minus-
  Zenoh este DIFERIT intre bern_15 (fara memorie) si ge_15_8 (rafale B=8). Adica se schimba
  CINE e victima. Pe SIL: bern_15 -> castiga Zenoh, ge_15_8 -> castiga CycloneDDS.
  Ipoteza de artefact: netem gemodel arunca PER PACHET, iar un esantion de 64 KB se sparge
  in ~44 de pachete pe un MTU de 1500 si in ~1-2 datagrame pe 'lo' (MTU 65536 masurat), deci
  acelasi parametru inseamna de ~44x mai multe incercari de drop pe fir decat pe loopback.

CE FACE
  Citeste arhivele SIL si HIL (structura <arhiva>/<rmw>/<conditie>/rep<N>/transport_p<P>.csv
  + _summary.json), STRICT READ-ONLY, si produce acelasi tabel pe aceleasi celule, cu delta
  SIL-vs-HIL. Merge si FARA --hil: atunci tipareste doar coloana SIL si spune limpede ca
  partea HIL asteapta campania (asta e modul in care ruleaza acum).

DISCIPLINA STATISTICA (aceeasi ca in restul C2, vezi make_hil_tables.py)
  - n0=k/N raportat SEPARAT: k rulari cu ZERO esantioane livrate din N gasite pe disc;
  - mediana/min/max DOAR pe supravietuitori (n>0) -- statistici CONDITIONATE pe supravietuire;
  - livrarea per rulare = received/sent CITIT din fiecare _summary.json (denominatorul NU e
    constanta 989: la 64 KB sent scade cand publicarea blocheaza timerul clientului);
  - livrarea EFECTIVA (neconditionata) = (1 - n0/N) * mediana, raportata ca o coloana proprie;
  - mediana RTT are DOUA definitii legitime, se alege explicit una si se DECLARA in tabel:
      p50med (implicit) = mediana celor N valori p50_ms, una per rulare supravietuitoare;
      pooled            = mediana peste TOATE esantioanele reunite ale supravietuitorilor.
    Celulele in care p50-urile per rulare se intind pe mai mult de PRAG_BIMODAL ordine de
    marime sunt marcate BIMODAL: acolo orice mediana unica ascunde doua populatii.

VERDICT (cele trei rezultate posibile sunt numite INAINTE de a vedea datele)
  (a) inversiunea PERSISTA pe fir      -> nu e artefact de MTU
  (b) inversiunea DISPARE pe fir       -> era artefact de MTU al loopback-ului
  (c) datele NU ajung sa decida        -> se spune DE CE (celule lipsa, prea multi n0,
                                          prabusire sub podea, contrast sub prag, sarcina
                                          oferita inegala intre RMW-uri)
  Scriptul nu are voie sa 'aleaga' (a) sau (b) cand garzile nu trec: orice garda cazuta duce
  determinist la (c), cu motivul tiparit. Pragurile sunt constante de modul si se tiparesc in
  raport, ca decizia sa fie reproductibila si contestabila.

SCRIERE
  Singura tinta permisa sub ~/DATE_CAMPANIE este ~/DATE_CAMPANIE/ANALIZA_C2/ (arhivele de
  campanie sunt SIGILATE); verifica_tinta() refuza orice altceva. Iesiri:
    compara_sil_hil_64k.md    -- tabel Markdown + verdict
    compara_sil_hil_64k.json  -- aceleasi cifre, structurate

Uz:
  python3 compara_sil_hil_64k.py --sil <dir> [--hil <dir>] [--payload 65536]
                                 [--rtt p50med|pooled] [--out DIR] [--stdout-only]
  python3 compara_sil_hil_64k.py --selftest
"""
import csv
import json
import os
import statistics
import sys

HOME = os.path.expanduser("~")
DATE = os.path.join(HOME, "DATE_CAMPANIE")
OUT_DEFAULT = os.path.join(DATE, "ANALIZA_C2")
SIL_DEFAULT = os.path.join(DATE, "C2_SIL64_20260719")
PAYLOAD_DEFAULT = 65536
RMWS = ("cyclonedds", "zenoh")
ETICHETA = {"cyclonedds": "cdds", "zenoh": "zenoh"}
EXCLUSE_SUFIXE = ("_INVALID", "_ECOUMORT")
ORDINE = ["ideal",
          "bern_5", "ge_5_3", "ge_5_8",
          "bern_15", "ge_15_3", "ge_15_8",
          "bern_30", "ge_30_3", "ge_30_8",
          "lat200_jit50_ge_15_8"]

# --- praguri de decizie (declarate, tiparite in raport, folosite de garzile verdictului)
PRAG_CONTRAST_PP = 5.0   # |livrare_cdds - livrare_zenoh| minim ca un contrast sa fie DECIS
PRAG_PODEA_PP = 5.0      # ambele mediane sub asta = prabusire; contrastul nu mai informeaza
PRAG_N0_FRACT = 0.5      # n0/N peste asta: celula prea moarta ca sa sustina o mediana
PRAG_VII_MIN = 3         # supravietuitori minimi intr-o celula folosita la contrast
PRAG_SARCINA = 1.25      # raport max al sarcinii oferite (sent med) intre cele doua RMW
PRAG_BIMODAL = 100.0     # max(p50)/min(p50) peste asta: celula marcata BIMODAL
MODURI_RTT = ("p50med", "pooled")

VERDICT_TEXT = {
    "a": "INVERSIUNEA PERSISTA PE FIR -- nu e artefact de MTU",
    "b": "INVERSIUNEA DISPARE PE FIR -- compatibila cu artefact de MTU al loopback-ului",
    "c": "NEDECIS -- datele nu ajung sa decida",
}


# ------------------------------------------------------------------ citire (read-only)
def e_proba(nume):
    """Director-proba (rulare invalidata manual), exclus din tabelele canonice."""
    return any(nume.endswith(s) for s in EXCLUSE_SUFIXE)


def _cheie_ordine(cond):
    return (ORDINE.index(cond) if cond in ORDINE else len(ORDINE), cond)


def descopera_conditii(root, rmw):
    """(conditii_valide, proba_excluse) din <root>/<rmw>/, in ordinea canonica."""
    d = os.path.join(root, rmw)
    if not os.path.isdir(d):
        return [], []
    toate = sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))
    valide = sorted((n for n in toate if not e_proba(n)), key=_cheie_ordine)
    return valide, [n for n in toate if e_proba(n)]


def detecteaza_payloaduri(root):
    """Payload-urile prezente pe disc, din numele fisierelor transport_p<P>.csv.
    O arhiva de campanie C2 contine UN SINGUR payload; daca gaseste altceva, apelantul
    trebuie sa avertizeze in loc sa presupuna."""
    gasite = set()
    for rmw in RMWS:
        d = os.path.join(root, rmw)
        if not os.path.isdir(d):
            continue
        for cond in sorted(os.listdir(d)):
            dc = os.path.join(d, cond)
            if not os.path.isdir(dc):
                continue
            for rep in sorted(os.listdir(dc)):
                dr = os.path.join(dc, rep)
                if not os.path.isdir(dr):
                    continue
                for f in os.listdir(dr):
                    if f.startswith("transport_p") and f.endswith(".csv"):
                        try:
                            gasite.add(int(f[len("transport_p"):-len(".csv")]))
                        except ValueError:
                            pass
    return sorted(gasite)


def _reps(root, rmw, cond):
    d = os.path.join(root, rmw, cond)
    if not os.path.isdir(d):
        return []
    nume = [x for x in os.listdir(d)
            if x.startswith("rep") and os.path.isdir(os.path.join(d, x))]

    def cheie(x):
        try:
            return (0, int(x[3:]))
        except ValueError:
            return (1, 0)
    return [os.path.join(d, x) for x in sorted(nume, key=cheie)]


def citeste_rep(rep_dir, payload, cu_rtt=False):
    """Faptele unei repetitii. Nu arunca exceptii; problemele devin campuri.
    Cand received=0, _summary.json NU are chei de percentile -- forma e suportata."""
    cf = os.path.join(rep_dir, "transport_p%d.csv" % payload)
    sj = os.path.join(rep_dir, "transport_p%d_summary.json" % payload)
    f = {"rep": os.path.basename(rep_dir), "n": None, "sent": None, "received": None,
         "p50_ms": None, "first_seq": None, "randuri": None, "rtts": [],
         "lipsa": False, "corupt": False}
    if not os.path.isfile(cf) or not os.path.isfile(sj):
        f["lipsa"] = True
        return f
    try:
        with open(sj) as fh:
            d = json.load(fh)
        f["n"] = d.get("n")
        f["sent"] = d.get("sent")
        f["received"] = d.get("received")
        f["p50_ms"] = d.get("p50_ms")
    except (ValueError, OSError):
        f["corupt"] = True
        return f
    randuri = 0
    with open(cf, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                seq = int(row["seq"])
            except (KeyError, ValueError, TypeError):
                continue
            randuri += 1
            if f["first_seq"] is None:
                f["first_seq"] = seq
            if cu_rtt:
                try:
                    f["rtts"].append(float(row["rtt_ms"]))
                except (KeyError, ValueError, TypeError):
                    pass
    f["randuri"] = randuri
    return f


def anomalii_rep(f, cond, rmw):
    """Anomalii MECANICE (nu stiintifice) ale unei repetitii."""
    out = []
    unde = "%s/%s/%s" % (rmw, cond, f["rep"])
    if f["lipsa"]:
        return [(unde, "fisiere lipsa (CSV sau _summary.json)")]
    if f["corupt"]:
        return [(unde, "_summary.json ilizibil")]
    if isinstance(f["n"], int) and isinstance(f["randuri"], int) and f["n"] != f["randuri"]:
        out.append((unde, "mismatch summary-vs-CSV: n=%s, randuri CSV=%s"
                    % (f["n"], f["randuri"])))
    if isinstance(f["n"], int) and isinstance(f["sent"], int) and f["n"] > f["sent"]:
        out.append((unde, "n=%d > sent=%d (imposibil)" % (f["n"], f["sent"])))
    if f["n"] and not f["sent"]:
        out.append((unde, "n=%s dar sent lipsa/zero (livrarea nu se poate calcula)" % f["n"]))
    return out


def celula(root, rmw, cond, payload, mod_rtt="p50med"):
    """Agrega o celula (conditie x RMW) cu disciplina supravietuitorilor.
    'prezenta' = am gasit repetitii pe disc; altfel celula lipseste din arhiva."""
    if mod_rtt not in MODURI_RTT:
        raise ValueError("mod RTT necunoscut: %s" % mod_rtt)
    reps = [citeste_rep(rd, payload, cu_rtt=(mod_rtt == "pooled"))
            for rd in _reps(root, rmw, cond)]
    anom = []
    for f in reps:
        anom += anomalii_rep(f, cond, rmw)
    reps = [f for f in reps if not f["lipsa"] and not f["corupt"]]
    N = len(reps)
    morti = [f for f in reps if not f["n"]]                 # n == 0 sau None
    vii = [f for f in reps if f["n"]]
    liv = [100.0 * f["received"] / f["sent"] for f in vii if f.get("sent")]
    p50 = [f["p50_ms"] for f in vii if f["p50_ms"] is not None]
    sent = [f["sent"] for f in vii if f.get("sent")]
    if mod_rtt == "pooled":
        pool = [v for f in vii for v in f["rtts"]]
        rtt_med = statistics.median(pool) if pool else None
    else:
        rtt_med = statistics.median(p50) if p50 else None
    liv_med = statistics.median(liv) if liv else None
    bimodal = bool(p50) and min(p50) > 0 and (max(p50) / min(p50)) >= PRAG_BIMODAL
    return {
        "cond": cond, "rmw": rmw, "payload": payload, "prezenta": N > 0,
        "N": N, "n0": len(morti), "vii": len(vii),
        "liv_med": liv_med,
        "liv_min": min(liv) if liv else None,
        "liv_max": max(liv) if liv else None,
        "liv_efect": (None if (liv_med is None or N == 0)
                      else (1.0 - len(morti) / float(N)) * liv_med),
        "rtt_mod": mod_rtt,
        "rtt_med": rtt_med,
        "rtt_min": min(p50) if p50 else None,
        "rtt_max": max(p50) if p50 else None,
        "bimodal": bimodal,
        "sent_med": statistics.median(sent) if sent else None,
        "n_med": statistics.median([f["n"] for f in vii]) if vii else None,
        "anomalii": anom,
    }


def celule_arhiva(root, payload, mod_rtt="p50med"):
    """{(rmw, cond): celula} pentru toata arhiva, plus directoarele-proba excluse."""
    out, excluse = {}, {}
    for rmw in RMWS:
        conds, ex = descopera_conditii(root, rmw)
        if ex:
            excluse[rmw] = ex
        for c in conds:
            out[(rmw, c)] = celula(root, rmw, c, payload, mod_rtt)
    return out, excluse


# ------------------------------------------------------- contrast intre RMW si inversiune
def contrast(cel_cdds, cel_zenoh, cond):
    """Contrastul CycloneDDS-minus-Zenoh la o conditie, cu TOATE garzile explicite.
    'utilizabil' False => contrastul nu poate sustine niciun verdict; 'motive' spune de ce."""
    c = {"cond": cond, "liv_cdds": None, "liv_zenoh": None, "delta_pp": None,
         "castigator": None, "utilizabil": False, "motive": []}
    m = c["motive"]
    for cel, nume in ((cel_cdds, "cdds"), (cel_zenoh, "zenoh")):
        if cel is None or not cel["prezenta"]:
            m.append("celula lipsa din arhiva (%s)" % nume)
            continue
        if cel["N"] and cel["n0"] == cel["N"]:
            m.append("celula complet moarta (%s): n0=%d/%d, fara mediana"
                     % (nume, cel["n0"], cel["N"]))
            continue
        if cel["N"] and cel["n0"] / float(cel["N"]) > PRAG_N0_FRACT:
            m.append("prea multi n0 (%s): %d/%d > %.0f%%"
                     % (nume, cel["n0"], cel["N"], 100.0 * PRAG_N0_FRACT))
        if cel["vii"] < PRAG_VII_MIN:
            m.append("prea putini supravietuitori (%s): %d < %d"
                     % (nume, cel["vii"], PRAG_VII_MIN))
        if cel["liv_med"] is None:
            m.append("fara mediana de livrare (%s)" % nume)
    if cel_cdds is not None and cel_cdds["prezenta"]:
        c["liv_cdds"] = cel_cdds["liv_med"]
    if cel_zenoh is not None and cel_zenoh["prezenta"]:
        c["liv_zenoh"] = cel_zenoh["liv_med"]
    if c["liv_cdds"] is None or c["liv_zenoh"] is None:
        return c
    c["delta_pp"] = c["liv_cdds"] - c["liv_zenoh"]
    # sarcina oferita: procentele de livrare nu sunt comparabile intre RMW-uri daca
    # unul a apucat sa trimita mult mai putin (contra-presiune RELIABLE la 64 KB)
    sc, sz = cel_cdds["sent_med"], cel_zenoh["sent_med"]
    if sc and sz:
        rap = max(sc, sz) / float(min(sc, sz))
        c["raport_sarcina"] = rap
        if rap > PRAG_SARCINA:
            m.append("sarcina oferita inegala: sent med cdds=%d vs zenoh=%d (raport %.2f > "
                     "%.2f), procentele nu sunt direct comparabile"
                     % (round(sc), round(sz), rap, PRAG_SARCINA))
    if max(c["liv_cdds"], c["liv_zenoh"]) < PRAG_PODEA_PP:
        m.append("prabusire: ambele mediane sub podeaua de %.1f pp (%.2f vs %.2f) -- "
                 "contrastul compara doua feluri de a muri"
                 % (PRAG_PODEA_PP, c["liv_cdds"], c["liv_zenoh"]))
    if abs(c["delta_pp"]) < PRAG_CONTRAST_PP:
        m.append("diferenta sub prag: abs(delta)=%.2f < %.1f pp"
                 % (abs(c["delta_pp"]), PRAG_CONTRAST_PP))
    if not m:
        c["utilizabil"] = True
        c["castigator"] = "cdds" if c["delta_pp"] > 0 else "zenoh"
    return c


def stare_inversiune(contraste):
    """PREZENTA / ABSENTA / NEDECIS pe un singur banc (SIL sau HIL).
    PREZENTA = cel putin doua conditii utilizabile cu castigatori DIFERITI."""
    utile = [c for c in contraste if c["utilizabil"]]
    st = {"utilizabile": [c["cond"] for c in utile],
          "castigatori": {c["cond"]: c["castigator"] for c in utile},
          "blocaje": [(c["cond"], mm) for c in contraste if not c["utilizabil"]
                      for mm in c["motive"]]}
    if len(utile) < 2:
        st["stare"] = "NEDECIS"
        st["motiv"] = ("doar %d conditie/conditii utilizabile (minim 2 ca sa existe un "
                       "contrast intre conditii)" % len(utile))
        return st
    if len(set(c["castigator"] for c in utile)) > 1:
        st["stare"] = "PREZENTA"
        st["motiv"] = "castigatori diferiti intre conditii: " + ", ".join(
            "%s->%s" % (c["cond"], c["castigator"]) for c in utile)
    else:
        st["stare"] = "ABSENTA"
        st["motiv"] = "acelasi castigator (%s) in toate cele %d conditii utilizabile" % (
            utile[0]["castigator"], len(utile))
    return st


def verdict(st_sil, st_hil, hil_prezent):
    """Cele trei rezultate, numite dinainte. Orice garda cazuta -> 'c', cu motiv."""
    v = {"cod": "c", "text": VERDICT_TEXT["c"], "motive": [],
         "sil": st_sil["stare"] if st_sil else None,
         "hil": st_hil["stare"] if st_hil else None}
    if not hil_prezent or st_hil is None:
        v["motive"].append("partea HIL lipseste: rulat fara --hil, campania cablata la "
                           "64 KB nu e (inca) in analiza")
        if st_sil is not None:
            v["motive"].append("referinta SIL: inversiune %s (%s)"
                               % (st_sil["stare"], st_sil["motiv"]))
        return v
    if st_sil is None or st_sil["stare"] == "NEDECIS":
        v["motive"].append("referinta SIL nu e decisa: %s"
                           % (st_sil["motiv"] if st_sil else "arhiva SIL absenta"))
        return v
    if st_sil["stare"] == "ABSENTA":
        v["motive"].append("pe SIL nu exista inversiune de testat: %s" % st_sil["motiv"])
        return v
    if st_hil["stare"] == "NEDECIS":
        v["motive"].append("pe HIL contrastele nu trec garzile: %s" % st_hil["motiv"])
        v["motive"] += ["%s: %s" % (c, m) for c, m in st_hil["blocaje"]]
        return v
    if st_hil["stare"] == "PREZENTA":
        v["cod"], v["text"] = "a", VERDICT_TEXT["a"]
        v["motive"].append("SIL: %s" % st_sil["motiv"])
        v["motive"].append("HIL: %s" % st_hil["motiv"])
        return v
    v["cod"], v["text"] = "b", VERDICT_TEXT["b"]
    v["motive"].append("SIL: %s" % st_sil["motiv"])
    v["motive"].append("HIL: %s" % st_hil["motiv"])
    return v


def analiza(cel_sil, cel_hil, conditii, mod_rtt):
    """Contrastele si starile pe ambele bancuri + verdictul final."""
    c_sil = [contrast(cel_sil.get(("cyclonedds", c)), cel_sil.get(("zenoh", c)), c)
             for c in conditii] if cel_sil is not None else []
    st_sil = stare_inversiune(c_sil) if cel_sil is not None else None
    if cel_hil is None:
        return {"contraste_sil": c_sil, "contraste_hil": [], "stare_sil": st_sil,
                "stare_hil": None, "verdict": verdict(st_sil, None, False),
                "rtt_mod": mod_rtt}
    c_hil = [contrast(cel_hil.get(("cyclonedds", c)), cel_hil.get(("zenoh", c)), c)
             for c in conditii]
    st_hil = stare_inversiune(c_hil)
    return {"contraste_sil": c_sil, "contraste_hil": c_hil, "stare_sil": st_sil,
            "stare_hil": st_hil, "verdict": verdict(st_sil, st_hil, True),
            "rtt_mod": mod_rtt}


# ---------------------------------------------------------------------- formatare (pura)
def _f(v, nd=1):
    return "-" if v is None else ("%%.%df" % nd) % v


def _fi(v):
    return "-" if v is None else "%d" % round(v)


def _d(v, nd=1):
    return "-" if v is None else ("%%+.%df" % nd) % v


CAP_SIL = ["conditie", "payload", "rmw", "N", "n0=k/N", "livr% med (supr.)",
           "livr% efect", "RTT med ms", "nota"]
CAP_AMBELE = ["conditie", "payload", "rmw",
              "SIL N", "SIL n0", "SIL livr% med", "SIL livr% efect", "SIL RTT ms",
              "HIL N", "HIL n0", "HIL livr% med", "HIL livr% efect", "HIL RTT ms",
              "d livr% (HIL-SIL)", "d RTT ms (HIL-SIL)"]


def _nota_celula(cel):
    if cel is None or not cel["prezenta"]:
        return "celula ABSENTA"
    note = []
    if cel["n0"] == cel["N"] and cel["N"]:
        note.append("complet moarta")
    if cel["bimodal"]:
        note.append("BIMODAL (p50 per rulare %.1f..%.1f ms)" % (cel["rtt_min"], cel["rtt_max"]))
    return "; ".join(note) or "-"


def _gol(cond, payload, rmw):
    """Randul unei celule absente: se TIPARESTE, nu dispare in tacere."""
    return {"cond": cond, "rmw": rmw, "payload": payload, "prezenta": False,
            "N": 0, "n0": 0, "vii": 0, "liv_med": None, "liv_min": None, "liv_max": None,
            "liv_efect": None, "rtt_mod": None, "rtt_med": None, "rtt_min": None,
            "rtt_max": None, "bimodal": False, "sent_med": None, "n_med": None,
            "anomalii": []}


def randuri_tabel(cel_sil, cel_hil, conditii, payload):
    """Randurile tabelului, pe UNIUNEA conditiilor, in ordinea canonica."""
    out = []
    for cond in conditii:
        for rmw in RMWS:
            s = (cel_sil or {}).get((rmw, cond)) or _gol(cond, payload, rmw)
            h = None if cel_hil is None else (cel_hil.get((rmw, cond))
                                              or _gol(cond, payload, rmw))
            out.append((cond, rmw, s, h))
    return out


def md_tabel(randuri, cu_hil):
    cap = CAP_AMBELE if cu_hil else CAP_SIL
    out = ["| " + " | ".join(cap) + " |",
           "|" + "|".join(["---"] * len(cap)) + "|"]
    for cond, rmw, s, h in randuri:
        baza = [cond, "%d" % s["payload"], ETICHETA[rmw]]
        if not cu_hil:
            out.append("| " + " | ".join(baza + [
                "%d" % s["N"], "%d/%d" % (s["n0"], s["N"]), _f(s["liv_med"]),
                _f(s["liv_efect"]), _f(s["rtt_med"]), _nota_celula(s)]) + " |")
            continue
        dl = (None if (s["liv_med"] is None or h["liv_med"] is None)
              else h["liv_med"] - s["liv_med"])
        dr = (None if (s["rtt_med"] is None or h["rtt_med"] is None)
              else h["rtt_med"] - s["rtt_med"])
        out.append("| " + " | ".join(baza + [
            "%d" % s["N"], "%d/%d" % (s["n0"], s["N"]), _f(s["liv_med"]),
            _f(s["liv_efect"]), _f(s["rtt_med"]),
            "%d" % h["N"], "%d/%d" % (h["n0"], h["N"]), _f(h["liv_med"]),
            _f(h["liv_efect"]), _f(h["rtt_med"]),
            _d(dl), _d(dr)]) + " |")
    out.append("")
    return "\n".join(out)


def _md_celula(s):
    """Un '|' brut intr-o celula rupe tabelul markdown; motivele sunt text liber."""
    return s.replace("|", "/")


def md_contraste(contraste, titlu):
    out = ["### %s" % titlu, "",
           "| conditie | livr% cdds | livr% zenoh | delta pp (cdds-zenoh) | castigator | "
           "utilizabil | motive |",
           "|---|---|---|---|---|---|---|"]
    for c in contraste:
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            c["cond"], _f(c["liv_cdds"], 2), _f(c["liv_zenoh"], 2), _d(c["delta_pp"], 2),
            c["castigator"] or "-", "DA" if c["utilizabil"] else "NU",
            _md_celula("; ".join(c["motive"]) or "-")))
    out.append("")
    return "\n".join(out)


def md_raport(meta, randuri, an, excluse, anomalii):
    cu_hil = meta["hil"] is not None
    o = ["# 64 KB: SIL-loopback vs HIL-cablat -- supravietuieste inversiunea pe fir?", "",
         "INTREBAREA: inversiunea de la 64 KB (la aceeasi pierdere medie de 15%, semnul",
         "avantajului cdds-minus-zenoh DIFERA intre bern_15 si ge_15_8) e proprietate a",
         "stivelor, sau artefact al MTU-ului de 65536 de pe 'lo'? netem gemodel arunca PER",
         "PACHET, deci acelasi parametru inseamna mult mai multe incercari de drop pe un",
         "MTU de 1500 decat pe loopback.", "",
         "## Provenienta", "",
         "- SIL (loopback): %s" % (meta["sil"] or "ABSENT"),
         "- HIL (cablat)  : %s" % (meta["hil"] or "ABSENT -- asteapta campania"),
         "- payload analizat: %d B" % meta["payload"],
         "- mediana RTT, mod: %s (%s)" % (
             meta["rtt_mod"],
             "mediana celor N valori p50_ms, una per rulare supravietuitoare"
             if meta["rtt_mod"] == "p50med"
             else "mediana peste TOATE esantioanele reunite ale supravietuitorilor"),
         "- conditii analizate: %s" % ", ".join(meta["conditii"]), ""]
    for et, av in (("SIL", meta.get("avert_sil")), ("HIL", meta.get("avert_hil"))):
        for a in (av or []):
            o.append("- ATENTIE %s: %s" % (et, a))
    o += ["", "## Conventii (Wuensch, aceleasi ca in restul C2)", "",
          "- n0=k/N e raportat SEPARAT: k rulari cu ZERO esantioane livrate din N gasite pe",
          "  disc. Medianele sunt CONDITIONATE pe supravietuitori (n>0).",
          "- livrarea per rulare = received/sent citit din fiecare _summary.json (la 64 KB",
          "  'sent' NU e constanta 989: publicarea blocheaza timerul clientului).",
          "- livrarea EFECTIVA (neconditionata) = (1 - n0/N) * mediana.",
          "- celulele BIMODALE sunt marcate: acolo o mediana unica ascunde doua populatii.", ""]
    if not cu_hil:
        o += ["## PARTEA HIL LIPSESTE", "",
              "Rulat FARA --hil. Tabelul de mai jos are DOAR coloana SIL (loopback).",
              "Coloanele HIL si DELTA raman goale pana la campania cablata; verdictul despre",
              "inversiune este prin constructie (c) NEDECIS -- nu exista masuratoare pe fir",
              "care sa poata confirma sau infirma ceva.", ""]
    o += ["## Tabel", "", md_tabel(randuri, cu_hil)]
    if cu_hil:
        o += ["Delta pozitiv = HIL livreaza MAI MULT / e MAI LENT decat SIL. Toate medianele",
              "sunt conditionate pe supravietuitori, deci se citesc IMPREUNA cu n0.", ""]
    o += ["## Contraste intre RMW (baza verdictului)", "",
          "Un 'contrast' = livrare mediana cdds minus livrare mediana zenoh, la aceeasi",
          "conditie si acelasi payload. Inversiunea EXISTA pe un banc daca doua conditii",
          "utilizabile au castigatori DIFERITI. Praguri (constante de modul, declarate):",
          "",
          "- PRAG_CONTRAST_PP = %.1f pp (sub asta diferenta nu se declara)" % PRAG_CONTRAST_PP,
          "- PRAG_PODEA_PP    = %.1f pp (ambele sub asta: prabusire, contrast neinformativ)"
          % PRAG_PODEA_PP,
          "- PRAG_N0_FRACT    = %.2f (n0/N peste asta: celula prea moarta)" % PRAG_N0_FRACT,
          "- PRAG_VII_MIN     = %d supravietuitori minimi" % PRAG_VII_MIN,
          "- PRAG_SARCINA     = %.2f (raport max al sarcinii oferite intre RMW-uri)"
          % PRAG_SARCINA,
          "- PRAG_BIMODAL     = %.0f (max/min p50 peste asta: celula marcata BIMODAL)"
          % PRAG_BIMODAL, ""]
    o.append(md_contraste(an["contraste_sil"], "SIL (loopback)"))
    if cu_hil:
        o.append(md_contraste(an["contraste_hil"], "HIL (cablat)"))
    for et, st in (("SIL", an["stare_sil"]), ("HIL", an["stare_hil"])):
        if st is not None:
            o.append("- inversiune pe %s: **%s** -- %s" % (et, st["stare"], st["motiv"]))
    v = an["verdict"]
    o += ["", "## VERDICT", "",
          "Cele trei rezultate posibile, numite INAINTE de a vedea datele:", "",
          "- (a) %s" % VERDICT_TEXT["a"],
          "- (b) %s" % VERDICT_TEXT["b"],
          "- (c) %s" % VERDICT_TEXT["c"], "",
          "**REZULTAT: (%s) %s**" % (v["cod"], v["text"]), ""]
    for m in v["motive"]:
        o.append("- %s" % m)
    o += ["", "Scriptul NU alege (a) sau (b) cand o garda cade: orice garda cazuta duce",
          "determinist la (c), cu motivul de mai sus.", ""]
    if excluse:
        for et, ex in sorted(excluse.items()):
            o.append("EXCLUS (director-proba, %s): %s" % (et, ", ".join(ex)))
        o.append("")
    o += ["## Anomalii mecanice", ""]
    if anomalii:
        for unde, ce in anomalii:
            o.append("- %s: %s" % (unde, ce))
    else:
        o.append("- niciuna")
    o.append("")
    return "\n".join(o)


def json_raport(meta, randuri, an, excluse, anomalii):
    def cel(c):
        if c is None:
            return None
        d = {k: v for k, v in c.items() if k != "anomalii"}
        return d
    return {
        "schema": "compara_sil_hil_64k/1",
        "meta": meta,
        "praguri": {"PRAG_CONTRAST_PP": PRAG_CONTRAST_PP, "PRAG_PODEA_PP": PRAG_PODEA_PP,
                    "PRAG_N0_FRACT": PRAG_N0_FRACT, "PRAG_VII_MIN": PRAG_VII_MIN,
                    "PRAG_SARCINA": PRAG_SARCINA, "PRAG_BIMODAL": PRAG_BIMODAL},
        "celule": [{"cond": c, "rmw": r, "sil": cel(s), "hil": cel(h)}
                   for c, r, s, h in randuri],
        "contraste_sil": an["contraste_sil"],
        "contraste_hil": an["contraste_hil"],
        "stare_sil": an["stare_sil"],
        "stare_hil": an["stare_hil"],
        "verdict": an["verdict"],
        "excluse": excluse,
        "anomalii": [{"unde": u, "ce": c} for u, c in anomalii],
    }


# --------------------------------------------------------------------- scriere protejata
def verifica_tinta(out_dir):
    """Arhivele de campanie sunt SIGILATE: singura tinta permisa sub ~/DATE_CAMPANIE este
    ~/DATE_CAMPANIE/ANALIZA_C2/. Orice alta cale de sub DATE_CAMPANIE e refuzata."""
    a = os.path.abspath(os.path.expanduser(out_dir))
    d, p = os.path.abspath(DATE), os.path.abspath(OUT_DEFAULT)
    sub_date = a == d or a.startswith(d + os.sep)
    sub_permis = a == p or a.startswith(p + os.sep)
    if sub_date and not sub_permis:
        raise ValueError("REFUZ sa scriu in %s: arhivele de campanie sunt sigilate, "
                         "singura tinta permisa sub %s este %s" % (a, d, p))
    return a


def scrie(cale, text):
    with open(cale, "w") as f:
        f.write(text)
    print("  scris %s (%d octeti)" % (cale, len(text.encode())))


# ------------------------------------------------------------------------------ selftest
def _fab(root, rmw, cond, rulari, payload=65536):
    """Fabrica o celula sintetica. 'rulari' = lista de (sent, received, p50_ms);
    received=0 => rulare moarta, iar _summary.json NU primeste chei de percentile
    (exact forma reala scrisa de bench_core.rtt_stats)."""
    for i, (sent, recv, p50) in enumerate(rulari, start=1):
        rd = os.path.join(root, rmw, cond, "rep%d" % i)
        os.makedirs(rd)
        with open(os.path.join(rd, "transport_p%d.csv" % payload), "w") as f:
            f.write("seq,rtt_ms\n")
            for k in range(recv):
                f.write("%d,%.3f\n" % (11 + k, p50))
        d = {"n": recv, "sent": sent, "received": recv,
             "loss": round(1.0 - (recv / float(sent) if sent else 0.0), 4)}
        if recv:
            d.update({"mean_ms": p50, "p50_ms": p50, "p95_ms": p50, "p99_ms": p50,
                      "min_ms": p50, "max_ms": p50})
        d.update({"payload": payload, "rate_hz": 50.0, "duration_s": 20.0, "rmw": rmw})
        with open(os.path.join(rd, "transport_p%d_summary.json" % payload), "w") as f:
            json.dump(d, f)


def _celule(root, payload=65536, mod="p50med"):
    return celule_arhiva(root, payload, mod)[0]


def _run(cel_sil, cel_hil, conditii=("bern_15", "ge_15_8"), mod="p50med"):
    return analiza(cel_sil, cel_hil, list(conditii), mod)


def _selftest():
    """Fixture SINTETICE in tmp. Fara retea, fara DATE_CAMPANIE, fara scriere in arhive."""
    import shutil
    import tempfile
    baza = tempfile.mkdtemp(prefix="compara64_selftest_")
    n_ver = 0

    def ok(cond, mesaj):
        nonlocal n_ver
        assert cond, mesaj
        n_ver += 1

    def liv(pct, sent=989):
        return (sent, int(round(sent * pct / 100.0)), 100.0)

    try:
        # ---------------------------------------------------------------- 1. n0 = k/N
        r = os.path.join(baza, "n0")
        # 5 rulari: 2 moarte, 3 vii cu livrare 10 / 20 / 60 % (din sent=100)
        _fab(r, "zenoh", "ge_15_8", [(100, 10, 5.0), (100, 20, 7.0), (100, 60, 9.0),
                                     (100, 0, 0.0), (100, 0, 0.0)])
        c = celula(r, "zenoh", "ge_15_8", 65536)
        ok(c["N"] == 5 and c["n0"] == 2 and c["vii"] == 3, "n0=k/N gresit: %s" % c)
        ok(c["liv_med"] == 20.0, "mediana pe supravietuitori gresita: %s" % c["liv_med"])
        ok(c["liv_min"] == 10.0 and c["liv_max"] == 60.0, "min/max pe supravietuitori")
        # mortii NU trag mediana in jos (cu zerourile ar fi fost 10.0)
        ok(statistics.median([0, 0, 10, 20, 60]) == 10.0, "control: mediana cu morti inclusi")
        # ---------------------------------------------- 2. livrare efectiva = (1-n0/N)*med
        ok(abs(c["liv_efect"] - (1 - 2 / 5.0) * 20.0) < 1e-9,
           "livrare efectiva gresita: %s" % c["liv_efect"])
        ok(abs(c["liv_efect"] - 12.0) < 1e-9, "livrare efectiva != 12.0: %s" % c["liv_efect"])
        # ------------------------------------------------------ 3. mediana RTT, doua moduri
        ok(c["rtt_med"] == 7.0, "RTT p50med gresit: %s" % c["rtt_med"])
        cp = celula(r, "zenoh", "ge_15_8", 65536, mod_rtt="pooled")
        # pooled: 10x5 + 20x7 + 60x9 esantioane -> mediana e 9.0 (dominata de rularea lunga)
        ok(cp["rtt_med"] == 9.0, "RTT pooled gresit: %s" % cp["rtt_med"])
        ok(cp["rtt_med"] != c["rtt_med"], "cele doua moduri trebuie sa poata diferi")
        # marcaj de bimodalitate (2.2 ms vs 3300 ms, ca in celula reala zenoh/ge_15_8)
        rb = os.path.join(baza, "bimodal")
        _fab(rb, "zenoh", "ge_15_8", [(989, 5, 2.2), (989, 5, 2.3), (989, 5, 3300.0),
                                      (989, 5, 4000.0)])
        ok(celula(rb, "zenoh", "ge_15_8", 65536)["bimodal"], "bimodalitatea nu a fost prinsa")
        ok(not c["bimodal"], "fals pozitiv de bimodalitate")
        # celula complet moarta: fara mediana, dar N si n0 raportate
        rm = os.path.join(baza, "moarta")
        _fab(rm, "zenoh", "ge_15_8", [(989, 0, 0.0)] * 4)
        cm = celula(rm, "zenoh", "ge_15_8", 65536)
        ok(cm["N"] == 4 and cm["n0"] == 4 and cm["liv_med"] is None and cm["liv_efect"] is None,
           "celula complet moarta: %s" % cm)

        # ------------------------------------------------------------- 4. VERDICT (a)
        # SIL: bern_15 -> zenoh castiga; ge_15_8 -> cdds castiga (inversiune PREZENTA)
        # HIL: acelasi tipar -> inversiunea PERSISTA
        sa = os.path.join(baza, "a_sil")
        ha = os.path.join(baza, "a_hil")
        for r0 in (sa, ha):
            _fab(r0, "cyclonedds", "bern_15", [liv(30.0)] * 10)
            _fab(r0, "zenoh", "bern_15", [liv(90.0)] * 10)
            _fab(r0, "cyclonedds", "ge_15_8", [liv(95.0)] * 10)
            _fab(r0, "zenoh", "ge_15_8", [liv(10.0)] * 10)
        an = _run(_celule(sa), _celule(ha))
        ok(an["stare_sil"]["stare"] == "PREZENTA", "SIL(a): %s" % an["stare_sil"])
        ok(an["stare_hil"]["stare"] == "PREZENTA", "HIL(a): %s" % an["stare_hil"])
        ok(an["verdict"]["cod"] == "a", "verdict(a) gresit: %s" % an["verdict"])
        ok(an["stare_sil"]["castigatori"] == {"bern_15": "zenoh", "ge_15_8": "cdds"},
           "castigatori(a): %s" % an["stare_sil"]["castigatori"])

        # ------------------------------------------------------------- 5. VERDICT (b)
        # HIL: acelasi castigator (cdds) la ambele conditii -> inversiunea DISPARE
        hb = os.path.join(baza, "b_hil")
        _fab(hb, "cyclonedds", "bern_15", [liv(90.0)] * 10)
        _fab(hb, "zenoh", "bern_15", [liv(30.0)] * 10)
        _fab(hb, "cyclonedds", "ge_15_8", [liv(95.0)] * 10)
        _fab(hb, "zenoh", "ge_15_8", [liv(10.0)] * 10)
        an = _run(_celule(sa), _celule(hb))
        ok(an["stare_hil"]["stare"] == "ABSENTA", "HIL(b): %s" % an["stare_hil"])
        ok(an["verdict"]["cod"] == "b", "verdict(b) gresit: %s" % an["verdict"])

        # ------------------------------------------------------------- 6. VERDICT (c)
        # (c1) HIL prabusit sub podea la bern_15 + celula complet moarta la ge_15_8
        hc = os.path.join(baza, "c_hil")
        _fab(hc, "cyclonedds", "bern_15", [liv(0.5)] * 10)
        _fab(hc, "zenoh", "bern_15", [liv(2.2)] * 10)
        _fab(hc, "cyclonedds", "ge_15_8", [liv(6.2)] * 10)
        _fab(hc, "zenoh", "ge_15_8", [(989, 0, 0.0)] * 10)
        an = _run(_celule(sa), _celule(hc))
        ok(an["stare_hil"]["stare"] == "NEDECIS", "HIL(c1): %s" % an["stare_hil"])
        ok(an["verdict"]["cod"] == "c", "verdict(c1) gresit: %s" % an["verdict"])
        mot = " ".join(an["verdict"]["motive"])
        ok("podeaua" in mot, "motivul de podea lipseste: %s" % mot)
        ok("complet moarta" in mot, "motivul de celula moarta lipseste: %s" % mot)
        # (c2) HIL absent cu totul (modul in care ruleaza acum, fara --hil)
        an = _run(_celule(sa), None)
        ok(an["stare_hil"] is None and an["verdict"]["cod"] == "c", "verdict(c2)")
        ok("partea HIL lipseste" in " ".join(an["verdict"]["motive"]), "motiv(c2)")
        # (c3) diferenta sub prag -> contrast NEUTILIZABIL, nu 'castigator la mustata'
        hc3 = os.path.join(baza, "c3_hil")
        _fab(hc3, "cyclonedds", "bern_15", [liv(50.0)] * 10)
        _fab(hc3, "zenoh", "bern_15", [liv(52.0)] * 10)   # delta 2 pp < 5 pp
        _fab(hc3, "cyclonedds", "ge_15_8", [liv(95.0)] * 10)
        _fab(hc3, "zenoh", "ge_15_8", [liv(10.0)] * 10)
        an = _run(_celule(sa), _celule(hc3))
        ok(an["verdict"]["cod"] == "c", "verdict(c3) gresit: %s" % an["verdict"])
        ok("sub prag" in " ".join(m for _, m in an["stare_hil"]["blocaje"]), "motiv(c3)")
        # tabelul de contraste ramane un tabel valid: 7 coloane => 8 bare pe fiecare rand
        linii = [l for l in md_contraste(an["contraste_hil"], "T").split("\n")
                 if l.startswith("|")]
        ok(linii and all(l.count("|") == 8 for l in linii),
           "un '|' din motive a rupt tabelul: %s" % linii)
        # (c4) sarcina oferita inegala intre RMW-uri (contra-presiune RELIABLE la 64 KB)
        hc4 = os.path.join(baza, "c4_hil")
        _fab(hc4, "cyclonedds", "bern_15", [liv(30.0, sent=400)] * 10)
        _fab(hc4, "zenoh", "bern_15", [liv(90.0, sent=989)] * 10)
        _fab(hc4, "cyclonedds", "ge_15_8", [liv(95.0)] * 10)
        _fab(hc4, "zenoh", "ge_15_8", [liv(10.0)] * 10)
        an = _run(_celule(sa), _celule(hc4))
        ok(an["verdict"]["cod"] == "c", "verdict(c4) gresit: %s" % an["verdict"])
        ok("sarcina oferita inegala" in " ".join(m for _, m in an["stare_hil"]["blocaje"]),
           "motiv(c4)")
        # (c5) fara inversiune nici pe SIL -> nu exista ce testa pe fir
        s5 = os.path.join(baza, "c5_sil")
        _fab(s5, "cyclonedds", "bern_15", [liv(90.0)] * 10)
        _fab(s5, "zenoh", "bern_15", [liv(30.0)] * 10)
        _fab(s5, "cyclonedds", "ge_15_8", [liv(95.0)] * 10)
        _fab(s5, "zenoh", "ge_15_8", [liv(10.0)] * 10)
        an = _run(_celule(s5), _celule(ha))
        ok(an["stare_sil"]["stare"] == "ABSENTA", "SIL(c5): %s" % an["stare_sil"])
        ok(an["verdict"]["cod"] == "c", "verdict(c5) gresit: %s" % an["verdict"])
        ok("nu exista inversiune de testat" in " ".join(an["verdict"]["motive"]), "motiv(c5)")
        # (c6) o singura conditie utilizabila -> NEDECIS (nu se poate vorbi de inversiune)
        an = _run(_celule(sa), _celule(ha), conditii=("bern_15",))
        ok(an["stare_sil"]["stare"] == "NEDECIS" and an["verdict"]["cod"] == "c", "(c6)")

        # ------------------------------------- 7. celule fara pereche (ideal doar pe HIL)
        hi = os.path.join(baza, "ideal_hil")
        _fab(hi, "cyclonedds", "ideal", [liv(100.0)] * 10)
        _fab(hi, "zenoh", "ideal", [liv(29.5)] * 10)
        _fab(hi, "cyclonedds", "bern_15", [liv(0.5)] * 10)
        _fab(hi, "zenoh", "bern_15", [liv(2.2)] * 10)
        cs, ch = _celule(sa), _celule(hi)
        conds = sorted(set(k[1] for k in cs) | set(k[1] for k in ch), key=_cheie_ordine)
        ok(conds == ["ideal", "bern_15", "ge_15_8"], "uniunea conditiilor: %s" % conds)
        rr = randuri_tabel(cs, ch, conds, 65536)
        ok(len(rr) == 6, "randuri: %d" % len(rr))
        ideal = [t for t in rr if t[0] == "ideal"][0]
        ok(not ideal[2]["prezenta"] and ideal[3]["prezenta"],
           "'ideal' trebuie sa apara cu SIL absent, nu sa dispara")
        md = md_tabel(rr, cu_hil=True)
        ok("| ideal | 65536 | cdds |" in md and "celula ABSENTA" not in md.split("\n")[0],
           "randul ideal lipseste din markdown")
        ok(md.count("| ge_15_8 |") == 2, "ge_15_8 trebuie sa apara pe ambele RMW")

        # --------------------------------------------------- 8. delta SIL-vs-HIL in tabel
        rr2 = randuri_tabel(_celule(sa), _celule(hb), ["bern_15", "ge_15_8"], 65536)
        md2 = md_tabel(rr2, cu_hil=True)
        # cdds/bern_15: SIL 30% -> HIL 90% => +60.0 pp
        linie = [l for l in md2.split("\n") if l.startswith("| bern_15 | 65536 | cdds |")][0]
        ok("+60.0" in linie, "delta livrare gresita: %s" % linie)

        # ------------------------------------------------- 9. detectia payload-ului
        ok(detecteaza_payloaduri(sa) == [65536], "detectie payload: %s"
           % detecteaza_payloaduri(sa))
        cgol = celula(sa, "cyclonedds", "bern_15", 4096)
        ok(cgol["N"] == 0 and not cgol["prezenta"],
           "payload inexistent trebuie sa dea celula ABSENTA, nu exceptie")

        # -------------------------------- 10. director-proba exclus + anomalii mecanice
        rp = os.path.join(baza, "proba")
        _fab(rp, "zenoh", "bern_15", [liv(50.0)] * 3)
        _fab(rp, "zenoh", "bern_15_MIXT_INVALID", [liv(50.0)] * 3)
        valide, ex = descopera_conditii(rp, "zenoh")
        ok(valide == ["bern_15"] and ex == ["bern_15_MIXT_INVALID"], "proba: %s %s"
           % (valide, ex))
        ok(e_proba("x_ECOUMORT") and e_proba("y_INVALID") and not e_proba("ge_15_8"),
           "e_proba")
        ra = os.path.join(baza, "anom")
        _fab(ra, "zenoh", "bern_15", [(989, 5, 1.0)])
        sjp = os.path.join(ra, "zenoh", "bern_15", "rep1", "transport_p65536_summary.json")
        with open(sjp) as fh:
            dd = json.load(fh)
        dd["n"] = 12
        dd["received"] = 12
        with open(sjp, "w") as fh:
            json.dump(dd, fh)
        ca = celula(ra, "zenoh", "bern_15", 65536)
        ok(any("mismatch summary-vs-CSV" in m for _, m in ca["anomalii"]),
           "mismatch neprins: %s" % ca["anomalii"])

        # ------------------------------------------------- 11. garda de scriere (pura)
        ok(verifica_tinta(OUT_DEFAULT).endswith("ANALIZA_C2"), "tinta permisa refuzata")
        for rea in (DATE, os.path.join(DATE, "C2_SIL64_20260719"),
                    os.path.join(DATE, "C2_SIL64_20260719", "cyclonedds")):
            try:
                verifica_tinta(rea)
                raise AssertionError("verifica_tinta a acceptat %s" % rea)
            except ValueError:
                n_ver += 1
        ok(verifica_tinta(baza) == os.path.abspath(baza), "tinta din tmp refuzata")

        # ------------------------------------------- 12. raportul se construieste intreg
        meta = {"sil": sa, "hil": None, "payload": 65536, "rtt_mod": "p50med",
                "conditii": ["bern_15", "ge_15_8"], "avert_sil": [], "avert_hil": []}
        an = _run(_celule(sa), None)
        rr3 = randuri_tabel(_celule(sa), None, ["bern_15", "ge_15_8"], 65536)
        txt = md_raport(meta, rr3, an, {}, [])
        ok("PARTEA HIL LIPSESTE" in txt, "modul fara HIL nu e anuntat")
        ok("**REZULTAT: (c)" in txt, "verdictul lipseste din raport")
        ok("d livr%" not in txt, "coloanele de delta nu au ce cauta fara HIL")
        js = json_raport(meta, rr3, an, {}, [])
        ok(json.loads(json.dumps(js))["verdict"]["cod"] == "c", "JSON neserializabil")
        ok(len(js["celule"]) == 4, "JSON: %d celule" % len(js["celule"]))
        ok(all(ord(ch) < 128 for ch in txt), "raportul contine non-ASCII")

        print("SELFTEST compara_sil_hil_64k OK (%d verificari, fixture temporar in tmp; "
              "fara retea, fara DATE_CAMPANIE)." % n_ver)
    finally:
        shutil.rmtree(baza, ignore_errors=True)


# ---------------------------------------------------------------------------------- main
def _arg(argv, nume, implicit=None):
    return argv[argv.index(nume) + 1] if nume in argv else implicit


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    try:
        sil = _arg(argv, "--sil", SIL_DEFAULT)
        hil = _arg(argv, "--hil", None)
        payload = int(_arg(argv, "--payload", PAYLOAD_DEFAULT))
        mod_rtt = _arg(argv, "--rtt", "p50med")
        out = _arg(argv, "--out", OUT_DEFAULT)
    except (IndexError, ValueError) as e:
        print("argumente invalide: %s" % e)
        return 2
    if mod_rtt not in MODURI_RTT:
        print("mod RTT necunoscut: %s (permise: %s)" % (mod_rtt, ", ".join(MODURI_RTT)))
        return 2
    sil = os.path.abspath(os.path.expanduser(sil))
    if not os.path.isdir(sil):
        print("arhiva SIL inexistenta: %s" % sil)
        return 2
    if hil is not None:
        hil = os.path.abspath(os.path.expanduser(hil))
        if not os.path.isdir(hil):
            print("arhiva HIL inexistenta: %s" % hil)
            return 2
    try:
        out = verifica_tinta(out)
    except ValueError as e:
        print(str(e))
        return 2

    print("SIL    : %s" % sil)
    print("HIL    : %s" % (hil or "ABSENT (rulare fara --hil: doar coloana SIL)"))
    print("payload: %d B   RTT: %s   iesire: %s" % (payload, mod_rtt, out))

    cel_sil, ex_sil = celule_arhiva(sil, payload, mod_rtt)
    excluse = {"SIL " + k: v for k, v in ex_sil.items()}
    avert_sil = []
    pls = detecteaza_payloaduri(sil)
    if pls and payload not in pls:
        avert_sil.append("arhiva SIL nu contine payload %d B (are: %s)"
                         % (payload, ", ".join(str(p) for p in pls)))
    if len(pls) > 1:
        avert_sil.append("arhiva SIL contine mai multe payload-uri: %s"
                         % ", ".join(str(p) for p in pls))
    cel_hil, avert_hil = None, []
    if hil is not None:
        cel_hil, ex_hil = celule_arhiva(hil, payload, mod_rtt)
        excluse.update({"HIL " + k: v for k, v in ex_hil.items()})
        plh = detecteaza_payloaduri(hil)
        if plh and payload not in plh:
            avert_hil.append("arhiva HIL nu contine payload %d B (are: %s)"
                             % (payload, ", ".join(str(p) for p in plh)))
        if len(plh) > 1:
            avert_hil.append("arhiva HIL contine mai multe payload-uri: %s"
                             % ", ".join(str(p) for p in plh))

    conditii = set(k[1] for k in cel_sil)
    if cel_hil is not None:
        conditii |= set(k[1] for k in cel_hil)
    conditii = sorted(conditii, key=_cheie_ordine)
    if not conditii:
        print("nicio conditie gasita: verifica structura <arhiva>/<rmw>/<conditie>/rep<N>/")
        return 2
    # conditiile fara pereche se anunta, nu dispar in tacere
    if cel_hil is not None:
        for c in conditii:
            fs = any((r, c) in cel_sil for r in RMWS)
            fh = any((r, c) in cel_hil for r in RMWS)
            if fs and not fh:
                avert_hil.append("conditia '%s' exista in SIL dar NU in HIL (fara pereche)" % c)
            if fh and not fs:
                avert_sil.append("conditia '%s' exista in HIL dar NU in SIL (fara pereche)" % c)

    an = analiza(cel_sil, cel_hil, conditii, mod_rtt)
    randuri = randuri_tabel(cel_sil, cel_hil, conditii, payload)
    anomalii = []
    for c in list(cel_sil.values()) + list((cel_hil or {}).values()):
        anomalii += c["anomalii"]
    meta = {"sil": sil, "hil": hil, "payload": payload, "rtt_mod": mod_rtt,
            "conditii": conditii, "avert_sil": avert_sil, "avert_hil": avert_hil}

    txt = md_raport(meta, randuri, an, excluse, anomalii)
    print("")
    print(txt)
    if "--stdout-only" not in argv:
        os.makedirs(out, exist_ok=True)
        scrie(os.path.join(out, "compara_sil_hil_64k.md"), txt)
        scrie(os.path.join(out, "compara_sil_hil_64k.json"),
              json.dumps(json_raport(meta, randuri, an, excluse, anomalii), indent=1) + "\n")
    print("VERDICT: (%s) %s" % (an["verdict"]["cod"], an["verdict"]["text"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
