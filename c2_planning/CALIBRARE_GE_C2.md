# CALIBRARE_GE_C2.md -- calibrare Gilbert-Elliott pentru C2 (planificare)

PLANIFICARE, READ-ONLY, ZERO netem. Nu s-a rulat tc/netem/sudo; c1_benchmark/
doar CITIT. Scop C2: la rata medie de pierdere EGALA, testeaza daca rafalele
(pierdere corelata) adancesc caderea Zenoh mai mult decat a CycloneDDS. Cheia
designului: perechi Gilbert-Elliott <-> Bernoulli la aceeasi rata medie L.

Reproducere: python3 ge_calib_sim.py  (si --selftest). Python pur (stdlib), fara retea.

================================================================================
PAS 1 -- Semantica 'loss gemodel' din sursa primara LOCALA
================================================================================
Sursa: /usr/share/man/man8/tc-netem.8.gz  (man tc-netem, masina curenta).

Gramatica (verbatim):
    LOSS := loss { random PERCENT [ CORRELATION ]  |
                   state p13 [ p31 [ p32 [ p23 [ p14]]]] |
                   gemodel p [ r [ 1-h [ 1-k ]]] }  [ ecn ]

loss gemodel (verbatim):
    "adds packet losses according to the Gilbert-Elliot loss model or its
     special cases (Gilbert, Simple Gilbert and Bernoulli). To use the
     Bernoulli model, the only needed parameter is p while the others will
     be set to the default values r=1-p, 1-h=1 and 1-k=0. The parameters
     needed for the Simple Gilbert model are two (p and r), while three
     parameters (p, r, 1-h) are needed for the Gilbert model and four (p, r,
     1-h and 1-k) are needed for the Gilbert-Elliot model. As known, p and r
     are the transition probabilities between the bad and the good states,
     1-h is the loss probability in the bad state and 1-k is the loss
     probability in the good state."

loss state (verbatim, pentru referinta -- alternativa 4-stari):
    "adds packet losses according to the 4-state Markov using the transition
     probabilities as input parameters. The parameter p13 is mandatory and if
     used alone corresponds to the Bernoulli model. The optional parameters
     allows one to extend the model to 2-state (p31), 3-state (p23 and p32)
     and 4-state (p14). State 1 corresponds to good reception, State 4 to
     independent losses, State 3 to burst losses and State 2 to good reception
     within a burst."

NOTA DE ONESTITATE (lectia jitter uniform din C1): man page-ul DESCRIE modelul,
nu GARANTEAZA ce implementeaza kernelul. In C1 man page-ul zicea distributie
'Normal' pentru jitter, dar kernelul aplica uniform (tabledist). Prin urmare:
validarea FINALA a distributiei realizate (rata + structura rafalelor) se face
LA CAMPANIE, din log-urile de pachete per-esantion, NU din documentatie si NICI
din simularea de mai jos (care valideaza doar aritmetica modelului).
CAVEAT de directie: man page-ul spune doar "p and r are the transition
probabilities between the bad and the good states" -- NU precizeaza sensul.
Aici asum conventia standard netem p = P(good->bad), r = P(bad->good). Aceasta
e confirmata de calibrarea proprie din bench_core (gilbert_20 cu p=0.05, r=0.20
tinteste L=20%, ceea ce cere pi_bad = p/(p+r) = 0.20, deci p=good->bad). De
reconfirmat totusi din comportamentul kernelului la campanie.

================================================================================
PAS 2 -- Derivare parametri (Simple Gilbert: 1-h=1, 1-k=0)
================================================================================
Simple Gilbert: pierzi MEREU in bad (1-h=1), niciodata in good (1-k=0) ->
pierderea unui pachet <=> stare bad.
  Stationar:  pi_bad = p / (p + r)
  Rata medie: L = pi_bad
  Lungime medie rafala: B = 1/r  (numar de stari bad consecutive; geometric(r))
Inversare (tinta -> parametri):
  r = 1 / B
  p = L / (B * (1 - L))

Grila ceruta: L in {5, 15, 30}% x B in {1 (control ~Bernoulli), 3, 8} pachete.

Tabel (p, r) + validare Monte Carlo (10^6 pachete/config; |dL|=|L_real-L| pp):
  L%   B   p%        r%        L_real%  B_real  B_p95  |dL|pp
  5    1   5.2632    100.0000  5.015    1.000   1      0.015
  5    3   1.7544    33.3333   5.079    3.004   8      0.079
  5    8   0.6579    12.5000   5.068    8.033   23     0.068
  15   1   17.6471   100.0000  15.005   1.000   1      0.005
  15   3   5.8824    33.3333   15.127   3.018   8      0.127
  15   8   2.2059    12.5000   15.064   7.992   23     0.064
  30   1   42.8571   100.0000  29.995   1.000   1      0.005
  30   3   14.2857   33.3333   30.271   3.019   8      0.271
  30   8   5.3571    12.5000   30.268   8.047   23     0.268
Toate configuratiile respecta toleranta |L_real - L| < 0.3 pp (max 0.271 pp la
L=30%, B=3). B_real coincide cu B tinta; B_p95 arata coada geometrica (23 la B=8).

COMENZI netem EXACTE (text, NErulate) -- Simple Gilbert (1-h=100%, 1-k=0%) +
perechea Bernoulli (memoryless) la acelasi L:
  -- L=5% --  Bernoulli: tc qdisc replace dev <IFACE> root netem loss 5.0000%
     B=1 (control ~Bernoulli): tc qdisc replace dev <IFACE> root netem loss gemodel 5.2632% 100.0000% 100% 0%
     B=3:                      tc qdisc replace dev <IFACE> root netem loss gemodel 1.7544% 33.3333% 100% 0%
     B=8:                      tc qdisc replace dev <IFACE> root netem loss gemodel 0.6579% 12.5000% 100% 0%
  -- L=15% --  Bernoulli: tc qdisc replace dev <IFACE> root netem loss 15.0000%
     B=1 (control ~Bernoulli): tc qdisc replace dev <IFACE> root netem loss gemodel 17.6471% 100.0000% 100% 0%
     B=3:                      tc qdisc replace dev <IFACE> root netem loss gemodel 5.8824% 33.3333% 100% 0%
     B=8:                      tc qdisc replace dev <IFACE> root netem loss gemodel 2.2059% 12.5000% 100% 0%
  -- L=30% --  Bernoulli: tc qdisc replace dev <IFACE> root netem loss 30.0000%
     B=1 (control ~Bernoulli): tc qdisc replace dev <IFACE> root netem loss gemodel 42.8571% 100.0000% 100% 0%
     B=3:                      tc qdisc replace dev <IFACE> root netem loss gemodel 14.2857% 33.3333% 100% 0%
     B=8:                      tc qdisc replace dev <IFACE> root netem loss gemodel 5.3571% 12.5000% 100% 0%
<IFACE> = interfata substituita la runtime (SIL: lo; HIL: interfata Wi-Fi).
'100% 0%' = 1-h, 1-k explicite (Simple Gilbert), ca in bench_core.netem_cmd.
Nota: B=1 => r=100% => rafala de lungime 1 => echivalent Bernoulli (control).

================================================================================
PAS 3 -- Validare Monte Carlo (rezumat)
================================================================================
Metoda: lant Markov 2-stari, 10^6 pachete/config, seed fix (reproductibil);
pierdere = stare bad; rafala = run de stari bad consecutive. Vezi tabelul din
PAS 2 pentru rata realizata, media si p95 lungimii rafalelor, si abaterea.
Concluzie: inversarea r=1/B, p=L/(B*(1-L)) e corecta (toate |dL| < 0.3 pp).
LIMITA: aceasta valideaza MODELUL Markov teoretic, nu netem-ul real (vezi nota
de onestitate PAS 1). La campanie se masoara rata + rafalele efective din log.

================================================================================
PAS 4 -- Audit conditii existente in bench_core.py (READ-ONLY, doar raport)
================================================================================
Transcris VERBATIM din c1_benchmark/bench_core.py (linii 30-37):
  # rafale simple (netem 'loss p% r%'): pierdere CORELATA, aceeasi medie
  dict(name="loss_20_burst", base_ms=0,   jitter_ms=0,  loss=0.20, corr=0.50),
  dict(name="loss_25_burst", base_ms=0,   jitter_ms=0,  loss=0.25, corr=0.50),
  dict(name="loss_30_burst", base_ms=0,   jitter_ms=0,  loss=0.30, corr=0.50),
  # gilbert_*: Gilbert-Elliott nativ netem ('loss gemodel'); aceeasi medie ca loss_*,
  # mean_burst_len=5 -> p, r din rf_interference.BurstProcess.from_steady (paritate SIL<->HIL).
  dict(name="gilbert_20",   base_ms=0,   jitter_ms=0,  loss=0.20, type="gilbert", p=0.0500, r=0.2000),
  dict(name="gilbert_25",   base_ms=0,   jitter_ms=0,  loss=0.25, type="gilbert", p=0.0667, r=0.2000),
  dict(name="gilbert_30",   base_ms=0,   jitter_ms=0,  loss=0.30, type="gilbert", p=0.0857, r=0.2000),

gilbert_* (loss gemodel) -> L, B implicite prin formulele PAS 2 + simulare:
  gilbert_20  p=0.0500 r=0.2000 -> L=20.00%  B=5.00  (Monte Carlo: L=20.23%, B=5.04)
  gilbert_25  p=0.0667 r=0.2000 -> L=25.01%  B=5.00  (Monte Carlo: L=25.23%, B=5.02)
  gilbert_30  p=0.0857 r=0.2000 -> L=30.00%  B=5.00  (Monte Carlo: L=30.15%, B=5.00)
  => toate trei sunt la B=5 (mean_burst_len=5, cum zice si comentariul din cod),
     L in {20,25,30}%.

loss_*_burst -> model CORELAT deprecat ('loss p% r%'), NU gemodel:
  loss_20/25/30_burst: L = 20/25/30% (parametrul loss). B NU e definit prin
  formulele GE (1/r): 'corr=0.50' e coeficientul de corelatie al modelului
  'loss random' cu corelatie, pe care man page-ul il marcheaza "now deprecated
  due to the noticed bad behavior". Nu e comparabil direct cu gemodel.

POTRIVIRE cu grila calibrata C2 (L in {5,15,30} x B in {1,3,8}):
  - gilbert_* folosesc B=5 si L in {20,25,30}. B=5 NU e in grila {1,3,8};
    din L, doar 30% e comun. Deci grila C2 propusa si conditiile existente
    NU coincid (nici pe B, nici pe majoritatea lui L).
  - loss_*_burst folosesc un model diferit (corelat deprecat), nu gemodel.
=> C2 va avea nevoie de DEFINITII NOI de conditii (sau de aliniere explicita).
   Aceasta e o CONSTATARE, nu o decizie -- vezi intrebarile deschise.

================================================================================
INTREBARI DESCHISE (decizia e a lui Alexandru)
================================================================================
1. Set de rate L: pastram {5,15,30}% (propunerea C2) sau aliniem la {20,25,30}%
   ale gilbert_* existente (comparabilitate cu C1)? Sau reuniune {5,15,20,25,30}?
2. Set de rafale B: {1,3,8} (propus, acopera control + moderat + lung) vs B=5
   deja folosit de gilbert_*. Includem B=5 ca punte cu C1? {1,3,5,8}?
3. Modelul de rafala: standardizam pe gemodel (Simple Gilbert, curat, calibrabil)
   si RETRAGEM loss_*_burst (corelat deprecat, "bad behavior")? Recomandare:
   da -- gemodel e reproductibil si documentat; loss_*_burst e deprecat.
4. 1-h / 1-k: ramanem pe Simple Gilbert (1-h=1, 1-k=0) sau modelam si pierdere
   reziduala in good (1-k>0) / supravietuire in bad (1-h<1)? Simple Gilbert e
   suficient pentru intrebarea "rafale la aceeasi medie" si mai usor de calibrat.
5. Payload: rulam grila GE pe toate cele 3 payload-uri (64B/4KB/64KB) ca in C1,
   sau doar 4KB (unde apare divergenta)? (Cost campanie vs acoperire.)
6. Validare realizata: confirmam ca planul de campanie C2 LOGHEAZA secventa de
   pierdere per-esantion (nu doar sumarul), ca sa putem masura B_real din date
   (obligatoriu, per nota de onestitate PAS 1).
