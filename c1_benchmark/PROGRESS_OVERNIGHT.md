# Progres overnight SIL/HIL flag
Task 1 (analyze_campaign --mode + subtitlu): DONE
Task 2 (propagare --mode in campaign_stats + sil_vs_hil_table): TODO
Task 3 (teste pentru logica de mod): TODO
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
