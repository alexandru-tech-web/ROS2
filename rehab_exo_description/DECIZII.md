# Registrul DECIZIILOR de proiectare -- rehab_exo_description

Deciziile care nu se pot deduce din cod si care, odata luate, constrang tot ce vine
dupa. Fiecare are data, cine a decis, dovada pe care s-a sprijinit si STATUTUL acelei
dovezi. Ipotezele numerice stau separat, in `IPOTEZE.md`.

---

## D1 (22 aug 2026, decizie a lui Alexandru) -- Conventia articulara B'

**Ce s-a decis.** Zeroul articular este ZEROUL MECANIC AL DISPOZITIVULUI:

| articulatie | zero | pozitiv |
|---|---|---|
| sold | coapsa ORIZONTALA (postura de lucru, sezut) | RIDICAREA coapsei |
| genunchi | gamba in prelungirea coapsei | flexie |
| glezna | talpa perpendiculara pe gamba | dorsiflexie |

Intentia conventiei B de la M1 -- comparabilitatea cu literatura clinica -- NU se
pierde: se pastreaza printr-o mapare anatomica documentata, exprimata **ca functie de
starea spatarului**. Pe un dispozitiv cu spatar mobil unghiul anatomic de sold nu e
definit fara starea scaunului, deci o singura constanta de conversie ar fi fost
gresita indiferent ce valoare i s-ar fi dat.

### Dovada care a decis: argumentul podelei

Piciorul NU poate atarna vertical din scaun. Cu axa soldului la 0.5988 m si piciorul
de 0.859 m (coapsa 0.4287 + gamba 0.4305), o rotatie de 90 de grade in jos duce
glezna la **-0.26 m**, sub podea. Argumentul e robust pe tot intervalul de reglaj: la
lungimea MINIMA (P5 femeie, 0.741 m) glezna iese tot dedesubt, la **-0.14 m**. Un
scaun nu poate fi mai inalt decat piciorul care atarna din el. Deci cursa soldului
merge in SUS, iar zeroul e coapsa orizontala.

**STATUT AL DOVEZII.** Argument construit pe cote din clasele ANTROPO si LAYOUT, plus
arhitectura din Fig 2.4. NU e inca un fapt masurat. Se promoveaza la fapt cand se
masoara geometria scaunului la vizita fizica. Daca masuratoarea contrazice inaltimea
soldului, argumentul se reevalueaza -- dar ar trebui ca scaunul real sa fie cu peste
26 cm mai inalt decat cel derivat, ceea ce ar insemna un scaun de aproape 0.9 m.

### Trei corectii de formulare, obligatorii

Fara ele registrul ar otravi deciziile viitoare cu propria lui prescurtare.

**(1) "URDF-ul initial era corect" -- DOAR despre semantica zeroului.**
`attic/rehab_exo.urdf.livrat` are intr-adevar `origin rpy="0 0 0"` si `axis="0 -1 0"`
pe sold, si isi declara in antet "Postura zero = SEZUT". Acea semantica e cea la care
se revine. VALORILE lui raman MOARTE: cursa lui de sold era -0.45 .. 0.70 rad, adica
**-25.78 .. +40.11 grade, cursa 65.89** -- nu cei 90 de grade documentati [PDF Tabel
3.1], si asimetrica fara justificare. Cursele vin din SPEC, nu din fisierul livrat.
A confunda cele doua ar insemna sa reintroducem, sub eticheta "revenire", exact
cifrele pe care F1a le-a retras.

**(2) M1 NU se anuleaza.** Masinaria construita atunci -- maparea derivata din FK,
echivalenta dovedita la 2.5e-16 m, cele 2404 de verificari de traiectorie -- e
fix ce face flip-ul de azi ieftin si verificabil: se refoloseste ca atare, doar cu
alta tinta. Mai mult: re-derivarea de la M1 e cea care a EXPUS imposibilitatea
geometrica. Fara ea, soldul ar fi ramas la 64.22..130.11 grade, o fereastra care
ascundea problema in loc s-o arate. M1 a fost pasul care a facut D1 posibila.

**(3) Banda de postura SEZUT nu se converteste tacit.** La flip se TRANSPORTA
mecanic, prin aceeasi mapare ca restul, ca sa nu ramana in doua conventii. Dar
CONTINUTUL ei -- unde incepe si unde se termina banda in noua conventie -- e o
IPOTEZA NOUA, care se rejustifica separat, la punctul 5, impreuna cu fraza din
document "in sitting position, the motion space of the hip joint is small". Ipoteza
veche (25..90 grade, adica o banda de 65 de grade DEPARTE de repaus) e incompatibila
cu repausul la zero si nu se transporta ca adevar, ci ca numar de convertit.

### Ce constrange decizia asta

- toate valorile dependente de conventie se convertesc prin ACEEASI mapare derivata
  din FK: limitele URDF, pragurile supervizorului, `safety_limits.yaml`,
  referintele de homing, verdictele monitorului;
- traiectoriile exercitiilor raman in conventia veche pana la reconversia din P2;
  pana atunci sunt BLOCATE ZGOMOTOS de gardianul de versiune de conventie, nu rulate
  gresit;
- invariantul podelei devine test permanent: argumentul care a decis conventia nu are
  voie sa ramana o amintire.

---

## D2 (22 aug 2026, decizie a lui Alexandru) -- Marje electrice PER CAPAT

**Ce s-a decis.** Stratul electric nu mai are o marja simetrica. Fiecare capat isi
are marja lui, ca parametru per articulatie:

| capat | marja | clasa |
|---|---:|---|
| jos | **0 grade** | IPOTEZA |
| sus | **5 grade** | IPOTEZA |

Ambele se inchid definitiv de pozitiile proximity-urilor, la vizita fizica.

### De ce: coerenta interna, nu preferinta

Repausul la sold 0 e **fapt documentat** -- e postura de sezut, si chiar ancora
conventiei B-prim. Un strat electric a carui zona interzisa CONTINE starea de repaus
documentata e **auto-contradictoriu**: pe dispozitivul real, proximity-ul de jos e
prin necesitate la sau sub repaus, altfel robotul s-ar autodeclansa stand pe loc.

Nu e un argument teoretic. Cu marja simetrica de 5 grade, smoke-ul complet din aceeasi
zi a dat 4 declansari, toate pe capatul `min`, intre 0.0664 si 0.0781 rad, si trei
exercitii tinute de propriul supervizor pana la finalul sesiunii.

### Ce a fost respins, si de ce

**Prag conditionat de viteza** ("declanseaza doar la apropiere rapida"): e o ipoteza
COMPORTAMENTALA despre dispozitiv, mai mare decat cea pe care o inlocuieste, si fara
niciun sprijin in document.

**Mutarea traiectoriilor** in fereastra electrica: traiectoriile sunt cele mai
auditate obiecte din pachet (3858 de verificari, doi invarianti separati), si oricum
repausul nu poate fi mutat de la 0 -- acolo E.

### Ce constrange

- capatul de jos nu mai protejeaza nimic, si asta e intentionat: acolo protejeaza
  invariantul podelei si limita mecanica din URDF;
- controalele negative ale armarii si ale comutarii s-au mutat pe capatul de SUS,
  fiindca jos cele doua praguri coincid acum si nu mai pot arata o diferenta;
- `supervizor:=false` ramane PORTITA DE DEPANARE. Demonstratiile pentru coordonator
  ruleaza cu supervizorul in lant.

---

## D3 (22 aug 2026, decizie a lui Alexandru) -- Opritorul sub repaus

**Ce s-a decis.** Fereastra soldului devine **-2 .. 88 grade**. Latimea documentata de
90 se pastreaza [PDF Tabel 3.1]; se muta PLASAREA, care a fost mereu IPOTEZA.
`POSTURA_INITIALA` ramane la sold 0: repausul e tinut de CONTROL, iar opritorul de la
-2 il prinde pasiv -- exact ca pe masina reala, unde motorul tine pozitia si stopul e
siguranta. Ancora lui D1 (repaus = coapsa orizontala) ramane intacta.
Banda de sezut isi urmeaza capatul de jos la -2, pastrandu-si capatul ANTROPO la 25.
Inaltimea talpii se re-alege prin propriul ei criteriu, de la 0.230 la **0.250 m**, ca
invariantul podelei sa redevina verde.

### Mecanismul care a impus decizia

Soldul se odihnea exact PE limita lui inferioara, acolo unde gravitatia il impinge cu
coapsa orizontala. Constrangerea de limita din solverul de fizica tinea articulatia,
iar comanda de viteza a lui gz_ros2_control nu o mai putea elibera. Dovada, A/B cu o
singura variabila si control de revenire: limita 0 -> soldul ramane la -0.0000;
limita -3 -> ajunge la +1.3464; inapoi la 0 -> blocat din nou.

### Trei linii independente converg spre aceeasi solutie

1. **Principiul de masina.** Opritorul sta SUB pozitia de repaus. Acelasi rationament
   care a produs D2 pentru proximity: un element de capat care contine starea de
   repaus e auto-contradictoriu.
2. **Ipoteza concurenta din registru primeste prima confirmare partiala.** La P2.1 am
   consemnat valorile URDF-ului livrat (-25.78 .. +40.11) ca "nefolosite, dar daca
   autorul initial cunostea dispozitivul, banda ar putea cobori sub 0". Fizica insasi
   cere acum exact semiplanul negativ pe care el il avea. Nu confirma valorile, dar
   confirma SEMNUL.
3. **O diferenta de modelare, acum inteleasa.** Pe dispozitivul real, in sezut, coapsa
   se odihneste PE PERNA, care preia sarcina. Modelul nostru nu are acel contact:
   perna se termina exact la axa soldului (masurat la P1). Deci coapsa atarna IN
   ARTICULATIE si incarca limita intr-un fel in care masina reala n-o incarca
   niciodata. Blocajul nu e doar artefact de solver, e simptomul acestei diferente.

### Ce a fost respins

**Fereastra -2..90 (92 de grade)**: ar depasi latimea documentata.
**POSTURA_INITIALA mutata la +2**: ar rupe ancora lui D1, repausul n-ar mai fi coapsa
orizontala.

### Ce ramane de separat

Rezerva de repaus (2 grade) e EXACT cat banda de armare a supervizorului (2 grade),
deci starea de armare la repaus sta la granita si poate bascula cu zgomotul
solverului. Nu afecteaza siguranta -- proprietatea robusta (nu declanseaza) e
asertata -- dar cele doua cifre nu ar trebui sa fie egale. Se separa dupa vizita,
cand inaltimile reale spun cat loc chiar exista.
