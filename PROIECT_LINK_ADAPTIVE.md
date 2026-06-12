# link_adaptive — proiect nou de la zero (contributia C3)

Design document. NU se scrie cod inainte de 22.06. Pachet nou, in afara
celor inghetate; refoloseste conventiile depozitului (linkstate JSON,
noduri subtiri, nuclee pure testate fara ROS).

## 1. Motivatia (direct din rezultatul N=5)

Campania a demonstrat doua filozofii de fiabilitate fara castigator
universal: DDS = zid uniform de intarziere + misiuni complete; Zenoh =
mediana rapida + pierderi care peste un prag devin pierderi de misiune
(1/5 la loss_30). Intrebarea de cercetare a lui C3: poate un strat
APLICATIV adaptiv sa pastreze prospetimea lui Zenoh SI supravietuirea
misiunii a lui DDS, comutand comportamentul dupa starea legaturii?

## 2. Adevarul tehnic care dicteaza designul

In ROS 2, QoS-ul unui publisher este FIXAT la creare — nu se poate schimba
in mers. Prin urmare adaptarea NU inseamna "schimba QoS la cald", ci:

| Mecanism | Cum functioneaza | Cand ajuta |
|---|---|---|
| canal dublu | acelasi flux publicat pe DOUA topicuri gemene (reliable + best_effort); receptorul asculta ambele, deduplica dupa msg_id; selectorul alege pe care se trimite | comuta filozofia per clasa de mesaj |
| scalarea ratei | telemetria 20 Hz -> 5 Hz sub degradare; video: calitate/rezolutie in trepte | reduce presiunea pe legatura inainte sa devina pierdere |
| redundanta k | sub pierdere mare, mesajele CRITICE (rth, estop) se trimit de k ori cu acelasi id; dedup la receptie | recupereaza fiabilitatea comenzilor rare fara coada DDS |
| degradare pe prioritati | sub presiune se taie intai video, apoi telemetria de volum, NICIODATA comenzile | pastreaza misiunea vie cu legatura minima |

## 3. Arhitectura

```
link_adaptive/
├── adapt_core.py        # NUCLEU PUR: LinkEstimator (EWMA pierdere, varsta,
│                        #  RTT din proba), StrategySelector (histerezis pe
│                        #  praguri), RedundancyCodec (k-replicare + dedup),
│                        #  RateGovernor (trepte de rata)
├── test_adapt_core.py   # tinta: 30+ verificari, fara ROS
├── nodes/
│   ├── link_estimator_node.py   # sub /sar/probe/stats + /sar/linkstate
│   │                            # -> pub /adapt/state {regim, loss_ewma, age}
│   └── adaptive_channel_node.py # infasoara un topic: in -> [strategie] ->
│                                # out_reliable / out_besteffort + dedup invers
├── sil_adapt.py         # scenariul SIL: degradare in trepte, adaptiv vs static
└── launch/adaptive_swarm.launch.py  # roiul + stratul adaptiv (fara a modifica
                                     # sar_swarm: doar remapari de topicuri)
```

Regimuri (histerezis ca sa nu clipoceasca): VERDE (ideal..loss<5%),
GALBEN (5-20% sau lat>150ms), ROSU (>20% sau down). Strategia per regim per
clasa: comenzi (mereu reliable + k=1/2/3), telemetrie (BE, 20/10/5 Hz),
video (on/calitate-redusa/off).

## 4. Ipotezele de evaluare (refolosesc campaniile existente)

- HA1: cu stratul adaptiv pornit, misiunile Zenoh la loss_30 revin la >=4/5
  (de la 1/5), fara a pierde avantajul de mediana din regimul GALBEN.
- HA2: comenzile critice (rth) ajung 100% in toate conditiile, pe ambele RMW.
- HA3: costul stratului in conditia ideala < 5% (latenta si CPU).
- HA4: adaptiv-pe-Zenoh >= static-pe-DDS la timp de misiune in TOATE
  conditiile (testul "nu mai alegi middleware-ul, alegi strategia").

Evaluarea = mission_experiment.sh cu o axa noua (adaptive on/off): 2 RMW x
2 profiluri x 2 adaptiv x 3 rep = 24 rulari (~2 h) + reutilizarea conditiilor
uniforme din c1 (dupa ridicarea inghetului).

## 5. Jaloane

| Jalon | Continut | Verificare |
|---|---|---|
| J1 (sapt. 1-2) | adapt_core pur + 30 teste | `python3 test_adapt_core.py` |
| J2 (sapt. 3) | sil_adapt: figura adaptiv-vs-static in trepte | PNG + raport |
| J3 (sapt. 4-5) | nodurile + integrarea prin remapare in roi | L1 cu `ros2 topic echo` |
| J4 (sapt. 6-7) | campania adaptiv-vs-static | CSV + 4 figuri |
| J5 (sapt. 8-10) | schita articolului A2 pe schema A1 | main.tex nou |

## 6. Riscuri

Dedup-ul pe canal dublu cere msg_id in payload (conventia JSON il permite
fara schimbari de tip); histerezisul prost calibrat oscileaza (de aceea J2
e SIL inainte de ROS); supra-adaptarea poate ascunde middleware-ul pe care
il studiem (raportam mereu si referinta statica).
