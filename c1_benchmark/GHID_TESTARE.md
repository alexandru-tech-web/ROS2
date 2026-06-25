# GHID_TESTARE -- C1 benchmark middleware (selector + campanie + figuri)

Ghid pas-cu-pas ca sa rulezi singur pipeline-ul C1 si sa vezi ce iese. Fiecare pas are:
**comanda** (copy-paste) -- **ce face** -- **ce astepti** (output real) -- **ce inseamna**.

Toate cifrele de mai jos sunt din rulari reale pe campania `fair_20260624_124558`
(SIL = loopback, o singura masina, N=10). HIL (doua masini + link real) ramane standardul
autoritar -- nimic de aici nu e etichetat HIL.

## Preconditii

- Pasii 1-8 (teste pure + selector + figuri) NU au nevoie de ROS pornit. Au nevoie doar de
  Python3 cu: `numpy pandas scikit-learn matplotlib` (pentru PDIA si figuri).
- Pasul 0 (build) si pasul 9 (smoke) au nevoie de ROS 2 Jazzy.
- Toti pasii pornesc din `~/ros2_ws/src/c1_benchmark` (sau cum e notat).

```bash
cd ~/ros2_ws/src/c1_benchmark
# variabila folosita mai jos: radacina transportului din ultima campanie
CAMP=$(ls -d ~/ros2_ws/new_data_sar/fair_* | tail -1)/c1_transport
echo "$CAMP"
```

## 0. Build (doar daca rulezi si noduri ROS; pt testele pure nu e nevoie)

```bash
cd ~/ros2_ws && colcon build && source install/setup.bash && cd src/c1_benchmark
```
- **Ce face:** compileaza workspace-ul; `c1_benchmark` ruleaza ca scripturi pure, nu prin colcon.
- **Ce astepti:** `Summary: 6 packages finished`. Stderr cu `pytest-repeat unbuilt egg` e cosmetic.
- **Ce inseamna:** mediu gata. Daca pici aici, vezi CLAUDE.md sectiunea 6 (gotchas).

## 1. Teste pure (fara ROS, fara date) -- valideaza nucleele

```bash
python3 test_selector_core.py | tail -1
python3 test_bench_core.py     | tail -1
python3 campaign_stats.py --selftest | tail -1
python3 reproduce_selector.py  --selftest | tail -1
python3 analyze_campaign.py    --selftest | tail -1
```
- **Ce face:** ruleaza nucleele pure (logica testabila izolat, fara ROS/IO).
- **Ce astepti:**
  ```
  TOATE TESTELE SELECTOR_CORE AU TRECUT: 30 verificari.
  TOATE TESTELE C1 AU TRECUT: 12 verificari.
  [selftest] 17 verificari trecute, toate OK
  OK selftest (nucleu pur).
  [ok] autotest: fluxul complet a produs rezumatul si figurile
  ```
- **Ce inseamna:** algoritmii (features, regret, LOCO, percentile/bootstrap/KS) sunt corecti.
  `analyze_campaign --selftest` fabrica un arbore sintetic si produce figuri in `selftest_out/`.

## 2. Bridge: campania reala -> dataset-ul selectorului

```bash
python3 build_selector_dataset.py "$CAMP" -o selector_dataset.csv
```
- **Ce face:** reconstruieste `selector_dataset.csv` din JSON-urile campaniei reale (loss MASURAT).
- **Ce astepti:**
  ```
  Scris 478 randuri in selector_dataset.csv
    rmw=['cyclonedds', 'zenoh']  cond=[8 conditii]  payload=[64, 4096, 65536]  reps=10
    randuri cu loss_pct>0 (semnal de pierdere REAL, vs orfanul cu 0): 333/478
    SARITE 2 rulari fara p95_ms (pierdere ~totala, nimic de masurat)
  ```
- **Ce inseamna:** repara veriga rupta (vechiul `ml_dataset.csv` avea loss=0 peste tot).
  `selector_dataset.csv` e gitignorat (regenerabil). Cele 2 rulari sarite = pierdere totala,
  nu se inventeaza un RTT pentru ele.

## 3. Selector -- obiectiv CONTROL (orb la pierdere = min RTT p95)

```bash
python3 reproduce_selector.py selector_dataset.csv
```
- **Ce face:** construieste 24 de celule (8 cond x 3 payload), alege RMW-ul cu RTT p95 minim,
  evalueaza selectoare invatate cu validare leave-one-condition-out (LOCO) si REGRET.
- **Ce astepti (extras):**
  ```
  TOTAL 24 celule -> {'cyclonedds': 17, 'zenoh': 7}
  always-cyclonedds  regret mediu= 142.1 ms
  always-zenoh       regret mediu=1142.8 ms
  selector 1-NN      regret mediu/celula : 557.7 ms
  selector arbore    regret mediu/celula : 652.7 ms
  ```
- **Ce inseamna:** pe acest obiectiv, regula triviala **always-CycloneDDS domina** (regret mic);
  selectorul invatat NU o bate. Validarea e LOCO (nu split aleator) ca sa nu scurga info intre
  repetitii. Figura: `selector_regret.png/.pdf` (gitignorate).

## 4. Selector -- obiectiv CONSTIENT DE PIERDERE + sensibilitate la deadline D

```bash
python3 reproduce_selector.py selector_dataset.csv --objective lossaware --penalty 1000
python3 reproduce_selector.py selector_dataset.csv --objective lossaware --penalty 5000
```
- **Ce face:** cost = (1-loss)*RTT_p95 + loss*D, unde D = costul unui esantion pierdut (deadline).
  Reruleaza LOCO+regret si afiseaza sensibilitatea la D.
- **Ce astepti (blocul de sensibilitate):**
  ```
  D=   200 ms -> always-cyc=  79.8  selector1NN= 207.6
  D=  1000 ms -> always-cyc=  90.0  selector1NN= 197.5
  D=  5000 ms -> always-cyc= 188.0  selector1NN= 104.0
  ```
- **Ce inseamna:** concluzie DEPENDENTA DE DEADLINE. La D mic/moderat always-CycloneDDS ramane
  cea mai buna; la **D=5000 ms selectorul invatat (104) BATE always-CycloneDDS (188)** -- un
  selector isi merita locul doar in regimul unde un pachet pierdut e foarte scump.

## 4b. Selector -- obiectiv TELEMETRIE (groundwork; cere o campanie cu strat mission)

```bash
# demo pe date sintetice (fara ROS): analyze_campaign --selftest scrie un campaign_summary.csv
python3 analyze_campaign.py --selftest >/dev/null
python3 reproduce_selector_mission.py selftest_out/campaign_summary.csv
```
- **Ce face:** alege RMW-ul cu **timpul de misiune minim** per conditie (obiectiv telemetrie),
  din `campaign_summary.csv` (coloana `mission_time_s`), cu acelasi cadru LOCO + regret.
- **Ce astepti (sintetic):** tabel castigatori per conditie; pe datele sintetice Zenoh castiga
  prin constructie -> selector 100% / regret 0 (trivial). Pe date reale va diferi.
- **Cum obtii date REALE de misiune** (campania doar-transport NU le are):
  ```bash
  cd ~/ros2_ws && colcon build && source install/setup.bash && sudo -v
  python3 src/c1_benchmark/run_campaign.py --reps 5 --layers transport mission
  python3 src/c1_benchmark/analyze_campaign.py <results_c1/>     # -> campaign_summary.csv
  python3 src/c1_benchmark/reproduce_selector_mission.py <results_c1/analysis/campaign_summary.csv>
  ```
- **Ce inseamna:** misiunea e payload-agnostica (o celula/conditie); timpii cenzurati (misiune
  neterminata) sunt raportati si sariti. Acelasi cod ingera date SIL sau HIL fara modificari.

## 5. Figurile campaniei (transport / misiune / CDF)

```bash
# pe date sintetice (autotest), rapid:
python3 analyze_campaign.py --selftest        # -> selftest_out/fig_transport|mission|cdf .png/.pdf
# sau pe o campanie reala cu arborele results_c1/:
# python3 analyze_campaign.py <results_c1/>
```
- **Ce astepti:** `[ok] rezumat + figuri in .../selftest_out`.
- **Ce inseamna:** Fig.2 (transport RTT p95 + pierdere ca etichete), Fig.3 (timp misiune, hasurat
  = plafon), Fig.4 (CDF). Etichete academice, caption SIL, `.png`+`.pdf`.

## 6. Figurile de analiza pe date REALE

```bash
python3 analysis/box_c1.py        "$CAMP" 4096
python3 analysis/payload_c1.py    "$CAMP" loss_30
python3 analysis/strip_c1.py      "$CAMP"
python3 analysis/variability_c1.py "$CAMP"
python3 analysis/cdf_c1.py        "$CAMP" loss_30 4096
```
- **Ce astepti:** cate un `[ok] .../analysis/fig_*.{png,pdf}` per script.
- **Ce inseamna:** povestea C1 vizual: CycloneDDS strans/predictibil, Zenoh coada grea/imprastiat.
  Figurile aterizeaza in `$CAMP/analysis/` (sub `new_data_sar/`, in afara git).

## 7. Statistica riguroasa (CI bootstrap + test KS)

```bash
python3 campaign_stats.py --demo --out /tmp/stats_out      # date sintetice
# sau pe campanie reala:
# python3 campaign_stats.py "$CAMP" --glob 'transport_p4096.csv' --out /tmp/stats_out
```
- **Ce astepti:** `stats_summary.csv`, `stats_compare.csv`, `fig_cdf_band_*.png/.pdf`, `fig_p95_ci.png/.pdf`.
- **Ce inseamna:** intervale de incredere pe p95 (bare de eroare) + KS (distributiile difera?).
  Raspunde la ce cere un recenzent peste o singura rulare.

## 8. PDIA -- caracterizatorul ML (prezice RTT din severitate + payload)

```bash
python3 reproduce_pdia.py
```
- **Ce astepti:** `R2 TEST = 0.904`, `Acuratete TEST = 0.944`; figuri regenerate in
  `Analiza_ML_18.06.2026/` (figA/figB/figC `.png`+`.pdf`, urmarite in git).
- **Ce inseamna:** modelul descriptiv (latenta creste cu severitatea). NU alege RMW-ul (asta e
  selectorul, pasii 3-4). Foloseste `ml_dataset.csv` (set fara semnal de pierdere -- vezi nota).

## 9. Verificare repo (nivel 0, fara ROS pornit)

```bash
cd ~/ros2_ws/src
bash check_repo.sh | grep REZULTAT     # -> REZULTAT: 36 trecute, 0 esuate
bash smoke_all.sh  | grep 'pasi:'      # -> pasi: 11 ok, 0 fail
```
- **Ce inseamna:** compilare Python, dependinte, teste pure si SIL pe toate pachetele -- verde.

## Unde aterizeaza fisierele (igiena git)

| Artefact | Locatie | In git? |
|----------|---------|---------|
| `selector_dataset.csv`, `selector_regret.png/.pdf` | `c1_benchmark/` | NU (gitignorate, regenerabile) |
| figuri campanie/analiza | `<campanie>/analysis/`, `selftest_out/`, `/tmp/stats_out` | NU |
| figuri PDIA `figA/B/C` + predictii | `c1_benchmark/Analiza_ML_18.06.2026/` | DA (figurile articolului) |
| date brute de campanie | `~/ros2_ws/new_data_sar/` (in afara `src`) | NU |

## Note oneste

- **SIL = loopback pe o masina.** Toate cifrele de aici sunt SIL. Comparatia autoritara cere HIL
  (doua masini + link real). Schema dataset-ului e identica SIL/HIL -> selectorul va ingera datele
  HIL fara modificari de cod (vezi BLOC C in TASK_SIL_HIL.md).
- **`ml_dataset.csv` (PDIA) este orfan:** loss_pct=0 si sent==recv peste tot, fara timp de misiune.
  Caracterizatorul PDIA il foloseste ca atare; selectorul NU -- el ruleaza pe `selector_dataset.csv`
  reconstruit din campania reala (pasul 2).
- Provizoriu: N=10, loopback. De inlocuit cu N mai mare / HIL inainte de orice submisie.
