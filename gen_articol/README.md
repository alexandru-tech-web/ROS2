# gen_articol — generatorul de schelete de articole stiintifice

Un singur script Python (fara dependinte) care transforma un fisier de
configurare simplu intr-un dosar complet de articol: `main.tex` cu
instructiuni de scriere per sectiune, bibliografie-samanta, scriptul de
compilare si checklist-ul de submisie. Generalizeaza scheletul articolului
SSRR 2026 (A1) pentru articolele urmatoare (A2, A3, A4) si capitolele tezei.

## Utilizare in 3 comenzi

```bash
cp config_exemplu.txt config_a2.txt    # 1) copiezi si editezi configul
python3 gen_articol.py config_a2.txt   # 2) generezi -> out/<slug>/
cd out/<slug> && ./build.sh            # 3) compilezi -> main.pdf
```

Verificarea generatorului insusi: `python3 gen_articol.py --selftest`.

## Fisierul de configurare

Format `cheie = valoare`, comentarii cu `#` (vezi `config_exemplu.txt`,
care e si documentatia completa). Cheile:

| Cheie | Valori | Ce face |
|---|---|---|
| `titlu` | text | titlul articolului |
| `slug` | text scurt | numele dosarului generat |
| `autori` | `Nume\|Afiliere\|Email; ...` | blocurile de autori IEEE |
| `anonim` | da / nu | submisie dublu-anonima (autorii ascunsi) |
| `format` | ieee_conf / article | IEEEtran conferinta sau clasa article A4 |
| `keywords` | lista | IEEEkeywords |
| `related`, `ipoteze`, `threats` | da / nu | sectiunile optionale |
| `figuri`, `tabele` | numar | cate placeholdere/schelete genereaza |
| `bib` | ros2 / gol | bibliografia-samanta (6 intrari din domeniu) sau goala |

Diacriticele si ghilimelele romanesti din valori sunt transliterate automat
— `.tex`-ul generat e garantat 100% ASCII.

## Ce contine scheletul generat

`main.tex` cu instructiuni `%` la fiecare sectiune: reteta abstractului in
5 fraze, structura introducerii in 3 paragrafe + contributii, regula
"fiecare paragraf din Results = o constatare cu cifre + verdictul ipotezei",
threats inainte sa le spuna recenzentul. Figurile lipsesc? Documentul tot
compileaza — placeholderele `\placeholderfig` sunt chenare cu TODO.
`CHECKLIST.md` are lista de dinaintea submisiei, inclusiv comanda de
verificare ASCII: `grep -nP '[^\x00-\x7F]' main.tex`.

## Cerinte de compilare (o singura data pe masina)

```bash
sudo apt install -y texlive-latex-base texlive-latex-extra \
                    texlive-bibtex-extra texlive-publishers
```

`texlive-publishers` e pachetul care contine IEEEtran — fara el compilarea
cade la prima linie (lectie platita).

## Limite oneste

Generatorul produce STRUCTURA si disciplina, nu continutul: textul ramane
al tau. Bibliografia-samanta acopera doar domeniul ROS2/middleware —
verifica fiecare intrare pe Scholar inainte de submisie. Nu genereaza
formate non-IEEE (Springer LNCS, Elsevier) — se adauga usor ca format nou
in `fa_main_tex()` cand va fi nevoie.
