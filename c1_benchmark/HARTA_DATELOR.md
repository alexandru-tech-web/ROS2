# Harta datelor C1 -- inventar complet (generat READ-ONLY, nimic modificat)

Data generarii: 2026-07-01. NIMIC nu a fost sters/mutat/modificat. Plasa de siguranta
(Trash, copii) e intacta. Clasificare SIL/HIL facuta din RTT mean la ideal (cyclonedds,
p4096): SIL loopback ~1.2 ms; HIL switch/cablu ~3.8 ms; HIL Wi-Fi ~11-13 ms.

## Rezumat executiv

- ~20 locatii cu date de campanie C1 (transport), plus 3 locatii de date de MISIUNE
  (strat diferit), plus ~3.5 GB in Trash (NEgolit).
- SIL: cel putin 6 campanii (c1_data/*, backup_2026-06-19, + 2 in Trash cu N=10).
- HIL: Wi-Fi (CAMPANII + 3-4 copii zenoh + cyclonedds verificat), switch (cyclonedds x2 +
  zenoh incomplet), plus early cyclonedds.
- Zero foldere cu permission-denied (toate citibile).
- REZOLVAT: loss-ul de 58% la ideal p65536 pentru Zenoh Wi-Fi e REAL (banda Wi-Fi), NU
  bug -- se reproduce IDENTIC in 4 rulari (CAMPANII + hil_zenoh_wifi_2056/2058/2059).

CANONIC (recomandare, sursa cea mai buna per sfert):
- SIL: c1_data/01_crossover_20250619 (N=5, 8 conditii, valid). DAR in Trash exista
  new_data_sar/fair_20260624_124558 (N=10, 8 conditii, valid) -- MAI BUN (N=10). De RECUPERAT.
- HIL Wi-Fi: c1_archive/hil_cyclonedds_wifi_verificat_20260701_2059 (cdds) +
  hil_zenoh_wifi_20260701_2059 (zenoh). CAMPANII/ e o copie de lucru a aceleiasi date.
- HIL switch: hil_cyclonedds_switch_20260629_0941 (cdds) + hil_zenoh_switch_20260629_0941
  (zenoh, DAR doar 6/8 conditii -- INCOMPLET).

## Tabel principal (locatii cu date de TRANSPORT C1)

| locatie | data | tip | RMW | cond | N | zenoh loss@ideal 64/4096/65536 | validitate | note |
|---------|------|-----|-----|------|---|-------------------------------|-----------|------|
| ros2_ws/src/c1_benchmark/CAMPANII | Jul1 | HIL Wi-Fi | ambele | 8 | 5 | 0/0/0.578 | VALID | data de lucru curenta; 58%=banda reala |
| ros2_ws/src/c1_benchmark/c1_data/01_crossover_20250619 | ~Jun | SIL | ambele | 8 | 5 | 0/0/0 | VALID | sweep SIL canonic |
| ros2_ws/src/c1_benchmark/c1_data/02_burst_20250619 | ~Jun | SIL | ambele | 6 (fara ideal) | 5 | - | valid | studiu burst (loss_20/25/30 + _burst) |
| ros2_ws/src/c1_benchmark/c1_data/03_var_n10_20250619 | ~Jun | SIL | ambele | 3 (fara ideal) | 10 | - | valid | varianta N=10 (loss_20/25/30) |
| ros2_ws/src/c1_benchmark/c1_data/_arhiva_veche/* | <16.06 | SIL vechi | mixt | 6 | 2-5 | 0/0/0 unde e | valid-vechi | multe campanii vechi imbricate (vezi mai jos) |
| backup_2026-06-19 | Jun19 | SIL | ambele | 8 | 5 | 0/0/0 | VALID | backup SIL (posibil duplicat crossover) |
| c1_archive/hil_cyclonedds_20260627_1005 | Jun27 | HIL (early) | cdds | 8 | 5 | (fara zenoh) | valid | cdds nu are router |
| c1_archive/hil_cyclonedds_20260627_1007 | Jun27 | HIL (early) | cdds | 8 | 5 | (fara zenoh) | valid | |
| c1_archive/hil_cyclonedds_switch_20260629_0823 | Jun29 | HIL switch | cdds | 8 | 5 | (fara zenoh) | valid | |
| c1_archive/hil_cyclonedds_switch_20260629_0941 | Jun29 | HIL switch | cdds | 8 | 5 | (fara zenoh) | valid | canonic switch cdds |
| c1_archive/hil_cyclonedds_wifi_20260629_1618 | Jun29 | HIL Wi-Fi | cdds | 8 | 5 | (fara zenoh) | valid | |
| c1_archive/hil_cyclonedds_wifi_verificat_20260701_2059 | Jul1 | HIL Wi-Fi | cdds | 8 | 5 | (fara zenoh) | VALID | 'verificat' -> canonic Wi-Fi cdds |
| c1_archive/hil_zenoh_switch_20260629_0941 | Jun29 | HIL switch | zenoh | 6 | 5 | 0/0/0 | valid dar INCOMPLET (6/8 cond) |
| c1_archive/hil_zenoh_wifi_20260701_2056 | Jul1 | HIL Wi-Fi | zenoh | 8 | 5 | 0/0/0.578 | VALID | copie 1/3 (identice) |
| c1_archive/hil_zenoh_wifi_20260701_2058 | Jul1 | HIL Wi-Fi | zenoh | 8 | 5 | 0/0/0.578 | VALID | copie 2/3 |
| c1_archive/hil_zenoh_wifi_20260701_2059 | Jul1 | HIL Wi-Fi | zenoh | 8 | 5 | 0/0/0.578 | VALID | copie 3/3 -> canonic Wi-Fi zenoh |
| c1_archive/mixed_backup_0856 | Jun27 | mixt | ambele | 2 | 5 | - | partial | backup mic |
| .local/share/Trash/.../new_data_sar/fair_20260624_124558 | Jun24 | SIL | ambele | 8 | 10 | 0/0/0 | VALID (in TRASH) | N=10 complet -- RECUPERABIL, valoros |
| .local/share/Trash/.../new_data_sar/run_20260623_073047 | Jun23 | SIL | ambele | 11 | 10 | 0/0/0 | VALID (in TRASH) | 11 conditii N=10 -- RECUPERABIL |
| .local/share/Trash/.../new_data_sar/fair_20260624_090315 | Jun24 | SIL | ambele | 8 | 1 | 0/0/0 | N=1 (in Trash) | provizoriu |
| .local/share/Trash/.../new_data_sar/run_20260623_071559 | Jun23 | SIL | ambele | 2 | 1 | 0/0/0 | N=1 (in Trash) | partial |

## Date recente cheie (munca recenta)

- CAMPANII/zenoh + CAMPANII/cyclonedds: HIL Wi-Fi, 8 cond, N=5, VALID. Zenoh 58% loss la
  ideal p65536 = banda Wi-Fi reala (Zenoh nu are back-pressure; CycloneDDS incetineste
  emitatorul si nu pierde). Confirmat de 3 re-rulari arhivate cu aceeasi cifra.
- c1_archive/hil_*_wifi_*_20260701_* : setul Wi-Fi verificat din Jul 1 (cdds 'verificat'
  + zenoh x3). Acesta e cel mai curat set HIL Wi-Fi.

## Date SIL

- c1_data/01_crossover_20250619: sweep complet 8 cond, N=5, CURAT (0% ideal). Sursa SIL principala.
- c1_data/02_burst_20250619: loss_20/25/30 + variante _burst (verifica parametrii pt a confirma
  Gilbert-Elliott vs burst simplu -- AMBIGUU din nume, de clarificat).
- c1_data/03_var_n10_20250619: loss_20/25/30, N=10 (studiu de varianta).
- backup_2026-06-19: SIL 8 cond N=5, curat (posibil acelasi lucru ca crossover -- de confirmat).
- IN TRASH: new_data_sar/fair_20260624_124558 (SIL N=10 complet!) si run_20260623_073047
  (SIL 11 cond N=10) -- MAI BUNE decat crossover (N=10 > N=5). Aruncate; RECUPERABILE.

## Date de MISIUNE (strat diferit, NU transport C1 -- pentru context)

- sil_campaign/ (Jun15): campanie SIL de MISIUNE (baseline_drone_d*.csv, mission metrics,
  drone_isolation, partition). 0 summary de transport. E stratul mission, nu benchmark-ul transport.
- mission_results_2 (20 mission_metrics), mission_results_severe (12): experimente de misiune.

## Ce e in Trash (recuperabil, NU golit -- ~3.5 GB total)

- new_data_sar/ (34 MB): contine campanii SIL VALIDE, inclusiv 2 cu N=10 (vezi mai sus).
  RECOMAND recuperare inainte de golire -- N=10 e mai valoros ca N=5.
- Restul (~3.4 GB): scripturi vechi (analyze_campaign.*.py versiuni), articole (.docx/.tex),
  imagini (bench_preview*.png), analize (analysis_hil_switch, analysis_hil_wifi). De trecut
  in revista inainte de golire; unele pot fi doar versiuni vechi (gunoi real), altele nu.

## Duplicate identificate

- Zenoh HIL Wi-Fi (loss 0/0/0.578): 4 copii aproape identice -- CAMPANII/zenoh +
  hil_zenoh_wifi_2056 + 2058 + 2059. Pastreaza una (2059, cea mai recenta); restul sunt copii.
- SIL crossover: c1_data/01_crossover vs backup_2026-06-19 (ambele SIL N=5 8-cond) -- probabil
  acelasi. De confirmat prin comparare de cifre.
- c1_data/_arhiva_veche: imbricari duplicate -- 2026-06-12_c1_N5 contine si o copie interna
  c1_results_full; mai multe 'Rezultate vechi <data'. Arhiva istorica, multe duplicate.
- Cdds Wi-Fi: hil_cyclonedds_wifi_1618 vs hil_cyclonedds_wifi_verificat_2059 -- posibil re-rulare.

## Foldere cu permission denied (de verificat manual)

- NICIUNUL. Toate locatiile scanate au fost citibile de user (nimic root).

## Ce NU e date de campanie (excluse din inventar)

- install/, log/build_*/, zenoh-python/ = instalarea/build-ul ROS + sursa Zenoh, nu date.
- Analiza_ML_18.06.2026/ (acum in CAMPANII/): iesiri de analiza ML/PDIA (figA/B/C, predictii_*.csv),
  NU date brute SIL. Confirmat: e PDIA, cum ai spus.
- results_c1/ : NU mai exista (mutat in CAMPANII). Confirmat.

## RECOMANDARI (doar sugestii -- UTILIZATORUL decide si executa; eu NU sterg/mut nimic)

1. RECUPEREAZA din Trash campaniile SIL N=10 (new_data_sar/fair_124558, run_073047) inainte de
   orice golire -- sunt cele mai bune date SIL (N=10 complet).
2. Structura canonica propusa (de reorganizat manual, cu README per folder):
   c1_data/SIL/ (crossover N=5 + N=10 recuperate) ; c1_data/HIL_WIFI/ (setul verificat Jul1) ;
   c1_data/HIL_SWITCH/ (cdds + zenoh; zenoh switch e INCOMPLET 6/8 -- de completat 2 conditii).
3. Duplicatele hil_zenoh_wifi_2056/2058 pot fi arhivate/sterse (pastreaza 2059). TU decizi.
4. c1_data/ (154 MB) e in arborele repo-ului (~/ros2_ws/src/c1_benchmark/). Datele brute NU
   ar trebui in git (CLAUDE.md sec.5) -- ia in calcul mutarea in afara repo-ului sau .gitignore.
5. Trash 3.5 GB -- trece in revista inainte de golire (contine date SIL N=10 recuperabile + articole).
6. De clarificat: 02_burst = Gilbert-Elliott sau burst simplu (verifica parametrii netem in log/nume).

NIMIC nu a fost modificat. Utilizatorul decide si executa curatenia dupa ce vede aceasta harta.
