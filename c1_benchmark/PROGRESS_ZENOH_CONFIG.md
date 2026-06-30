# PROGRESS_ZENOH_CONFIG -- config router Zenoh JSON5 pentru HIL Wi-Fi

Branch: `zenoh-router-configs-wifi` (din main). FARA push, FARA merge.

## Ce am creat (2 fisiere, continut EXACT din sarcina)

- `router_pi.json5` -- ROUTER pe Raspberry Pi (pi4-node), wlan0, IP 192.168.100.19.
  mode:"router", connect:[] (nu se conecteaza nicaieri), listen:["tcp/192.168.100.19:7447"],
  scouting.multicast.enabled:false.
- `router_m1.json5` -- ROUTER pe laptop M1 (client), wlp4s0, IP 192.168.100.14.
  mode:"router", connect:["tcp/192.168.100.19:7447"] (spre Pi), listen:["tcp/192.168.100.14:7447"],
  scouting.multicast.enabled:false.

Fiecare are un comentariu // de antet (masina, IP, cum se foloseste).

## Validare
- ASCII: `grep -rnP '[^\x00-\x7F]'` -> gol (curat).
- JSON5: modulul Python `json5` LIPSESTE in mediu. Am validat structural cu Python
  (strip // comentarii + citare chei alfabetice -> json.loads) si vizual. Rezultat:
  ambele VALIDE -> mode=router, endpoints corecte, multicast dezactivat. Confirmat.

## DISCREPANTA gasita -- fisierul vechi de sters NU se numeste asa (NU am ghicit)

Sarcina cere stergerea lui `zenoh_pi.json5`. ACEST FISIER NU EXISTA si nu a fost
NICIODATA in git (verificat: `git log --all -- zenoh_pi.json5` gol, `ls` gol).

EXISTA insa `zenoh_m1.json5` (UNTRACKED + gitignorat in sesiunea anterioara ca
artefact), care se potriveste EXACT cu descrierea fisierului-gresit din sarcina:
  - mode:"peer" (config de NOD, nu de router) -- gresit;
  - IP-uri AMESTECATE: connect "tcp/192.168.100.17:7447" (.17 = Pi-CABLU) cu
    listen "tcp/192.168.100.14:7447" (.14 = M1-WiFi) -- incoerent, exact ca in sarcina.

Deci numele real al fisierului-gresit pare a fi `zenoh_m1.json5`, nu `zenoh_pi.json5`
(probabil o confuzie de nume in sarcina). NU l-am sters: numele difera de ce cere
sarcina, e untracked/gitignorat, iar regula e "nu ghici". ASTEPT CONFIRMAREA
UTILIZATORULUI.

RECOMANDARE: da, `zenoh_m1.json5` ar trebui sters (e configul incoerent mode:peer,
inlocuit acum de router_pi/router_m1). Fiind untracked, stergerea lui nu afecteaza
git -- e doar curatenie pe disc. Confirma si il sterg.

## INSTRUCTIUNI PENTRU UTILIZATOR (cum se folosesc config-urile)

Pe Pi (.19):
    export ZENOH_ROUTER_CONFIG_URI=~/ros2_ws/src/c1_benchmark/router_pi.json5
    ros2 run rmw_zenoh_cpp rmw_zenohd

Pe M1 (.14):
    export ZENOH_ROUTER_CONFIG_URI=~/ros2_ws/src/c1_benchmark/router_m1.json5
    ros2 run rmw_zenoh_cpp rmw_zenohd

Nodurile (ecou pe Pi, bench_client pe M1) raman DEFAULT -- NU seta
ZENOH_SESSION_CONFIG_URI pe ele (vorbesc cu routerul local prin localhost).

Verificare:
- Fiecare router trebuie sa afiseze ca asculta pe IP-ul REAL (.19 / .14), NU pe
  localhost/127.0.0.1.
- Apoi proba bench_client -> tinta: received complet, loss ~0.
- Coroboreaza cu fix-ul din run_campaign.py (deja pe main): pe HIL campania NU mai
  porneste router intern -- aceste routere externe sunt singurele.

NU am rulat nimic ROS. Branch local, FARA push/merge.
