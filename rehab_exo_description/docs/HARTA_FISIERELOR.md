# Harta fisierelor si denumirilor

## Puncte de intrare recomandate

Lansarea C4 foloseste denumirile de domeniu de mai jos. Fisierele vechi in engleza
raman temporar pentru compatibilitate cu testele si comenzile existente.

| Punct de intrare nou | Rol | Implementare compatibila |
|---|---|---|
| `controler_exercitii_reabilitare.py` | programe si serii pentru 6 axe | `exercise_controller.py` |
| `panou_operator_reabilitare.py` | HMI complet | autonom |
| `simulator_senzori_reabilitare.py` | semnale sintetice LLR | `senzori_node.py` |
| `monitor_senzori_reabilitare.py` | tablou text | `monitor_senzori.py` |
| `inregistrator_sesiune_reabilitare.py` | CSV complet | `session_recorder.py` |
| `grafice_reabilitare_live.py` | grafice live | `telemetry_display.py` |
| `initializare_encodere_absolute.py` | bariera de homing | `homing_node.py` |
| `supervizor_siguranta_electrica.py` | praguri software si oprire | `supervizor_electric.py` |

Aliasurile sunt intentionate. Stergerea numelor vechi ar rupe launch-uri istorice,
documente si teste fara sa imbunatateasca functionalitatea.

## Module active

- `exercise_core.py`: traiectorii, limite, sesiuni si player fara ROS;
- `geometrie_core.py`: cote si invarianti geometrici;
- `transmisie_core.py`, `spec_derivate.py`: transmisii si valori derivate;
- `senzori_core.py`: modele sintetice, mapari si provenienta;
- `monitor_core.py`: criterii de urmarire/coerenta/calitate;
- `recorder_core.py`: formatul CSV si verificarea canalelor;
- `supervizor_core.py`: logica pura a pragurilor electrice;
- `rmw_guard.py`: verificarea consistenta a middleware-ului.

## Lansari

- `demo_c4.launch.py`: demonstratia integrata recomandata;
- `operator.launch.py`: vizualizare RViz/legacy fara fizica Gazebo;
- `gazebo.launch.py`: lansare tehnica mai veche;
- `exercitii_*.launch.py`: scurtaturi istorice pentru grupe;
- `telerehab.launch.py`: infrastructura de teleoperare experimentala.

## Documente cu autoritate

- `docs/GHID_UTILIZARE.md`: instalare, operare, export si depanare pentru colega;
- `docs/START_AICI.md`: traseul colegei de la build la date;
- `docs/MANUAL_TEHNIC_LLR.md`: arhitectura, senzori, control si limite;
- `README_DEMO.md`: operarea demonstratiei C4;
- `DECIZII.md`: decizii si motive;
- `IPOTEZE.md`, `urdf/IPOTEZE_LIMITE.md`, `urdf/MASE_NEVERIFICATE.md`:
  ce nu este inca masurat;
- `docs/AUDIT_SIMULARE_2026-09-23.md`: auditul tehnic al simularii;
- `attic/`: variante istorice, **nu surse active**.

## Regula pentru comentarii

Codul activ documenteaza deciziile, unitatile, provenienta si motivele de siguranta.
Nu se adauga comentarii care repeta mecanic fiecare instructiune: ele ar ascunde
exact informatia importanta si s-ar invechi mai repede decat codul.
