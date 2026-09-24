#!/usr/bin/env python3
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


RESEARCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_ROOT / "tools"))

from rtu_probe import (  # noqa: E402
    ConfigError,
    FrameError,
    READ_FUNCTIONS,
    append_crc,
    build_read_request,
    crc16_modbus,
    enumerate_serial_devices,
    load_config,
    parse_read_response,
    run_probe,
    validate_config,
)


DEFAULT_CONFIG = RESEARCH_ROOT / "configs" / "rtu_probe.yaml"


def active_config(output_directory):
    return {
        "schema_version": "1.0",
        "mode": "ACTIVE_READ_ONLY",
        "serial": {
            "port": "/dev/fake-rs485",
            "baud": 9600,
            "parity": "N",
            "stop_bits": 1,
            "data_bits": 8,
            "timeout_s": 0.1,
        },
        "safety": {
            "allow_active_transmit": True,
            "existing_master_confirmed_absent": True,
            "isolated_rs485_adapter_confirmed": True,
            "wiring_and_topology_approved": True,
        },
        "probe": {
            "active_scan_enabled": True,
            "slave_ids": [7],
            "register_ranges": [{
                "name": "manual-confirmed-range",
                "function": "holding_registers",
                "start_address": 10,
                "count": 2,
            }],
            "inter_request_delay_s": 0.0,
        },
        "output": {"directory": str(output_directory)},
    }


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.closed = False

    def transact(self, request):
        self.requests.append(request)
        return self.response

    def close(self):
        self.closed = True


class FrameTest(unittest.TestCase):
    def test_known_crc_vector(self):
        payload = bytes.fromhex("01 03 00 00 00 0a")
        self.assertEqual(crc16_modbus(payload), 0xCDC5)
        self.assertEqual(append_crc(payload).hex(" "),
                         "01 03 00 00 00 0a c5 cd")

    def test_only_read_function_codes_exist(self):
        self.assertEqual(READ_FUNCTIONS,
                         {"holding_registers": 0x03,
                          "input_registers": 0x04})
        with self.assertRaises(ValueError):
            build_read_request(1, "write_single_register", 0, 1)

    def test_read_response_returns_raw_unsigned_registers(self):
        response = append_crc(bytes.fromhex("07 03 04 12 34 ff fe"))
        parsed = parse_read_response(
            response, expected_slave_id=7,
            expected_function="holding_registers", expected_count=2)
        self.assertEqual(parsed["status"], "ok")
        self.assertEqual(parsed["raw_registers_u16"], [0x1234, 0xFFFE])

    def test_bad_crc_is_rejected(self):
        response = bytearray(append_crc(bytes.fromhex("07 04 02 00 01")))
        response[-1] ^= 0x01
        with self.assertRaises(FrameError):
            parse_read_response(
                bytes(response), expected_slave_id=7,
                expected_function="input_registers", expected_count=1)

    def test_exception_response_is_recorded_without_interpretation(self):
        response = append_crc(bytes.fromhex("07 83 02"))
        parsed = parse_read_response(
            response, expected_slave_id=7,
            expected_function="holding_registers", expected_count=1)
        self.assertEqual(parsed["status"], "modbus_exception")
        self.assertEqual(parsed["exception_code"], 2)


class ConfigurationTest(unittest.TestCase):
    def test_shipped_configuration_is_disabled_and_unknown(self):
        config = load_config(DEFAULT_CONFIG)
        validate_config(config, active=False)
        self.assertEqual(config["mode"], "DRY_RUN")
        self.assertFalse(config["safety"]["allow_active_transmit"])
        self.assertFalse(config["probe"]["active_scan_enabled"])
        self.assertEqual(config["probe"]["slave_ids"], [])
        self.assertEqual(config["probe"]["register_ranges"], [])
        self.assertTrue(all(value is None
                            for value in config["serial"].values()))

    def test_shipped_configuration_cannot_be_activated(self):
        with self.assertRaises(ConfigError):
            validate_config(load_config(DEFAULT_CONFIG), active=True)

    def test_all_safety_gates_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            base = active_config(directory)
            for key in base["safety"]:
                config = copy.deepcopy(base)
                config["safety"][key] = None
                with self.subTest(key=key), self.assertRaises(ConfigError):
                    validate_config(config, active=True)

    def test_unknown_configuration_key_is_rejected(self):
        config = load_config(DEFAULT_CONFIG)
        config["serial"]["register"] = 42
        with self.assertRaises(ConfigError):
            validate_config(config, active=False)


class DryRunTest(unittest.TestCase):
    def test_dry_run_never_constructs_transport(self):
        config = load_config(DEFAULT_CONFIG)

        def forbidden_transport(_):
            raise AssertionError("transport must not be constructed in DRY_RUN")

        result = run_probe(
            config, transmit_read_only=False,
            transport_factory=forbidden_transport)
        self.assertFalse(result["serial_port_opened"])
        self.assertEqual(result["frames_transmitted"], 0)

    def test_serial_enumeration_does_not_open_devices(self):
        def fake_glob(pattern):
            return ["/dev/ttyUSB9"] if "ttyUSB" in pattern else []

        devices = enumerate_serial_devices(globber=fake_glob)
        self.assertEqual([item["path"] for item in devices],
                         ["/dev/ttyUSB9"])


class ActiveReadTest(unittest.TestCase):
    def test_active_probe_logs_raw_frames_and_monotonic_rtt(self):
        with tempfile.TemporaryDirectory() as directory:
            config = active_config(directory)
            response = append_crc(bytes.fromhex("07 03 04 00 11 00 22"))
            transport = FakeTransport(response)
            ticks = iter((1000, 1100, 1300, 1500))

            result = run_probe(
                config,
                transmit_read_only=True,
                transport_factory=lambda _: transport,
                clock=lambda: next(ticks),
                sleeper=lambda _: None,
            )

            self.assertTrue(transport.closed)
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(transport.requests[0][1], 0x03)
            self.assertEqual(result["responding_slave_ids"], [7])
            self.assertEqual(result["rtt_ns"]["min"], 200)
            self.assertFalse(result["register_semantics_interpreted"])

            transaction_path = Path(result["transactions_file"])
            records = [json.loads(line)
                       for line in transaction_path.read_text().splitlines()]
            self.assertEqual(records[1]["raw_registers_u16"], [17, 34])
            self.assertEqual(records[1]["monotonic_start_ns"], 1100)
            self.assertEqual(records[1]["monotonic_end_ns"], 1300)
            self.assertIn("request_hex", records[1])
            self.assertIn("response_hex", records[1])

    def test_only_explicit_ids_and_ranges_are_transmitted(self):
        with tempfile.TemporaryDirectory() as directory:
            config = active_config(directory)
            config["probe"]["slave_ids"] = [7, 9]
            config["probe"]["register_ranges"].append({
                "name": "manual-confirmed-input",
                "function": "input_registers",
                "start_address": 20,
                "count": 1,
            })
            response_by_fc = {
                0x03: append_crc(bytes.fromhex("07 03 04 00 01 00 02")),
                0x04: append_crc(bytes.fromhex("07 04 02 00 03")),
            }

            class EchoingTransport(FakeTransport):
                def transact(self, request):
                    self.requests.append(request)
                    response = bytearray(response_by_fc[request[1]])
                    response[0] = request[0]
                    return append_crc(bytes(response[:-2]))

            transport = EchoingTransport(b"")
            tick = 0

            def clock():
                nonlocal tick
                tick += 100
                return tick

            result = run_probe(
                config,
                transmit_read_only=True,
                transport_factory=lambda _: transport,
                clock=clock,
                sleeper=lambda _: None,
            )
            self.assertEqual(result["transactions"], 4)
            self.assertEqual({request[0] for request in transport.requests},
                             {7, 9})
            self.assertEqual({request[1] for request in transport.requests},
                             {0x03, 0x04})


if __name__ == "__main__":
    unittest.main()
