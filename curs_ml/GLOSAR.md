# GLOSAR.md -- termeni ML, EN -> RO

O definitie scurta per termen. Referentiat din `teorie.md` (sectiunea Vocabular
cheie). Se completeaza pe masura ce sunt construite modulele.

| EN | RO | Definitie scurta |
|----|----|------------------|
| feature | trasatura / caracteristica | variabila de intrare folosita de model |
| label / target | eticheta / tinta | variabila de iesire pe care o prezice modelul |
| supervised learning | invatare supervizata | invatare din perechi (intrare, eticheta) |
| unsupervised learning | invatare nesupervizata | invatare din date fara eticheta |
| training set | set de antrenare | datele pe care modelul isi invata parametrii |
| validation set | set de validare | date pentru a alege model / hiperparametri |
| test set | set de test | date tinute deoparte, raportate o singura data |
| loss function | functie de pierdere | masura a erorii pe care optimizarea o minimizeaza |
| empirical risk | risc empiric | pierderea medie pe datele observate (ERM) |
| overfitting | supra-invatare | modelul memoreaza zgomotul; merge slab pe date noi |
| underfitting | sub-invatare | modelul prea simplu; rateaza structura reala |
| bias-variance | bias-varianta | descompunerea erorii in eroare sistematica + sensibilitate |
| regularization | regularizare | penalizare a complexitatii pentru a reduce supra-invatarea |
| gradient descent | coborare pe gradient | optimizare iterativa in directia -gradient |
| learning rate | rata de invatare | marimea pasului in coborarea pe gradient |
| cross-validation | validare incrucisata | estimare a performantei prin k falduri |
| data leakage | scurgere de date | informatie din test/viitor ajunge in antrenare |
| confusion matrix | matrice de confuzie | tabel TN/FP/FN/TP pentru clasificare |
| precision | precizie | TP / (TP + FP) |
| recall | recall / sensibilitate | TP / (TP + FN) |
| calibration | calibrare | probabilitatile prezise reflecta frecvente reale |
| ensemble | ensemblu | combinatie de modele (bagging, boosting) |
| clustering | grupare | partitionare nesupervizata in grupuri |
| dimensionality reduction | reducerea dimensionalitatii | proiectie in spatiu mai mic (PCA) |
| uncertainty quantification | cuantificarea incertitudinii | bare de eroare / intervale pe predictii |
| hyperparameter | hiperparametru | setare aleasa inainte de antrenare (ex: lambda) |
| Markov decision process | proces decizional Markov | cadru stare-actiune-recompensa pentru RL |
| Q-learning | Q-learning | invatare a valorilor actiune-stare prin Bellman |
