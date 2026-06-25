# gen_articol -- generator de schelete de articole stiintifice (unealta de infrastructura)

Un singur script Python fara dependinte (`gen_articol.py`) care transforma un
fisier de configurare simplu (`cheie = valoare`) intr-un dosar complet de
articol: `main.tex` cu instructiuni de scriere per sectiune, bibliografie-samanta,
scriptul de compilare si checklist-ul de submisie. Nu este o contributie
stiintifica (nu intra in harta C1-C4 / A1-A5); este o unealta de scris care
generalizeaza scheletul articolului SSRR 2026 (A1) pentru articolele urmatoare
(A2, A3, A4) si capitolele tezei, impunand disciplina ASCII si reteta de
sectiuni invatata pe articolul A1.

## 1. Scop

Producerea reproductibila a unui dosar LaTeX de pornire pentru un articol nou,
cu structura IEEE/article completa si cu instructiunile de scriere (`%` la fiecare
sectiune) incorporate, astfel incat autorul sa nu rescrie de fiecare data acelasi
schelet si sa nu repete lectiile deja platite. Cele trei reguli incorporate in
generator, citate direct din docstringul lui `gen_articol.py`:

- `.tex`-ul ramane 100% ASCII -- diacriticele si ghilimelele romanesti din valori
  sunt transliterate automat (ele strica encodingul OT1);
- figurile lipsa nu blocheaza compilarea -- sunt inlocuite cu placeholdere
  compilabile (`\placeholderfig`);
- lantul de compilare in 4 pasi (pdflatex, bibtex, pdflatex, pdflatex) si
  tabelele in stil booktabs.

Generatorul produce STRUCTURA si disciplina, nu continutul: textul (abstract,
introducere, rezultate) ramane al autorului, marcat peste tot cu `TODO`.

## 2. Context si loc in arhitectura

Proiectul produce mai multe articole (harta A1-A5) si capitole de teza care
impart aceeasi forma: aceeasi clasa IEEEtran, aceeasi disciplina ASCII (vezi
CLAUDE.md sectiunea 3), aceeasi reteta de sectiuni rafinata pe articolul A1
(`c1_benchmark/paper/`). Problema practica: la fiecare articol nou, scheletul si
lectiile (IEEEtran prin `texlive-publishers`, ASCII, placeholdere pentru figuri
inca nefacute) se reinventeaza manual si inconsistent.

`gen_articol` rezolva exact aceasta repetitie: este o unealta de infrastructura
editoriala, separata de coloana stiintifica. Nu are nimic ROS (nu publica/asculta
topicuri, nu este nod), nu atinge date de campanie si nu produce metrici. Locul
sau in repo este alaturi de celelalte unelte transversale (`check_repo.sh`,
`smoke_all.sh`), nu in lantul de masuratori. Iesirea sa tipica este un dosar de
articol (de exemplu pentru A2 link-adaptive, vezi `config_exemplu.txt`) care apoi
se editeaza si se compileaza independent.

## 3. Arhitectura

### 3.1 Structura generala

Pachetul NU urmeaza tiparul "nucleu pur -> nod ROS subtire -> SIL" din metodologia
proiectului (CLAUDE.md sectiunea 2), pentru ca nu are componenta ROS si nu este
un experiment. Este un singur fisier procedural, ROS-free, cu un `_selftest`
incorporat (functia `selftest()` rulata prin `--selftest`). Fluxul este liniar:

```
config (cheie = valoare)
   |  citeste_config()  -- parsare + curatare ASCII (curata())
   v
dictionar cfg  (peste IMPLICITE, suprascris de config)
   |  genereaza()
   v
out/<slug>/
   |-- main.tex        fa_main_tex()  -> fa_autori(), fa_figuri(), fa_tabele()
   |-- references.bib  BIB_ROS2 (bib=ros2) sau comentariu gol (bib=gol)
   |-- build.sh        BUILD_SH (chmod 0755)
   |-- CHECKLIST.md    CHECKLIST
   `-- figs/           director gol pentru figuri
   |  verifica()       -- acolade echilibrate, ASCII, fisiere prezente
   v
verdict [ok] schelet valid
```

### 3.2 Functiile-cheie (din cod)

| Functie | Rol |
|---|---|
| `curata(s)` | translitereaza diacriticele/ghilimelele (tabelul `TRANS`) si elimina orice ramasita non-ASCII, cu avertisment |
| `tex_escape(s)` | escapeaza `& % _ #` pentru LaTeX |
| `citeste_config(cale)` | citeste `cheie = valoare`, ignora comentarii `#` si linii goale, opreste cu eroare daca lipseste `=` |
| `fa_autori(cfg)` | blocuri `\IEEEauthorblockN/A` din `autori` (separator `;`, campuri `Nume\|Afiliere\|Email`); daca `anonim = da`, inlocuieste cu bloc anonim |
| `fa_figuri(n)` / `fa_tabele(n)` | genereaza `n` placeholdere de figura, respectiv `n` schelete de tabel booktabs, fiecare cu `TODO` |
| `fa_main_tex(cfg)` | asambleaza `main.tex`; comuta IEEEtran-conference vs. clasa `article` dupa `format`; include conditionat Related Work / Hypotheses / Threats |
| `genereaza(cfg, radacina)` | scrie cele 4 fisiere + `figs/` in `out/<slug>/` |
| `verifica(d)` | validare prin `assert`: acolade `{`=`}`, zero octeti > 127, prezenta `references.bib`, `build.sh`, `CHECKLIST.md`, `figs` |
| `selftest()` | genereaza si verifica doua scenarii (vezi sectiunea 7) |

Nu exista diagrama mermaid in cod; schema ASCII de mai sus reflecta apelurile
reale din `gen_articol.py`.

## 4. Inventar fisiere

| Fisier | Rol | Cum se verifica |
|---|---|---|
| `gen_articol.py` | generatorul (un singur script, fara dependinte externe; doar `os`, `re`, `sys` din stdlib) | `python3 gen_articol.py --selftest` |
| `config_exemplu.txt` | configurarea-sablon, comentata, care e si documentatia cheilor (exemplul A2 link-adaptive) | `python3 gen_articol.py config_exemplu.txt --out <dir>` |
| `README.md` | acest document | `grep -nP '[^\x00-\x7F]' README.md` (tacere = ok) |

Nota de onestitate: pachetul NU contine `package.xml`, `setup.py` sau `setup.cfg`
(confirmat: cele trei fisiere lipsesc din director). Deci NU este un pachet ament
inregistrat -- nu exista `ros2 run gen_articol ...`. Se ruleaza direct cu
`python3 gen_articol.py`. Nu exista director `launch/` si niciun fisier de teste
separat (`test_*.py`); verificarea este `selftest()`, incorporat in script.

## 5. Date tehnice

### 5.1 Cheile de configurare si valorile implicite

Valorile implicite vin din dictionarul `IMPLICITE` din cod; orice cheie din
fisierul de configurare le suprascrie. Cheile sunt convertite la litere mici la
citire (`k.strip().lower()`).

| Cheie | Valori acceptate | Implicit (`IMPLICITE`) | Efect |
|---|---|---|---|
| `titlu` | text | `Titlul articolului (de completat)` | `\title{...}` (escapat) |
| `slug` | text scurt | `articol_nou` | numele dosarului generat `out/<slug>/` |
| `format` | `ieee_conf` \| `article` | `ieee_conf` | `\documentclass[conference]{IEEEtran}` vs. `article` A4 cu `geometry` |
| `autori` | `Nume\|Afiliere\|Email; ...` | `Prenume Nume\|Afilierea\|email@exemplu.ro` | blocuri de autori IEEE |
| `keywords` | lista | `cuvant1, cuvant2, cuvant3` | continutul `\begin{IEEEkeywords}` |
| `anonim` | `da` \| `nu` | `nu` | `da` = inlocuieste autorii cu bloc dublu-anonim |
| `related` | `da` \| (orice) | `da` | include sectiunea Related Work daca `= da` |
| `ipoteze` | `da` \| (orice) | `da` | include subsectiunea Hypotheses (H1..Hn) daca `= da` |
| `threats` | `da` \| (orice) | `da` | include paragraful Threats to validity daca `= da` |
| `figuri` | numar | `3` | cate placeholdere de figura compilabile |
| `tabele` | numar | `1` | cate schelete de tabel booktabs |
| `bib` | `ros2` \| `gol` | `ros2` | bibliografia-samanta sau fisier gol |

Logica sectiunilor optionale este "include daca egal cu `da`": orice alta valoare
(inclusiv `nu`) le omite (`"" if cfg[x] != "da" else ...`).

### 5.2 Bibliografia-samanta (`bib = ros2`)

Sablonul `BIB_ROS2` contine 6 intrari din domeniu (confirmate prin numarare in
cod): `liang2023zenoh`, `macenski2022ros2`, `maruyama2016ros2`,
`murphy2014disaster`, `hemminger2005netem`, `zenoh`. Cu `bib = gol` se scrie doar
comentariul `% bibliografie goala`. Aceste intrari sunt un punct de pornire pentru
articolele din domeniul ROS2/middleware; trebuie verificate intrare cu intrare
inainte de submisie (vezi `CHECKLIST.md` generat).

### 5.3 Regula ASCII (mecanismul)

`curata()` aplica tabelul de transliterare `TRANS` (diacriticele romanesti in
ambele encodari, plus em/en-dash si ghilimelele curbate/unghiulare la `-` / `'`),
apoi elimina orice octet ramas > 127 cu avertisment. `verifica()` reintareste
invariantul cu un `assert` care interzice orice octet > 127 in `main.tex`.
Rezultatul a fost confirmat aici: generarea din `config_exemplu.txt` produce un
`main.tex` cu zero caractere non-ASCII.

## 6. Sintaxe de pornire

Pachetul NU este ament (fara `package.xml`/`setup.py`), deci nu exista build
colcon si nici `ros2 run`. Se ruleaza direct cu Python 3 (stdlib, fara instalare
de dependinte).

```bash
cd ~/ros2_ws/src/gen_articol

# 0) verificarea generatorului insusi (fara ROS, fara LaTeX)
python3 gen_articol.py --selftest

# 1) copiezi si editezi configul
cp config_exemplu.txt config_a2.txt
#   ... editeaza titlu / slug / autori / figuri / tabele ...

# 2) generezi dosarul -> out/<slug>/ (implicit radacina "out")
python3 gen_articol.py config_a2.txt
#   sau alta radacina:
python3 gen_articol.py config_a2.txt --out ~/articole

# 3) compilezi -> main.pdf (cere LaTeX, vezi mai jos)
cd out/<slug> && ./build.sh
```

Cerintele de compilare (o singura data pe masina; `texlive-publishers` aduce
IEEEtran -- fara el compilarea cade la prima linie, lectie platita):

```bash
sudo apt install -y texlive-latex-base texlive-latex-extra \
                    texlive-bibtex-extra texlive-publishers
```

Limitari, oneste:
- generatorul produce structura si instructiuni, nu continut -- toate sectiunile
  contin `TODO`;
- formatele sunt doar IEEEtran-conference si clasa `article` A4; alte formate
  (Springer LNCS, Elsevier) se adauga in `fa_main_tex()` cand va fi nevoie;
- bibliografia-samanta acopera doar domeniul ROS2/middleware;
- nota din CLAUDE.md sectiunea 4: IEEEtran (`.cls`/`.bst`) poate lipsi local;
  daca citarile apar `[?]`, se comuta pe `plain` local sau pe Overleaf -- nu este
  o problema a generatorului.

## 7. Verificare

Verificarea este `selftest()`, rulat prin `python3 gen_articol.py --selftest`.
NU este un harnais cu numar de teste de forma "X/X"; sunt doua scenarii generate
si validate prin `assert` in `verifica()`:

1. config cu diacritice si ghilimele romanesti in titlu, doi autori separati prin
   `;`, `figuri = 2`, `tabele = 1`, neanonim, format implicit (ieee_conf) -- caz
   care exercita transliterarea ASCII si blocurile multi-autor;
2. acelasi config cu `anonim = da`, `format = article`, `related = nu`,
   `ipoteze = nu`, `bib = gol` -- caz care exercita blocul anonim, clasa
   `article`, omiterea sectiunilor optionale si bibliografia goala.

Fiecare scenariu trece prin `verifica()`, care da `assert` pe: (i) acolade
echilibrate `{` = `}`, (ii) zero octeti > 127 in `main.tex`, (iii) prezenta
`references.bib`, `build.sh`, `CHECKLIST.md` si `figs/`. La succes tipareste
`[ok] schelet valid: ...` pentru fiecare scenariu, apoi `[ok] selftest incheiat`,
si iese cu cod 0.

Rezultat reprodus aici (`python3 gen_articol.py --selftest`):

```
[ok] schelet valid: <tmp>/test_articol
[ok] schelet valid: <tmp>/test_anonim
[ok] selftest incheiat
```

Smoke suplimentar reprodus: generarea din `config_exemplu.txt` produce dosarul
`a2_link_adaptive/` cu `build.sh`, `CHECKLIST.md`, `figs/`, `main.tex`,
`references.bib`, iar `grep -cP '[^\x00-\x7F]' main.tex` intoarce 0.

Acoperire neacoperita de selftest (TODO): compilarea efectiva a `main.tex`
generat (`./build.sh`) nu este verificata automat -- selftest valideaza
structura si invariantul ASCII, dar nu lanseaza `pdflatex`. Validarea LaTeX
ramane manuala, cu LaTeX instalat.

## 8. Igiena datelor si reproductibilitate

Generatorul nu produce date de campanie si nu atinge figuri sau CSV-uri; deci nu
i se aplica regula de arhivare a datelor brute din CLAUDE.md sectiunea 5. Singura
igiena relevanta tine de iesirea sa LaTeX:

- dosarele generate `out/<slug>/` sunt artefacte derivate (regenerabile din
  config); de regula nu intra in git decat dupa ce sunt editate si devin articol
  propriu-zis;
- invariantul ASCII este garantat de cod (`curata()` + `assert`-ul din
  `verifica()`) si verificabil cu `grep -nP '[^\x00-\x7F]' main.tex` -- aceeasi
  comanda din `CHECKLIST.md` generat;
- reproductibilitate: din acelasi `config_*.txt` se obtine acelasi dosar; sursa
  de adevar a cheilor si valorilor implicite este `gen_articol.py`
  (dictionarul `IMPLICITE`), iar exemplul comentat este `config_exemplu.txt`.

Aceasta documentatie reflecta doar ce exista in cod la data scrierii; nu exista
metrici, citari sau rezultate experimentale de raportat pentru aceasta unealta.
