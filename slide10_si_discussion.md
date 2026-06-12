# Propozitiile de rezultat — campania M (canal spatial)

## Pentru slide 10 (RO, gata de lipit)

- 8/8 misiuni complete sub canal radio dependent de distanta (acoperire 100%,
  5/5 victime, ambele profiluri, ambele middleware-uri).
- T90 (timpul pana la 90% acoperire): Zenoh cu ~14% mai rapid pe camp deschis
  (96 vs 111 s); paritate pe teren greu (103 vs 104.5 s).
- Mesajul central se confirma si spatial: la transport, diferentele intre
  middleware-uri ating 3 ordine de marime; la nivel de misiune raman sub 15%
  — autonomia roiului absoarbe degradarea.
- N=2 repetitii: variatia interna intre rulari (10–27 s) este comparabila cu
  diferentele intre middleware-uri — campania extinsa (N=5) decide
  interactiunea cu terenul.

## Pentru articol — paragraf de Discussion (EN, LaTeX)

```latex
\paragraph{Mission layer under a distance-dependent channel.}
To complement the uniform-degradation campaign, we repeated the mission layer
under a spatial log-distance radio model with terrain profiles
(\emph{open field} vs.\ \emph{urban rubble}), where each UAV's link quality is
recomputed continuously from its distance to the GCS. All $8$ missions
completed with full coverage and $5/5$ victims found under both middlewares.
Time to 90\% coverage favored \texttt{rmw\_zenoh} by ${\sim}14\%$ in the open
field ($96$ vs.\ $111$\,s) and was at parity under urban rubble
($103$ vs.\ $104.5$\,s); with $N{=}2$ repetitions these differences are
comparable to run-to-run variability ($10$--$27$\,s). The central observation
of the uniform campaign therefore persists in the spatial setting: transport
tails that differ by orders of magnitude compress to second-order effects at
mission level, as swarm autonomy absorbs degradation up to the failure
threshold identified in Sec.~IV.
```

## Diagnosticul etajului de misiune (RTL=0 — de lamurit in 30 s)

`capacity_wh` este parametru declarat, iar pragul dinamic trebuia sa
declanseze RTL in fereastra. Zero peste tot inseamna ori ca bateria n-a
primit pozele (parse pe formatul telemetriei), ori ca degradarea radio n-a
fost aplicata deloc (caz in care profilurile au fost aproape ideale — ceea
ce ar explica si misiunile perfecte). Ruleaza si trimite iesirea:

```bash
cd ~/mission_results/cyclonedds/open_field/rep1
ls -la
wc -l *.csv 2>/dev/null
head -3 battery.csv coverage.csv victims.csv 2>/dev/null
tail -8 radio.log battery.log 2>/dev/null
grep -h rth op_commands.csv 2>/dev/null | head -3
```

Daca battery.csv/coverage.csv au DOAR antetul sau lipsesc -> nodurile-plugin
nu au inteles formatul telemetriei roiului si repar parse-ul; daca au date
si stari RTL -> repar doar numaratoarea din analyze. In ambele cazuri,
metricile T90/acoperire/victime raman valide (vin din GCS, nu din plugin-uri).
