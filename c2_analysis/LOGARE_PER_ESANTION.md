# LOGARE_PER_ESANTION.md -- confirmare logare pe disc (decizia #6 C2)

Intrebare: seq + timestamp per esantion se SALVEAZA pe disc la fiecare rulare
(nu doar sumarul)? Verificare DIN COD (READ-ONLY), fisier:linie.

## Ce SE salveaza (confirmat din cod)
c1_benchmark/bench_client.py:61-64 scrie, la fiecare rulare, un CSV per esantion:
    61  with open(a.out, "w") as f:
    62      f.write("seq,rtt_ms\n")
    63      for s, r in n.rtts:
    64          f.write(f"{s},{r:.3f}\n")
Calea: run_campaign.py:156-160 seteaza --out = <outdir>/rep<N>/transport_p<P>.csv.
Deci pe disc raman, PER REPETITIE: numarul de secventa 'seq' + RTT-ul 'rtt_ms'
pentru fiecare esantion RECEPTIONAT. Plus sumarul JSON (bench_client.py:65-66).
n.rtts se umple in on_pong (bench_client.py:43): (seq, RTT). Incalzirea: primele
10 dupa numar de secventa sunt excluse (bench_client.py:41).

## Ce NU se salveaza
- Timestamp ABSOLUT per esantion: NU. Ora de plecare exista in memorie
  (self.sent[seq] = time.time(), bench_client.py:34) dar NU se scrie in CSV.
- Inregistrari EXPLICITE de pierdere: NU. Esantioanele pierdute lipsesc din CSV.

## Suficienta pentru metrici burst-aware (C2)
DA pentru rafale in PACHETE. Esantioanele pierdute = GOLURI in secventa de 'seq'
receptionate: intre seq a si b consecutive receptionate sunt (b-a-1) pierderi
consecutive = o rafala de esec. burst_metrics.py reconstruieste asa cea mai lunga
rafala, distributia lungimilor si numarul de rafale, FARA sa aiba nevoie de
timestamp. Timpul (daca e nevoie) se deduce din rata fixa: 50 Hz => 20 ms/pachet
(bench_client.py: --rate default 50; run_campaign NU trimite --rate).

CONCLUZIE: pentru intrebarea C2 (rafalele adancesc caderea?), logarea existenta
(seq per esantion) e SUFICIENTA -- nu e nevoie de patch obligatoriu.

## Patch minim PROPUS (RAPORT -- NU aplicat; bench_client.py e protejat in acest task)
Daca se doreste timestamp absolut (pt. detectarea neregularitatilor de rata sau
aliniere intre masini la HIL), modificarea minima ar fi:
  - bench_client.py:34 pastreaza deja t0 = self.sent[seq].
  - bench_client.py:43:  self.rtts.append((d["seq"], (time.time()-t0)*1000.0))
      -> self.rtts.append((d["seq"], t0, (time.time()-t0)*1000.0))
  - bench_client.py:62-64:
      f.write("seq,send_t,rtt_ms\n")
      for s, t0, r in n.rtts: f.write(f"{s},{t0:.6f},{r:.3f}\n")
Impact: adauga o coloana 'send_t' (epoch secunde). Compatibil inapoi daca cititorii
folosesc DictReader dupa nume de coloana (burst_metrics.py deja face asa).
NU se aplica fara OK explicit (bench_client.py e in lista de NEmodificat a taskului
C2 kickoff). Recomandare: OPTIONAL -- utila la HIL pentru aliniere temporala, dar
metricile de rafala NU o cer.
