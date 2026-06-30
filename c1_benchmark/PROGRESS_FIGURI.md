# PROGRESS_FIGURI -- figuri C1 HIL Wi-Fi (corectare + grafice noi)

Branch: `fig-hil-wifi-improvements` (din main). FARA push, FARA merge.
Mediul ARE matplotlib/pandas/numpy + datele reale in results_c1/ -> figurile au fost
generate si VERIFICATE VIZUAL pe date reale (nu doar cod).

## Reparat in analyze_campaign.py (3 probleme)

PROBLEMA 1 -- fig_cdf inselator (received=0 nemarcat). REPARAT: la conditia aleasa,
orice RMW fara pachete (received=0) e marcat acum cu o caseta rosie explicita
"zenoh: 100% loss la 'lat200_l15' (received=0, fara RTT)". Cititorul nu mai crede ca
Zenoh n-a fost testat. (Verificat vizual: caseta apare.)

PROBLEMA 2 -- fig_mission irelevant pe HIL transport. REPARAT: detectie DIN DATE
(has_mission = exista vreun timp de misiune real?). Daca stratul mission nu a rulat
(cazul HIL transport), figura e SARITA cu mesaj "[skip] fig_mission: stratul mission
nu a rulat". Nu se mai genereaza figura muta la plafon. (Merge si pe SIL, care are
mission -> figura se genereaza normal; confirmat de selftest.)

PROBLEMA 3 -- fig_transport gol la cedare totala. REPARAT: unde RTT=0 si loss>=99.9%
(received=0), se deseneaza un marcaj hasurat simbolic + text rosu "received=0 /
cedare totala". Lipsa barei nu mai pare date lipsa. (Verificat vizual la lat200_l15.)

## Grafice NOI in plot_extra.py (toate 3 facute -- niciunul sarit)

GRAFIC 1 -- fig_loss_vs_latency: doua panouri (LOSS pur vs LATENTA). Separa cele doua
moduri de esec. Arata ca Zenoh cedeaza pe AMBELE axe: ~3x mai mult sub loss
(loss_15: 21% vs 62%), si CATASTROFAL sub latenta (lat200_jit50: CycloneDDS 15% vs
Zenoh 96%; lat200_l15: 72% vs 100%).

GRAFIC 2 -- fig_rtt_log: RTT p95 pe scara LOGARITMICA. Pe liniar, ideal (~15ms) se
turtea langa Zenoh loss_25 (~12000ms). Pe log se vede si degradarea usoara.
received=0 marcat explicit (text rosu), nu plotat ca 0.

GRAFIC 3 -- fig_payload: efectul sarcinii utile (64/4096/65536 B) asupra pierderii,
la 'ideal' si 'loss_15'. Insight: chiar la 'ideal' (fara netem), payload 65536 da
Zenoh 58% loss (banda Wi-Fi), unde CycloneDDS rezista (0%); la loss_15, 65536 B
prabuseste ambele (~99%). NU a fost sarit (extragerea per-payload e simpla).

## Cum se genereaza (pe datele EXISTENTE, fara ROS)

    cd ~/ros2_ws/src/c1_benchmark
    python3 analyze_campaign.py results_c1 --mode hil_wifi --out results_c1/analysis_hil_wifi_v2
    python3 plot_extra.py     results_c1 --env  hil_wifi --out results_c1/analysis_hil_wifi_v2
    # ambele scriu .png + .pdf in acelasi --out; culori consistente (cyclonedds albastru, zenoh mov)
    # selfteste fara date reale: python3 analyze_campaign.py --selftest ; python3 plot_extra.py --selftest

NOTA: results_c1/ e gitignorat (date) -> figurile NU intra in git; se regenereaza din
scripturi. In repo intra DOAR scripturile (analyze_campaign.py, plot_extra.py).

## Ce figuri sunt "de folosit pentru teza" vs "diagnostic intern"

PENTRU TEZA (povestea principala):
- fig_loss_vs_latency  -- cele doua moduri de esec (figura-cheie a poveste).
- fig_transport        -- p95 RTT per conditie (cu marcaj de cedare totala).
- fig_payload          -- efectul payload-ului (banda Wi-Fi).
- fig_cdf              -- distributia RTT la conditia severa (cu nota de cedare Zenoh).

DIAGNOSTIC INTERN (util la analiza, optional in articol):
- fig_rtt_log          -- aceeasi info ca fig_transport dar pe log; bun pentru a vedea
                          conditiile usoare; alege intre fig_transport si fig_rtt_log
                          dupa ce vrei sa accentuezi.
- fig_mission          -- NU se genereaza pe HIL transport (irelevant).

## NOTA pentru utilizator (context teza -- onestitate)

Figurile reflecta Wi-Fi DEGRADAT (tc netem). Pe Wi-Fi SANATOS, literatura
(arXiv 2309.07496) arata Zenoh SUPERIOR. De mentionat in teza ca rezultatul C1 e
specific REGIMULUI DEGRADAT (teleoperare SAR pe retea proasta), NU o contradictie cu
literatura -- exact valoarea contributiei: nimeni nu a masurat sistematic regimul degradat.

## ATENTIE -- modificare necomisa gasita in router_m1.json5 (in afara scopului)

Pe acest branch, router_m1.json5 avea o modificare NECOMISA in working tree:
  listen: ["tcp/192.168.100.14:7447"]  ->  listen: ["tcp/[::]:7447"]
(asculta pe TOATE interfetele in loc de IP-ul specific .14 -- de obicei MAI ROBUST).
Pare o editare intentionata a utilizatorului (de pe M1, la testarea routerului). Am
readus fisierul la starea comisa ca sa tin branch-ul de figuri curat, DAR daca acea
editare era a ta si o vrei pastrata, spune-mi -- o aplic pe main ca un commit separat
de config (nu apartine branch-ului de figuri).
