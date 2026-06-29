# M07 -- Evaluare si validare

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici de ce eroarea pe setul de antrenare e optimista si cum o corectezi;
- sa implementezi k-fold si LOOCV si sa stii cand folosesti fiecare;
- sa raportezi corect RMSE/MAE/R2 cu o masura a variabilitatii;
- sa citesti o curba de invatare si o curba de validare (sub/supra-invatare).

Prerechizite: M05 (regresie), M03 (risc empiric vs real). Timp estimat: 2-3 h.
Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): set de antrenare/validare/test, k-fold, LOOCV,
RMSE, MAE, R2, curba de invatare, scurgere de date in CV, variabilitate.

## 1. Intuitie

Eroarea masurata pe aceleasi date pe care ai antrenat e prea optimista -- modelul
le-a vazut. Ne intereseaza eroarea pe date NOI. Validarea incrucisata simuleaza
'date noi' antrenand pe o parte si testand pe restul, rotind partile, ca sa
folosesti fiecare exemplu si la antrenare si la test (in falduri diferite).

## 2. Formalizare

- Split simplu: train (invata parametrii) / validare (alegi model/hiperparametri) /
  test (raportezi O SINGURA data).
- k-fold: imparte datele in k falduri ~egale; de k ori, antreneaza pe k-1 falduri si
  testeaza pe al k-lea; mediaza scorurile. Estimare cu varianta mai mica decat un
  singur split.
- LOOCV (leave-one-out): k = n. Aproape nepartinitor, dar costisitor (n potriviri) si
  cu varianta mare a estimarii. CRITIC la N mic: cu N=5, LOOCV foloseste 4 puncte la
  antrenare si 1 la test, de 5 ori.

Metrici de regresie:
- RMSE = sqrt( (1/n) sum (y_i - p_i)^2 )   (penalizeaza erorile mari)
- MAE  = (1/n) sum |y_i - p_i|             (robusta la outlieri)
- R2   = 1 - SS_res / SS_tot               (1 = perfect, 0 = cat media)

## 3. Capcana de scurgere in CV

Orice pas care INVATA din date (standardizare, imputare, selectie de feature) trebuie
facut INAUNTRUL fiecarui fald, doar pe partea de antrenare. Daca standardizezi pe tot
setul inainte de split, statisticile de test 'se scurg' in antrenare si scorul iese
prea bun. Regula: pipeline-ul intra in CV, nu invers.

La date corelate (repetitii ale aceleiasi conditii, ca in campaniile mele), split-ul
aleator scurge informatie intre falduri; foloseste leave-one-GROUP-out (vezi
selectorul C1, validare LOCO).

## 4. Algoritm (k-fold)

```
kfold(n, k): amesteca indicii (optional, seed); imparte in k blocuri
  pentru i = 1..k:
    test  = bloc_i ; train = restul
cross_val(X, y, fit_predict, k):
  pentru fiecare (train, test): pred = fit_predict(X[train], y[train], X[test])
                                scor_i = metric(y[test], pred)
  intoarce scorurile ; raporteaza media +/- abaterea
```

## 5. Exemplu lucrat numeric (verifica-l de mana)

(a) k-fold contiguu. n = 6, k = 3, fara amestecare. Indicii 0..5 se impart in
    blocuri: [0,1], [2,3], [4,5]. Faldul 1 testeaza {0,1} si antreneaza pe {2,3,4,5};
    faldul 2 testeaza {2,3}; faldul 3 testeaza {4,5}. Fiecare indice e testat EXACT
    o data; reuniunea testelor = {0,1,2,3,4,5}.

(b) LOOCV. n = 6 -> k = 6 falduri, fiecare cu un singur index de test.

(c) RMSE si MAE. y = [1, 2, 3], p = [1, 4, 3].
    erori: |1-1|=0, |2-4|=2, |3-3|=0.
    MAE  = (0 + 2 + 0) / 3 = 2/3 = 0.6667.
    RMSE = sqrt((0^2 + 2^2 + 0^2)/3) = sqrt(4/3) = 1.1547.
    RMSE > MAE: o singura eroare mare (2) e amplificata de patrat.

(Selftest-ul nucleului si exercitiile verifica exact aceste valori.)

## 6. Vizualizare

`demo_sil.py` produce `fig_curba_invatare.png`: RMSE de train si de validare vs
marimea setului de antrenare pe datele de latenta. Golul mare train-validare la
seturi mici = varianta (supra-invatare); convergenta celor doua = ai destule date.
Date SINTETICE.

## 7. Capcane frecvente

- A te uita la setul de TEST de mai multe ori: il transformi in set de validare si
  raportezi optimist. O singura privire, la final.
- Scurgere de preprocesare in CV (vezi sectiunea 3).
- A raporta o singura cifra fara variabilitate: media CV fara abatere ascunde
  instabilitatea (critic la N mic).
- LOOCV vazut ca 'mereu cel mai bun': are varianta mare a estimarii si e scump.

## 8. De ce conteaza pentru teza

Campaniile mele au N mic (C1: N=5). Aici raportarea corecta NU e optionala: media
CV cu interval, validare pe grupuri (LOCO) ca repetitiile sa nu se scurga, si
scepticism fata de imbunatatiri mici. Exact metodologia folosita la selectorul C1.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa explici de ce eroarea de train e optimista;
- [ ] sa construiesti falduri k-fold care acopera tot fara suprapunere;
- [ ] sa calculezi RMSE si MAE de mana pe un caz mic;
- [ ] sa identifici o scurgere de preprocesare intr-un pipeline de CV;
- [ ] sa citesti o curba de invatare (unde e supra-invatare).

## Mergi mai departe

ESL cap. 7, ISL cap. 5. Vezi BIBLIOGRAFIE.md.
