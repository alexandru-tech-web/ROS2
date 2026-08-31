# VERSIUNI -- amprente de mediu, document canonic si harta de nume a conditiilor

Culese de pe ACEASTA masina (laptop) la 2026-07-07, READ-ONLY (uname/dpkg; niciun nod ROS pornit).
CONFIRMA ca se potrivesc cu masina care a rulat campania: SIL 2026-06-24, HIL 2026-07-01.
Datele de build ale pachetelor rmw (20260412) preced campania -> consistent.

## Laptop (client + router Zenoh) -- cules acum
- Kernel:            6.17.0-35-generic
- Distro:            Ubuntu 24.04.4 LTS
- ROS 2:             Jazzy Jalisco (/opt/ros/jazzy)
- rmw_cyclonedds_cpp: 2.2.3      (ros-jazzy-rmw-cyclonedds-cpp 2.2.3-1noble.20260412.033317)
- CycloneDDS:         0.10.5     (ros-jazzy-cyclonedds 0.10.5-1noble.20260225.142613)
- rmw_zenoh_cpp:      0.2.9      (ros-jazzy-rmw-zenoh-cpp 0.2.9-1noble.20260412.030951)
- zenohd / zenoh-cpp: 0.2.9      (ros-jazzy-zenoh-cpp-vendor 0.2.9-1noble.20260225.231114;
                                  routerul rmw_zenohd e livrat cu acest pachet)

## Raspberry Pi 4 (echo server + router Zenoh) -- DE COMPLETAT de Alexandru
NU am deschis conexiuni catre Pi (regula 2). Ruleaza SNIPPET-ul de mai jos prin SSH si
lipeste iesirea aici:

```
ssh <user>@<pi-host> 'uname -r; . /etc/os-release; echo "$PRETTY_NAME"; \
  dpkg -l 2>/dev/null | grep -iE "rmw-zenoh|rmw-cyclonedds|^ii  ros-jazzy-cyclonedds|zenoh-cpp-vendor" \
    | awk "{print \$2, \$3}"'
```

Pi -- kernel:            [DE COMPLETAT]
Pi -- distro:            [DE COMPLETAT]
Pi -- rmw_cyclonedds_cpp:[DE COMPLETAT]
Pi -- CycloneDDS:        [DE COMPLETAT]
Pi -- rmw_zenoh_cpp:     [DE COMPLETAT]
Pi -- zenoh-cpp-vendor:  [DE COMPLETAT]

## Fraza gata de lipit in Sec. 3.1 (dupa completarea Pi)
"Both environments ran ROS 2 Jazzy on Ubuntu 24.04 (laptop kernel 6.17.0-35; Raspberry Pi 4
kernel [Pi kernel]). The middlewares were rmw_cyclonedds_cpp 2.2.3 over CycloneDDS 0.10.5 and
rmw_zenoh_cpp 0.2.9 (zenoh-cpp-vendor 0.2.9); the Zenoh router is the rmw_zenohd shipped with
rmw_zenoh_cpp 0.2.9."
(Daca versiunile Pi difera de laptop, raporteaza-le separat -- e o testbed HIL, nu o masina.)

---

## Descendenta: manuscris <-> cod <-> date

Nu exista un singur "canonic": exista o descendenta. Fiecare manuscris se
citeste impreuna cu commitul de cod care i-a produs cifrele si cu manifestul
datelor pe care le-a folosit.

| Manuscris | Data | Cod (commit / tag) | Manifest de date | Stare |
|-----------|------|--------------------|------------------|-------|
| `Draft_..._v3_4.docx` | 2026-07-08 | `ec88db1`, fixat de tagul **`c1-paper-v3.4`** | `paper/MANIFEST_SHA256.txt` (720) | canonic PENTRU TAG |
| `Draft_..._v3_5.docx` | 2026-07-10 | `3dfa755` | `paper/MANIFEST_SHA256.txt` (720) | diagrame de arhitectura EN |
| `Articol_C1_v4.docx` | 2026-07-18 | `a8ffc17` | `paper/MANIFEST_SHA256.txt` (720) | trimis coordonatorului 2026-07-18; dupa spusele autorului, 11 comentarii, in revizie (copia din git nu continea comentarii) |
| `V5` | -- | tagul de submisie, inca necreat | idem | de produs la submisie |

### Setul de date <-> campanie <-> cod

Recuperata din `MANIFEST_DATE.md` v1 (`894f3c7`), unde era sectiunea
"Mapare reproductibilitate".

| Set de date | Campanie | Data | Cod / invocare | Ancora git | Manifest |
|-------------|----------|------|----------------|-----------|----------|
| `SIL/` | SIL N=10 | 2026-06-24 | `run_campaign.py --reps 10` (metoda "fair" din working-tree, codificata ulterior ca `run_campaign_fair.sh`) | working-tree 06-24, **hash neinregistrat** -- NU `c61c1e2` (metoda fair postdateaza `c61c1e2`) | `paper/MANIFEST_SHA256.txt` |
| `HIL_WIFI/` | HIL N=5 | 2026-07-01 | `run_campaign.py --mode hil` | `426bd77` (2026-06-26) | `paper/MANIFEST_SHA256.txt` |

Diferenta `c61c1e2..426bd77` NU afecteaza cele 8 conditii studiate: reconstructia
duala a lui `netem_cmd` da comenzi byte-identice, iar `rtt_stats`,
`bench_client.py` si `bench_echo_server.py` sunt identice (dovada completa in
`AUDIT_CIFRE_ARTICOL.md`, sec. 1e).

**CAVEAT, pastrat din v1:** commitul per rulare NU a fost inregistrat. Maparea
presupune working tree curat la rulare, ceea ce nu se poate verifica retroactiv.
Arhiva SIL (`sil_N10_fair_20260624`) a fost recuperata din Trash la 2026-07-01.

`main.tex` nu intra in tabel: se auto-declara schelet, cu `TODO` in text si in
`references.bib`.

Manuscrisele NU mai sunt in arbore (depozitul e public, iar un artefact de cod
nu are motiv sa distribuie drafturi). Raman accesibile prin istoric.

## Seturi scoase din arbore

Istoricul nu a fost rescris: fiecare set ramane accesibil la commiturile de
dinaintea scoaterii.

| Set | In git pana la | Acum la | Manifest | Verificat |
|-----|----------------|---------|----------|-----------|
| `c1_data/` (2651 fisiere, 154 MB) -- campanii C1 anterioare | `f1a0822` | `~/ARHIVA_PHD/istoric/c1_data/` | `manifests/c1_data_SHA256.txt` | 2651/2651 |
| `CAMPANII/` (506 fisiere, 4.7 MB) -- **pilot C1 HIL Wi-Fi**, 8 conditii C1, 2026-06-25..06-30 | `e30decd` | `~/ARHIVA_PHD/istoric/CAMPANII/` | `manifests/CAMPANII_SHA256.txt` | 506/506 |
| 7 manuscrise `.docx` (3.6 MB) | `7333d36` | `~/ARHIVA_PHD/manuscrise/` | `manifests/manuscrise_SHA256.txt` | 7/7 |

Niciunul dintre cele doua seturi de date nu continea vreunul dintre cele 720 de
fisiere din `paper/MANIFEST_SHA256.txt` (0/720 fiecare): sunt campanii C1 anterioare
celei raportate in articol. Eticheta lui `CAMPANII/` a fost stabilita din lista de
conditii, nu presupusa: 8 conditii C1 pe ambele rmw, niciuna C2.

Radacinile sunt separate: `~/DATE_CAMPANIE/` ramane strict datele canonice ale
campaniilor; materialul scos din arbore sta in `~/ARHIVA_PHD/`.

**TODO(Alexandru) -- copia comentata a lui v4.** Versiunea trimisa coordonatorului
la 2026-07-18 s-a intors cu comentarii; copia care era in git nu le continea.
Cand ajunge la tine, arhiveaz-o in `~/ARHIVA_PHD/manuscrise/` cu SHA256 si data
primirii, si adaug-o in tabelul de descendenta ca rand propriu.

## Manifestul datelor: v1 -> v2

| Versiune | Acopera | In depozit | Stare |
|----------|---------|------------|-------|
| v1 `paper/MANIFEST_DATE.md` | 720 fisiere summary `.json` | pana la `865964f`; ultima modificare `894f3c7` | inlocuit, ramane in istoric |
| v2 `paper/MANIFEST_SHA256.txt` | setul canonic COMPLET: `SIL/`, `HIL_WIFI/`, plus `README_SIL.md`, `README_HIL_WIFI.md`, `netem_journal_M2.log` | de la commitul F9-A | in vigoare |

v1 hash-uia doar sumarele `.json`, nu si brutele `.csv` sau jurnalul netem; v2
acopera integral subarborii declarati in antetul lui. Concret, v2 adauga datele
brute `.csv` de langa fiecare summary, figurile (`.png`, `.pdf`) si cele trei
fisiere de la radacina. Toate cele 720 de intrari
din v1 sunt in v2 cu **hash identic** (verificat: 0 absente, 0 hash-uri diferite),
deci v2 este o extindere, nu o re-masurare.

v2 este generat si verificat cu `manifest_tool.py`, deci cifrele stau intr-un
singur loc -- antetul manifestului -- iar README-urile trimit acolo.

Proza din v1 (matricea de completitudine, maparea campanie -> cod, structura de
arhiva Zenodo propusa) ramane accesibila in istoric la `894f3c7`.

## Harta de nume a conditiilor de retea (C1 <-> C2)

Cele doua articole numesc altfel aceleasi canale. Numele si parametrii de mai jos
sunt cititi direct din `bench_core.CONDITIONS`; pierderea de regim si rafala medie
sunt derivate din `(p, r)` prin `pierdere = p/(p+r)` si `rafala = 1/r`.

### Echivalente

| C1 | C2 | Canal | Verificare |
|----|----|-------|-----------|
| `loss_5`  | `bern_5`  | Bernoulli 5 %  | acelasi canal, sintaxa netem diferita |
| `loss_15` | `bern_15` | Bernoulli 15 % | idem |
| `loss_30` | `bern_30` | Bernoulli 30 % | idem |

C1 exprima pierderea independenta prin `netem loss <L>%`. C2 o exprima prin
`netem loss gemodel <L>% <100-L>%`, adica un Gilbert-Elliott cu `r = 1-p`, care
este matematic fara memorie -- deci acelasi canal. Rafala medie calculata pentru
`bern_*` iese 1.1-1.4 pachete, ceea ce confirma echivalenta.

Este **aceeasi distributie pe alta cale de cod netem**: `loss_15` ajunge pe ramura
de pierdere independenta (`tc ... netem loss 15.0%`), iar `bern_15` pe ramura
Gilbert-Elliott (`tc ... netem loss gemodel 15.000% 85.000% 100% 0%`). Diferenta e
de implementare in netem, nu de model statistic, si asta trebuie spus cand cele
doua articole se citesc impreuna.

Cei patru parametri ai lui `gemodel` sunt emisi **explicit**, nu lasati pe seama
implicitelor: `netem_cmd` scrie intotdeauna si `1-h = 100%` (pierdere totala in
starea Bad) si `1-k = 0%` (fara pierdere in starea Good) -- vezi
`bench_core.py:98`. Sunt exact valorile implicite din `tc-netem(8)`, deci
comportamentul nu depinde de versiunea de `iproute2`; le scriem oricum, ca sa nu
depinda.

### Fara corespondent

| Nume | Prezent in | Canal |
|------|-----------|-------|
| `gilbert_20/25/30` | C1 | GE, pierdere 20/25/30 %, rafala medie 5 pachete |
| `loss_20/25/30_burst` | C1 | pierdere corelata netem (`loss <L>% 50%`), NU Gilbert-Elliott |
| `ge_<L>_<B>` | C2 | GE, pierdere L %, rafala medie B pachete (`r = 1/B`) |
| `lat200_jit50_ge_15_8` | C2 | combinat: 200 ms + 50 ms jitter SI rafala GE 15 %, B = 8 |

Valorile derivate, pentru control:

```
gilbert_20  p=0.050000 r=0.200000 -> 20.0 %  rafala 5.0
gilbert_25  p=0.066700 r=0.200000 -> 25.0 %  rafala 5.0
gilbert_30  p=0.085700 r=0.200000 -> 30.0 %  rafala 5.0
ge_5_3      p=0.017544 r=0.333333 ->  5.0 %  rafala 3.0
ge_5_8      p=0.006579 r=0.125000 ->  5.0 %  rafala 8.0
ge_15_3     p=0.058824 r=0.333333 -> 15.0 %  rafala 3.0
ge_15_8     p=0.022059 r=0.125000 -> 15.0 %  rafala 8.0
ge_30_3     p=0.142857 r=0.333333 -> 30.0 %  rafala 3.0
ge_30_8     p=0.053571 r=0.125000 -> 30.0 %  rafala 8.0
```

### Ce a raportat de fapt articolul C1 v3.4

Din cele 24 de conditii definite azi in `bench_core.CONDITIONS`, articolul v3.4
raporteaza doar `loss_*` si `lat200_jit50`. Conditiile Gilbert-Elliott
(`gilbert_*`) erau **implementate la data tagului dar neraportate**; setul C2
(`bern_*`, `ge_*`, `lat200_jit50_ge_15_8`) a fost adaugat pe `main` DUPA tag si nu
face parte din C1. Cine reproduce articolul foloseste tagul `c1-paper-v3.4`.

### Versiuni de referinta ale masinii de campanie

Pentru cine reproduce canalele, versiunile care conteaza sunt kernelul (netem
traieste in kernel) si `iproute2` (comanda `tc` care le programeaza).

| Ce | Valoare | Provenienta |
|----|---------|-------------|
| `uname -r` | `6.17.0-35-generic` | cules de pe laptop la 2026-07-07, DUPA campanie (SIL 2026-06-24, HIL 2026-07-01); nu e o amprenta luata in timpul rularii |
| `tc -V` (iproute2) | TODO(Alexandru) | nu apare in niciun antet CSV, manifest sau jurnal din artefact -- nu a fost cules |

`tc -V` nu se poate reconstitui din ce exista in depozit, asa ca ramane TODO in
loc sa fie completat cu o valoare presupusa. Culegerea e o singura comanda pe
masina de campanie, daca mai e in aceeasi stare.
