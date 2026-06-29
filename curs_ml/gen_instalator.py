#!/usr/bin/env python3
"""gen_instalator.py -- genereaza instaleaza_curs_ml.sh auto-suficient.

Parcurge pachetul curs_ml/ si emite un script bash care recreeaza intregul arbore
din heredoc-uri citate (<< '__CURS_ML_EOF__'), EXCLUZAND figurile PNG (SIL-urile le
regenereaza), cache-ul si artefactele. Foloseste-l cand distribui cursul fara git.

Rulare:
  python3 gen_instalator.py            # scrie instaleaza_curs_ml.sh
"""
import os
import stat

ROOT = os.path.dirname(os.path.abspath(__file__))           # .../curs_ml
OUT = os.path.join(ROOT, "instaleaza_curs_ml.sh")
MARK = "__CURS_ML_EOF__"
SKIP_DIRS = {"__pycache__", ".git"}
SKIP_EXT = {".png", ".pyc", ".npz"}
SKIP_FILES = {"instaleaza_curs_ml.sh", "gen_instalator.py"}  # nu se includ (unelte/artefacte)


def collect():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in sorted(filenames):
            if f in SKIP_FILES or os.path.splitext(f)[1] in SKIP_EXT:
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, ROOT)
            files.append((rel, full))
    return sorted(files)


def main():
    files = collect()
    lines = [
        "#!/usr/bin/env bash",
        "# instaleaza_curs_ml.sh -- recreeaza pachetul curs_ml din heredoc-uri (auto-generat).",
        "# Figurile PNG sunt EXCLUSE (SIL-urile le regenereaza). Rulare: ./instaleaza_curs_ml.sh [TARGET]",
        "# TARGET implicit: ./curs_ml (apoi: venv ML + colcon -- vezi README.md).",
        "set -euo pipefail",
        'TARGET="${1:-curs_ml}"',
        'echo "Recreez curs_ml in: $TARGET (%d fisiere)"' % len(files),
        'mkdir -p "$TARGET"',
        "",
    ]
    for rel, full in files:
        with open(full, "r", encoding="utf-8") as fh:
            content = fh.read()
        if MARK in content:
            raise SystemExit("EROARE: marcatorul %s apare in %s" % (MARK, rel))
        d = os.path.dirname(rel)
        if d:
            lines.append('mkdir -p "$TARGET/%s"' % d)
        lines.append("cat > \"$TARGET/%s\" << '%s'" % (rel, MARK))
        lines.append(content.rstrip("\n"))
        lines.append(MARK)
    # fa scripturile executabile
    lines.append("")
    lines.append('chmod +x "$TARGET/verifica_ml.sh" 2>/dev/null || true')
    lines.append('chmod +x "$TARGET/instaleaza_curs_ml.sh" 2>/dev/null || true')
    lines.append('echo "Gata. Urmatorii pasi (README.md):"')
    lines.append('echo "  python3 -m venv ~/ros2_ws/.venv_ml && source ~/ros2_ws/.venv_ml/bin/activate"')
    lines.append('echo "  pip install -r $TARGET/requirements.txt"')
    lines.append('echo "  cd $TARGET && ./verifica_ml.sh"')
    lines.append("")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(OUT, os.stat(OUT).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print("scris %s (%d fisiere incluse)" % (OUT, len(files)))


if __name__ == "__main__":
    main()
