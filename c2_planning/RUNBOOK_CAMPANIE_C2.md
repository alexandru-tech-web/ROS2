# RUNBOOK_CAMPANIE_C2.md -- executia campaniei C2 (o ruleaza Alexandru)

Campania C2 masoara: la rata medie de pierdere EGALA, adancesc rafalele (pierdere
corelata) caderea Zenoh mai mult decat a CycloneDDS? Comparatie GE <-> Bernoulli la
acelasi L. ATENTIE: acest runbook implica tc/netem/sudo -- il ruleaza OMUL, nu agentul.

================================================================================
## 0. DECIZII INGHETATE C2 (kickoff)
================================================================================
Grila (10 conditii; type=gilbert => excluse implicit din C1, se aleg cu --conditions):
  ideal (REFOLOSIT din C1) + bern_{5,15,30} + ge_{5,15,30} x B{3,8}
  - bern_L: Bernoulli ADEVARAT via netem gemodel cu r=1-p (memoryless). Control proaspat.
  - ge_L_B: Simple Gilbert (1-h=1, 1-k=0); r=1/B, p=L/(B*(1-L)); (p,r) EXACT din
    CALIBRARE_GE_C2.md. B=1 ELIMINAT (r=1 interzice pierderi consecutive -> nu e Bernoulli;
    vezi CORECTIE 2026-07-15 in CALIBRARE_GE_C2.md).
  - Comenzile netem exacte per conditie: c1_benchmark/test_c2_conditions.py (9/9 OK).
Parametri:
  - N = 10 repetitii in AMBELE medii (SIL loopback + HIL Wi-Fi).
  - Payload PRINCIPAL: 4 KB (4096 B). Sonda 64 KB DOAR la ge_15_8 (decizie dupa SIL).
  - lat200_jit50 + GE = OPTIONAL, decizie dupa SIL.
  - Durata rulare: 20 s @ 50 Hz (default run_campaign.py; NU schimba).
Intrebarea stiintifica se masoara cu c2_analysis/burst_metrics.py (rafale din golurile
de seq) PLUS metricile C1 (loss, RTT p95) din sumare.

## 0.1 DECIZII APROBATE 2026-07-14 (poarta de review: Alexandru citeste sect. 0/0.1 inainte de lansare)
- Sonda 64 KB: DOAR daca SIL/HIL arata efect de rafala la 4 KB. Candidat combo HIL:
  lat200_jit50 + ge_15_8 -- ambele decise DUPA SIL.
- Patch timestamp bench_client.py: RESPINS. Protocolul ramane BYTE-IDENTIC cu C1
  (comparabilitate inter-articole); golurile de seq ajung pentru rafale.
- loss_*_burst: raman DEPRECATED, NU se sterg.
- Intercalare per repetitie: NU (adiacenta per conditie inchide R9; vezi sect. 2).
- PAYLOADS=[4096] pentru grila principala.
- NOTA DE EVALUARE: ipoteza GE se judeca pe HIL. Efect mic pe SIL = CONSISTENTA cu C1
  (mediul e mecanismul), NU infirmarea ipotezei.

## 0.1-AMENDAMENT 2026-07-19 (dupa SIL; APPEND -- pre-inregistrarea de mai sus RAMANE)
- Criteriul sondei 64 KB: INDEPLINIT. SIL la 4 KB arata efect de rafala clar (Zenoh
  app-loss ~7-25x intre bern_L si ge_L_8 la L=15%; vezi QUICKLOOK_C2_SIL). Sonda 64 KB
  APROBATA: SIL, conditii {bern_15, ge_15_8}, PAYLOADS=[65536], N=10 (vezi sect. 3.1).
- Combo HIL CONFIRMAT ca candidat: lat200_jit50 + ge_15_8 (ge_15_8 zenoh = 75.9% pe SIL).
- Nota de evaluare RAFINATA: SIL a aratat efect MARE (nu mic, contrar premisei initiale) =>
  intrebarea pe HIL devine "mediul FIZIC amplifica SUPLIMENTAR colapsul indus de corelare?",
  nu "exista efect?". Ipoteza tot pe HIL; SIL = rezultat, nu verdict.
- Calibrarea netem a ramas NEVALIDATA de calea RELIABLE -> sonda UDP best-effort (sect. 8).

================================================================================
## 1. PRE-FLIGHT (ABORT daca oricare pica)
================================================================================
a. Versiuni == C1 (ABORT daca difera):
     uname -r                      # asteptat: 6.17.0-35-generic
     dpkg -l | grep -E 'ros-jazzy-rmw-zenoh-cpp|ros-jazzy-rmw-cyclonedds-cpp'
     # asteptat: rmw_cyclonedds_cpp 2.2.3 ; rmw_zenoh_cpp 0.2.9
   Daca kernel-ul sau versiunile RMW difera de C1 -> STOP (datele nu ar fi comparabile).
b. qdisc CURAT inainte:
     tc qdisc show dev <IFACE>     # nu trebuie sa contina 'netem'
     sudo tc qdisc del dev <IFACE> root 2>/dev/null || true
c. Selftest-uri (fara ROS, fara retea):
     python3 c1_benchmark/test_c2_conditions.py       # 9/9 conditii
     python3 c2_analysis/burst_metrics.py --selftest   # 6 verificari
     python3 c1_benchmark/test_bench_core.py           # 13/13 (nenrupt)
d. Memorie partajata reziduala (non-fatal): rm -f /dev/shm/fastrtps_*
e. DRY-RUN de validare (nu aplica netem, doar printeaza comenzile):
     python3 c1_benchmark/run_campaign.py --dry --mode sil --iface lo --reps 10 \
       --rmws cyclonedds,zenoh --conditions ge_5_3 --layers transport
   Verifica vizual comanda 'loss gemodel ...' == cea din test_c2_conditions.py.

Optimizare payload (RECOMANDAT): pentru sweep-ul principal la 4 KB, editeaza LOCAL
(NU comite) run_campaign.py:43  PAYLOADS = [4096]  -> de ~3x mai rapid. Pentru sonda
64 KB la ge_15_8 ruleaza separat cu PAYLOADS = [4096, 65536]. (Alternativ: lasa
default [64,4096,65536] si analizeaza doar transport_p4096 -- corect, dar mai lent.)

================================================================================
## 2. ORDINEA RULARILOR -- INTERCALATA pe RMW per conditie (lectia R9 din C1)
================================================================================
In C1 build_plan era 'for rmw: for c: for rep' -> TOT CycloneDDS, apoi TOT Zenoh;
cele doua RMW pentru ACEEASI conditie erau departate in timp (drift de mediu intre
ele). C2 corecteaza: o rulare run_campaign.py PER CONDITIE cu --rmws cyclonedds,zenoh
=> pentru fiecare conditie ruleaza CycloneDDS x10 apoi Zenoh x10, adiacent in timp,
sub acelasi netem. Astfel comparatia RMW la o conditie e izolata de drift.
(Intercalare mai fina, alternand per repetitie, ar cere modificarea build_plan -- in
afara scopului; adiacenta per conditie rezolva deja R9.)

Ordinea conditiilor (severitate crescatoare):
  ideal, bern_5, ge_5_3, ge_5_8, bern_15, ge_15_3, ge_15_8, bern_30, ge_30_3, ge_30_8
run_campaign.py aplica netem per rulare (:137) si CURATA qdisc la final (:185, finally).

================================================================================
## 3. COMENZI SIL (loopback, o masina), N=10, 4 KB
================================================================================
ARCH=~/DATE_CAMPANIE/C2_SIL_$(date +%Y%m%d)     # locatie de arhiva
Pentru FIECARE conditie (ruleaza-le pe rand, in ordinea de la sect. 2):
  sudo -v
  python3 c1_benchmark/run_campaign.py --mode sil --iface lo --reps 10 \
    --rmws cyclonedds,zenoh --conditions <COND> --layers transport --out "$ARCH"
  tc qdisc show dev lo        # verifica CURAT dupa (run_campaign curata in finally)
Exemplu (ge_5_3):
  python3 c1_benchmark/run_campaign.py --mode sil --iface lo --reps 10 \
    --rmws cyclonedds,zenoh --conditions ge_5_3 --layers transport --out "$ARCH"
Sonda 64 KB (DUPA ce SIL 4 KB e complet si validat), doar ge_15_8:
  # editeaza local PAYLOADS = [4096, 65536], apoi:
  python3 c1_benchmark/run_campaign.py --mode sil --iface lo --reps 10 \
    --rmws cyclonedds,zenoh --conditions ge_15_8 --layers transport --out "$ARCH"_probe64k

## 3.1 SONDA 64 KB (post-SIL, aprobata 2026-07-19) -- doar bern_15 + ge_15_8
ARCH64=~/DATE_CAMPANIE/C2_SIL64_$(date +%Y%m%d)
Mecanism payload (LOCAL, NECOMIS -- documentat):
  sed -i 's/^PAYLOADS = .*/PAYLOADS = [65536]/' c1_benchmark/run_campaign.py   # NU comite
  # ... ruleaza cele doua conditii ... apoi REVINO:
  git checkout -- c1_benchmark/run_campaign.py
Pentru fiecare din {bern_15, ge_15_8}:
  sudo -v
  python3 c1_benchmark/run_campaign.py --mode sil --iface lo --reps 10 \
    --rmws cyclonedds,zenoh --conditions <COND> --layers transport --out "$ARCH64"
  tc qdisc show dev lo        # CURAT dupa (run_campaign curata in finally)
NOTA: la 64 KB CycloneDDS trimite ~364/rulare (throttling de publicare RELIABLE, ca in C1),
NU ~989 -> delivery = received/sent (nu received/989). Se analizeaza transport_p65536.

================================================================================
## 4. COMENZI HIL (doua masini, Wi-Fi real), N=10, 4 KB
================================================================================
Pre-conditii HIL: ecoul (bench_echo_server.py) + routerul Zenoh ruleaza pe masina 2
(vezi c1_benchmark/HIL_RUNBOOK.md). <IFACE> = interfata Wi-Fi reala (NU lo).
ARCH=~/DATE_CAMPANIE/C2_HIL_WIFI_$(date +%Y%m%d)
Pentru FIECARE conditie:
  sudo -v
  python3 c1_benchmark/run_campaign.py --mode hil --iface <IFACE_WIFI> --reps 10 \
    --rmws cyclonedds,zenoh --conditions <COND> --layers transport --out "$ARCH"
NOTA: pe HIL routerul Zenoh e gestionat EXTERN (run_campaign NU-l porneste, :124-127).

================================================================================
## 5. ESTIMARE DURATA (aproximativa)
================================================================================
Per rulare (1 payload, 1 rep) ~24 s (20 s masurare + ~1.5 s gratie + ~1.5 s pornire ecou/overhead).
SIL, 4 KB, 10 conditii x 2 RMW x 10 rep = 200 rulari ~ 80 min + overhead ~= 1.5 h.
  + sonda 64 KB ge_15_8 (2x10 rulari) ~ 8 min.
HIL, 4 KB, aceleasi 200 rulari ~ 1.5-2 h (+ setup fizic + variabilitate Wi-Fi).
Daca lasi PAYLOADS default (3 payload-uri): de ~3x (SIL ~4.5 h).
lat200_jit50 + GE (optional): +cost proportional cu numarul de conditii adaugate.

================================================================================
## 6. CRITERII DE ABORT
================================================================================
- Versiuni != C1 (kernel/RMW) -> abort inainte de start.
- qdisc nu se curata / netem nu se aplica (eroare tc) -> abort, investigheaza.
- 'ideal' arata pierdere > ~1% (sanity) -> mediu murdar, investigheaza inainte sa continui.
- SIL: routerul Zenoh moare repetat (watchdog il reporneste; daca insista) -> abort.
- HIL: 0 receptionate pe o conditie usoara (ex. bern_5) neasteptat -> problema de link/ecou.
- Orice rulare cu sent << 989 la 4 KB fara motiv -> verifica rata/CPU.

================================================================================
## 7. ARHIVARE + ANALIZA
================================================================================
Datele brute NU intra in git (regula 5). Arhiveaza in:
  SIL:  ~/DATE_CAMPANIE/C2_SIL_<YYYYMMDD>/<rmw>/<conditie>/rep<N>/transport_p<P>{.csv,_summary.json}
  HIL:  ~/DATE_CAMPANIE/C2_HIL_WIFI_<YYYYMMDD>/...
In repo intra ulterior DOAR sumarele agregate + figurile.
Dupa campanie, metrici burst-aware pe fisierele 4 KB:
  python3 c2_analysis/burst_metrics.py <ARCH>/*/*/rep*/transport_p4096.csv
Compara, la acelasi L: rafalele (longest/medie/p95) si loss/RTT p95 intre bern_L si
ge_L_B, separat pentru CycloneDDS si Zenoh -> raspunde la intrebarea C2.
Validare distributie realizata (nota de onestitate din CALIBRARE_GE_C2.md): confirma
din golurile de seq ca B_real ~ B tinta (3 sau 8) inainte de a trage concluzii.


================================================================================
## 8. VALIDAREA INSTRUMENTULUI (sonda UDP best-effort; comenzi TIPARITE, NErulate)
================================================================================
Scop: pe calea ROS RELIABLE, L/B de la aplicatie NU sunt cele injectate de netem (CDDS
recupereaza, Zenoh amplifica -- vezi QUICKLOOK). O sonda UDP one-way best-effort pe lo vede
pierderea EXACT cum o aplica netem, deci valideaza calibrarea (p,r).
NOTA: tranzitiile gemodel sunt PER-PACHET (nu per-timp) => procesul de pierdere e
INDEPENDENT de rata; folosim 100 Hz doar ca sa scurtam durata.

Pentru FIECARE din cele 9 conditii de pierdere:
  sudo tc qdisc replace dev lo root netem delay 0ms 0ms loss gemodel <P>% <R>% 100% 0%
  python3 c2_analysis/probe_udp.py --rate 100 --count 10000 \
    --out ~/DATE_CAMPANIE/C2_PROBE_$(date +%Y%m%d)/<COND>.csv
  tc qdisc show dev lo           # confirma netem activ in timpul sondei
  sudo tc qdisc del dev lo root  # CURATARE obligatorie dupa fiecare conditie
  tc qdisc show dev lo           # confirma CURAT

(P, R) per conditie (verbatim din c1_benchmark/test_c2_conditions.py):
  bern_5   gemodel 5.000%  95.000%      bern_15  gemodel 15.000% 85.000%
  bern_30  gemodel 30.000% 70.000%      ge_5_3   gemodel 1.754%  33.333%
  ge_5_8   gemodel 0.658%  12.500%      ge_15_3  gemodel 5.882%  33.333%
  ge_15_8  gemodel 2.206%  12.500%      ge_30_3  gemodel 14.286% 33.333%
  ge_30_8  gemodel 5.357%  12.500%

VERDICT calibrare (din summary-ul sondei):
  - |L_real - L_tinta| < 1 pp   (L_tinta = 5/15/30%).
  - GE: B_real in [0.7*B, 1.3*B]  (B = 3 sau 8).
  - Bernoulli (bern_L): B_real ~ 1/(1-p)  (1.05 / 1.18 / 1.43 la 5/15/30%).
Daca sonda TRECE -> calibrarea netem confirmata; tabelul app-level din QUICKLOOK ramane
REZULTAT (efectul middleware-ului), nu eroare de calibrare.
