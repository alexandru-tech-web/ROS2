# Progres overnight SIL/HIL flag
Task 1 (analyze_campaign --mode + subtitlu): DONE
Task 2 (propagare --mode in campaign_stats + sil_vs_hil_table): DONE
Task 3 (teste pentru logica de mod): DONE
Note:
- Task 1: adaugat mode_label(mode) (functie PURA) + flag --mode {sil,hil} in analyze_campaign.py.
  DECIZIE DE DESIGN: --mode are default=None; daca lipseste -> AVERTISMENT pe stderr + presupun
  "sil" (NU eroare dura), ca sa nu rup apelantii existenti (HIL_RUNBOOK.md ruleaza analyze_campaign
  fara --mode). default=None permite sa disting "explicit" de "presupus".
  Cele 3 subtitluri hardcodate "SIL (loopback)" -> mode_label(mode) (transport/mission/cdf).
  Nimic altceva schimbat (cifre/layout/calcule neatinse).
  VERIFICAT (rulare reala, READ-ONLY pe arhiva, --out in scratch ca sa NU scriu in arhiva):
    * --mode hil pe ~/c1_archive/hil_cyclonedds_20260627_1005 -> subtitlu "HIL (two-machine)"
      (confirmat VIZUAL in fig_transport.png).
    * --mode sil pe ~/c1_archive/mixed_backup_0856 -> subtitlu "SIL (loopback)".
    * fara --mode -> avertisment pe stderr, presupune sil.
    * mode_label('sil')='SIL (loopback)', mode_label('hil')='HIL (two-machine)'.
    * arhiva NEATINSA (find -newermt: niciun fisier nou scris in ea).
  ASCII curat, py_compile OK, --selftest OK.
- Task 2: campaign_stats.py hardcoda "SIL (loopback)" in 2 captions (plot_cdf, plot_p95_ci) ->
  adaugat mode_label (DUPLICAT, identic) + --mode {sil,hil} (default None + avertisment) +
  param label la cele 2 functii. VERIFICAT: --demo --mode hil -> caption "HIL (two-machine)"
  (confirmat VIZUAL in fig_p95_ci.png); --selftest 17/17; avertisment pe stderr fara --mode.
  sil_vs_hil_table.py: compara prin NATURA SIL vs HIL -> NU am fortat un singur --mode (per spec);
  coloanele folosesc acum mode_label -> "SIL (loopback)" / "HIL (two-machine)" + linie de legenda.
  --selftest 10/10.
  DECIZIE: mode_label DUPLICAT in 3 fisiere (analyze_campaign = canonic; campaign_stats +
  sil_vs_hil_table identice). Motiv: cea mai mica atingere -- importul lui analyze_campaign ar trage
  matplotlib la nivel de modul + cuplaj la un CLI. Cele 3 copii TREBUIE tinute identice.
  ASCII curat ambele, py_compile OK.
- Task 3: fisier nou test_mode_label.py (stil identic cu test_bench_core.py -- script simplu cu
  check()+contor, NU pytest-functii, fiindca asta e conventia existenta a suitei; ruleaza cu
  `python3 test_mode_label.py`). 5 verificari: mode_label('sil')/('hil'), input invalid -> ValueError,
  cele 3 copii IDENTICE (garda anti-divergenta), si --mode bogus respins de CLI (cod != 0).
  Toate 5 trec. ASCII curat. NU am adaugat teste peste scopul cerut.

## RAPORT FINAL
Toate 3 task-urile DONE. Branch: overnight-sil-hil-flag (FARA merge in main, FARA push). Commit-uri
separate per task + per progres, conform spec.

FISIERE SCHIMBATE:
- analyze_campaign.py: +mode_label(mode) (pur) + flag --mode {sil,hil}; cele 3 subtitluri hardcodate
  "SIL (loopback)" -> mode_label(mode). Logica de analiza (cifre/calcule/layout) NEATINSA.
- campaign_stats.py: +mode_label (duplicat identic) + --mode; plot_cdf/plot_p95_ci primesc param
  label; cele 2 captions -> label.
- sil_vs_hil_table.py: +mode_label (duplicat); format_table foloseste mode_label pentru coloane +
  linie de legenda. Fara --mode (compara prin natura SIL vs HIL).
- test_mode_label.py (NOU): 5 verificari.

VERIFICAT (rulat efectiv, rezultate):
- analyze_campaign --mode hil pe ~/c1_archive/hil_cyclonedds_20260627_1005 (READ-ONLY, --out scratch)
  -> subtitlu "HIL (two-machine)" (confirmat VIZUAL in PNG); --mode sil -> "SIL (loopback)".
- campaign_stats --demo --mode hil -> caption "HIL (two-machine)" (vizual); --selftest 17/17.
- sil_vs_hil_table --selftest 10/10; antet nou cu etichete complete.
- test_mode_label.py: 5/5. analyze_campaign --selftest OK.
- avertisment pe stderr cand --mode lipseste (ambele CLI). Arhivele ~/c1_archive NEATINSE.

DECIZII DE DESIGN:
- --mode default=None -> daca lipseste: avertisment stderr + presupun "sil" (NU eroare dura), ca sa
  nu rup apelantii existenti (HIL_RUNBOOK ruleaza analyze_campaign fara --mode).
- mode_label DUPLICAT in 3 fisiere (nu mutat in modul comun, nu importat din analyze_campaign care
  trage matplotlib la nivel de modul). test_mode_label prinde orice divergenta a copiilor.

DE VAZUT DE ALEXANDRU DIMINEATA:
- Daca preferi sursa UNICA pentru mode_label: muta-l intr-un mode_label.py comun + importa din toate
  3 (test_mode_label ramane valabil). Am ales duplicarea pt atingere minima, conform spec.
- Daca vrei ca --mode sa fie OBLIGATORIU (eroare, nu avertisment): o linie de schimbat in fiecare
  main(). Am ales avertisment ca sa nu rup apelantii existenti.
- HIL_RUNBOOK.md / HIL_TRANSPORT_CHEATSHEET.md cheama analyze_campaign FARA --mode -> vor da
  avertismentul si presupun sil. Pe date HIL adauga --mode hil (sau actualizeaza runbook-urile --
  NU le-am atins, nu era in scopul celor 3 task-uri).
