# SUMAR FINAL -- audit + inchidere date articol C1 (branch paper/audit-v2)

## VERDICT GLOBAL
AUDIT CIFRE (Pas 1): PASS INTEGRAL. Zero valori picate dincolo de rotunjire.
- Tabel II: 32/32 celule PASS.  Tabel III: 8/8 PASS.  Sec 4.5 rulare reprezentativa: localizata
  exact (nu [NEVERIFICABIL]).  Sec 4.1 + Abstract: coerente.
FIGURI (Pas 2/3): fig_payload_en (Fig. 4) regenerata cu zecimale canonice si swap-uita in docx
  (image6, pixel-identic). fig_loss_sil_hil_en + fig_divergence_en generate (embedded==Tabel II).
BLOCAJ ONEST: fig_rtt_p95_en (Fig. 7 / image7) NU generabila -- HIL zenoh lat200_l15 received=0
  (p95 gol), load_summary face float('') si crapa; fix in afara editarii permise. image7 NEATINS.
Doua neconcordante de FORMULARE (nu de cifra): Sec 4.1 ("11-13 ms") si Sec 3.2/ec.(1) (distributie).

## CELE 3 RASPUNSURI DE ONESTITATE (1a, din cod)
1. Jitter: pipeline-ul NU calculeaza jitter. rtt_stats (bench_core.py:48-60) da doar loss + RTT
   percentile/mean/min/max. "jitter" = doar parametru netem la intrare (jitter_ms). Corect in draft.
2. RTT single-clock: DA -- client stampileaza plecare+intoarcere pe acelasi time.time()
   (bench_client.py:34,43). Sec 3.3 "RTT uses a single clock" = PASS.
3. Agregare: media pe repetitii a metricilor per-rep (make_tables.py:37-64), NU concatenare.
   Draftul o afirma deja corect in Sec 3.3.

## FRAZE GATA DE LIPIT (Alexandru le scrie cu vocea lui)
(a) Fix Sec 4.1 -- restrange "11-13 ms":
    varianta minima:  "... clean at 64 B and 4 KB (0% loss); mean RTT of 11-13 ms at 4 KB."
    varianta completa (ambele payload-uri): "... mean RTT of 4-18 ms at 64 B and 11-13 ms at 4 KB,
      0% loss." (canonic HIL ideal mean: 64B cdds 4.0 / zenoh 18.1; 4KB cdds 11.3 / zenoh 12.9.)
(b) Sterge TODO-ul de agregare din Sec 3.3 -- metoda e CONFIRMATA corecta (media pe rep). Fraza
    "condition-level figures aggregate per-repetition summaries" ramane ca atare (e adevarata).
(c) Rewording Sec 3.2 / ec. (1) / Lim. 6 la distributie UNIFORMA (comanda tc a rulat FARA
    'distribution normal' -> kernel uniform; vezi 1d):
    Sec 3.2: "delay variation (jitter) uses netem's uniform distribution (no distribution table
      loaded; per the kernel the jitter is drawn uniformly, despite the man page's nominal
      'Normal')."
    ec. (1): "d_i = DELAY + x_i * JITTER,   x_i ~ U(-1, 1)."
    Lim. (6): "uniform-distributed jitter."
(d) Fig. 4 (caption/text) -- zecimale exacte: la ideal, 64 KB pe Wi-Fi, Zenoh pierde 57.8%
    (rotunjit 58%), CycloneDDS 0%.
(e) Sec 3.1 versiuni: vezi VERSIUNI_3.1.md (laptop cules; Pi de completat prin snippet SSH).

## TOP 3 DECIZII CARE RAMAN LA ALEXANDRU
1. Fig. 7 (image7): fie extinde make_figures_c1_en.py (load_summary sa tolereze p95 gol +
   fig_rtt_p95 sa marcheze received=0, ca figura RO) apoi regenereaza + swap; fie pastreaza Fig. 7
   RO provizorie. NU am editat load_summary (in afara scopului). image7 e NEATINS in docx.
2. Distributia jitter (1d): accepta rewording-ul la UNIFORM (datele reflecta uniform), SAU
   re-ruleaza cu 'distribution normal' explicit daca vrei modelul normal (schimba doar forma
   jitter-ului, nu concluziile). Recomand rewording la uniform -- nicio re-rulare, mai onest.
3. Confirma versiunile Pi (VERSIUNI_3.1.md) si ca versiunile laptop culese azi == cele din campanie.

## LIVRABILE (branch paper/audit-v2, un commit per pas; MERGE il face Alexandru)
- pas 0: draft v2 + make_figures_c1_en.py in paper/
- pas 1 + 1d: AUDIT_CIFRE_ARTICOL.md (PASS integral + comanda tc netem)
- pas 2: campaign_summary.csv + figuri_en/ + PAYLOAD_LOSS canonic
- pas 3a: swap image6 (Fig.4) in docx; original pastrat ca _pre-swap.docx
- pas 4: MANIFEST_DATE.md (sursa de adevar, 720 SHA256, matrice, structura Zenodo)
- pas 5: VERSIUNI_3.1.md
- pas 6: acest SUMAR_FINAL.md
NEATINS (regula): datele brute ~/DATE_CAMPANIE/, codul c1_benchmark/*.py, textul articolului.
