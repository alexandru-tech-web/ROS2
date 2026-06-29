# gen_articol

Generator de schelete de articole stiintifice: un singur script Python
(`gen_articol.py`, doar stdlib -- `os` si `sys` la nivel de modul, plus
`tempfile` in `selftest()`; `re` e importat dar momentan nefolosit) care citeste
un fisier de configurare `cheie = valoare` si scrie un dosar LaTeX complet de
articol. Unealta
de infrastructura editoriala din teza (teleoperare peste retele degradate), nu o
contributie stiintifica.

## Scop

Din docstring: produce reproductibil un dosar `out/<slug>/` cu `main.tex`
(schelet IEEEtran/article cu instructiuni `%` per sectiune), `references.bib`
(samanta ros2 sau gol), `figs/`, `build.sh` (pdflatex+bibtex) si `CHECKLIST.md`.
Reguli incorporate din cod: `.tex` ramane 100% ASCII (diacriticele si ghilimelele
sunt transliterate de `curata()`), figurile lipsa devin placeholdere compilabile,
lant de compilare in 4 pasi, tabele booktabs. Continutul ramane al autorului,
marcat peste tot cu `TODO`.

## Fisiere

- `gen_articol.py` -- generatorul; `citeste_config()` parseaza configul (chei
  lowercase, comentarii `#`, eroare daca lipseste `=`), `genereaza()` scrie cele
  4 fisiere + `figs/`, `verifica()` valideaza prin `assert` (acolade `{`=`}`,
  zero octeti >127 in `main.tex`, prezenta fisierelor), `selftest()` ruleaza 2
  scenarii (config cu diacritice + 2 autori; varianta `anonim=da`/`format=article`).
- `config_exemplu.txt` -- config-sablon comentat (exemplul A2 link-adaptive),
  documentatia cheilor: `titlu`, `slug`, `autori` (separator `;`, campuri
  `Nume|Afiliere|Email`), `anonim`, `format` (`ieee_conf`|`article`), `keywords`,
  `related`/`ipoteze`/`threats` (da/nu), `figuri`, `tabele`, `bib` (`ros2`|`gol`).

## Sintaxe de rulare

Pachetul NU contine `package.xml`/`setup.py`/`setup.cfg` (confirmat: lipsesc) --
nu este pachet ament, nu exista `ros2 run`. Se ruleaza direct cu Python 3:

```bash
cd ~/ros2_ws/src/gen_articol
python3 gen_articol.py --selftest                 # validare offline (2 scenarii)
python3 gen_articol.py config_exemplu.txt         # genereaza in out/<slug>/
python3 gen_articol.py config_exemplu.txt --out ~/articole
```

Argumentele CLI reale (din `__main__`): primul argument pozitional = fisierul de
config; `--selftest` ruleaza selftest si iese; `--out <dir>` schimba radacina
(implicit `out`). Compilarea PDF cere LaTeX cu IEEEtran (comentariul din
`build.sh` cere `texlive-latex-extra texlive-publishers`):
`cd out/<slug> && ./build.sh`.

Nota: pachet de arhiva/demo, unealta de scris, fara componenta ROS (nu publica/
asculta topicuri, nu declara parametri).
