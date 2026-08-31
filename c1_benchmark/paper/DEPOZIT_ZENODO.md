# DEPOZIT_ZENODO.md -- structura depunerii de date C1

Propunere. Se confirma la submisie, nu inainte: pana atunci nici arhiva nu se
creeaza, nici DOI-ul nu se rezerva. Recuperat si revizuit din sectiunea
"Structura de arhiva propusa pentru Zenodo" a lui `MANIFEST_DATE.md` v1
(`894f3c7`), adus pe manifestul v2.

## 1. Ce contine depunerea

Continutul este **exact lista din manifest**, plus manifestul insusi, plus un
README de nivel superior. Nimic in plus, nimic ales pe loc: daca un fisier nu e
in `MANIFEST_SHA256.txt`, nu intra in arhiva.

```
c1-benchmark-data/
  README.md                 # de nivel superior; sinteza din README_SIL.md
                            # si README_HIL_WIFI.md, plus cum se verifica arhiva
  MANIFEST_SHA256.txt       # manifestul v2, neschimbat
  SIL/                      # exact fisierele listate in manifest
  HIL_WIFI/                 # idem
  README_SIL.md             # incluse ca fisiere, sunt in manifest
  README_HIL_WIFI.md
  netem_journal_M2.log
```

Numarul de fisiere, descompunerea pe subarbore si aritmetica
`celule x repetitii x payload-uri` stau in antetul manifestului. Nu se repeta
aici: un singur loc generat, ca sa nu existe doua cifre care se pot contrazice.

## 2. Cum verifica cine descarca

Din radacina arhivei dezarhivate, oricare dintre cele doua:

```bash
# fara unealta noastra, doar coreutils
grep -v '^#' MANIFEST_SHA256.txt | sha256sum -c --quiet

# cu unealta din depozitul de cod, care raporteaza si fisierele in plus
python3 manifest_tool.py check . MANIFEST_SHA256.txt
```

Prima nu are nevoie de nimic din depozitul de cod. A doua adauga detectarea
fisierelor **in plus** fata de manifest, pe care `sha256sum -c` nu o face.

## 3. Legatura cu codul

Depunerea de date se face ca snapshot al unui tag de cod, iar tagul se numeste
explicit in campul Description. Maparea set de date -> campanie -> commit de cod,
cu tot cu caveatul ei (commitul per rulare nu a fost inregistrat), este in
`VERSIUNI.md`, sectiunea "Setul de date <-> campanie <-> cod"; aceeasi mapare
intra in campul Method al depunerii.

Codul NU se copiaza in arhiva de date: se citeaza prin tag si prin adresa
depozitului, ca sa existe o singura sursa pentru el.

## 4. Licenta

**TODO(Alexandru).** `LICENSE` din `c1_benchmark/` este Apache-2.0 si acopera
codul, nu datele. Propunere pentru setul de campanie: **CC BY 4.0**. Decizia
este a autorului si nu se ia in cod.

## 5. Stare

| Element | Stare |
|---------|-------|
| structura de mai sus | propunere, neconfirmata |
| arhiva | NU e creata |
| incarcare | NU s-a facut |
| DOI | se rezerva la submisie |
| licenta datelor | TODO(Alexandru) |
