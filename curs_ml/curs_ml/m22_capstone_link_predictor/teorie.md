# M22 -- CAPSTONE: Predictor de stare a linkului ca nod ROS 2

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa antrenezi OFFLINE un predictor binar de 'usable' din feature-uri de link;
- sa salvezi si sa incarci modelul astfel incat inferenta sa fie reproductibila;
- sa impachetezi modelul intr-un nod ROS 2 subtire care publica o decizie JSON;
- sa explici de ce o politica adaptiva (comuta dupa predictie) bate una statica;
- sa argumentezi cum inchide acest modul cursul inapoi in teza (contributia C3).

Prerechizite: M05 (regresie liniara), M08 (regresie logistica -- modelul reutilizat
aici), M13 (ensembluri, ca alternativa de model), si notiuni de ROS 2 (noduri,
topicuri, std_msgs/String). Timp estimat: 3-4 h. Dificultate: 3/3 (modul de sinteza).

Vocabular cheie (vezi GLOSAR.md): predictor de link, feature de fereastra, eticheta
'usable', antrenare offline, serializare model (.npz), nod ROS subtire, core pur,
politica adaptiva vs statica, histerezis (vezi C3), inferenta fara scurgere.

## 1. Intuitie

Tot cursul a construit modele in numpy si le-a validat. Acesta e capatul firului:
un model nu valoreaza nimic intr-un notebook daca sistemul real nu il poate folosi.
CAPSTONE-ul ia un predictor SIMPLU (regresie logistica din M08), il antreneaza o
data pe date de link, il INGHEATA intr-un fisier, si il pune intr-un nod ROS 2 care
asculta feature-uri proaspete si publica o predictie. Stratul adaptiv al tezei
(link_adaptive, C3) consuma acea predictie ca sa decida cum sa trimita telemetria.

Intuitia de control: daca stii din timp ca linkul devine inutilizabil, COMUTI pe un
mod de rezerva (rata mica, fara blocaj) inainte sa se blocheze bucla de teleoperatie.
Un predictor bun transforma o reactie tarzie intr-o anticipare.

## 2. Formalizare

Fereastra de link: un vector de feature-uri x rezumat pe un interval scurt:
  x = (p95_ms, loss_frac, jitter_ms, base_lat_ms, mw_zenoh, distance_m).
Eticheta: y = 'usable' in {0, 1}; y = 1 daca fereastra suporta teleoperatie in timp
real. In datele sintetice (date_sar.make_link_usability_dataset) regula generatoare e
  usable = 1  <=>  p95 < lat_thresh_ms (300 ms)  SI  loss < loss_thresh (0.05),
motivata in M08/M09 (peste ~300 ms RTT bucla de teleoperatie se degradeaza). Clasele
ies DEZECHILIBRATE (usable minoritar, ~30%) -- exact cazul real al degradarii.

Modelul: probabilitatea prezisa
  P(usable=1 | x) = sigmoid(w^T x_std + b),
unde x_std e x standardizat cu media/abaterea invatate pe TRAIN. Greutatile w, b se
gasesc prin coborare pe gradientul log-loss-ului (M08). Eticheta prezisa aplica un
prag: usable = 1 daca P >= 0.5.

## 3. Antrenare OFFLINE si serializare

OFFLINE inseamna: in afara ROS, in venv-ul de ML, o singura data. Pasii:
1. construieste (X, y) din dataset; imparte train/test (sau LOCO, vezi M07);
2. standardizeaza pe TRAIN, memoreaza (mean, std) IN model (nu doar pentru antrenare);
3. coboara pe gradient pana converge log-loss-ul;
4. SALVEAZA intr-un .npz: w, mean, std, ordinea feature-urilor, pragul.

De ce memoram (mean, std) si ordinea feature-urilor in fisier: la inferenta nodul
ROS primeste feature-uri BRUTE; trebuie sa le standardizeze cu EXACT statisticile de
la antrenare (altfel scurgere/incompatibilitate) si sa le aseze in EXACT ordinea pe
care a vazut-o w. load() reconstruieste un model care da predictii identice cu
originalul -- proprietate verificata in _selftest (save->load bit-identic).

## 4. Nodul ROS subtire (impachetarea)

Regula de fier a tezei (CLAUDE.md sec.2): core pur + _selftest -> nod ROS subtire.
Nodul link_predictor_node NU contine matematica de invatare; el doar:
- la __init__ face sys.path.insert(0, dirname(__file__)) si importa nucleul, apoi
  INCARCA modelul .npz (sau il antreneaza pe loc daca lipseste, si il salveaza);
- se aboneaza la <features_topic> (std_msgs/String cu JSON {p95_ms, loss_frac, ...});
- la fiecare mesaj cheama model.predict(feats) si PUBLICA pe /link_predictor/state
  un JSON {usable: bool, prob: float, label: int}.

JSON pe std_msgs/String, ca tot depozitul -- nodul expune o DECIZIE curata, exact ca
link_adaptive_node expune o politica. Asa, predictorul devine o piesa Lego in graful
ROS: link_adaptive il poate asculta si folosi predictia in controlerul lui.

Flux:
```
[masuratori de link] --JSON--> /link/features
                                     |
                          link_predictor_node (incarca .npz, predict)
                                     |
                                     v
                    /link_predictor/state  {usable, prob, label}
                                     |
                              link_adaptive_node (C3) --> politica de trimitere
```

## 5. Exemplu lucrat numeric (verifica-l de mana)

Doua feature-uri singure (p95_ms, loss_frac), model deja antrenat, greutati alese
pe datele standardizate. Presupune ca pe TRAIN: p95 are mean=900, std=1100; loss are
mean=0.10, std=0.13. Greutati invatate (in spatiul standardizat): b = 0.0,
w_p95 = -3.0, w_loss = -3.0 (ambele negative: p95 mare sau pierdere mare scad sansa
de 'usable').

Fereastra A (link bun): p95 = 20 ms, loss = 0.0.
  z_p95 = (20 - 900) / 1100 = -0.80 ; z_loss = (0.0 - 0.10) / 0.13 = -0.77.
  logit = 0 + (-3.0)(-0.80) + (-3.0)(-0.77) = 2.40 + 2.31 = 4.71.
  P = sigmoid(4.71) = 1 / (1 + e^-4.71) = 0.991  ->  usable = 1.  (corect)

Fereastra B (link rau): p95 = 2300 ms, loss = 0.35.
  z_p95 = (2300 - 900) / 1100 = 1.27 ; z_loss = (0.35 - 0.10) / 0.13 = 1.92.
  logit = 0 + (-3.0)(1.27) + (-3.0)(1.92) = -3.81 - 5.77 = -9.58.
  P = sigmoid(-9.58) = 0.00007  ->  usable = 0.  (corect)

Predictorul anticipa: pe B comuta din timp pe modul de rezerva, evitand blocajul.

## 6. Vizualizare

`demo_sil.py` produce `fig_adaptiv_vs_static.png`: pe o cronologie de 240 ferestre
(cu o 'furtuna' de degradare la mijloc), suprapune linkul real inutilizabil cu
decizia predictorului (sus) si compara numarul de pasi blocati intre politica statica
si cea adaptiva (jos). Castigul tipic: ~90% din blocaje evitate prin comutare la timp.
Date SINTETICE.

## 7. Capcane frecvente

- A standardiza cu statistici noi la inferenta: scurgere/incompatibilitate. Memoreaza
  (mean, std) de la antrenare in fisierul de model si REFOLOSESTE-le.
- A schimba ordinea feature-urilor intre antrenare si nod: w se aplica pe pozitia
  gresita. De aceea ordinea (FEATURE_NAMES) e salvata si verificata.
- A pune matematica de invatare in nod: incalca regula core pur -> nod subtire; nu
  mai poti testa izolat. Toata invatarea sta in core, cu _selftest.
- A raporta acuratetea fara o baza: la clase dezechilibrate baza triviala (clasa
  majoritara) e deja mare; modelul trebuie sa o BATA cu marja (vezi M09).
- entry_point care intoarce truthy: main() trebuie sa intoarca None (CLAUDE.md sec.6),
  altfel `ros2 run` raporteaza 'failure 1' desi nodul a mers.

## 8. De ce conteaza pentru teza (inchide cursul in C3)

Contributia C3 (link_adaptive) e stratul care adapteaza trimiterea la starea retelei.
Pana acum decidea cu un controler cu praguri/histerezis pe metrici masurate. Acest
CAPSTONE arata cum un model ML, antrenat pe datele de campanie (aici SINTETICE,
calibrate pe C1/M), poate ALIMENTA aceeasi decizie: o predictie de 'usable' pe care
controlerul adaptiv o consuma. Astfel cursul de ML nu e un anex, ci se inchide
inapoi in coloana stiintifica a tezei: ML offline -> nod ROS subtire -> decizie de
control adaptiva, reproductibila si publicabila (NU production-grade).

Legatura cu M21 (MDP / Q-learning): acolo politica adaptiva e invatata ca solutie a
unui MDP (stare = conditie de link, actiune = mod de trimitere, recompensa = control
reusit minus cost). Aici facem versiunea PRAGMATICA: in loc sa rezolvam tot MDP-ul,
prezicem un singur bit de stare ('usable') si cuplam o regula simpla de comutare.
Predictorul + regula = o aproximare ieftina si testabila a politicii optime din M21,
suficienta pentru a bate politica statica -- exact compromisul pe care il cere o teza
cu buget mic (un singur track de cod activ, don't break the chain).

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa antrenezi un predictor de link offline si sa-i masori acuratetea fata de baza;
- [ ] sa explici de ce (mean, std) si ordinea feature-urilor trebuie salvate in model;
- [ ] sa descrii ce face nodul ROS subtire si pe ce topicuri lucreaza;
- [ ] sa argumentezi castigul politicii adaptive fata de cea statica;
- [ ] sa explici cum inchide acest modul cursul inapoi in C3 si cum se leaga de M21.

## Mergi mai departe

ESL cap. 4 (clasificare logistica), Sutton & Barto cap. 3-4 (MDP, legatura M21).
Pentru ROS: documentatia rclpy (noduri, publishers/subscribers). Vezi BIBLIOGRAFIE.md.
