# FAPTE_C2.md -- fapte-first ale campaniei C2 SIL (scris ACUM, nu la audit)

Lectia C1: scrii FAPTELE inainte de orice interpretare. Fiecare afirmatie cu fisier:linie.
Cod FROZEN, protocol BYTE-IDENTIC cu C1 (comparabil): bench_client.py, bench_echo_server.py.

## QoS efectiv
- Publisher/subscriber cu adancime 50 (KEEP_LAST); reliability/durability NEsetate explicit
  -> implicitul rclpy (RELIABLE, VOLATILE):
    bench_client.py:26  self.pub = self.create_publisher(String, "/bench/ping", 50)
    bench_client.py:27  self.create_subscription(String, "/bench/pong", self.on_pong, 50)
    bench_echo_server.py:12-14  (ecoul, depth 50)
- Fara DeadlineQoS in cod (niciun import QoSProfile in cele doua fisiere).

## Definitia pierderii
- Un esantion e PIERDUT daca ecoul (pong) nu revine pana la sfarsitul ferestrei de rulare:
    bench_client.py:53  t_stop = time.time() + a.duration + 1.5   # +1.5 s ecourile in zbor
    bench_client.py:54  while rclpy.ok() and time.time() < t_stop:
- loss = round(1 - received/sent, 4): bench_core.py:74 (rtt_stats). delivery = received/sent.
- Incalzire: primele 10 (dupa NUMAR DE SECVENTA) ignorate la RTT: bench_client.py:24,41.

## sent=989 (denominatorul)
- warm=10 (bench_client.py:24); sent_eff = max(0, seq - warm) (bench_client.py:56).
- 50 Hz x 20 s => ~999 declansari de timer - 10 incalzire = 989 (verificat pe date: sent=989).
- Rata: run_campaign NU trimite --rate -> default bench_client 50 Hz (bench_client.py:48).
- Durata: run_campaign --duration default 20.0 s (run_campaign.py:63).

## Agregare
- delivery/loss = MEDIA pe cele 10 repetitii a valorilor per-rulare (make_tables_c2.py:delivery).
  std = abaterea standard de populatie (pstdev). B_real = media lungimilor de rafala din
  GOLURILE de seq (burst_metrics.failure_bursts, IMPORTAT).

## Editari locale PAYLOADS (documentate, NECOMISE)
- Grila 4KB: PAYLOADS=[4096] local, revenit (C2_SIL_20260718 are DOAR transport_p4096).
- Sonda 64KB: PAYLOADS=[65536] local, revenit (C2_SIL64 are DOAR transport_p65536).
- Combo: PAYLOADS=[4096] local.
- Toate NECOMISE (arbore git CURAT la analiza); runbook sect. 2.1/3.1/3.2 documenteaza mecanismul
  (sed pe run_campaign.py:43 + git checkout de revenire).

## Provenienta (dataset -> HEAD -> note)
  C2_SIL_20260718      (grila 4KB) @ 2a27029    PAYLOADS=[4096]; 200 summary; validat in C2-1
  C2_PROBE_20260719    (sonda UDP) @ f966b0e    9x10k + 3x30k (B=8); best-effort valideaza netem
  C2_SIL64_20260719    (64KB)      @ f966b0e    40 summary + CONSOLE_LOG.txt (1008 linii)
  C2_SILCOMBO_20260719 (combo)     @ >=1bc02c9  conditia combo; HEAD exact NEinregistrat in date
NOTA: sumarele JSON NU stocheaza git-hash/versiuni (ca in C1). run_campaign NU logheaza hash-ul
(de adaugat la metadata rularii in campaniile viitoare). Provenanta = starea git + runbook +
acest fisier + MANIFEST_DATE_C2.md.
