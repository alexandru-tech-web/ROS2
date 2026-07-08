# FAPTE_V4.md -- fapte verificate pentru versiunea v4 a articolului C1

READ-ONLY pe cod si date (zero modificari). Fiecare fapt are citat verbatim +
fisier:linie. Ce nu se poate verifica din cod/date canonice -> [NEVERIFICABIL] + motiv.
Date canonice: ~/DATE_CAMPANIE/{SIL,HIL_WIFI}/date/<rmw>/<cond>/rep<N>/transport_p<P>_summary.json.
Cod FROZEN: ~/ros2_ws/src/c1_benchmark/*.py.

================================================================================
R3 -- Profilul QoS exact (reliability/history/depth/durability)
================================================================================
Codul seteaza DOAR adancimea cozii (int), nu un QoSProfile explicit:
  bench_client.py:26  self.pub = self.create_publisher(String, "/bench/ping", 50)
  bench_client.py:27  self.create_subscription(String, "/bench/pong", self.on_pong, 50)
  bench_echo_server.py:12  self.pub = self.create_publisher(String, "/bench/pong", 50)
  bench_echo_server.py:13-14  self.create_subscription(String, "/bench/ping",
                                 lambda m: self.pub.publish(m), 50)
Cand argumentul QoS e un int in rclpy, se creeaza QoSProfile(depth=N) cu:
  - history    = KEEP_LAST   (implicat de int depth)
  - depth      = 50          (EXPLICIT in cod, toate cele 4 endpoint-uri)
  - reliability = RELIABLE   (default rclpy -- NU e setat explicit in cod)
  - durability  = VOLATILE   (default rclpy -- NU e setat explicit in cod)
VERIFICAT: nu exista niciun import QoSProfile / QoSReliabilityPolicy in cele doua
fisiere; singurul parametru QoS setat de autor e depth=50. reliability=RELIABLE si
durability=VOLATILE sunt valorile IMPLICITE rclpy (documentate), nu alegeri explicite.
Pentru articol: "KEEP_LAST depth 50; reliability si durability lasate pe implicitul
rclpy (RELIABLE, VOLATILE)".

================================================================================
R4 -- Valoarea per-sample deadline din cod
================================================================================
[NEVERIFICABIL -- INEXISTENT] Nu exista niciun deadline per-esantion / QoS Deadline
in cod. Nu se seteaza DeadlineQoS nicaieri (nici in client, nici in echo). Un esantion
e considerat "pierdut" daca ecoul lui nu revine pana la sfarsitul buclei de rulare:
  bench_client.py:25  self.t_end = time.time() + a.duration + 1.0
  bench_client.py:53  t_stop = time.time() + a.duration + 1.5   # +1.5 s: ecourile in zbor
  bench_client.py:54  while rclpy.ok() and time.time() < t_stop:
Deci "termenul" efectiv per rulare = start + duration + 1.5 s (nu per-esantion).
Recomandare articol: NU afirma un "per-sample deadline"; formuleaza "un esantion e
pierdut daca ecoul nu s-a intors in fereastra de rulare (durata + 1.5 s de gratie)".

================================================================================
R2 -- received per repetitie la HIL/zenoh/lat200_jit50 (4 KB) -- CONFIRMA "4/5 = 0"
================================================================================
Din transport_p4096_summary.json, HIL_WIFI/date/zenoh/lat200_jit50/rep{1..5}:
  rep1: received=184/989   loss=0.814
  rep2: received=0/989     loss=1.0
  rep3: received=0/989     loss=1.0
  rep4: received=0/989     loss=1.0
  rep5: received=0/989     loss=1.0
CONFIRMAT: 4 din 5 repetitii = ZERO livrari. Media p95 raportata (7696.9 ms) provine
dintr-o SINGURA repetitie (rep1). Aceasta e o valoare SURVIVORSHIP-BIASED: agregarea
"media pe repetitii" a p95-ului are n=1 aici (make_tables ignora repetitiile fara p95).
Implicatie pentru v4: marcheaza explicit ca RTT-ul HIL/Zenoh la lat200_jit50 e dintr-o
singura repetitie supravietuitoare; celelalte 4 au fost pierdere totala.

================================================================================
R5 -- Durata de perete reala a rularii 64 KB ideal HIL (CDDS si Zenoh) vs nominal 20 s
================================================================================
[NEVERIFICABIL ca marime inregistrata] Summary-ul stocheaza duration_s = NOMINAL:
  bench_client.py:58  st.update(payload=a.payload, rate_hz=a.rate, duration_s=a.duration, ...)
Toate summary-urile 64 KB ideal HIL au duration_s=20.0 (parametrul, nu perete masurat).
Nu exista timestamp de start/stop nici in JSON, nici in CSV brut (doar seq,rtt_ms) ->
durata de perete reala nu e recuperabila din date; mtime-urile sunt timpul de arhivare.
STRUCTURAL insa durata e FIXA prin bucla: t_stop = start + duration + 1.5 s
(bench_client.py:53-54) -> ~21.5 s pentru ORICE rulare, indiferent de payload/RMW.
FAPT ADIACENT VERIFICABIL (efectul payload-ului asupra debitului de trimitere), 64 KB ideal HIL:
  CDDS  sent per rep = 364/355/372/310/378 (received == sent, 0 pierdere)
  Zenoh sent per rep = 989 (received = 412/427/409/464/373)
Interpretare: la 64 KB, publicarea RELIABLE CDDS blocheaza si franeaza timer-ul (~364
trimiteri in 20 s in loc de ~989), pe cand Zenoh trimite ~989 dar livreaza doar ~40%.
Deci "durata" nu difera (bucla fixa), dar NUMARUL de esantioane trimise da -- de citat cu grija.

================================================================================
R9 -- Ordinea rularilor: intercalat sau secvential per conditie?
================================================================================
SECVENTIAL per conditie (repetitiile consecutive), blocat pe RMW. build_plan:
  bench_core.py:89-104
  """...blocat pe RMW (routerul Zenoh pornit o singura data per bloc), conditiile in
     ordine crescatoare de severitate, repetitiile consecutive..."""
  for rmw in rmws:
      for c in conditions:
          for rep in range(1, reps + 1):
              for layer in layers:
Deci: bloc RMW -> conditie (ordine de severitate) -> toate repetitiile aceleiasi
conditii consecutiv -> abia apoi urmatoarea conditie. NU intercalat intre conditii.
Consecinta metodologica (corecta): repetitiile aceleiasi conditii impart acelasi mediu
netem (o singura aplicare per (RMW,conditie)) -- vezi run_campaign.py:120 "o singura
instanta per bloc RMW".

================================================================================
R13 / R14 -- De ce 989 (nu 1000) + incepe masurarea dupa primul echo reusit?
================================================================================
sent=989, rate_hz=50.0, duration_s=20.0 (verificat pe summary HIL cdds ideal p4096).
Aritmetica: nominal 50 Hz x 20 s = 1000 declansari de timer. Numarul EFECTIV trimis:
  bench_client.py:24  self.warm = 10                      # primele 10: incalzire, ignorate
  bench_client.py:56  sent_eff = max(0, n.seq - n.warm)
Deci sent = seq - 10. sent=989 => seq a ajuns la 999 (nu 1000). Cauza celei -1 declansari:
  bench_client.py:25,31  t_end = start + duration + 1.0 ; tick returneaza daca
                         time.time() >= self.t_end - 1.0  (adica start + 20 s)
Timer-ul la 1/50 s peste fereastra de 20 s produce tipic 999 incrementari inainte de
prag (granularitate de programare a callback-ului), nu fix 1000. Minus warm=10 -> 989.
R14: NU -- masurarea NU incepe dupa primul echo reusit. Incalzirea e dupa NUMARUL DE
SECVENTA, nu dupa succesul ecoului:
  bench_client.py:41  if t0 is None or d["seq"] <= self.warm: return
Primele 10 mesaje TRIMISE (dupa seq) sunt ignorate la RTT, indiferent daca ecoul lor
a reusit sau nu. Denominatorul (sent=989) = trimise efectiv dupa incalzire.

================================================================================
R1 / R10 -- loss_std (Tabel II, HIL 4 KB, 8x2) + p95 min-max peste rep (Tabel III)
================================================================================
loss_std = abaterea standard de populatie (pstdev) a pierderilor per-repetitie [%],
consistent cu make_tables.py (pstdev). HIL, payload 4 KB, N=5:
  conditie        CDDS: loss_mean / loss_std     Zenoh: loss_mean / loss_std
  ideal            0.00 / 0.00                     0.00 / 0.00
  loss_5           0.00 / 0.00                     0.00 / 0.00
  loss_15         20.79 / 1.21                    61.58 / 19.65
  loss_20         53.51 / 5.56                    93.71 / 9.56
  loss_25         70.35 / 2.04                    98.81 / 1.84
  loss_30         80.55 / 1.47                    99.17 / 1.66
  lat200_jit50    14.74 / 14.02                   96.28 / 7.44
  lat200_l15      72.42 / 4.11                   100.00 / 0.00
Note: CDDS lat200_jit50 loss_std=14.02 (foarte mare) reflecta variabilitatea intre
repetitii la aceasta conditie; Zenoh loss_15 loss_std=19.65 la fel. Utile pt. bare de
eroare / coloana +/- in Tabel II.

R10 -- Tabel III, lat200_jit50, 4 KB, p95 min/max/mean peste repetitii:
  SIL  CDDS : n=10  p95 min=469.2  max=497.5  mean=484.2
  SIL  Zenoh: n=10  p95 min=469.6  max=481.6  mean=475.7
  HIL  CDDS : n=5   p95 min=494.4  max=1189.1 mean=635.2
  HIL  Zenoh: n=1   p95 = 7696.9 (min=max=mean -- o SINGURA repetitie; vezi R2)
Atentie la Tabel III: HIL/Zenoh 7696.9 ms are n=1 (survivorship, R2), NU o medie pe 5.

================================================================================
R16 -- Binarul de router Zenoh folosit + versiunea
================================================================================
Binar: rmw_zenohd (din pachetul rmw_zenoh_cpp), pornit prin ros2 run:
  run_campaign.py:129-130  router = subprocess.Popen(
                             ["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"], ...)
Doar pe SIL porneste campania router-ul (o instanta per bloc RMW, run_campaign.py:120).
Pe HIL router-ul e gestionat EXTERN (run_campaign.py:124-127: "routerul Zenoh e
gestionat EXTERN ... Campania NU porneste router pe HIL.") -- acelasi binar, pornit manual.
Versiune (VERSIUNI_3.1.md): rmw_zenoh_cpp 0.2.9; zenoh-cpp-vendor 0.2.9 (routerul
rmw_zenohd e livrat cu acest pachet). Amprenta Pi: [DE COMPLETAT de Alexandru -- vezi
VERSIUNI_3.1.md]; asa ca versiunea router-ului pe MASINA-router HIL ramane de confirmat.

================================================================================
REZUMAT CELE 8 FAPTE (o linie fiecare)
================================================================================
R3  QoS: KEEP_LAST depth=50 (explicit); reliability=RELIABLE, durability=VOLATILE (implicit rclpy).
R4  Deadline per-esantion: INEXISTENT in cod; "pierdut" = fara ecou pana la start+duration+1.5s.
R2  HIL/zenoh/lat200_jit50 received/rep = 184,0,0,0,0 -> CONFIRMA 4/5 = 0 livrari (survivorship).
R5  Durata perete = FIXA ~21.5 s (bucla), NEinregistrata ca masura; 64 KB: CDDS trimite ~364, Zenoh 989.
R9  Ordine: SECVENTIAL per conditie (rep consecutive), blocat pe RMW; nu intercalat.
R13 sent=989 = seq(~999) - warm(10); ~999 nu 1000 din granularitatea timer-ului pe 20 s.
R14 Masurarea NU incepe dupa primul echo; ignora primele 10 dupa numar de secventa.
R1/R10 loss_std (Tabel II) si p95 min-max (Tabel III) tabelate mai sus; HIL/Zenoh Tabel III n=1.
R16 Router: rmw_zenohd (ros2 run rmw_zenoh_cpp rmw_zenohd) 0.2.9; pe HIL pornit extern.
