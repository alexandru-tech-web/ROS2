# Manual tehnic actualizat — twin-ul LLR

## 1. Sursa si limita documentarii

Sursa primara furnizata este `Technical documents.pdf`, SHA-256:

```text
a889058d3eb118301b9e3011e3ede8f049d34bfe8bda2a0a0c822429fe7b8f23
```

Documentul contine trei echipamente diferite: LLR (robot membre inferioare), LTE
(trainer pentru varstnici) si FRR (degete). Pachetul modeleaza **LLR**. Informatiile
LTE/FRR nu se transfera automat la LLR.

## 2. Arhitectura fizica descrisa

LLR are doua picioare mecanice simetrice. Fiecare are trei axe actionate — sold,
genunchi, glezna — si reglaje de lungime. Documentatia mai descrie scaun mobil,
limitari mecanice si senzori de proximitate.

| Subsistem | Documentul LLR | Reprezentarea curenta |
|---|---|---|
| sold | SMP8024B, ACP-055-40, SHG-40-100-2UH | articulatie actionata Gazebo |
| genunchi | SMP8024B, ACP-055-40, SHG-32-100-2UH | articulatie actionata Gazebo |
| glezna | TBM60-25/TBM6025, ADP-090-40, SHG-20-100-2UH | articulatie actionata Gazebo |
| reglaj coapsa/gamba | actuatoare liniare; rigla 406 la gamba | articulatii prismatice |
| scaun | coloane/actuator de pozitionare | axa prismatica simplificata |

Raporturile documentate in Tabelul 3.1 sunt 2700:11 la sold, 2160:11 la
genunchi si 100 la glezna; cursele declarate sunt 90°, 140° si 70°. Aceste cifre
sunt folosite de modulele de transmisie si de limite, cu ipotezele separate in
`IPOTEZE.md` si `urdf/IPOTEZE_LIMITE.md`.

## 3. Ce senzori exista de fapt in LLR

| Marime fizica | Dispozitiv in PDF | Numar logic | Topic in twin | Stare |
|---|---|---:|---|---|
| unghi sold/genunchi | encoder absolut RS485-RTU | 4 | `/joint_states` | SIM Gazebo |
| unghi glezna | BWK216 | 2 | `/rehab/unghi_glezna/{left,right}` | sintetic |
| cuplu sold/genunchi | M2210B SRI | 4 | `/rehab/cuplu/<parte>_<axa>` | sintetic |
| interactiune la talpa | TR69-1500 TAIER | 2 | `/rehab/forta_6d/<parte>` | sintetic |
| lungime gamba | rigla electronica 406 | 2 | `/rehab/rigla_gamba/<parte>` | sintetic |
| proximitati/limite | intrari digitale PCI2321 | de verificat | supervizor software | modelat partial |

Pentru TR69-1500, documentul numeste explicit trei marimi utile in planul sagital:
`Ff` paralel cu pedala, `FN` normal pe pedala si `MC` moment sagital. Twin-ul le
mapeaza pe `force.x`, `force.z`, respectiv `torque.y`. Celelalte componente sunt
`NaN`, nu zero, deoarece documentatia nu le defineste.

**Corectie importanta:** senzorul/encoderul liniar care urmareste deplasarea
pedalei este descris la LTE. La LLR, sub talpa este senzorul 6D, iar rigla liniara
406 masoara reglajul lungimii gambei.

## 4. Control si pornire fara salt

Controlerul de exercitii nu foloseste un timp fix de asteptare. Cu timpul simulat,
primul mesaj `/clock` poate sari direct la cateva secunde. De aceea, prima
traiectorie este blocata pana cand:

1. au fost receptionate pozitii pentru toate cele sase axe actionate;
2. versiunea conventiei cinematice din URDF coincide cu cea a traiectoriilor.

Traiectoria se construieste apoi din pozitia masurata, nu din sase zerouri
implicite. Aceasta bariera este o proprietate de siguranta, nu un delay cosmetic.

## 5. Moduri de reabilitare

PDF-ul mentioneaza modurile pasiv, asistiv si activ, dar nu ofera in capitolul de
control un algoritm suficient pentru a le reproduce. Statusul onest este:

- **pasiv:** implementat ca urmarire de traiectorie de pozitie;
- **asistiv:** neimplementat; necesita estimarea intentiei/efortului pacientului;
- **activ/rezistiv:** neimplementat; necesita control de cuplu/impedanta si limite
  validate pe hardware.

HMI-ul nu prezinta ultimele doua ca functii disponibile. Introducerea lor trebuie
sa porneasca de la semnalele fizice validate si de la un protocol aprobat clinic.

## 6. Exercitii si serii disponibile

Exista 12 miscari demonstrative: cate trei pentru glezna, genunchi si sold si trei
coordonate. Patru serii le inlantuie pe grupe. Interpolarea cosinus are viteza zero
la capete, fiecare program porneste din starea curenta, iar limitele/vitezele sunt
verificate in nucleul pur `exercise_core.py`.

Acestea sunt stimuli pentru verificarea platformei si achizitiei, nu protocoale
terapeutice validate.

## 7. Achizitie si trasabilitate

`inregistrator_sesiune_reabilitare.py` porneste cu lansarea C4 si scrie:

- timestamp simulat si Unix;
- pozitie, viteza, efort Gazebo si referinta pentru cele sase axe;
- cele patru cupluri sintetice M2210B;
- forta/moment la ambele talpi;
- doua unghiuri de glezna si doua rigle de gamba;
- metadate: commit, conventie, exercitiu, postura, viteza si provenienta;
- evenimentele supervizorului si contoare de calitate la inchidere.

Director implicit: `~/DATE_TWIN/<timestamp>_<exercitiu>/sesiune.csv`.

### Figuri si raport reproductibil

Pentru figurile brute, cu titlu generat din metadatele CSV:

```bash
/usr/bin/python3 scripts/plot_sesiune.py ~/DATE_TWIN/<director_sesiune>/
```

Pentru raportul tehnic complet:

```bash
/usr/bin/python3 scripts/session_report.py ~/DATE_TWIN/<director_sesiune>/
```

Se genereaza `raport_sesiune.pdf`, `raport_sesiune.md`,
`metrici_sesiune.csv` si `metrici_sesiune.json`. Indicatorii includ ROM,
eroarea de urmarire pe intervalul activ, viteza maxima, efortul Gazebo si
simetria stanga-dreapta. Raportul pastreaza eticheta de provenienta: efortul
Gazebo nu este numit cuplu fizic, iar senzorii sintetici nu sunt prezentati ca
masuratori.

Modelul vizual arata schematic M2210B, BWK216, TR69-1500 si rigla 406 prin
culori distincte. Aceste repere nu au coliziune sau inertie si nu reprezinta
geometrie CAD cotata; rolul lor este sa faca arhitectura documentata lizibila.

## 8. Ce trebuie verificat inainte de sistemul real

1. mase, centre de masa si inertii;
2. zero-uri, semne si rapoarte reale pentru fiecare axa;
3. pinout, scalare si rata pentru M2210B, TR69-1500, BWK216 si encodere;
4. topologia completa PCI/RS485/CAN si configuratia driverelor Copley;
5. limite mecanice si electrice, proximitati, frane, STO si E-stop;
6. fidelitatea cuplului observat fata de cuplul fizic independent;
7. evaluare de risc si aprobare clinica inainte de orice interactiune umana.

## 9. Provenienta afirmatiilor din PDF

- structura membrului si cuplurile: capitolul 2, paginile tiparite 5–9;
- achizitie, rapoarte, curse, forta la talpa si drive-uri: capitolul 3,
  paginile tiparite 10–13;
- lista exacta de componente LLR: Tabelul 6.1, pagina tiparita 23;
- LTE incepe la capitolul 5 si nu este sursa pentru arhitectura LLR.
