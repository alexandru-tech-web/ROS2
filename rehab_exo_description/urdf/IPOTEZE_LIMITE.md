# Impartirea min/max a curselor articulare -- IPOTEZE LOCALE (GAP 4)

Documentul tehnic [PDF Tabel 3.1, p.10-11] da CURSELE TOTALE, nu impartirea lor fata
de zero: sold 90 grade, genunchi 140 grade, glezna 70 grade. Impartirea min/max NU
exista in document (GAP 4 din SPEC_LLR_twin_din_PDF.md). Valorile de mai jos sunt
IPOTEZE, alese cu motiv si etichetate ca atare. Sunt PARAMETRI xacro: se schimba fara
sa se atinga structura, iar suma lor e asertata egala cu cursa documentata.

## Conventia

Zero ANATOMIC, plan sagital (decizia B din registrul de pe 18 aug):
- sold: 0 = coapsa colineara cu trunchiul; POZITIV = flexie
- genunchi: 0 = gamba colineara cu coapsa (extensie completa); POZITIV = flexie
- glezna: 0 = talpa perpendiculara pe gamba; POZITIV = dorsiflexie

## Ipotezele

| articulatie | ipoteza | cursa | rationament |
|---|---|---|---|
| sold (culcat) | 0 .. +90 | 90 | Cele doua posturi documentate ale dispozitivului sunt exact capetele: culcat drept = 0, sezut = 90 de flexie. Ipoteza nu are nevoie de nicio cifra in plus fata de document. |
| sold (sezut) | +25 .. +90 | 65 | In sezut, inelul de oprire (reper 208, PDF p.7) reduce MECANIC cursa. Cifra de 65 e capatul de jos al benzii 65-80 citate in literatura LLR-Ro pentru restrictia de sezut; alegerea capatului de jos e conservatoare. NU e in document. |
| genunchi | 0 .. +140 | 140 | Conventia clinica standard: zero la extensie completa, flexia pozitiva. Nu se presupune hiperextensie, care ar cere justificare separata. |
| glezna | -35 .. +35 | 70 | Impartire SIMETRICA. Alternativa clinica ar fi -50 plantar / +20 dorsi (tot 70), dar dispozitivul e o masina cu opritoare, iar modelul mostenit folosea deja o impartire simetrica (+-34.38 grade, adica 68.75 total, evident derivata din cei 70 documentati). Simetria e ipoteza cu cele mai putine presupuneri in plus. |

## BANDA DE POSTURA SEZUT, re-justificata 22 aug 2026 (nu convertita)

Banda transportata mecanic din conventia veche (minus 65 pana la 0 in B-prim) e
MOARTA: cadea integral sub coapsa orizontala, adica in jumatatea in care piciorul
trece prin podea. Ce urmeaza e construit de la zero, in termeni B-prim.

### Sursa 1 -- FORMA benzii. FAPT plus o presupunere NUMITA.

[PDF p.7], verbatim: *"In sitting position, the motion space of the hip joint is
small. By making the third electric push rod 210, the stop ring 208 is extended from
the position ring 201, so that the motion range of the hip positioning block 204
between the position ring 201 and the stop ring 208 is reduced."*

Ce e FAPT: blocul 204 se misca INTRE doua inele, iar extinderea lui 208 REDUCE cursa.
Deci banda de sezut e o SUBMULTIME a cursei complete, care pastreaza un capat.

Ce e PRESUPUNERE, si se scrie ca atare: textul NU spune care capat se pastreaza. Se
presupune ca repausul (B-prim zero, coapsa orizontala) apartine benzii de antrenament
in sezut -- altfel dispozitivul n-ar putea antrena in chiar postura in care sta.
De aici forma `0 .. X`, cu X sub 90. **Pozitiile celor doua proximity-uri rastoarna
sau confirma presupunerea asta la prima vizita.**

### Sursa 2 -- CAPATUL DE SUS. Argument ANTROPO.

Argumentul geometric pe care il banuisem -- ca perna scaunului ar bloca coborarea
coapsei sub orizontala -- e INFIRMAT prin masurare: perna se termina exact la axa
soldului, coapsa pleaca inainte pe langa ea, si nici la minus 30 de grade nu exista
contact. Se consemneaza ca respins ca sa nu fie reinventat.

Ce margineste efectiv:
  in JOS, invariantul podelei, adica chiar argumentul deciziei D1; el e cel care
         face ca banda sa nu poata cobori sub zero;
  in SUS, interferenta coapsa-trunchi. La spatar vertical, coapsa ridicata intra in
         abdomen. **X = 25 grade** mecanic inseamna circa 115 grade de flexie
         anatomica, marginea conservatoare pentru populatia de reabilitare.

### Sursa 3 -- banda 65-80 din literatura LLR-Ro: NEUTILIZABILA.

Citata aici ca sa nu fie recuperata din greseala mai tarziu. Trei motive:
cifra de 65 e o LATIME, nu o pozitie (venea din 90 minus 25 al ipotezei vechi);
o latime de 65-80 dintr-un total de 90 nu e o reducere, deci contrazice
"the motion space is small" din document; iar sursa e "literatura LLR-Ro" fara nicio
referinta verificabila in repo. Nu se foloseste.

### Valoarea

`sold_sezut_min_deg = 0`, `sold_sezut_max_deg = 25`, clasa **IPOTEZA-ANTROPO**.

### Ipoteza CONCURENTA, consemnata si nefolosita

URDF-ul livrat initial avea soldul la -25.78 .. +40.11 grade fata de un zero declarat
"SEZUT". Valorile n-au nicio sursa in document si de aceea nu se folosesc. Dar daca
autorul lor cunostea dispozitivul fizic, ele sugereaza o banda reala care coboara
usor sub orizontala si urca spre 40 de grade, nu spre 25. E o alternativa plauzibila
la ce am ales, si o las scrisa: proximity-urile transeaza intre cele doua.

## POSTSCRIPTUM, 22 aug 2026: ipoteza "culcat" a MURIT pe geometrie

Ipoteza de la randul "sold (culcat)" era cea mai curata din tot GAP 4: capetele
ferestrei erau chiar cele doua posturi documentate ale dispozitivului, deci nu avea
nevoie de nicio cifra inventata in plus. Tocmai ea s-a dovedit imposibila.

Flip-ul de conventie (DECIZII.md, D1) a dat o mapare derivata din FK: se scad 90 de
grade la sold. Transportata mecanic prin ea, fereastra 0..90 anatomic devine
**-90..0 mecanic**, adica INTEGRAL sub coapsa orizontala. Iar sub orizontala piciorul
trece prin podea, pentru orice lungime din intervalul de reglaj. Deci ipoteza nu era
doar nesigura: plasa toata cursa in jumatatea geometric imposibila.

Ce se invata din asta, si e mai important decat cifra: o provenienta buna NU e o
verificare. Rationamentul "capetele = posturile documentate" era corect ca
rationament si fals ca rezultat, fiindca nu fusese confruntat niciodata cu geometria.
Confruntarea exista acum ca test permanent, `test/test_podea.py`.

CONSECINTA PENTRU PUNCTUL 5. Nu doar banda de SEZUT se rejustifica. Se rejustifica
**ambele**, in termeni B-prim, si se rescrie rationamentul, nu doar cifrele: argumentul
"capetele = posturile" nu se transporta, fiindca a fost aratat gresit. Ce ramane
valabil e latimea de 90 de grade, care e documentata [PDF Tabel 3.1].

## Ce ar confirma sau infirma

- masurare pe dispozitivul fizic: unghiul la fiecare opritor mecanic, in ambele posturi;
- CAD sau desenele cotate (Fig 2.2-2.9), din care cotele nu sunt extractibile ca text;
- pozitia inelului 208 in cele doua stari, care fixeaza direct cursa de sezut.

Pana atunci: ipoteze, nu fapte.

## Consecinta care NU e ipoteza

Traiectoriile de exercitii ale soldului au fost RE-DERIVATE, nu convertite.

Formularea precisa conteaza, fiindca prima varianta a acestui paragraf era un
OVERCLAIM. Masurat pe cele 636 de valori de sold din exercitiile vechi, exprimate in
conventia anatomica:
  limitele vechi   64.22 .. 130.11 grade  (span 65.89)
  punctele reale   90.00 .. 124.38 grade  (span 34.38)
Punctele INCAP intr-o fereastra de 90 de grade -- spanul lor e doar 34.38. Ce NU
exista e o fereastra de 90 de grade ANCORATA ANATOMIC care sa le contina: cu zero la
culcat drept si cursa documentata de 90, fereastra e 0..90, iar punctele urca la
124.38. Ancorarea nu e libera: e fixata de zeroul anatomic (decizia B) impreuna cu
cele doua posturi documentate ale dispozitivului, care sunt chiar capetele intervalului.

Cu alte cuvinte, exercitiile vechi erau miscari PORNITE DIN SEZUT (punctul de minim e
exact 90.00 grade, adica vechiul zero) care ridicau coapsa cu inca pana la 34.38 grade
peste sezut. Sub cursa documentata, ancorata anatomic, nu exista loc peste 90.
Limitele vechi erau placeholdere fara sursa; documentul are prioritate. Punctele pastreaza FRACTIA
din cursa disponibila (forma exercitiului), nu unghiul fizic absolut -- vezi
test/test_traiectorii.py, care verifica exact asta si separa cele doua invariante.
