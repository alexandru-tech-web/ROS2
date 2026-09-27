# Conversia documentelor Markdown în PDF

Proiectul conține un convertor local pentru documente tehnice Markdown. Acesta
păstrează diacriticele, formulele LaTeX, tabelele, imaginile locale, legăturile și
generează automat un cuprins.

## Utilizare rapidă

Din directorul `joint_emulator`:

```bash
./tools/md_to_pdf.sh docs/RAPORT_LABORATOR_VIPRO.md
```

Rezultatul implicit este creat lângă sursă:

```text
docs/RAPORT_LABORATOR_VIPRO.pdf
```

O destinație explicită poate fi transmisă ca al doilea argument:

```bash
./tools/md_to_pdf.sh docs/RAPORT_LABORATOR_VIPRO.md /tmp/raport_vipro.pdf
```

## Pregătirea pe alt calculator Ubuntu

Pandoc poate fi instalat numai în workspace, fără drepturi de administrator:

```bash
./tools/setup_md_to_pdf.sh
```

Scriptul folosește pachetele Ubuntu `pandoc` și `pandoc-data`, extrase în
`ros2_ws/.tools/pandoc`. Pentru tipărirea rezultatului HTML intermediar este
necesar Chromium (`chromium` sau `/snap/bin/chromium`).

## Limitări cunoscute

Blocurile Mermaid sunt păstrate ca text tehnic în PDF. Pentru transformarea lor
în diagrame vectoriale este necesar un motor Mermaid separat. Referințele către
fișiere locale rămân legături; conținutul acelor fișiere nu este inserat automat.

