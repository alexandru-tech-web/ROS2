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

Traiectoriile de exercitii ale soldului au fost RE-DERIVATE, nu convertite. Cursa
veche a soldului, exprimata in conventia anatomica, era 64.22 .. 130.11 grade: sold
permanent flectat, pana peste flexia umana normala (~120-125). Nicio fereastra de 90
de grade nu o contine, deci nicio impartire min/max nu ar fi salvat-o. Limitele vechi
erau placeholdere fara sursa; documentul are prioritate. Punctele pastreaza FRACTIA
din cursa disponibila (forma exercitiului), nu unghiul fizic absolut -- vezi
test/test_traiectorii.py, care verifica exact asta si separa cele doua invariante.
