#!/usr/bin/env python3
"""gen_articol.py — generator de schelete de articole stiintifice.

Citeste un fisier de configurare simplu (chei = valori, comentarii cu #)
si produce un dosar complet de articol:

    out/<slug>/
    ├── main.tex        scheletul IEEE/article, cu instructiuni % per sectiune
    ├── references.bib  samanta de bibliografie (ros2 | gol)
    ├── figs/           directorul figurilor
    ├── build.sh        lantul de compilare (pdflatex+bibtex)
    └── CHECKLIST.md    lista de verificari inainte de submisie

Utilizare:
    python3 gen_articol.py config_exemplu.txt          # genereaza in out/<slug>/
    python3 gen_articol.py config.txt --out ~/articole
    python3 gen_articol.py --selftest                  # validare completa

Reguli incorporate (lectii platite): doar ASCII in .tex (diacriticele si
ghilimelele romanesti strica encodingul OT1); figurile lipsa = placeholdere
compilabile; tabelele booktabs; lantul de compilare in 4 pasi.
"""
import os
import re
import sys

# ----------------------------------------------------------------------
# curatarea textului: tex-ul ramane 100% ASCII
TRANS = str.maketrans({
    "ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
    "Ă": "A", "Â": "A", "Î": "I", "Ș": "S", "Ş": "S", "Ț": "T", "Ţ": "T",
    "—": "-", "–": "-", "«": "'", "»": "'", "„": "'", "”": "'", "’": "'",
})


def curata(s):
    s = s.translate(TRANS)
    ramase = [c for c in s if ord(c) > 127]
    if ramase:
        print(f"[atentie] caractere non-ASCII eliminate: {set(ramase)}")
        s = "".join(c for c in s if ord(c) < 128)
    return s.strip()


def tex_escape(s):
    for a, b in (("&", "\\&"), ("%", "\\%"), ("_", "\\_"), ("#", "\\#")):
        s = s.replace(a, b)
    return s


# ----------------------------------------------------------------------
def citeste_config(cale):
    cfg = {}
    for nr, linie in enumerate(open(cale, encoding="utf-8"), 1):
        linie = linie.split("#", 1)[0].strip()
        if not linie:
            continue
        if "=" not in linie:
            sys.exit(f"[eroare] linia {nr}: astept 'cheie = valoare'")
        k, v = linie.split("=", 1)
        cfg[k.strip().lower()] = curata(v)
    return cfg


IMPLICITE = {
    "titlu": "Titlul articolului (de completat)",
    "slug": "articol_nou",
    "format": "ieee_conf",          # ieee_conf | article
    "autori": "Prenume Nume|Afilierea|email@exemplu.ro",
    "keywords": "cuvant1, cuvant2, cuvant3",
    "anonim": "nu",                 # da = submisie dublu-anonima
    "related": "da",
    "ipoteze": "da",
    "threats": "da",
    "figuri": "3",
    "tabele": "1",
    "bib": "ros2",                  # ros2 | gol
}

BIB_ROS2 = r"""@article{liang2023zenoh,
  author={Liang, Wen-Yew and Yuan, You-Sheng and Lin, Hong-Jie},
  title={A Performance Study on the Throughput and Latency of Zenoh, {MQTT},
         {Kafka}, and {DDS}},
  journal={arXiv preprint arXiv:2303.09419}, year={2023}}
@article{macenski2022ros2,
  author={Macenski, Steven and Foote, Tully and Gerkey, Brian and
          Lalancette, Chris and Woodall, William},
  title={Robot Operating System 2: Design, architecture, and uses in the wild},
  journal={Science Robotics}, volume={7}, number={66}, year={2022}}
@inproceedings{maruyama2016ros2,
  author={Maruyama, Yuya and Kato, Shinpei and Azumi, Takuya},
  title={Exploring the performance of {ROS2}},
  booktitle={Proc. EMSOFT}, year={2016}}
@book{murphy2014disaster,
  author={Murphy, Robin R.}, title={Disaster Robotics},
  publisher={MIT Press}, year={2014}}
@inproceedings{hemminger2005netem,
  author={Hemminger, Stephen}, title={Network Emulation with {NetEm}},
  booktitle={Proc. Linux Conf. Australia}, year={2005}}
@misc{zenoh, author={{Eclipse Foundation}},
  title={Eclipse Zenoh}, howpublished={\url{https://zenoh.io}},
  note={Accesat 2026}}
"""


def fa_autori(cfg):
    intrari = [a.strip() for a in cfg["autori"].split(";") if a.strip()]
    if cfg["anonim"] == "da":
        return ("\\author{\\IEEEauthorblockN{Anonim}\n"
                "\\IEEEauthorblockA{Submisie dublu-anonima}}")
    blocuri = []
    for a in intrari:
        parti = (a.split("|") + ["", ""])[:3]
        nume, afil, mail = (tex_escape(p.strip()) for p in parti)
        blocuri.append(f"\\IEEEauthorblockN{{{nume}}}\n"
                       f"\\IEEEauthorblockA{{{afil}\\\\ {mail}}}")
    return "\\author{" + "\n\\and\n".join(blocuri) + "}"


def fa_figuri(n):
    out = []
    for i in range(1, n + 1):
        out.append(f"""
\\begin{{figure}}[t]
\\centering
% TODO: pune figura in figs/ si decomenteaza linia de mai jos
%\\includegraphics[width=\\linewidth]{{figura_{i}.png}}
\\placeholderfig{{4cm}}{{TODO figura {i}: ce arata, din ce date provine}}
\\caption{{TODO legenda figurii {i} -- o propozitie cu CONCLUZIA figurii,
nu doar descrierea ei.}}
\\label{{fig:f{i}}}
\\end{{figure}}""")
    return "\n".join(out)


def fa_tabele(n):
    out = []
    for i in range(1, n + 1):
        out.append(f"""
\\begin{{table}}[t]
\\centering
\\caption{{TODO titlul tabelului {i} (deasupra, conventia IEEE).}}
\\label{{tab:t{i}}}
\\begin{{tabular}}{{l rr}}
\\toprule
Conditie & Metrica A & Metrica B \\\\
\\midrule
TODO & 0 & 0 \\\\
TODO & 0 & 0 \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}""")
    return "\n".join(out)


def fa_main_tex(cfg):
    conf = cfg["format"] == "ieee_conf"
    docclass = ("\\documentclass[conference]{IEEEtran}" if conf
                else "\\documentclass[11pt,a4paper]{article}\n"
                     "\\usepackage[margin=2.5cm]{geometry}")
    titlu = tex_escape(cfg["titlu"])
    kw = tex_escape(cfg["keywords"])
    s_related = "" if cfg["related"] != "da" else r"""
\section{Related Work}
% INSTRUCTIUNI: 1-2 paragrafe pe fir cronologic sau tematic.
% Fiecare lucrare citata primeste O fraza: ce a facut + ce i-a lipsit.
% Ultima fraza = lacuna pe care o ataci tu (oglinda contributiilor).
TODO related work.~\cite{liang2023zenoh}
"""
    s_ipoteze = "" if cfg["ipoteze"] != "da" else r"""
\subsection{Hypotheses}
% INSTRUCTIUNI: ipoteze FALSIFICABILE, numerotate H1..Hn, fiecare legata
% de o metrica masurabila. In Results fiecare primeste verdict explicit.
\textbf{H1}: TODO. \textbf{H2}: TODO.
"""
    s_threats = "" if cfg["threats"] != "da" else r"""
\paragraph{Threats to validity}
% INSTRUCTIUNI: numeste singur slabiciunile inainte sa o faca recenzentul:
% ce NU modeleaza simularea, N-ul repetitiilor, hardware-ul comun, etc.
TODO threats.
"""
    return f"""% =====================================================================
% Schelet generat de gen_articol.py -- {cfg['slug']}
% Compilare: ./build.sh   (sau: pdflatex, bibtex, pdflatex, pdflatex)
% REGULA DE AUR: fisierul ramane 100% ASCII (fara diacritice, fara <<>>).
% =====================================================================
{docclass}
\\usepackage{{graphicx}}
\\usepackage{{booktabs}}
\\usepackage{{amsmath}}
\\usepackage{{cite}}
\\graphicspath{{{{figs/}}}}
% placeholder compilabil pentru figurile inca nefacute
\\newcommand{{\\placeholderfig}}[2]{{\\fbox{{\\parbox[c][#1][c]{{0.96\\linewidth}}{{%
  \\centering\\small\\ttfamily #2}}}}}}

\\title{{{titlu}}}
{fa_autori(cfg)}

\\begin{{document}}
\\maketitle

\\begin{{abstract}}
% INSTRUCTIUNI (4-6 fraze, in ordinea asta):
% 1. Contextul si problema (1 fraza).  2. Lacuna din literatura (1).
% 3. Ce ai facut -- metoda (1-2).      4. Rezultatul-cheie CU CIFRE (1-2).
% 5. Implicatia / ce se deschide (1).
TODO abstract.
\\end{{abstract}}

\\begin{{IEEEkeywords}}
{kw}
\\end{{IEEEkeywords}}

\\section{{Introduction}}
% INSTRUCTIUNI: 3 paragrafe + lista de contributii.
% P1: de ce conteaza problema (cu citare).  P2: ce lipseste azi si
% intrebarea de cercetare, cu litere de-o schioapa.  P3: cum raspunzi.
% Apoi: Contributions: (i)...(iv) -- fiecare verificabila in Results.
TODO introducere.
{s_related}
\\section{{System and Method}}
% INSTRUCTIUNI: subsectiuni scurte A/B/C; cititorul trebuie sa poata
% REPRODUCE. Definitiile metricilor primesc formule sau pseudo-formule.
\\subsection{{Architecture}}
TODO arhitectura (figura~\\ref{{fig:f1}}).
\\subsection{{Experimental setup}}
TODO conditii, parametri, repetitii.
{s_ipoteze}
\\section{{Results}}
% INSTRUCTIUNI: fiecare paragraf = o constatare cu cifre + trimitere la
% figura/tabel. Verdictele ipotezelor apar EXPLICIT (H1 supported/...).
TODO rezultate (tabelul~\\ref{{tab:t1}}).
{fa_tabele(int(cfg['tabele']))}
{fa_figuri(int(cfg['figuri']))}

\\section{{Discussion}}
% INSTRUCTIUNI: ce inseamna rezultatele dincolo de cifre; comparatia cu
% literatura; unde se aplica si unde NU.
TODO discutie.
{s_threats}
\\section{{Conclusion}}
% INSTRUCTIUNI: 1 paragraf -- rezultatul central reformulat + 1 fraza de
% deschidere. FARA informatie noua.
TODO concluzie.

\\bibliographystyle{{IEEEtran}}
\\bibliography{{references}}
\\end{{document}}
"""


BUILD_SH = """#!/usr/bin/env bash
# lantul complet de compilare; cere: texlive-latex-extra texlive-publishers
set -e
pdflatex -interaction=nonstopmode main.tex
bibtex main || true
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
echo "[ok] main.pdf"
"""

CHECKLIST = """# Checklist inainte de submisie

- [ ] fiecare cifra din text verificata contra CSV-ului sursa
- [ ] toate TODO-urile din main.tex rezolvate: `grep -n TODO main.tex`
- [ ] fisierul 100% ASCII: `grep -nP '[^\\x00-\\x7F]' main.tex` (tacere = ok)
- [ ] figurile la >=300 dpi, lizibile alb-negru
- [ ] bibliografia verificata intrare cu intrare (titlu, an, autori)
- [ ] limita de pagini respectata; autorii/afilierea/acknowledgment completate
- [ ] compilare curata: ./build.sh fara erori, doar avertismente benigne
"""


def genereaza(cfg, radacina):
    d = os.path.join(radacina, cfg["slug"])
    os.makedirs(os.path.join(d, "figs"), exist_ok=True)
    open(os.path.join(d, "main.tex"), "w").write(fa_main_tex(cfg))
    bib = BIB_ROS2 if cfg["bib"] == "ros2" else "% bibliografie goala\n"
    open(os.path.join(d, "references.bib"), "w").write(bib)
    cale_build = os.path.join(d, "build.sh")
    open(cale_build, "w").write(BUILD_SH)
    os.chmod(cale_build, 0o755)
    open(os.path.join(d, "CHECKLIST.md"), "w").write(CHECKLIST)
    return d


def verifica(d):
    tex = open(os.path.join(d, "main.tex")).read()
    assert tex.count("{") == tex.count("}"), "acolade dezechilibrate"
    assert not [c for c in tex if ord(c) > 127], "non-ASCII in tex"
    for f in ("references.bib", "build.sh", "CHECKLIST.md", "figs"):
        assert os.path.exists(os.path.join(d, f)), f"lipseste {f}"
    print(f"[ok] schelet valid: {d}")


def selftest():
    import tempfile
    t = tempfile.mkdtemp()
    cfgf = os.path.join(t, "c.txt")
    open(cfgf, "w", encoding="utf-8").write(
        "titlu = Articol de testare — cu diacritice șî «ghilimele»\n"
        "slug = test_articol\n"
        "autori = Ion Pop|IMSAR|ion@x.ro; Ana M|UPB|ana@y.ro\n"
        "figuri = 2\ntabele = 1\nanonim = nu\n")
    cfg = dict(IMPLICITE)
    cfg.update(citeste_config(cfgf))
    d = genereaza(cfg, t)
    verifica(d)
    # varianta anonima + article class
    cfg.update({"anonim": "da", "format": "article", "slug": "test_anonim",
                "related": "nu", "ipoteze": "nu", "bib": "gol"})
    verifica(genereaza(cfg, t))
    print("[ok] selftest incheiat")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cfg = dict(IMPLICITE)
    cfg.update(citeste_config(sys.argv[1]))
    out = "out"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    d = genereaza(cfg, out)
    verifica(d)
    print(f"urmatorul pas: cd {d} && ./build.sh")
