# Memoriu de fezabilitate — articolul SSRR (termen: joi 18.06)

## Verdict scurt: FEZABIL, cu conditii clare.

## Ce ai DEJA (in template, ~75% din articol)
- Abstract complet cu cifrele finale N=5.
- Introducere cu lacuna + 4 contributii formulate.
- Related Work cu 6 referinte reale pozitionate.
- Metoda completa: arhitectura (figura TikZ gata), microbenchmark, strat de
  misiune, conditii, ipoteze H1-H4 reformulate pe povestea N=5.
- Results: tabelul N=5 + 3 figuri de date existente + naratiunea
  "two failure modes" cu toate verdictele sustinute.
- Discussion cu threats oneste (i.i.d. loss, localhost, offset router, N=2
  spatial) — exact ce dezarmeaza recenzentul.
- Bibliografia .bib gata (VERIFICA fiecare intrare inainte de submisie).

## Ce ramane de facut (estimare: 8-10 ore in 5 zile = confortabil)
1. Captura Gazebo (30 min) — singura figura lipsa din cele 8 pagini.
2. Autorii + afilierea + acknowledgment (15 min, cu conducatorul).
3. Citire critica a Intro/Related si ajustare in vocea ta (2-3 h).
4. Compilare + incadrare in 8 pagini (1-2 h; template-ul e deja compact).
5. Verificarea fiecarei cifre contra campaign_summary.csv (1 h).
6. Buffer conducator/coautori (miercuri).

## Riscuri si atenuarea lor
- SIMULARE-ONLY: tratat explicit in Threats + Future Work (testbed real) —
  acceptabil la SSRR, care valorizeaza relevanta operationala.
- N=2 pe stratul spatial: mentionat ca atare, o singura propozitie de
  sustinere, nu claim principal.
- Diagnosticul RTL/radio inca deschis: propozitia spatiala din Results e
  formulata prudent; daca diagnosticul arata ca degradarea spatiala nu s-a
  aplicat, se sterge O propozitie, restul articolului nu depinde de ea.
- Bibliografia: intrarile sunt reale dupa cunostintele mele, dar verifica
  titlurile/anii pe Google Scholar inainte de submisie (15 min).

## Decizia recomandata
Mergi. Povestea N=5 ("doua filozofii, esecuri diferite, compresie") e mai
puternica si mai credibila decat cea de la N=2. Daca vineri seara tabelul
compileaza si sambata intra captura Gazebo, restul e slefuire.
