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
