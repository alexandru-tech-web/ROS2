# Pozitionarea PHSC in teza

## Decizie luata: Optiunea A -- contributie proprie

Decizia iti apartine si a fost luata. Ce urmeaza este lista conditiilor, cu
starea reala a fiecareia, plus doua rezerve pe care e mai bine sa le ai in
scris decat sa le descoperi la review.

## Starea conditiilor

| conditie | stare | nota |
|---|---|---|
| rezultate masurate, reproductibile | INDEPLINITA | ablatie, praguri, estimator, implementare ROS 2 care ruleaza la rata declarata |
| Monte Carlo cu N>=5 si bare de eroare | INDEPLINITA | N=50 incercari perechi, interval Wilson 95%, vezi `RESULTS.md` |
| originalitate fata de literatura | **NEVERIFICATA DE MINE** | vezi sec. 'Rezerva 1' |
| legatura explicita cu C1-C4 | DE ARTICULAT | vezi sec. 'Legatura cu C1' |
| articol submis inainte de teza | de facut | vezi `ARTICLE_DRAFT.md` |

## Rezerva 1: originalitatea se sprijina pe o cautare pe care nu am facut-o eu

Afirmatia 'ablatia si mecanismul nu apar in literatura' provine din cautarea
facuta de Kimi, nu dintr-una facuta si verificata de mine. Nu am acces la
rezultatele acelei cautari si nu am deschis niciuna dintre lucrarile citate.

Asta conteaza pentru ca **intreaga decizie 'contributie proprie vs
demonstrator' se sprijina pe acea singura afirmatie.** Daca se dovedeste
gresita la review, incadrarea articolului cade, nu si rezultatele.

Recomandare practica, inainte de submisie:
- verifica personal 5-10 lucrari, nu doar titlurile: in special pe
  robustetea predictorului Smith la nepotrivire si pe saturatie in
  predictoare, unde exista literatura consistenta
- cauta explicit formulari echivalente: 'prediction with incorrect input
  assumption', 'predictor mismatch destabilization', 'open-loop prediction
  in delay compensation'
- daca gasesti rezultatul deja publicat, **nu e o pierdere**: incadrarea se
  muta pe caracterizare cantitativa + implementare reproductibila, care
  raman publicabile

Referintele mentionate in cautare (Smith 1959, Artstein 1982, Krstic 2008,
Bekiaris-Liberis & Krstic 2013, Bresch-Pietri 2012, Anderson & Spong,
Niemeyer & Slotine, Tavakoli, Zheng et al., Hatori, Abubakar 2025, Lima
et al.) sunt reproduse aici **ca lista de verificat**, nu ca bibliografie
validata. Nu le-am citit si nu confirm ca exista in forma citata. Conform
CLAUDE.md sec. 0, nu le trec ca citari pana nu sunt verificate la sursa.

## Rezerva 2: nu exista validare pe hardware si nici operator uman

Titlul directiei contine 'Haptic Shared Control'. In stadiul actual:
- feedback-ul haptic este calculat si publicat, dar **nu a fost evaluat cu
  un dispozitiv haptic real si nici cu un operator uman**
- bucla de shared control este **deschisa**: `alpha` nu influenteaza planta
- nu exista validare pe robot

Un reviewer de la un venue de haptica sau teleoperare va observa asta
imediat. Doua variante oneste:
1. reincadreaza articolul ca fiind despre **compensarea latentei**, cu
   haptica mentionata ca lucru viitor -- titlul si abstractul se schimba
2. inchide bucla de shared control si adauga o evaluare, fie si simpla,
   inainte de submisie

Recomand varianta 1 pentru primul articol: e mai rapida si mai aparabila.

## Legatura cu C1-C4

PHSC nu apare in harta C1-C4 din CLAUDE.md. Puntea cea mai naturala este
**estimatorul de latenta catre C1**:

- C1 masoara RTT si pierderi sub degradare controlata (`netem`), comparand
  rmw_zenoh cu rmw_cyclonedds_cpp
- PHSC consuma exact acea marime: `tau` estimat online, cu sensibilitate
  masurata (+/-20% eroare injumatateste marja de stabilitate)

Formularea care leaga cele doua fara sa forteze:

> C1 caracterizeaza canalul; PHSC arata ce inseamna acea caracterizare
> pentru o bucla de control inchisa peste el. Sensibilitatea masurata a
> pragului de stabilitate la eroarea de estimare a latentei transforma
> metrica de retea din C1 intr-o cerinta de proiectare cuantificata.

Asta e o legatura reala, nu una cosmetica: cifra de +/-20% da un criteriu
concret pentru cat de bine trebuie sa masoare C1.

**Atentie la sec. 1 din CLAUDE.md**: 'un singur track de cod activ o data'.
PHSC ca al doilea track activ, in paralel cu C1/C3, contrazice acea regula.
Daca il promovezi la contributie proprie, merita decis explicit care track
se pune pe pauza.

## Ce recomand concret

1. Verifica personal originalitatea (jumatate de zi). Este singurul lucru
   care poate schimba incadrarea.
2. Reincadreaza primul articol pe compensarea latentei, nu pe haptica.
3. Articuleaza legatura cu C1 in introducere -- ii da articolului un context
   pe care un cart-pole singur nu il are.
4. Decide ce track se pune pe pauza cat timp PHSC e activ.
