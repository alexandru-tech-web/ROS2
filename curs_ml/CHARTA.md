# CHARTA.md -- charter pedagogic curs_ml

## Obiective generale

La finalul cursului, cititorul poate:
- sa explice si sa derive (nu doar sa enunte) modelele clasice de ML, de la
  regresie liniara la ensembluri, incertitudine si o introducere in RL;
- sa implementeze fiecare model de la zero in numpy si sa il valideze incrucisat
  cu scikit-learn;
- sa evalueze corect la N mic (validare incrucisata, regularizare, incertitudine);
- sa impacheteze un model intr-un nod ROS 2 consumabil de restul sistemului.

## Prerechizite

- Programare Python (functii, clase, numpy de baza).
- Matematica de liceu solida; calcul diferential elementar (derivate partiale).
  M00-M02 reimprospata algebra liniara, probabilitatile si optimizarea de care
  e nevoie -- cursul e auto-suficient.

## Nivel si stil

Master/doctorat. Derivari complete cu notatie consecventa (definita in M00-M03).
Fiecare modul are un exemplu lucrat numeric (un caz mic, calculat de mana) ca
cititorul sa verifice ce face codul -- elementul didactic central.

## Evaluare (autoevaluare)

Fiecare modul se incheie cu:
- un checklist 'bifeaza daca poti...' (4-6 itemi de stapanire);
- `exercitii.md` + `exercitii.py`: 4-6 exercitii gradate cu asserturi care pica
  pana sunt rezolvate; solutiile complete in `solutii.py`.

Proiectele de sinteza (`PROIECTE_SINTEZA.md`) sunt evaluarea integratoare: patru
mini-proiecte pe datele reale ale tezei, fiecare cu livrabil si interpretare scrisa.

## Sablonul fiecarui modul (mXX_*)

Fisiere (7-9 per modul):
- `teorie.md` -- predare auto-suficienta, structura fixa (vezi mai jos);
- `<topic>_core.py` -- implementare PURA from-scratch (numpy permis, scikit-learn
  INTERZIS), docstring matematic, `_selftest()` care verifica corectitudinea pe un
  caz cunoscut (ex: solutie analitica vs gradient; gradient verificat cu diferente
  finite), tipareste PASS/FAIL, `sys.exit(0/1)`;
- `<topic>_sklearn.py` -- aceeasi sarcina cu biblioteca, pentru VALIDARE
  incrucisata (acelasi rezultat sub o toleranta);
- `demo_sil.py` -- demonstratie headless pe datele mele (`date_sar`), fara
  argumente; daca matplotlib exista emite `fig_*.png`, altfel tipareste numeric;
- `exercitii.md` + `exercitii.py` -- exercitii gradate cu stub-uri TODO;
- `solutii.py` -- solutiile complete, separate;
- `README.md` -- rezumat scurt al modulului.

Structura fixa a lui `teorie.md`:
1. Antet pedagogic: obiective de invatare (3-5 verbe actionabile), prerechizite,
   timp si dificultate (1-3), vocabular cheie (5-12 termeni, cu trimitere la GLOSAR).
2. Corp: intuitie; formalizare; derivare pas cu pas (ASCII-LaTeX inline);
   algoritm (pseudocod); EXEMPLU LUCRAT NUMERIC (obligatoriu); vizualizare
   (referinta la figura din demo_sil); capcane; de ce conteaza pentru teza.
3. Inchidere: checklist de stapanire; trimiteri la BIBLIOGRAFIE pentru aprofundare.

## Reguli de calitate (vezi si PRINCIPII_TRANSVERSALE.md)

- ASCII 100% in tot ce se genereaza (cod, .md, .sh).
- Determinism: orice aleator prin `numpy.random.default_rng(seed)`.
- DRY: codul comun (split, standardizare, metrici, plot, seeding) sta in `utils.py`.
- Onestitate: datele sunt sintetice, semanate din C1/M -- marcat in fiecare loc.
