# Sincronizare cu repository-ul RehabRob

Sursa canonica de lucru este:

```text
/home/ubuntu/ros2_ws/src/rehab_exo_description
```

Destinatia Git a colegei este:

```text
/home/ubuntu/RehabRob/rehab_exo_description
```

Nu se foloseste o legatura simbolica: cele doua directoare apartin unor repository-uri
Git diferite. Instrumentul `tools/sync_rehabrob.py` face o sincronizare
**unidirectionala si conservatoare**. Nu sterge fisiere din destinatie si nu executa
niciodata `git add`, `commit` sau `push`.

## Comenzi

Doar vezi diferentele (implicit, fara scriere):

```bash
/usr/bin/python3 /home/ubuntu/ros2_ws/src/rehab_exo_description/tools/sync_rehabrob.py
```

Copiaza diferentele sigure:

```bash
/usr/bin/python3 /home/ubuntu/ros2_ws/src/rehab_exo_description/tools/sync_rehabrob.py --apply
```

Sincronizeaza automat dupa fiecare salvare (verificare la o secunda):

```bash
/usr/bin/python3 /home/ubuntu/ros2_ws/src/rehab_exo_description/tools/sync_rehabrob.py --watch
```

`Ctrl+C` opreste urmarirea. Pentru CI, `--check` intoarce codul 1 daca exista diferente.

## Protectii

- Prima aplicare este refuzata daca pachetul din `RehabRob` are modificari Git locale.
- Dupa prima aplicare, hash-urile sunt tinute numai in `.git/rehab_sync_state_v1.json`
  din repository-ul destinatie; fisierul nu poate ajunge intr-un commit.
- Daca un fisier a fost modificat independent in destinatie, apare `CONFLICT` si nu
  este suprascris.
- Fisierele existente numai in destinatie apar ca `KEEP` si nu sunt sterse.
- Modificari din afara subdirectorului `rehab_exo_description` (de exemplu documente)
  nu sunt atinse.

Dupa sincronizare, colega trebuie sa inspecteze `git diff`, sa ruleze testele si sa
decida explicit ce intra in commit.
