# Progres matrice 2x2
(branch overnight-matrix-2x2, construit peste overnight-sil-hil-flag, deja merge-uit in main)
Task 1 (extindere etichetare mediu+middleware): DONE
Task 2 (comparatie 4-way / structura tabel matrice): DONE
Task 3 (runbook-uri pentru ambele interfete): DONE
Task 4 (teste): DONE
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
- Task 2: fisier NOU matrix_table.py (mai curat decat sa contorsionez sil_vs_hil_table; reutilizeaza
  env_label + summarize_reps din sil_vs_hil_table, importabil fara matplotlib -- text-only, fara figuri).
  * matrix_summarize(groups): {(env,mw): [p95_per_rep]} -> {(env,mw): summary}; cheile fara date raman
    absente -> 'nerulat' in tabel.
  * format_matrix: tabel 2x2 (mediu x middleware) + comparatie VALIDA doar INTRA-mediu (cyclonedds vs
    zenoh pe acelasi transport) + axa secundara 'efectul transportului fizic' (acelasi mw, intre medii,
    etichetata clar ca NEcomparatie de validitate) + NOTA METODOLOGICA de non-comparabilitate intre medii.
  * Sferturi lipsa -> 'nerulat' (NU valori inventate). Date de test = SINTETICE etichetate
    'synthetic_for_test'; NU rulat pe ~/c1_archive.
  * --selftest 9/9 (aliniere, nerulat, nota non-comparabilitate, comparatie valida intra-mediu,
    indisponibila unde lipseste un mw, axa secundara). ASCII curat, py_compile OK.
  DECIZIE: statusul de SETUP (validat-setup vs de-rulat) NU e codat in tabelul de DATE -- tabelul arata
  fie valoarea (mean p95 / N) fie 'nerulat'. Statusul de setup ramane in runbook-uri / context (Task 3).
  Adnotari de status per celula = extensie ulterioara (am ales sa nu incarc/inventez).
- Task 3: editari chirurgicale in HIL_RUNBOOK.md + HIL_TRANSPORT_CHEATSHEET.md:
  * iface ca parametru EXPLICIT: enp2s0 (switch Gigabit -> mediu hil_switch) / wlp4s0 (Wi-Fi ->
    mediu hil_wifi).
  * apelurile analyze_campaign -> --mode hil_switch (cu nota: hil_wifi pe Wi-Fi); NU "hil", NU sil.
  * nota de ASIMETRIE discovery: CycloneDDS multicast/fara router; Zenoh router pe FIECARE masina +
    connect block -> trimite la HIL_ZENOH_SETUP.md.
  HIL_ZENOH_SETUP.md LIPSESTE in repo -> NU l-am recreat din memorie (per spec); runbook-urile trimit
  la el; Alexandru il are separat.
  INCONSISTENTA SEMNALATA (de reconciliat de Alexandru via HIL_ZENOH_SETUP.md): ghidajul Zenoh era
  contradictoriu in repo -- HIL_RUNBOOK vechi "un router pe M1 accesibil ambelor", cheatsheet "P2P fara
  router", contextul matricei (dat de spec) "router pe fiecare masina + connect". Am aliniat la
  finding-ul DAT (router per masina), am marcat indicatia "P2P" ca SUPERSEDED si am trimis la
  HIL_ZENOH_SETUP.md. NU am rescris procedura Zenoh (nu o recreez din memorie).
  Verificat: ASCII curat ambele; coerenta enp2s0/wlp4s0 + hil_switch/hil_wifi + HIL_ZENOH_SETUP in ambele.
- Task 4: extins test_mode_label.py pentru env_label (cele 3 medii sil/hil_wifi/hil_switch -> etichete
  corecte, input invalid -> ValueError, cele 3 COPII identice -- garda anti-divergenta pentru AMBELE
  functii). Plus 2 teste de CLI --mode pe campaign_stats (matplotlib-robust): valoare necunoscuta
  respinsa + "hil" generic -> eroare blanda (ambiguu). Adaugat STUB matplotlib in test (shim: matplotlib
  lipseste in mediu, analyze_campaign il importa eager -> stub doar ca sa pot importa modulele pentru
  testarea functiilor pure). test_mode_label: 11/11.
  Logica de aliniere a matricei (Task 2) e testata de matrix_table --selftest (9/9), convetie built-in
  ca campaign_stats/sil_vs_hil_table. Stil: script cu check()+contor (ca suita existenta), NU pytest.
  NU am adaugat teste peste scop.

## RAPORT FINAL
Toate 4 task-urile DONE. Branch: overnight-matrix-2x2 (peste main, care avea deja flag-ul SIL/HIL).
FARA merge in main, FARA push. Commit-uri separate per task + per progres.

FISIERE SCHIMBATE:
- analyze_campaign.py: +ENV_LABELS + env_label (sil/hil_wifi/hil_switch); analyze() foloseste env_label;
  --mode extins {sil,hil_wifi,hil_switch,hil}, "hil" -> EROARE blanda. mode_label PASTRAT.
- campaign_stats.py: idem (env_label DUPLICAT identic + --mode extins; plot_*_ci primesc label).
- sil_vs_hil_table.py: +env_label (DUPLICAT identic).
- matrix_table.py (NOU): tabel matrice 2x2 + paritate VALIDA doar intra-mediu + 'nerulat' pt sferturi
  lipsa + axa secundara 'efectul transportului fizic' + nota de non-comparabilitate. --selftest 9/9.
- HIL_RUNBOOK.md + HIL_TRANSPORT_CHEATSHEET.md: iface parametric (enp2s0 switch / wlp4s0 Wi-Fi) +
  analyze_campaign --mode hil_switch/hil_wifi + nota asimetrie discovery -> HIL_ZENOH_SETUP.md.
- test_mode_label.py: +teste env_label (3 medii + invalid + 3 copii identice) + 2 teste --mode CLI +
  stub matplotlib. 11/11.

VERIFICAT (rulat efectiv):
- test_mode_label 11/11, matrix_table 9/9, campaign_stats 17/17, sil_vs_hil_table 10/10.
- FARA regresie: test_bench_core 13/13, test_selector_core 37/37.
- env_label IDENTIC in 3 copii + ValueError; mode_label compat; "hil" -> eroare blanda exit 2
  (verificat pe campaign_stats). Tabelul matrice marcheaza nerulat + non-comparabilitate (selftest).
- ASCII curat in toate fisierele atinse.

DECIZII DE DESIGN:
- "hil" generic pe --mode -> EROARE blanda care cere hil_wifi/hil_switch (NU avertisment): pe matrice
  ambiguitatea wifi/switch conteaza (per spec).
- env_label DUPLICAT in 3 fisiere (ca mode_label); test_mode_label prinde divergenta pt AMBELE functii.
- matrix_table fisier NOU (mai curat decat sa contorsionez sil_vs_hil_table); reutilizeaza
  env_label + summarize_reps. Status de setup NU codat in tabelul de date (doar valoare sau 'nerulat').

CE TREBUIE SA VADA ALEXANDRU:
1. APELANTI SPARTI: orice apel "analyze_campaign/campaign_stats --mode hil" da acum EROARE (exit 2).
   Runbook-urile le-am actualizat la hil_switch/hil_wifi (Task 3). Verifica daca mai ai
   scripturi/aliasuri/cron care dau "--mode hil" -- de schimbat la hil_wifi sau hil_switch.
2. matplotlib LIPSESTE in mediul de overnight -> analyze_campaign (import matplotlib EAGER, liniile
   27-29) NU ruleaza ca CLI aici; campaign_stats (import lenes) ruleaza. Optiuni: instaleaza matplotlib,
   SAU fa importul lenes in analyze_campaign (ca campaign_stats). Eu NU am facut pip install si NU am
   refactorizat (ambele = peste scop/risc). Am verificat analyze_campaign prin cod-identitate cu
   campaign_stats + import cu stub.
3. HIL_ZENOH_SETUP.md LIPSESTE in repo -- runbook-urile trimit la el; il ai separat. Ghidajul Zenoh era
   CONTRADICTORIU in repo (P2P fara router vs router pe M1 vs router per masina). Am aliniat la
   finding-ul DAT (router per masina + connect) si am marcat "P2P fara router" ca SUPERSEDED. Reconciliaza
   procedura completa in HIL_ZENOH_SETUP.md (NU am recreat-o din memorie).
4. matrix_table consuma {(env, middleware): [p95_per_rep]}. Cand ai date HIL reale, mai trebuie un mic
   LOADER care eticheteaza datele pe (env, mw) (sau extinde sil_vs_hil_table.load_rep_p95). Acum doar
   STRUCTURA, validata pe date sintetice (per spec: nu am rulat pe ~/c1_archive).
