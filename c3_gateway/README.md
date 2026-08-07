# c3_gateway -- gateway de selectie a transportului, condus de starea linkului

Contributia C3. Ideea: traficul de teleoperare nu trebuie sa ramana pe un transport ales
la compilare. Linkul isi schimba starea (rata de pierdere L si lungimea rafalelor B), iar
transportul potrivit se schimba odata cu ea. Gateway-ul estimeaza starea ONLINE si comuta
intre stive, folosind o politica derivata din masuratorile C2, nu din intuitie.

## Starea: ETAPA 1 (nucleu pur)

In pachet exista DOAR nucleul, si el nu stie ce e ROS-ul:

    c3_gateway/core/estimator.py   L si B online (EWMA), cu incertitudine si flag de stabilitate
    c3_gateway/core/policy.py      politica = TABELA pe (L, B, payload), incarcata din JSON
    c3_gateway/core/switching.py   masina de stare: histerezis asimetric + dwell-time
    c3_gateway/core/channel.py     canal Gilbert-Elliott determinist (pentru teste)
    c3_gateway/core/policy_table.json   DATE, generate din tabelele C2 (nu scrise de mana)

Interdictii respectate in `core/`: fara `rclpy`, fara `socket`, fara `os.environ`. Verificat
automat de `test/test_core_pur.py` -- daca cineva strecoara un import interzis, testul pica.

NU exista noduri ROS si nici cod de retea in etapa asta. `entry_points` e gol, intentionat.

## Cum se verifica (fara ROS, fara retea)

    python3 test/test_c3_core.py          # suita completa: selfteste + teste de integrare
    python3 c3_gateway/core/estimator.py --selftest
    python3 c3_gateway/core/policy.py --selftest
    python3 c3_gateway/core/switching.py --selftest
    python3 c3_gateway/core/channel.py --selftest

## De unde vin cifrele

- `FAPTE_C3.md` -- gate-ul de fapte: izolarea intre RMW-uri (cu controale pozitive),
  scope-ul lui `SetEnvironmentVariable` in launch, si costul masurat de re-stabilire.
  Dwell-time-ul din `switching.py` se deriveaza din cifra de acolo.
- `policy_table.json` -- generata de `tools/derive_policy.py` din tabelele canonice C2 din
  `~/DATE_CAMPANIE/ANALIZA_C2/`. Fiecare intrare poarta provenienta (fisierul sursa).
  Regenerare: `python3 tools/derive_policy.py`.
- `gate/` -- harness-ul de masura al gate-ului. Foloseste rclpy, deci NU e parte din pachetul
  instalat; e pastrat ca sa fie reproductibile cifrele din FAPTE_C3.md.

## Ce urmeaza (etapa 2, NU acum)

Noduri subtiri peste nucleu (un nod de estimare care consuma numere de secventa, un nod de
decizie care publica transportul ales), launch cu stive paralele per RMW (Arhitectura B,
confirmata in gate), si abia apoi masuratori pe HIL.
