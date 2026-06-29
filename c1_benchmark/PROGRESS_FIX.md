# PROGRESS_FIX -- fix bug router Zenoh pe HIL in run_campaign.py

Branch: `fix-hil-router-watchdog` (din main). FARA push, FARA merge.
Fix CHIRURGICAL: 2 modificari in `run_campaign.py`, nimic altceva atins.

## Ce am modificat (linii reale)

Codul real s-a potrivit EXACT cu descrierea sarcinii. `a.mode` e variabila reala a
modului (folosita deja la liniile 84, 92, 94 etc.).

MODIFICAREA 1 -- watchdog doar pe SIL (liniile 115-116):
- Comentariul + conditia `if` a watchdog-ului. Adaugat `a.mode == "sil"` ca prima
  conditie, deci pe HIL watchdog-ul NU mai reporneste niciun router.

MODIFICAREA 2 -- pornirea routerului doar pe SIL (in jurul liniei 124):
- In blocul `if p["rmw"] != cur_rmw:`, am adaugat o ramura noua `if p["needs_router"]
  and a.mode == "hil":` care DOAR tipareste ca routerul e gestionat extern (NU porneste
  router). Vechiul `if p["needs_router"] and not a.dry:` a devenit `elif`. Restul
  (Popen rmw_zenohd pe SIL, ramura --dry) neschimbat.

## stop_router() -- verificat, NU atinge routerul extern
`stop_router()` (linia ~101) face `if router and router.poll() is None: os.killpg(...)`.
Pe HIL, variabila `router` ramane None (nu se mai porneste), deci `stop_router()` nu
face NIMIC -- NU omoara routerul extern al utilizatorului. Corect. Niciun alt cod nu
omoara un router extern pe HIL.

## Verificari
- `python3 -m py_compile run_campaign.py` -> sintaxa OK.
- `grep -nP '[^\x00-\x7F]' run_campaign.py` -> gol (ASCII curat).
- `git diff` -> doar cele 2 zone, nimic altceva.

## Validare prin rulare (--dry; mediul ARE ros2 in /opt/ros/jazzy)
`run_campaign.py` NU importa rclpy, deci --dry ruleaza pur-Python (fara subprocese reale).
- `--mode hil --iface eth0 --dry --rmws zenoh --conditions ideal` ->
  afiseaza "[hil] routerul Zenoh e gestionat EXTERN (porneste-l manual cu
  ZENOH_CONFIG_OVERRIDE). Campania NU porneste router pe HIL." si NICIO pornire de
  router (niciun "[dry] pornesc routerul"). Exit 0.
- `--mode sil --iface lo --dry --rmws zenoh --conditions ideal` ->
  afiseaza "[dry] pornesc routerul Zenoh (rmw_zenohd)" -- comportament SIL NESCHIMBAT.
  Exit 0.

## CE TREBUIE SA FACA UTILIZATORUL (important -- date compromise)

1. RE-RULEAZA Zenoh HIL pe AMBELE transporturi (switch SI Wi-Fi), cu routerele
   pornite MANUAL pe fiecare masina, cu ZENOH_CONFIG_OVERRIDE corect (connect/endpoints
   catre masina 2). Vezi HIL_RUNBOOK.md / HIL_TRANSPORT_CHEATSHEET.md.
   -> Datele Zenoh HIL anterioare sunt COMPROMISE de acest bug (routerul intern izolat
      a rupt mesh-ul cross-machine -> loss artificial mare, RTT mare). Arunca-le / reface-le.

2. REVERIFICA si datele Zenoh SWITCH: la pierdere mare (loss_25/loss_30), acelasi
   watchdog putea "vedea" routerul ca mort si il repornea (gresit), poluand acele rulari.
   Compara cu asteptarile; daca arata anormal, re-ruleaza si acele conditii.

3. CycloneDDS NU e afectat (nu foloseste router) -- datele CycloneDDS raman valide.

NOTA: eu NU am sters nicio data (results_c1 / arhive). Utilizatorul decide ce arunca.
NU am rulat campanie reala. Branch local, FARA push/merge -- revizuieste si decide.
