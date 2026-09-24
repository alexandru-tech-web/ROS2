# Schema datelor experimentale ViPRO — TASK-002

## Scop

Acest document descrie contractul de date pentru sesiuni, trial-uri, hardware,
semnale, timp, proveniență și calibrare. Contractul nu modifică simulatorul,
controlul, nodurile ROS sau loggerele existente.

Implementarea executabilă este în
`research/schemas/experimental_data.py`, iar forma JSON interoperabilă este în
`research/schemas/experimental_manifest.schema.json`. Versiunea inițială a
contractului este `1.0.0`.

Artefactele nominale ale TASK-001 (`vipo_inventory.md`,
`vipo_inventory.yaml`, `ros_graph.md`, `signals.md`) nu au fost găsite în
workspace sau sub `/home/ubuntu` la realizarea TASK-002. Prin urmare, această
etapă definește tipurile și regulile, dar nu populează un inventar concret și nu
deduce proprietăți ale bancului din cod sau din imagini.

## Regula fundamentală pentru valori necunoscute

O valoare necunoscută este `null` și are proveniența `UNKNOWN`. Zero, șirul gol
și o valoare presupusă nu sunt înlocuitori pentru necunoscut.

```json
{
  "value": null,
  "provenance": "UNKNOWN",
  "evidence": [],
  "unit": "N.m",
  "method": null,
  "uncertainty": null
}
```

O valoare nenulă trebuie să aibă cel puțin o referință `evidence`. Valorile
`IDENTIFIED` și `DERIVED` trebuie să specifice și metoda. Exemplul de mai jos
arată numai forma contractului și nu afirmă nimic despre hardware-ul ViPRO:

```json
{
  "value": 1.0,
  "provenance": "SIMULATED",
  "evidence": [
    {
      "source": "synthetic-test-fixture",
      "locator": "case-1",
      "sha256": null
    }
  ],
  "unit": "rad",
  "method": null,
  "uncertainty": null
}
```

Categoriile admise sunt exact: `MEASURED`, `MANUAL`, `CODE_CONFIG`,
`IDENTIFIED`, `DERIVED`, `SIMULATED`, `UNKNOWN`.

## Structurile contractului

### `ExperimentManifest`

Este rădăcina unui set experimental și conține:

- versiunea schemei;
- exact o sesiune și manifestul hardware asociat;
- cataloage de ceasuri, semnale și calibrări;
- trial-urile sesiunii;
- artefactele de date brute, procesate și derivate.

Identificatorii trebuie să fie unici în colecția lor. Toate referințele sunt
validate: un semnal nu poate indica un hardware, ceas sau calibrare absentă, iar
un trial nu poate indica altă sesiune.

### `SessionRecord`

Separă identitatea sesiunii de afirmațiile fizice. Reține tipul sesiunii cu
proveniență, starea ei, intervalul temporal, configurația hardware, revizia
software, hash-ul configurației și artefactele asociate.

`software_revision` și `configuration_hash` rămân `UNKNOWN` dacă nu există o
dovadă capturată la momentul sesiunii. Nu se completează retrospectiv din
memorie.

### `TrialRecord`

Un trial aparține unei singure sesiuni și are ordine explicită, interval
temporal, identificatori cu proveniență pentru mecanism și excitație, starea
hardware relevantă, rezultat și artefacte. Un trial `INVALID` trebuie să aibă
cel puțin un motiv explicit.

### `HardwareManifest` și `HardwareComponent`

Componentele au identificatori logici stabili, rol cu proveniență și câmpuri
separate pentru producător, model, serie, pereche și relația cu alte componente.
Un identificator logic poate exista chiar dacă toate caracteristicile fizice
rămân `UNKNOWN`; identificatorul nu este o măsurătoare.

Rolurile disponibile includ actuatorul de test A, actuatorul de sarcină B,
drive, encoder, cuplaj, senzor de cuplu, controler și calculator. Alegerea unui
rol pentru o componentă reală necesită dovadă din TASK-001 sau din documentația
hardware.

### `SignalMetadata`

Pentru fiecare semnal sunt declarate separat:

- mărimea fizică și unitatea;
- tipul valorii și forma eșantionului;
- hardware-ul și interfața sursă;
- rata nominală și domeniul de ceas;
- nivelul de date (`RAW`, `PROCESSED`, `DERIVED`);
- calibrarea și semnalele-părinte.

Faptul că un câmp se numește „torque” în software nu demonstrează că este un
cuplu măsurat. Această concluzie se exprimă numai prin `physical_quantity`,
`source_hardware_ids`, `calibration_ids` și proveniența lor.

### `CalibrationRecord`

O calibrare identifică țintele, metoda cu proveniență, coeficienții individuali,
starea și intervalul UTC de valabilitate. Cel puțin o țintă hardware sau un
semnal este obligatorie. `UNKNOWN` se păstrează dacă metoda, coeficienții ori
valabilitatea nu sunt documentate.

### `DataArtifact`

Artefactele sunt separate în `RAW`, `PROCESSED` și `DERIVED`. Un artefact
`RAW` trebuie declarat imuabil. Produsele procesate și derivate indică
`parent_artifact_ids`, păstrând trasabilitatea fără suprascrierea datelor brute.
Hash-ul rămâne `UNKNOWN` până când este calculat și înregistrat cu dovadă.

## Modelul temporal

`TimePoint` conține obligatoriu:

- `clock_id` — identifică domeniul de ceas;
- `monotonic_ns` — întreg nenegativ pentru ordine și durate.

Opțional poate conține:

- `sequence_index` pentru detectarea golurilor și reordonării;
- `utc_iso8601` în UTC pentru corelarea între sisteme și jurnalizare;
- `device_ticks` pentru timestamp-ul nativ al dispozitivului.

Duratele se calculează numai din timestamp-uri monotone ale aceluiași ceas.
UTC nu este folosit pentru durate. O relație de sincronizare între ceasuri este
o valoare cu proveniență, nu o presupunere implicită.

## Nivelurile validării

Schema JSON verifică forma documentului, câmpurile obligatorii, enumerările și
regula `null`/`UNKNOWN`. Modulul Python este contractul semantic și verifică în
plus:

- referințele dintre colecții;
- unicitatea identificatorilor;
- ordinea temporală pe același ceas;
- valori finite și intervale de incertitudine valide;
- dovada obligatorie pentru valori cunoscute;
- metoda obligatorie pentru `IDENTIFIED` și `DERIVED`;
- imuabilitatea artefactelor brute.

## Utilizare minimă

```python
from research.schemas.experimental_data import unknown

rated_torque = unknown(unit="N.m")
```

Validarea se execută la construirea dataclass-urilor. Serializarea unui manifest
valid se face cu `manifest.to_json()` sau `manifest.write_json(path)`.
`write_json` refuză suprascrierea unui fișier existent.

Testele contractului se rulează din rădăcina workspace-ului:

```bash
/usr/bin/python3 -m unittest discover \
  -s src/joint_emulator/research/tests -v
```

## Limită explicită a TASK-002

Maparea câmpurilor din logurile curente în această schemă aparține auditului de
logging ulterior. TASK-002 nu declară logurile curente drept date măsurate, nu
creează o calibrare și nu completează valori hardware absente din TASK-001.
