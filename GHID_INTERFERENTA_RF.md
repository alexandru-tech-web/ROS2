# Ghid: pluginul de interferenta RF + HMI de teste + C4 (stability margin)

Acest ghid documenteaza ce s-a construit in faza autonoma de constructie (vezi
`~/ros2_ws/OVERNIGHT_LOG.md` pentru hash-urile exacte ale celor ~30 de commit-uri) si da
comenzi pe care le poti rula TU ca sa verifici codul si sa vezi ce se intampla. Tot ce e
marcat [TESTAT] a fost rulat si a trecut in mediul curent (SIL / fara fier). Ce are nevoie de
ROS pornit sau de un ecran (GUI) e marcat ca atare -- nu pretind ca am rulat acele bucati headless.

Limbaj: cod si fisiere .md/.tex = ASCII (vezi CLAUDE.md sectiunea 3). Onestitate SIL vs HIL:
cifrele de mai jos sunt din loopback / modele sintetice; trebuie inlocuite cu HIL pe doua masini
inainte de orice submisie (vezi sectiunea 8).

## 1. Ce este si de ce

Profesorul a cerut un experiment "cu interferente". Plugin-ul modeleaza interferenta RF la doua
niveluri ortogonale, ambele deterministe (seed) si PURE (fara ROS/I/O), in
`sar_plugins/rf_interference.py`:

- **Pierdere CORELATA in rafale (Gilbert-Elliott)** -- lant Markov cu 2 stari GOOD/BAD. Pierderea
  nu mai e independenta (Bernoulli), ci vine in rafale, ca la bruiaj real. Are PARITATE DE MODEL cu
  `tc netem ... loss gemodel`, deci ACELASI model (aceiasi parametri si statistici) ruleaza in SIL
  (Python) si pe fier (netem). Asta inchide gap-ul metodologic: burst-ul vechi `loss p% r%` era un
  model mai sarac decat Gilbert complet.
- **Degradare CO-CANAL (SINR)** -- cand mai multi emitatori folosesc aceeasi banda, SINR scade.
  Functie pura `cochannel_sinr(...)`; integrarea in lant e Faza 2 (dupa A1).

Lantul complet: nucleu pur -> hook in canalul SIL (sar_swarm/mesh/teleop) -> conditii `gilbert_*`
in campanie -> feature de burstiness in selector -> escaladare in link_adaptive -> noduri ROS
(publisher + punte SIL->HIL) -> HMI de teste x3.

## 2. Verificare rapida (toate nucleele) [TESTAT]

Ruleaza din `~/ros2_ws/src`. Fiecare e un nucleu pur cu `_selftest()`, fara ROS:

```bash
cd ~/ros2_ws/src
python3 sar_plugins/rf_interference.py            # nucleul interferentei
python3 sar_plugins/test_rf_interference.py       # 14 verificari
python3 sar_swarm/test_burst_channel.py           # burst vs memoryless la aceeasi medie
python3 c1_benchmark/test_bench_core.py           # 13 (incl. gemodel in campanie)
python3 c1_benchmark/test_selector_core.py        # 37 (incl. feature burstiness)
python3 link_adaptive/link_adaptive/link_adaptive_core.py   # 26 + tabel demo
python3 joint_emulator/test_joint_core.py         # 38 (incl. stability margin + ESTOP)
python3 sar_plugins/campaign_hmi_core.py          # nucleu HMI panou campanie
python3 sar_plugins/post_run_core.py              # nucleu HMI post-rulare
python3 sar_swarm/rf_status_core.py               # nucleu bara RF dashboard
```

Sau, integrat in suita repo-ului:

```bash
cd ~/ros2_ws/src && bash smoke_all.sh             # sar_plugins/sar_swarm/c1_benchmark/teleop PASS
```

## 3. Nucleul rf_interference (detaliu)

`BurstProcess(p, r, loss_bad=1.0, loss_good=0.0, seed=0)`:
- `p = P(GOOD->BAD)`, `r = P(BAD->GOOD)`; pierdere conditionata de stare.
- `steady_loss = (r*loss_good + p*loss_bad)/(p+r)` -- pierderea medie stationara.
- `mean_burst_len = 1/r` -- durata medie a rafalei.
- `draw()` -> True daca pachetul e pierdut (avanseaza lantul un pas).
- `to_netem_gemodel()` -> `"loss gemodel p% r% loss_bad% loss_good%"` (paritate SIL<->HIL).
- `BurstProcess.from_steady(steady_loss, mean_burst_len)` -- construieste un Gilbert simplu dintr-o
  pierdere medie tinta si o lungime de rafala (folosit de `conditions_gilbert`).

`cochannel_sinr(rx_dbm, interferers_dbm, noise_dbm=-95.0)` -> `(sinr_db, interference_db)`, unde
`interference_db = 10log10((N+I)/N)` (cat a scazut SINR fata de cazul fara interferenta).

`linkstate_to_netem(ls, iface)` -- logica PURA a puntii SIL->HIL: dintr-un dict `/sar/linkstate`
construieste comanda `tc netem` (gemodel daca p,r prezenti, altfel memoryless). E nucleul testat al
lui `netem_bridge_node`.

## 4. SIL: burst vs memoryless [TESTAT]

`sar_swarm/test_burst_channel.py` demonstreaza diferenta la ACEEASI pierdere medie (0.3):

```
la aceeasi medie 0.3, outage burst=7.96 > memoryless=1.43 (5.6x)
```

Adica: cu aceeasi pierdere medie, rafalele produc perioade de intrerupere ~5.6x mai lungi decat
modelul independent. ASTA conteaza pentru teleoperare (o rafala lunga inseamna pierderea controlului
temporar). Raportarea e DIRECTIONALA si onesta (delta masurat), nu un prag inventat.

Conditiile `gilbert_20/25/30` exista acum in `c1_benchmark/bench_core.py` (CONDITIONS) cu aceeasi
pierdere medie ca `loss_20/25/30`, dar rafale parametrizate -- ca sa poti compara cap la cap burst
vs memoryless intr-o campanie. NOTA: parametrii sunt dintr-un SWEEP SINTETIC (nu calibrati pe un
trace radio real); calibrarea reala e pas HIL/viitor.

## 5. Noduri ROS (necesita ROS pornit)

Doua noduri subtiri peste nucleul testat (in `sar_plugins/nodes/`):

```bash
# Terminal cu ROS 2 Jazzy + source install/setup.bash
# Publisher: stare RF variabila in timp pe /sar/linkstate (Gilbert-Elliott)
python3 ~/ros2_ws/src/sar_plugins/nodes/rf_channel_node.py --ros-args \
  -p p:=0.0857 -p r:=0.2 -p rate_hz:=5.0

# Punte SIL->HIL: asculta /sar/linkstate si construieste comanda tc netem.
# DRY-RUN implicit (doar logheaza comanda, NU o executa). Pe a doua masina (HIL):
python3 ~/ros2_ws/src/sar_plugins/nodes/netem_bridge_node.py --ros-args \
  -p iface:=eth0 -p enable:=false        # enable:=true executa cu sudo pe fier
```

Schema `/sar/linkstate` e extinsa ADITIV cu `{loss, burst_len, instant_drop, p, r}`; subscriberii
vechi ignora cheile noi (nu se rupe contractul). py_compile pe ambele noduri = OK.

## 6. HMI de teste x3

### a) Vizualizator post-rulare (offline, fara ROS) [nucleu TESTAT]
```bash
cd ~/ros2_ws/src
python3 sar_plugins/post_run_viewer.py --root <DIR_CAMPANIE> --out /tmp/post_run.png
```
`<DIR_CAMPANIE>` = un director cu `transport_p*.csv` (din `run_campaign.py`). Produce
`post_run_summary.csv` + o figura in stil C1, separand conditiile `gilbert_*` de `loss_*`. Nucleul
(`post_run_core.py`) e testat; figura insasi cere date de campanie reale.

### b) Dashboard operator + banc de defecte (necesita ROS + ecran)
`sar_swarm/dashboard_node.py` arata acum starea RF (`loss/burst_len/interf_db`, nivel ok/warn/crit
via `rf_status_core`) plus modul `link_adaptive`. `fault_panel.py` are campuri noi `rafala` (burst_len)
si `interf [dB]` pe randul global -- poti injecta interferenta, nu doar latenta/jitter/pierdere.

### c) Panou de campanie unificat (necesita ecran)
```bash
cd ~/ros2_ws/src && python3 sar_plugins/campaign_panel.py
```
Selectezi RMW x conditii (incl. `gilbert_*`) x reps x mod (SIL/HIL); valideaza si construieste/
lanseaza comanda `run_campaign.py`. Logica e in `campaign_hmi_core` (testat); panoul e doar GUI.

NOTA HMI: layout-urile GUI nu se pot verifica vizual headless -- de revizuit cand le rulezi tu pe
ecran. Logica din spate (nucleele) e testata.

## 7. C4: stability margin glisant + ESTOP

`joint_core.EnergyMonitor` calculeaza margine de stabilitate pe fereastra de 1s:
`win_energy = integ(tau_B*om)` pe ultima secunda. Un controler pasiv doar disipa (energie marginita);
cresterea = semn de instabilitate (teleimpedanta sub legatura degradata).

`emulator_node` alimenteaza cate un monitor pe pereche si publica ADITIV `win_energy` + `estopped`
in `/joint/state`. Parametrul `estop_energy`:
- `0.0` (implicit) -> doar monitorizeaza, comportament NESCHIMBAT (compatibil cu SIL-ul existent).
- `>0` -> auto-ESTOP cand energia pe fereastra trece pragul (taie cuplul).

`operator_panel_node` afiseaza in titlu `stabilitate (E pe 1s): X J` + marcaj `[ESTOP]`.

```bash
# Necesita ROS + ecran. Auto-ESTOP opt-in:
python3 ~/ros2_ws/src/joint_emulator/nodes/emulator_node.py --ros-args -p estop_energy:=0.5
```

## 8. Trecerea sim -> HIL (ce urmeaza pe doua masini)

Pregatit in SIL, de rulat pe PC + RPi:
1. Pe masina B (RPi): `netem_bridge_node` cu `enable:=true` aplica `tc netem ... loss gemodel ...`
   pe interfata reala -- ACELASI model Gilbert care a rulat in SIL (paritate de model).
2. Campanie reala N>=5 (nu N=1 SIL) prin `campaign_panel` in mod `hil`, conditii `gilbert_*` + `loss_*`.
3. Calibrare: inlocuieste sweep-ul sintetic de parametri Gilbert cu valori dintr-un trace radio real.
4. Co-canal (Faza 2): leaga `cochannel_sinr` de `radio_link.loss_from_snr` pentru degradare dependenta
   de geometrie/trafic.

Vezi si `HIL_RUNBOOK` / `TASK_SIL_HIL.md` pentru pasii de mediu (doua masini, ceas, RMW).

## 9. Onestitate (de citit inainte de a folosi cifrele)

- Tot ce e mai sus e SIL / loopback sau model sintetic. NU sunt rezultate HIL.
- Parametrii Gilbert (`gilbert_*`) sunt parametrizati, nu calibrati pe trace real.
- `5.6x` (sectiunea 4) e o proprietate a MODELULUI la parametrii alesi, nu o masura de fier.
- Pragul `estop_energy` si forma energiei sunt alegeri de modelare -- de validat pe HIL.
- Inainte de orice submisie: HIL pe doua masini, N>=5, parametri calibrati.
