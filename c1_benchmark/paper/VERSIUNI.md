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

## Documentul canonic al articolului

In acest director exista mai multe versiuni `.docx`. Canonicul este:

| Fisier | Statut |
|--------|--------|
| `Draft_Articol_C1_2coloane_v3_4.docx` | **CANONIC** -- corespunde tagului `c1-paper-v3.4` |
| `Draft_Articol_C1_2coloane_v3.docx`, `..._v3_pre-image7.docx` | istoric, nu se citeaza |
| `Draft_Articol_C1_2coloane_v2.docx`, `..._v2_pre-swap.docx` | istoric, nu se citeaza |

`main.tex` NU este articolul: se auto-declara schelet, cu `TODO` in text si in
`references.bib`. Sursa de referinta este `.docx`-ul canonic de mai sus.

---

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
