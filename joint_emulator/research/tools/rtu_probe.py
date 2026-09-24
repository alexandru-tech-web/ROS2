#!/usr/bin/env python3
"""Read-only Modbus RTU discovery utility for the ViPRO bench.

The module deliberately implements only function codes 0x03 and 0x04.  It has
no API for coils, register writes, motor enable, fault reset or motion command.
Without the explicit ``--transmit-read-only`` CLI flag it never opens a serial
port and never emits a frame.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Callable, Mapping, Protocol, Sequence


READ_FUNCTIONS = {
    "holding_registers": 0x03,
    "input_registers": 0x04,
}
SERIAL_PATTERNS = (
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/ttyAMA*",
    "/dev/ttyS*",
)


class ConfigError(ValueError):
    """Configuration is incomplete, ambiguous or unsafe for active probing."""


class FrameError(ValueError):
    """A received frame is incomplete or violates the expected RTU contract."""


class Transport(Protocol):
    def transact(self, request: bytes) -> bytes:
        ...

    def close(self) -> None:
        ...


@dataclass(frozen=True)
class OutputPaths:
    transactions: Path
    summary: Path


def monotonic_ns() -> int:
    """Read CLOCK_MONOTONIC explicitly for transaction timing."""

    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def crc16_modbus(payload: bytes) -> int:
    crc = 0xFFFF
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def append_crc(payload: bytes) -> bytes:
    return payload + crc16_modbus(payload).to_bytes(2, byteorder="little")


def build_read_request(slave_id: int, function: str,
                       start_address: int, count: int) -> bytes:
    """Build one FC03/FC04 request; no write function can be selected."""

    if isinstance(slave_id, bool) or not 1 <= slave_id <= 247:
        raise ValueError("slave_id must be an integer in [1, 247]")
    if function not in READ_FUNCTIONS:
        raise ValueError("function must be holding_registers or input_registers")
    if isinstance(start_address, bool) or not 0 <= start_address <= 0xFFFF:
        raise ValueError("start_address must be an integer in [0, 65535]")
    if isinstance(count, bool) or not 1 <= count <= 125:
        raise ValueError("count must be an integer in [1, 125]")
    if start_address + count > 0x10000:
        raise ValueError("register range exceeds address 65535")
    payload = bytes((slave_id, READ_FUNCTIONS[function]))
    payload += start_address.to_bytes(2, "big")
    payload += count.to_bytes(2, "big")
    return append_crc(payload)


def parse_read_response(response: bytes, *, expected_slave_id: int,
                        expected_function: str,
                        expected_count: int) -> dict[str, Any]:
    if len(response) < 5:
        raise FrameError(f"incomplete response: {len(response)} bytes")
    expected_crc = crc16_modbus(response[:-2])
    received_crc = int.from_bytes(response[-2:], byteorder="little")
    if received_crc != expected_crc:
        raise FrameError(
            f"CRC mismatch: received 0x{received_crc:04x}, "
            f"expected 0x{expected_crc:04x}")
    if response[0] != expected_slave_id:
        raise FrameError(
            f"unexpected slave id {response[0]}, expected {expected_slave_id}")

    function_code = READ_FUNCTIONS[expected_function]
    if response[1] == function_code | 0x80:
        if len(response) != 5:
            raise FrameError("invalid Modbus exception-frame length")
        return {
            "status": "modbus_exception",
            "function_code": response[1],
            "exception_code": response[2],
            "raw_registers_u16": [],
        }
    if response[1] != function_code:
        raise FrameError(
            f"unexpected function code 0x{response[1]:02x}, "
            f"expected 0x{function_code:02x}")

    byte_count = response[2]
    expected_bytes = expected_count * 2
    if byte_count != expected_bytes:
        raise FrameError(
            f"unexpected byte count {byte_count}, expected {expected_bytes}")
    if len(response) != byte_count + 5:
        raise FrameError(
            f"invalid response length {len(response)}, expected {byte_count + 5}")
    register_bytes = response[3:3 + byte_count]
    registers = [
        int.from_bytes(register_bytes[index:index + 2], "big")
        for index in range(0, byte_count, 2)
    ]
    return {
        "status": "ok",
        "function_code": response[1],
        "exception_code": None,
        "raw_registers_u16": registers,
    }


def _strict_keys(value: Mapping[str, Any], *, required: set[str],
                 label: str) -> None:
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    if missing or extra:
        raise ConfigError(f"{label}: missing={missing}, unknown={extra}")


def load_config(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on target image
        raise ConfigError("PyYAML is required to load the probe configuration") from exc
    target = Path(path)
    try:
        payload = yaml.safe_load(target.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read configuration {target}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {target}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError("configuration root must be a mapping")
    return payload


def validate_config(config: Mapping[str, Any], *, active: bool) -> None:
    top_keys = {"schema_version", "mode", "serial", "safety", "probe", "output"}
    _strict_keys(config, required=top_keys, label="configuration")
    if config["schema_version"] != "1.0":
        raise ConfigError("supported schema_version is 1.0")
    if config["mode"] not in {"DRY_RUN", "ACTIVE_READ_ONLY"}:
        raise ConfigError("mode must be DRY_RUN or ACTIVE_READ_ONLY")

    serial_cfg = config["serial"]
    safety = config["safety"]
    probe = config["probe"]
    output = config["output"]
    for name, value in (("serial", serial_cfg), ("safety", safety),
                        ("probe", probe), ("output", output)):
        if not isinstance(value, Mapping):
            raise ConfigError(f"{name} must be a mapping")

    _strict_keys(
        serial_cfg,
        required={"port", "baud", "parity", "stop_bits", "data_bits", "timeout_s"},
        label="serial",
    )
    _strict_keys(
        safety,
        required={"allow_active_transmit", "existing_master_confirmed_absent",
                  "isolated_rs485_adapter_confirmed", "wiring_and_topology_approved"},
        label="safety",
    )
    _strict_keys(
        probe,
        required={"active_scan_enabled", "slave_ids", "register_ranges",
                  "inter_request_delay_s"},
        label="probe",
    )
    _strict_keys(output, required={"directory"}, label="output")

    if not isinstance(probe["slave_ids"], list):
        raise ConfigError("probe.slave_ids must be a list")
    if not isinstance(probe["register_ranges"], list):
        raise ConfigError("probe.register_ranges must be a list")
    if not isinstance(probe["active_scan_enabled"], bool):
        raise ConfigError("probe.active_scan_enabled must be boolean")
    for key, value in safety.items():
        if value is not None and not isinstance(value, bool):
            raise ConfigError(f"safety.{key} must be boolean or null")

    slave_ids = probe["slave_ids"]
    for slave_id in slave_ids:
        if isinstance(slave_id, bool) or not isinstance(slave_id, int):
            raise ConfigError("each slave id must be an integer")
        if not 1 <= slave_id <= 247:
            raise ConfigError("slave ids must be in [1, 247]; broadcast 0 is forbidden")
    if len(slave_ids) != len(set(slave_ids)):
        raise ConfigError("probe.slave_ids contains duplicates")

    range_names: set[str] = set()
    for index, item in enumerate(probe["register_ranges"]):
        if not isinstance(item, Mapping):
            raise ConfigError(f"register_ranges[{index}] must be a mapping")
        _strict_keys(
            item,
            required={"name", "function", "start_address", "count"},
            label=f"register_ranges[{index}]",
        )
        if not isinstance(item["name"], str) or not item["name"].strip():
            raise ConfigError(f"register_ranges[{index}].name must be non-empty")
        if item["name"] in range_names:
            raise ConfigError(f"duplicate register range name: {item['name']}")
        range_names.add(item["name"])
        try:
            build_read_request(1, item["function"], item["start_address"], item["count"])
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"register_ranges[{index}]: {exc}") from exc

    if not active:
        return

    if config["mode"] != "ACTIVE_READ_ONLY":
        raise ConfigError("active transmission requires mode=ACTIVE_READ_ONLY")
    required_true = (
        "allow_active_transmit",
        "existing_master_confirmed_absent",
        "isolated_rs485_adapter_confirmed",
        "wiring_and_topology_approved",
    )
    for key in required_true:
        if safety[key] is not True:
            raise ConfigError(f"active transmission requires safety.{key}=true")
    if probe["active_scan_enabled"] is not True:
        raise ConfigError("active transmission requires probe.active_scan_enabled=true")
    if not slave_ids:
        raise ConfigError("active transmission requires explicit probe.slave_ids")
    if not probe["register_ranges"]:
        raise ConfigError("active transmission requires explicit register_ranges")

    if not isinstance(serial_cfg["port"], str) or not serial_cfg["port"].strip():
        raise ConfigError("active transmission requires serial.port")
    if (isinstance(serial_cfg["baud"], bool) or
            not isinstance(serial_cfg["baud"], int) or serial_cfg["baud"] <= 0):
        raise ConfigError("active transmission requires a positive integer serial.baud")
    if serial_cfg["parity"] not in {"N", "E", "O"}:
        raise ConfigError("serial.parity must be N, E or O")
    if serial_cfg["stop_bits"] not in {1, 1.5, 2}:
        raise ConfigError("serial.stop_bits must be 1, 1.5 or 2")
    if serial_cfg["data_bits"] not in {5, 6, 7, 8}:
        raise ConfigError("serial.data_bits must be one of 5, 6, 7, 8")
    timeout = serial_cfg["timeout_s"]
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or
            not math.isfinite(timeout) or timeout <= 0):
        raise ConfigError("serial.timeout_s must be finite and positive")
    delay = probe["inter_request_delay_s"]
    if (isinstance(delay, bool) or not isinstance(delay, (int, float)) or
            not math.isfinite(delay) or delay < 0):
        raise ConfigError("probe.inter_request_delay_s must be finite and nonnegative")
    if not isinstance(output["directory"], str) or not output["directory"].strip():
        raise ConfigError("active transmission requires output.directory")


def build_plan(config: Mapping[str, Any]) -> dict[str, Any]:
    validate_config(config, active=False)
    unknown = []
    for key, value in config["serial"].items():
        if value is None:
            unknown.append(f"serial.{key}")
    for key, value in config["safety"].items():
        if value is None:
            unknown.append(f"safety.{key}")
    if config["probe"]["inter_request_delay_s"] is None:
        unknown.append("probe.inter_request_delay_s")
    if config["output"]["directory"] is None:
        unknown.append("output.directory")
    return {
        "mode": "DRY_RUN",
        "serial_port_opened": False,
        "frames_transmitted": 0,
        "configured_slave_ids": list(config["probe"]["slave_ids"]),
        "configured_register_ranges": list(config["probe"]["register_ranges"]),
        "planned_transaction_count": (
            len(config["probe"]["slave_ids"])
            * len(config["probe"]["register_ranges"])
        ),
        "unknown_or_unconfirmed": unknown,
    }


def _read_sysfs_text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def enumerate_serial_devices(
    patterns: Sequence[str] = SERIAL_PATTERNS,
    globber: Callable[[str], Sequence[str]] = glob.glob,
) -> list[dict[str, Any]]:
    """Enumerate candidate Linux serial nodes without opening them."""

    paths = sorted({path for pattern in patterns for path in globber(pattern)})
    devices = []
    for raw_path in paths:
        path = Path(raw_path)
        sys_tty = Path("/sys/class/tty") / path.name
        driver_link = sys_tty / "device/driver"
        try:
            driver = driver_link.resolve(strict=True).name
        except OSError:
            driver = None
        device = sys_tty / "device"
        devices.append({
            "path": str(path),
            "resolved_path": str(path.resolve(strict=False)),
            "driver": driver,
            "manufacturer": _read_sysfs_text(device / "../manufacturer"),
            "product": _read_sysfs_text(device / "../product"),
            "serial_number": _read_sysfs_text(device / "../serial"),
        })
    return devices


class SerialRtuTransport:
    """Minimal FC03/FC04 transport. Import/open occurs only in active mode."""

    def __init__(self, serial_config: Mapping[str, Any]):
        try:
            import serial
        except ImportError as exc:  # pragma: no cover - target dependency
            raise RuntimeError("pyserial is required for active RTU probing") from exc
        kwargs = {
            "port": serial_config["port"],
            "baudrate": serial_config["baud"],
            "bytesize": serial_config["data_bits"],
            "parity": serial_config["parity"],
            "stopbits": serial_config["stop_bits"],
            "timeout": serial_config["timeout_s"],
            "write_timeout": serial_config["timeout_s"],
        }
        try:
            self._serial = serial.Serial(exclusive=True, **kwargs)
        except TypeError:  # pyserial/platform without exclusive support
            self._serial = serial.Serial(**kwargs)

    def _read_remaining(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self._serial.read(size - len(chunks))
            if not chunk:
                break
            chunks.extend(chunk)
        return bytes(chunks)

    def transact(self, request: bytes) -> bytes:
        self._serial.reset_input_buffer()
        self._serial.write(request)
        self._serial.flush()
        header = self._read_remaining(3)
        if len(header) < 3:
            return header
        remaining = 2 if header[1] & 0x80 else header[2] + 2
        return header + self._read_remaining(remaining)

    def close(self) -> None:
        self._serial.close()


class JsonlRecorder:
    def __init__(self, directory: str | Path):
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        stem = f"rtu_probe_{tag}_{os.getpid()}"
        self.paths = OutputPaths(
            transactions=output_dir / f"{stem}_transactions.jsonl",
            summary=output_dir / f"{stem}_summary.json",
        )
        self._stream = self.paths.transactions.open("x", encoding="utf-8")

    def record(self, item: Mapping[str, Any]) -> None:
        self._stream.write(json.dumps(item, sort_keys=True) + "\n")
        self._stream.flush()

    def finish(self, summary: Mapping[str, Any]) -> None:
        self._stream.close()
        with self.paths.summary.open("x", encoding="utf-8") as stream:
            json.dump(summary, stream, indent=2, sort_keys=True)
            stream.write("\n")


def _percentile_nearest_rank(values: Sequence[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def _estimated_wire_time_s(config: Mapping[str, Any], byte_count: int) -> float:
    serial_cfg = config["serial"]
    parity_bits = 0 if serial_cfg["parity"] == "N" else 1
    bits_per_character = (
        1 + serial_cfg["data_bits"] + parity_bits + serial_cfg["stop_bits"]
    )
    return byte_count * bits_per_character / serial_cfg["baud"]


def _config_digest(config: Mapping[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_probe(
    config: Mapping[str, Any],
    *,
    transmit_read_only: bool,
    transport_factory: Callable[[Mapping[str, Any]], Transport] = SerialRtuTransport,
    clock: Callable[[], int] = monotonic_ns,
    sleeper: Callable[[float], None] = time.sleep,
    recorder_factory: Callable[[str | Path], JsonlRecorder] = JsonlRecorder,
) -> dict[str, Any]:
    """Run a plan or active read-only probe.

    ``transmit_read_only=False`` returns before transport construction, which
    makes DRY_RUN a testable zero-transmission guarantee.
    """

    if not transmit_read_only:
        return build_plan(config)

    validate_config(config, active=True)
    recorder = recorder_factory(config["output"]["directory"])
    transport = transport_factory(config["serial"])
    rtt_values = []
    responding_ids: set[int] = set()
    status_counts: dict[str, int] = {}
    transactions = 0
    total_wire_bytes = 0
    probe_start_ns = clock()
    try:
        recorder.record({
            "record_type": "configuration",
            "time_utc": utc_now(),
            "config_sha256": _config_digest(config),
            "serial": dict(config["serial"]),
            "function_codes_allowed": sorted(READ_FUNCTIONS.values()),
        })
        plan = [
            (slave_id, register_range)
            for slave_id in config["probe"]["slave_ids"]
            for register_range in config["probe"]["register_ranges"]
        ]
        for plan_index, (slave_id, register_range) in enumerate(plan):
            request = build_read_request(
                slave_id,
                register_range["function"],
                register_range["start_address"],
                register_range["count"],
            )
            start_ns = clock()
            response = b""
            parsed: dict[str, Any]
            try:
                response = transport.transact(request)
                parsed = parse_read_response(
                    response,
                    expected_slave_id=slave_id,
                    expected_function=register_range["function"],
                    expected_count=register_range["count"],
                )
                responding_ids.add(slave_id)
            except Exception as exc:  # transaction errors belong in the log
                parsed = {
                    "status": "communication_error",
                    "function_code": READ_FUNCTIONS[register_range["function"]],
                    "exception_code": None,
                    "raw_registers_u16": [],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            end_ns = clock()
            rtt_ns = end_ns - start_ns
            if rtt_ns < 0:
                raise RuntimeError("CLOCK_MONOTONIC moved backwards")
            rtt_values.append(rtt_ns)
            transactions += 1
            total_wire_bytes += len(request) + len(response)
            status = parsed["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            recorder.record({
                "record_type": "transaction",
                "transaction_index": plan_index,
                "monotonic_start_ns": start_ns,
                "monotonic_end_ns": end_ns,
                "rtt_ns": rtt_ns,
                "time_utc_at_log": utc_now(),
                "slave_id": slave_id,
                "range_name": register_range["name"],
                "function": register_range["function"],
                "function_code": READ_FUNCTIONS[register_range["function"]],
                "start_address": register_range["start_address"],
                "count": register_range["count"],
                "request_hex": request.hex(" "),
                "response_hex": response.hex(" "),
                **parsed,
            })
            if plan_index + 1 < len(plan):
                sleeper(config["probe"]["inter_request_delay_s"])
    finally:
        transport.close()
    probe_end_ns = clock()

    duration_ns = probe_end_ns - probe_start_ns
    wire_time_s = _estimated_wire_time_s(config, total_wire_bytes)
    occupancy = None
    if duration_ns > 0:
        occupancy = wire_time_s / (duration_ns / 1_000_000_000)
    summary = {
        "mode": "ACTIVE_READ_ONLY",
        "time_utc_completed": utc_now(),
        "clock": "CLOCK_MONOTONIC",
        "config_sha256": _config_digest(config),
        "transactions": transactions,
        "responding_slave_ids": sorted(responding_ids),
        "status_counts": status_counts,
        "communication_error_count": status_counts.get("communication_error", 0),
        "modbus_exception_count": status_counts.get("modbus_exception", 0),
        "rtt_ns": {
            "min": min(rtt_values) if rtt_values else None,
            "mean": statistics.fmean(rtt_values) if rtt_values else None,
            "p50": _percentile_nearest_rank(rtt_values, 0.50),
            "p95": _percentile_nearest_rank(rtt_values, 0.95),
            "max": max(rtt_values) if rtt_values else None,
        },
        "probe_duration_ns": duration_ns,
        "raw_wire_bytes_observed": total_wire_bytes,
        "estimated_wire_time_s": wire_time_s,
        "estimated_probe_bus_occupancy_fraction": occupancy,
        "occupancy_note": (
            "Derived from observed request/response byte counts and configured "
            "serial framing; excludes unknown traffic and adapter/drive timing."
        ),
        "register_semantics_interpreted": False,
        "transactions_file": str(recorder.paths.transactions),
        "summary_file": str(recorder.paths.summary),
    }
    recorder.finish(summary)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Modbus RTU discovery tool; dry-run by default")
    parser.add_argument("--config", required=True, help="explicit YAML configuration")
    parser.add_argument(
        "--list-ports", action="store_true",
        help="enumerate candidate Linux serial devices without opening them",
    )
    parser.add_argument(
        "--transmit-read-only", action="store_true",
        help=("open the configured port and emit only FC03/FC04 requests; "
              "all configuration safety gates must also be true"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.list_ports:
            print(json.dumps({"serial_devices": enumerate_serial_devices()}, indent=2))
            if not args.transmit_read_only:
                return 0
        result = run_probe(config, transmit_read_only=args.transmit_read_only)
    except (ConfigError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
