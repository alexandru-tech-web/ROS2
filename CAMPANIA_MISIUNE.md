# Campania de misiune (M) — rolul, datele si contributia

Documentul campaniei de date la NIVEL DE MISIUNE pentru roi (sar_swarm +
sar_plugins). Complementara campaniei C1 (transport): C1 a masurat firul,
campania M masoara OPERATIUNEA. Infrastructura exista deja
(`sar_plugins/tools/mission_experiment.sh` + `analyze_missions.py`) — acest
document fixeaza protocolul, semnificatia datelor si ipotezele.

---

## 1. Rolul campaniei — de ce nu ajunge C1

C1 a aplicat degradare UNIFORMA (tc netem pe interfata: aceeasi latenta si
pierdere pentru toate dronele, tot timpul) si a masurat transportul + un strat
subtire de misiune. Campania M schimba natura degradarii:

- canalul radio devine DEPENDENT DE DISTANTA (`radio_link_node`, model
  log-distance cu umbrire): drona departata de GCS pierde mai mult decat cea
  apropiata — exact fizica unei operatiuni reale;
- terenul devine variabila experimentala: profilul `open_field` vs.
  `urban_rubble` (atenuare mai agresiva, praguri mai stranse);
- metricile devin OPERATIONALE: cat de repede e acoperita zona, cate victime
  sunt gasite, cand se declanseaza failsafe-ul energetic.

Mecanismul cauzal care leaga transportul de misiune (verificat in
`demo_plugins_sim.py`): acoperirea se marcheaza LA GCS numai din telemetria
LIVRATA. O legatura proasta nu "incetineste" abstract misiunea — sterge efectiv
celule din harta de acoperire pana la urmatoarea livrare. Campania M masoara
acest lant cap-coada, pe ambele RMW-uri.

## 2. Proiectul experimental

| Factor | Niveluri |
|---|---|
| RMW | `rmw_cyclonedds_cpp`, `rmw_zenoh_cpp` (router pornit automat de script) |
| Profil de canal | `open_field`, `urban_rubble` |
| Repetitii | 2 (implicit; 3 daca timpul permite) |
| Durata unei rulari | ~5 min (plafon) |
| Seed | determinist, incrementat per repetitie (`SEED0`) |

Total implicit: 2 x 2 x 2 = 8 rulari, ~45 de minute. Bateria este scalata
(`BATT_WH=8`) astfel incat failsafe-ul RTL sa fie OBSERVABIL in fereastra —
altfel pragul de 30% nu s-ar atinge in 5 minute.

Regula unui singur publisher: in aceasta campanie `/sar/linkstate` apartine
EXCLUSIV nodului `radio_link_node` (degradarea spatiala); injectorul de
scenarii statice ramane pe stare curata. Scriptul de campanie respecta singur
regula — nu porni nimic in paralel.

## 3. Protocolul (pas cu pas)

```bash
cd ~/ros2_ws/src/sar_plugins

# 0) garda de mediu (nou): procese vii, qdisc rezidual, teste, disc
tools/preflight_misiune.sh                  # asteptat: VERDICT: GO

# 1) planul, fara executie
DRY=1 tools/mission_experiment.sh

# 2) executia (~45 min; masina ramane LIBERA — fara build, fara browser greu)
tools/mission_experiment.sh

# 3) agregarea + figurile
python3 tools/analyze_missions.py ~/mission_results
ls ~/mission_results/analysis/
#   mission_summary.csv + mission_coverage.png + mission_t90.png
#   + mission_victims.png + mission_rtl.png

# 4) verdictele in limbaj de articol (nou)
python3 tools/verdict_misiune.py ~/mission_results

# 5) arhivarea datelor brute (NU intra in git)
mkdir -p ~/c1_archive && cp -r ~/mission_results ~/c1_archive/$(date +%F)_misiune/
```

Variabile optionale: `RMWS`, `PROFILES`, `REPS`, `DUR`, `SEED0`, `BATT_WH`,
`OUT`. Exemplu pentru 3 repetitii: `REPS=3 tools/mission_experiment.sh` (~65 min).

## 4. Ce reprezinta datele extrase

| Metrica | Sursa | Ce inseamna operational | Figura |
|---|---|---|---|
| T90 (timpul pana la 90% acoperire) | jaloanele din `/mission/coverage` | viteza utila a cautarii; metrica principala — sensibila direct la prospetimea telemetriei la GCS | `mission_t90.png` |
| Curba de acoperire in timp | `coverage.csv` (1 Hz) | dinamica intregii cautari; platourile = perioade cu legatura proasta sau drone intoarse | `mission_coverage.png` |
| Victime gasite / total | evenimentele `/mission/victims` | eficacitatea misiunii; detectia e la bord, dar EVENIMENTUL calatoreste prin link | `mission_victims.png` |
| Evenimente RTL (failsafe baterie) | tranzitiile din `/sar/battery` | costul energetic al operarii; arata daca degradarea comunicatiei se traduce in consum si retrageri | `mission_rtl.png` |
| Timp de misiune / finalizare | criteriul de completare | rezultatul agregat, comparabil direct cu stratul de misiune din C1 | `mission_summary.csv` |

Fiecare rulare are manifest JSON (data, host, RMW, profil, seed, git) — orice
cifra din articol e trasabila la o rulare anume.

## 5. Ipotezele campaniei (falsificabile)

- M1 (compresie): ierarhia RMW din C1 se pastreaza pe T90, dar comprimata —
  diferenta relativa intre RMW pe T90 ramane sub ~20%, fata de ordinele de
  marime de la transport. Confirmarea intareste constatarea centrala a tezei.
- M2 (interactiunea teren x RMW): pe `urban_rubble` diferenta dintre RMW-uri
  CRESTE fata de `open_field` — degradarea spatiala agresiva amplifica
  filozofiile diferite de fiabilitate.
- M3 (failsafe robust): numarul evenimentelor RTL nu difera sistematic intre
  RMW-uri — comanda de failsafe (mica, rara, critica) trece pe ambele; daca
  difera, e un rezultat IMPORTANT despre fiabilitatea comenzilor rare.
- M4 (pragul de esec): pe `open_field` toate misiunile se incheie; eventualele
  neterminari apar numai pe `urban_rubble` — granita operationala spatiala,
  perechea celei gasite la 30% pierdere uniforma in C1.

Verdictele pe M1–M4 le scoate `tools/verdict_misiune.py` direct din
`mission_summary.csv`, in propozitii gata de lipit in slide-uri/articol.

## 6. Contributia (unde intra in teza si articol)

1. Inchide povestea pe DOUA straturi cu degradare SPATIALA realista — C1 a
   raspuns la "ce face middleware-ul sub degradare uniforma", campania M
   raspunde la "ce simte OPERATIUNEA cand canalul depinde de distanta si
   teren". Impreuna formeaza argumentul complet al articolului A1.
2. Adauga dimensiunea pe care literatura n-o are deloc: interactiunea
   middleware x profil de teren, pe metrici de misiune (T90, victime, RTL).
3. Cuantifica mecanismul cauzal transport -> misiune (acoperirea marcata doar
   din telemetria livrata), nu doar corelatia.
4. Produce figurile pentru slide 10 al prezentarii si paragraful de misiune
   din Discussion; datele raman reutilizabile pentru articolul A3 (acoperire
   sub degradare) fara nicio rulare suplimentara.

## 7. Igiena si incadrarea in calendar

- NU rula simultan cu nimic altceva; verifica intai `tools/preflight_misiune.sh`.
- Pachetele `sar_swarm` si `c1_benchmark` raman INGHETATE — campania foloseste
  exclusiv instrumente din `sar_plugins/tools/` si nu modifica niciun fisier.
- In git intra numai `mission_summary.csv` + figurile (de ex. in
  `c1_benchmark/paper/figs/`), datele brute merg in `~/c1_archive/`.
- Calendar: rularea diseara sau vineri; figurile intra sambata in slide 10;
  `mission_summary.csv` se trimite la Claude pentru propozitiile de rezultat.

Dupa campanie urmeaza verificarea integritatii fiecarei aplicatii:
`PLAN_TESTE_SWARM.md` nivelurile L0–L2 + sectiunea "Sintaxe de pornire" din
README-ul fiecarui pachet.
