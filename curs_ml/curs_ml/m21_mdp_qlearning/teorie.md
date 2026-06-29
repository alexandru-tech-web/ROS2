# M21 -- Procese de decizie Markov (MDP) si Q-learning

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa FORMALIZEZI o problema de decizie secventiala ca MDP (stari, actiuni,
  tranzitii P, recompense R, factor de discount gamma);
- sa DERIVI ecuatia Bellman de optimalitate si actualizarea Q-learning din ea;
- sa IMPLEMENTEZI Q-learning tabular epsilon-greedy si iteratia pe valoare ca
  referinta optima;
- sa ARGUMENTEZI compromisul explorare/exploatare si rolul ratei de invatare;
- sa EXPLICI de ce comutarea adaptiva QoS/middleware se modeleaza ca MDP (C3).

Prerechizite: M01 (probabilitate: variabile aleatoare, asteptare, lanturi de
tranzitie). Calcul de baza (sume, maxime, puncte fixe). Python + numpy.
Timp estimat: 3-4 h. Dificultate: 3/3.

Vocabular cheie (vezi GLOSAR.md): proces de decizie Markov (MDP), stare, actiune,
functie de tranzitie P, functie de recompensa R, factor de discount gamma,
politica, functie de valoare V, functie de valoare-actiune Q, ecuatia Bellman,
iteratie pe valoare, Q-learning, eroare de diferenta temporala (TD), epsilon-greedy,
explorare vs exploatare, rata de invatare alpha.

## 1. Intuitie (invatare prin recompensa)

Pana acum (M03-M20) am invatat din perechi (intrare, eticheta) date dinainte:
cineva ne spunea raspunsul corect. Invatarea prin recompensa (RL) e altceva.
Un AGENT ia DECIZII secventiale intr-un MEDIU, primeste o RECOMPENSA numerica
dupa fiecare decizie si trebuie sa invete singur ce decizii duc, pe termen lung,
la recompensa cumulata maxima. Nimeni nu-i spune actiunea corecta; o descopera
incercand si vazand ce a iesit.

Doua lucruri fac problema grea si interesanta:
- recompensele sunt INTARZIATE: o actiune buna acum poate da roade abia peste
  cativa pasi (a comuta pe un middleware rezistent INAINTE ca linkul sa cada);
- agentul trebuie sa EXPLOREZE ca sa afle ce e bun, dar si sa EXPLOATEZE ce stie
  deja ca sa nu piarda recompensa -- tensiunea explorare/exploatare.

Exemplul firului rosu al modulului: un robot teleoperat alege, la fiecare interval,
ce middleware foloseste (DDS sau Zenoh) in functie de conditia retelei. Vrem o
REGULA care, pe termen lung, maximizeaza valoarea misiunii. Asta E contributia C3.

## 2. Formalizare: procesul de decizie Markov (MDP)

Un MDP finit este tuplul (S, A, P, R, gamma):
- S: multime finita de STARI (ex: {GOOD, DEGRADED, BAD} -- conditia linkului);
- A: multime finita de ACTIUNI (ex: {DDS, Zenoh} -- middleware-ul ales);
- P: functia de TRANZITIE, P(s' | s, a) = probabilitatea ca, luand actiunea a in
  starea s, sa ajungem in s'. Pentru fiecare (s, a), sum_{s'} P(s'|s,a) = 1.
  In cod e un tensor P[s, a, s'];
- R: functia de RECOMPENSA, R(s, a, s') = recompensa numerica primita la tranzitia
  s -a-> s'. In cod, tensor R[s, a, s'];
- gamma in [0, 1): factorul de DISCOUNT, cat de mult conteaza viitorul fata de
  prezent. gamma -> 0 = miop (doar recompensa imediata); gamma -> 1 = prevazator.

Proprietatea MARKOV: viitorul depinde de trecut DOAR prin starea curenta. Starea
rezuma tot ce conteaza; istoria completa nu mai aduce informatie. Asta e ce face
problema rezolvabila prin programare dinamica.

O POLITICA determinista pi: S -> A spune ce actiune iei in fiecare stare. Scopul:
gaseste politica pi* care maximizeaza recompensa cumulata cu discount, pornind din
orice stare:

    G_t = R_{t+1} + gamma R_{t+2} + gamma^2 R_{t+3} + ...   (return-ul)

## 3. Functii de valoare si ecuatia Bellman de optimalitate

Functia de VALOARE a unei politici, V_pi(s), e return-ul ASTEPTAT pornind din s si
urmand pi de acolo incolo. Functia de valoare-ACTIUNE, Q_pi(s, a), e return-ul
asteptat daca iei intai actiunea a in s, apoi urmezi pi. Valorile OPTIME (sub cea
mai buna politica) se noteaza V* si Q*.

Valoarea optima satisface ecuatia BELLMAN DE OPTIMALITATE -- o conditie de punct fix
care leaga valoarea unei stari de valorile succesorilor ei:

    Q*(s, a) = sum_{s'} P(s'|s,a) [ R(s,a,s') + gamma V*(s') ]
    V*(s)    = max_a Q*(s, a)

In cuvinte: valoarea optima a lui (s, a) este recompensa imediata asteptata plus
valoarea optima cu discount a starii in care ajungi, mediata peste unde te poate
duce P. Politica optima e GREEDY fata de Q*:

    pi*(s) = argmax_a Q*(s, a)

Aceasta ecuatie are solutie unica (operatorul Bellman e o contractie cu factor
gamma < 1, deci are un singur punct fix). De aici doua cai de a o rezolva:
- daca CUNOSTI P si R: programare dinamica (iteratie pe valoare, sectiunea 5);
- daca NU le cunosti, doar vezi tranzitii: Q-learning (sectiunea 4).

## 4. Derivarea actualizarii Q-learning

Q-learning invata Q* FARA sa cunoasca P sau R -- doar din tranzitii observate
(s, a, r, s'). Ideea: ecuatia Bellman spune ca, la optim,

    Q*(s, a) = E_{s'} [ r + gamma max_{a'} Q*(s', a') ]

Partea dreapta e o ASTEPTARE peste s' (si r) pe care nu o putem calcula fara P.
Dar putem ESTIMA o asteptare prin medierea de esantioane. La fiecare tranzitie
observata (s, a, r, s') avem un ESANTION al cantitatii din interior:

    tinta_TD = r + gamma max_{a'} Q(s', a')        (o ghicire bootstrap, folosind Q curent)

Diferenta dintre acest esantion si estimarea curenta e EROAREA DE DIFERENTA
TEMPORALA (TD):

    delta = [ r + gamma max_{a'} Q(s', a') ] - Q(s, a)

Updatam Q(s, a) un pas mic in directia care reduce eroarea -- o medie incrementala
cu rata de invatare alpha (exact forma "noua_estimare = veche + alpha*(tinta - veche)"
din mediile online):

    Q(s, a) <- Q(s, a) + alpha [ r + gamma max_{a'} Q(s', a') - Q(s, a) ]

Aceasta E actualizarea Q-learning. Observatii:
- e OFF-POLICY: tinta foloseste max_{a'} (cea mai buna actiune urmatoare), nu
  actiunea pe care chiar o iei. De aceea invata Q* chiar daca exploreaza;
- e BOOTSTRAP: tinta foloseste propria estimare Q(s', .) -- invatam dintr-o ghicire
  imbunatatind-o, nu asteptam pana la finalul episodului;
- daca alpha scade potrivit (vezi sectiunea 8) si toate perechile (s, a) sunt
  vizitate infinit de des, Q converge la Q* (teorema lui Watkins).

## 5. Iteratia pe valoare (referinta optima, cand stim P si R)

Cand cunoastem modelul, rezolvam ecuatia Bellman direct prin programare dinamica.
Iteratia pe valoare aplica repetat operatorul Bellman pana la punct fix:

    repeta:
      Q(s, a) <- sum_{s'} P(s'|s,a) [ R(s,a,s') + gamma max_{a''} Q(s', a'') ]
      V(s)    <- max_a Q(s, a)
    pana cand V nu se mai schimba (sub o toleranta)

Fiindca operatorul e o contractie (factor gamma), convergenta e garantata
geometric. Iesirea: V*, Q* si pi*(s) = argmax_a Q*(s, a). In curs folosim iteratia
pe valoare ca REFERINTA: ce ar invata un agent perfect care cunoaste mediul.
Q-learning, model-free, trebuie sa ajunga la ACEEASI politica -- exact ce verifica
selftest-ul si fratele `qlearning_sklearn.py`.

## 6. Explorare vs exploatare: epsilon-greedy

Daca agentul ar lua mereu actiunea pe care o crede cea mai buna (greedy pur), ar
rata actiuni mai bune pe care nu le-a incercat inca -- ramane blocat pe o estimare
gresita. Daca ar explora la nesfarsit, ar irosi recompensa. epsilon-greedy
echilibreaza simplu:

    cu probabilitate epsilon: actiune ALEATOARE (explorare)
    altfel                  : argmax_a Q(s, a) (exploatare)

Cu epsilon > 0, fiecare actiune e luata cu probabilitate pozitiva in fiecare stare,
deci toate perechile (s, a) sunt vizitate la nesfarsit -- conditia de care
convergenta Q-learning are nevoie. Practic, epsilon poate fi scazut treptat (mult
explorare la inceput, exploatare la final).

## 7. Algoritm (pseudocod)

```
value_iteration(P, R, gamma):           # REFERINTA optima (stie modelul)
  V <- 0
  repeta:
    Q[s,a] <- sum_s' P[s,a,s'] (R[s,a,s'] + gamma * max_a'' Q[s',a''])
    V_new  <- max_a Q[s,a]
    daca max|V_new - V| < tol: stop
    V <- V_new
  intoarce V, Q, pi = argmax_a Q[s,a]

q_learning(env, n_episodes, alpha, gamma, epsilon):   # MODEL-FREE
  Q <- 0
  pentru fiecare episod:
    s <- stare initiala
    pentru fiecare pas:
      a  <- epsilon_greedy(Q, s, epsilon)        # explorare / exploatare
      (s', r) <- env.step(s, a)                  # observa o tranzitie
      Q[s,a] <- Q[s,a] + alpha * (r + gamma * max_a' Q[s',a'] - Q[s,a])
      s <- s'
  intoarce Q ; politica greedy pi(s) = argmax_a Q[s,a]
```

## 8. Exemplu lucrat numeric (verifica-l de mana)

O singura actualizare Q-learning pe un MDP minuscul cu doua stari
(GOOD = 0, DEGRADED = 1) si doua actiuni (DDS = 0, Zenoh = 1).

Tabelul Q curent (linie = stare, coloana = actiune):

            DDS    Zenoh
    GOOD     2.0    1.0
    DEGRADED 3.0    5.0

Parametri: rata de invatare alpha = 0.5, discount gamma = 0.9.

Agentul, in starea GOOD, ia actiunea DDS, primeste recompensa r = 10 si ajunge in
DEGRADED (s' = DEGRADED). Tranzitia observata: (s=GOOD, a=DDS, r=10, s'=DEGRADED).

Pas 1 -- cea mai buna valoare a starii urmatoare:
    max_{a'} Q(DEGRADED, a') = max(3.0, 5.0) = 5.0

Pas 2 -- tinta TD (bootstrap):
    tinta = r + gamma * max = 10 + 0.9 * 5.0 = 10 + 4.5 = 14.5

Pas 3 -- eroarea TD:
    delta = tinta - Q(GOOD, DDS) = 14.5 - 2.0 = 12.5

Pas 4 -- actualizarea:
    Q(GOOD, DDS) <- 2.0 + 0.5 * 12.5 = 2.0 + 6.25 = 8.25

Deci Q(GOOD, DDS) trece de la 2.0 la 8.25 dupa o singura tranzitie -- valoarea ei
a crescut fiindca actiunea a dus la o recompensa mare (10) si la o stare inca
valoroasa (DEGRADED, valoarea 5.0). Restul tabelului ramane neschimbat la acest pas.

(Selftest-ul nucleului verifica EXACT aceste numere: max=5.0, tinta=14.5,
delta=12.5, Q_nou=8.25; iar exercitiul E2 reproduce calculul de mana.)

## 9. Vizualizare

`demo_sil.py` produce `fig_invatare_qlearning.png`: recompensa pe episod (medie
alunecatoare) pe masura ce agentul Q-learning se antreneaza pe MDP-ul de comutare
a legaturii, cu doua linii de referinta -- optimul (iteratie pe valoare) si cea mai
buna politica STATICA. Curba urca de la nivelul de start spre optim; agentul invatat
intrece politica statica. Pe MDP-ul sintetic, comutarea invatata bate cea mai buna
politica statica (mereu Zenoh) cu ~31% recompensa pe episod. Date SINTETICE.

## 10. Capcane frecvente

- Rata de invatare prost aleasa. alpha prea mare = updaturi instabile care
  oscileaza si nu se aseaza; alpha CONSTANT = Q "roieste" la nesfarsit in jurul lui
  Q* (reziduu Bellman care nu mai scade), fiindca fiecare tranzitie noua zguduie
  estimarea. Remediu: rata DESCRESCATOARE care satisface conditiile Robbins-Monro
  (sum alpha = infinit, sum alpha^2 < infinit), ex. alpha ~ 1/n^0.7 per pereche
  (s, a). Atunci media incrementala converge la valoarea adevarata.
- Explorare insuficienta. Cu epsilon prea mic (sau 0), unele perechi (s, a) nu sunt
  vizitate niciodata; Q ramane gresit acolo si politica e suboptima. epsilon-greedy
  cu epsilon > 0 garanteaza vizitarea tuturor actiunilor -- conditia de convergenta.
- A confunda iteratia pe valoare cu Q-learning. Prima CUNOASTE P si R (referinta);
  a doua invata din esantioane fara model. A le compara e validare, nu acelasi lucru.
- gamma prost calibrat. gamma prea mic face agentul miop -- nu mai "vede" recompensa
  intarziata (a comuta proactiv inainte de o cadere de link), deci alege gresit.
- Recompensa prost proiectata. Agentul optimizeaza EXACT ce ii dai ca recompensa.
  O recompensa care nu reflecta valoarea reala a misiunii produce o politica
  "corecta" pentru obiectivul gresit.

## 11. De ce conteaza pentru teza (contributia C3)

ASTA E PUNTEA catre contributia C3 a tezei: comutarea adaptiva QoS/middleware ca
proces de decizie Markov. Pana acum (C1, selectorul link-aware) am ales
middleware-ul ca o decizie de un pas, statica per conditie: masoara conditia,
alege DDS sau Zenoh dupa o regula invatata sau o referinta (always-CycloneDDS).
Asta e o politica fara MEMORIE si fara ANTICIPARE.

MDP-ul ridica problema la decizie SECVENTIALA. Starea e conditia linkului (din
taxonomia C1: GOOD / DEGRADED / BAD, generalizabila la conditiile reale de
campanie); actiunile sunt middleware-urile (DDS / Zenoh, extensibil la setari de
QoS -- best-effort vs reliable, adancime de coada); recompensa e o VALOARE DE
MISIUNE (telemetrie livrata la timp, deadline-uri respectate, penalizare la cadere).
Doua lucruri noi fata de selectorul de un pas:
- tranzitiile P leaga deciziile in timp: alegerea de acum influenteaza in ce stare
  ajungi, deci ce decizii vei putea lua dupa (a comuta proactiv pe Zenoh INAINTE ca
  degradarea sa devina cadere);
- discount-ul gamma face agentul sa optimizeze valoarea pe TERMEN LUNG a misiunii,
  nu doar RTT-ul intervalului curent.

Concluzia onesta a lui C3, in continuarea concluziei lui C1 (un selector invatat isi
merita locul doar cand dropul e foarte scump -- D mare): un controler MDP merita
complexitatea doar daca dinamica temporala (tranzitii ne-triviale intre conditii)
si recompensele intarziate exista cu adevarat in date. Daca conditiile sunt
cvasi-statice pe orizontul deciziei, MDP-ul colapseaza inapoi la selectorul de un
pas. MDP-ul din acest modul este un MODEL SINTETIC care pune in scena ipoteza C3;
validarea ei cere un MDP estimat din date HIL (tranzitii si recompense masurate),
NU presupuse -- exact disciplina pe care campaniile mele o cer.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa scrii tuplul (S, A, P, R, gamma) al unui MDP si sa explici fiecare termen;
- [ ] sa scrii ecuatia Bellman de optimalitate si sa derivi din ea actualizarea Q-learning;
- [ ] sa faci de mana o actualizare Q pe un MDP cu 2 stari (ca in sectiunea 8);
- [ ] sa explici de ce epsilon-greedy cu epsilon > 0 e necesar pentru convergenta;
- [ ] sa distingi iteratia pe valoare (cu model) de Q-learning (model-free);
- [ ] sa argumentezi de ce comutarea QoS/middleware e o decizie SECVENTIALA (C3).

## Mergi mai departe

Sutton & Barto, Reinforcement Learning: An Introduction (editia 2), cap. 3 (MDP),
cap. 4 (programare dinamica / iteratie pe valoare), cap. 6 (TD si Q-learning).
Vezi BIBLIOGRAFIE.md.
