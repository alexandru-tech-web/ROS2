#!/usr/bin/env python3
"""Jurnale de sesiune si export Excel, fara dependente ROS sau externe.

CSV-urile se scriu continuu, astfel incat datele raman disponibile si daca
panoul se inchide inainte de export. XLSX este o fotografie a lor la momentul
apasarii butonului, nu sursa primara de date.
"""
import csv
import math
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape


STATE_FIELDS = (
    "time_s", "time_utc", "pair", "theta_axis_rad", "omega_axis_rad_s",
    "theta_a_sim_rad", "theta_b_sim_rad", "omega_a_sim_rad_s",
    "omega_b_sim_rad_s", "tau_a_cmd_nm", "tau_b_cmd_nm",
    "k_set_nm_rad", "b_set_nms_rad", "k_eff_nm_rad", "b_eff_nms_rad",
    "theta0_rad", "link_ms", "link_jit_ms", "link_loss", "link_down",
    "win_energy_j", "estopped", "reaction_mode", "contact_angle_deg",
    "reset_status", "source",
)
EVENT_FIELDS = (
    "time_s", "time_utc", "event", "pair", "tau_a_cmd_nm",
    "k_set_nm_rad", "b_set_nms_rad", "link_ms", "status",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def checked_session_id(session_id):
    value = str(session_id)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("session_id trebuie sa contina doar litere, cifre, _ sau -")
    return value


def session_path(data_dir, session_id, kind, extension="csv"):
    checked_session_id(session_id)
    return os.path.join(os.path.expanduser(str(data_dir)),
                        f"session_{session_id}_{kind}.{extension}")


class CsvJournal:
    def __init__(self, path, fields):
        self.path = path
        self.fields = fields
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.stream = open(path, "x", newline="", encoding="utf-8", buffering=1)
        self.writer = csv.DictWriter(self.stream, fieldnames=fields)
        self.writer.writeheader()

    def row(self, data):
        self.writer.writerow(data)

    def close(self):
        self.stream.close()


class SessionStateLogger(CsvJournal):
    def __init__(self, path):
        super().__init__(path, STATE_FIELDS)

    def row(self, pair, state, law, link, time_utc=None):
        motors = state.get("motors", {})
        motor_a = motors.get("A", {})
        motor_b = motors.get("B", {})
        data = {
            "time_s": state["t"], "time_utc": time_utc or utc_now(),
            "pair": pair, "theta_axis_rad": state.get("th"),
            "omega_axis_rad_s": state.get("om"),
            "theta_a_sim_rad": motor_a.get("th"),
            "theta_b_sim_rad": motor_b.get("th"),
            "omega_a_sim_rad_s": motor_a.get("om"),
            "omega_b_sim_rad_s": motor_b.get("om"),
            "tau_a_cmd_nm": state.get("tau_a_cmd"),
            "tau_b_cmd_nm": state.get("tau_b"),
            "k_set_nm_rad": getattr(law, "k0", getattr(law, "k", None)),
            "b_set_nms_rad": getattr(law, "b0", getattr(law, "b", None)),
            "k_eff_nm_rad": state.get("k_ef"),
            "b_eff_nms_rad": getattr(law, "b_ef", getattr(law, "b", None)),
            "theta0_rad": getattr(law, "th0", None),
            "link_ms": getattr(link, "ms", None),
            "link_jit_ms": getattr(link, "jit", None),
            "link_loss": getattr(link, "loss", None),
            "link_down": int(bool(getattr(link, "down", False))),
            "win_energy_j": state.get("win_energy"),
            "estopped": int(bool(state.get("estopped", False))),
            "reaction_mode": state.get("reaction_mode"),
            "contact_angle_deg": state.get("contact_angle_deg"),
            "reset_status": state.get("reset_status"),
            "source": motor_a.get("source", "sim"),
        }
        super().row(data)


class SessionEventLogger(CsvJournal):
    def __init__(self, path):
        super().__init__(path, EVENT_FIELDS)

    def row(self, time_s, event, pair="", status="", time_utc=None,
            **values):
        data = {"time_s": time_s, "time_utc": time_utc or utc_now(),
                "event": event, "pair": pair, "status": status}
        data.update(values)
        super().row(data)


def write_config(path, values):
    """Parametrii statici ai rularii; fisier separat de telemetria dinamica."""
    journal = CsvJournal(path, ("key", "value"))
    try:
        for key, value in values.items():
            journal.row({"key": key, "value": value})
    finally:
        journal.close()


def _col_name(index):
    result = ""
    while index:
        index, digit = divmod(index - 1, 26)
        result = chr(65 + digit) + result
    return result


def _cell(value, coordinate):
    if value is None or value == "":
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = None
    if numeric is not None and math.isfinite(numeric):
        return f'<c r="{coordinate}"><v>{numeric:.15g}</v></c>'
    return (f'<c r="{coordinate}" t="inlineStr"><is><t>'
            f'{escape(str(value))}</t></is></c>')


def _write_sheet(archive, index, rows):
    name = f"xl/worksheets/sheet{index}.xml"
    with archive.open(name, "w") as stream:
        stream.write(b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        stream.write(b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')
        for number, values in enumerate(rows, start=1):
            if number > 1_048_576:
                raise ValueError("Sesiunea depaseste limita Excel de 1.048.576 randuri")
            cells = "".join(_cell(value, f"{_col_name(col)}{number}")
                            for col, value in enumerate(values, start=1))
            stream.write(f'<row r="{number}">{cells}</row>'.encode("utf-8"))
        stream.write(b'</sheetData></worksheet>')


def _csv_rows(path, export_time_utc):
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if "time_utc" not in header:
            raise ValueError(f"Jurnalul nu are time_utc: {path}")
        time_col = header.index("time_utc")
        yield header
        for row in reader:
            # Un alt proces poate scrie ultima linie exact in timpul exportului.
            if len(row) == len(header) and row[time_col] <= export_time_utc:
                yield row


def export_session_xlsx(data_dir, session_id, export_time_utc=None):
    """Fotografie completa pana la momentul exportului; nu suprascrie date."""
    data_dir = os.path.expanduser(str(data_dir))
    session_id = checked_session_id(session_id)
    export_time_utc = export_time_utc or utc_now()
    sources = (
        ("Stare", session_path(data_dir, session_id, "states")),
        ("Encodere_6", os.path.join(data_dir, f"motor_encoders_{session_id}.csv")),
        ("Axe_3", os.path.join(data_dir, f"encoders_{session_id}.csv")),
        ("Evenimente", session_path(data_dir, session_id, "events")),
    )
    for _, source in sources:
        if not os.path.isfile(source):
            raise FileNotFoundError(f"Jurnalul sesiunii lipseste: {source}")
    name = f"session_{session_id}_export_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.xlsx"
    target = os.path.join(data_dir, name)
    os.makedirs(data_dir, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(prefix=".vipro_export_", suffix=".xlsx",
                                            dir=data_dir, delete=False)
    temp_path = temporary.name
    temporary.close()
    try:
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED,
                             allowZip64=True) as archive:
            sheet_names = [title for title, _ in sources] + ["Info"]
            types = ''.join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for i in range(1, len(sheet_names) + 1))
            archive.writestr("[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                + types + '</Types>')
            archive.writestr("_rels/.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '</Relationships>')
            sheets = ''.join(
                f'<sheet name="{title}" sheetId="{i}" r:id="rId{i}"/>'
                for i, title in enumerate(sheet_names, start=1))
            archive.writestr("xl/workbook.xml",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets>' + sheets + '</sheets></workbook>')
            relations = ''.join(
                f'<Relationship Id="rId{i}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(sheet_names) + 1))
            archive.writestr("xl/_rels/workbook.xml.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                + relations + '</Relationships>')
            for index, (_, source) in enumerate(sources, start=1):
                _write_sheet(archive, index, _csv_rows(source, export_time_utc))
            info = (("camp", "valoare"), ("session_id", session_id),
                    ("export_time_utc", export_time_utc),
                    ("time_s", "timpul simularii; nu este ceas de perete"),
                    ("time_utc", "ceas UTC ISO 8601 la scrierea jurnalului"),
                    ("source", "SIM; cupluri comandate, nu masurate pe ABB"),
                    ("theta_axis_rad", "pozitia modelului fizic SIM"),
                    ("theta_a_sim_rad", "pozitia simulata a motorului A"),
                    ("theta_b_sim_rad", "pozitia simulata a motorului B"),
                    ("th_raw", "encoder cuantizat, inainte de filtru"),
                    ("th", "pozitie estimata de filtrul alpha-beta-gamma"),
                    ("om", "viteza estimata de acelasi filtru"),
                    ("win_energy_j", "energie pe fereastra glisanta de 1 s"),
                    ("nota", "CSV-urile sursa continua dupa exportul XLSX"))
            config_rows = []
            for origin, path in (
                    ("sim", session_path(data_dir, session_id, "sim_config")),
                    ("encoder", session_path(data_dir, session_id, "encoder_config"))):
                if os.path.isfile(path):
                    with open(path, newline="", encoding="utf-8") as stream:
                        for item in csv.DictReader(stream):
                            config_rows.append((f'{origin}.{item["key"]}',
                                                item["value"]))
            _write_sheet(archive, len(sheet_names), (*info, *config_rows))
        os.link(temp_path, target)  # creat exclusiv; nu suprascrie un export
        return target
    finally:
        os.unlink(temp_path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Exporta o sesiune ViPRO in Excel")
    parser.add_argument("session_id", help="ID-ul comun din numele CSV-urilor")
    parser.add_argument("--data-dir", default="/home/ubuntu/Analiza_Teza/ViPRO/DATE")
    args = parser.parse_args()
    print(export_session_xlsx(args.data_dir, args.session_id))


if __name__ == "__main__":
    main()
