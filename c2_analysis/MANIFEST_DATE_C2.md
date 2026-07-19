# MANIFEST_DATE_C2.md -- amprente SHA256 seturi C2 SIL

Datele brute NU intra in git (regula 5). Rollup per set = sha256 al listei sortate de
sha256sum-uri ale fisierelor .json/.csv. Recalcul:
  find <set> -type f \( -name '*.json' -o -name '*.csv' \) | sort | xargs sha256sum | sha256sum

  set                    rollup[:16]         fisiere  dim
  C2_SIL_20260718        f65ebf47b04459b5    400      3.6M
  C2_PROBE_20260719      bdd566b619f7d976    24       852K
  C2_SIL64_20260719      656e1d978c9a5676    80       740K
  C2_SILCOMBO_20260719   500a3b1864583c08    40       400K

Provenienta HEAD per set: vezi FAPTE_C2.md (sect. Provenienta).
Arhivare Zenodo propusa: cele 4 seturi C2 + sumarele agregate (make_tables_c2.py) +
figurile (make_figures_c2.py v1.0) + FAPTE_C2.md. Licenta date: CC-BY-4.0 (ca C1).
Nota: datele fizice raman in ~/DATE_CAMPANIE/ (+ backup ~/PHD_backup_20260719.tar.gz).
