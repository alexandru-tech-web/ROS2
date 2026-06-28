# Progres matrice 2x2
(branch overnight-matrix-2x2, construit peste overnight-sil-hil-flag, deja merge-uit in main)
Task 1 (extindere etichetare mediu+middleware): DONE
Task 2 (comparatie 4-way / structura tabel matrice): TODO
Task 3 (runbook-uri pentru ambele interfete): TODO
Task 4 (teste): TODO
Note:
- Task 1: adaugat env_label(env) {sil/hil_wifi/hil_switch} ALATURI de mode_label (PASTRAT) in
  analyze_campaign.py, campaign_stats.py, sil_vs_hil_table.py (DUPLICAT identic, ca mode_label).
  analyze() foloseste acum env_label (param redenumit mode->env). CLI --mode: choices extinse la
  {sil, hil_wifi, hil_switch, hil}; "hil" generic -> EROARE blanda (exit 2) care cere hil_wifi/
  hil_switch (per spec: ambiguitatea wifi/switch conteaza pe matrice); lipsa --mode -> avertisment+sil.
  APELANTI SPARTI (de actualizat in Task 3): runbook-urile care dau "--mode hil" vor primi eroare;
  de schimbat la hil_wifi sau hil_switch.
- PROBLEMA DE MEDIU (NU codul meu): matplotlib LIPSESTE in acest mediu (sesiunea trecuta era prezent).
  analyze_campaign il importa la nivel de MODUL (liniile 27-29) -> ne-importabil/ne-rulabil aici;
  campaign_stats il importa LENES (in functii) -> importabil. NU am facut pip install (spec) si NU am
  refactorizat importul matplotlib din analyze_campaign (ar fi extindere de scop + risc pe selftest).
  Consecinta: nu pot rula analyze_campaign ca CLI aici (--mode hil da exit 1 = eroare de import, nu
  exit 2). Am verificat env_label + eroarea blanda prin: (a) campaign_stats (rulabil) -> exit 2
  confirmat; (b) cod IDENTIC in analyze_campaign; (c) test cu STUB matplotlib -> env_label identic in
  cele 3 copii + ValueError, mode_label compat.
  DE VAZUT ALEXANDRU: ori instaleaza matplotlib, ori analyze_campaign are nevoie de import LENES
  (ca campaign_stats) ca sa ruleze fara matplotlib. test_mode_label importa analyze_campaign -> e rupt
  in acest mediu fara matplotlib; in Task 4 il fac robust (stub matplotlib daca lipseste).
  VERIFICAT: ASCII curat (3 fisiere), py_compile OK, campaign_stats --selftest 17/17.
