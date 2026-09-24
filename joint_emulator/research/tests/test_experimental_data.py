#!/usr/bin/env python3
import json
import sys
import unittest
from pathlib import Path


RESEARCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_ROOT))

from schemas.experimental_data import (  # noqa: E402
    ClockDomain,
    ClockMetadata,
    DataArtifact,
    DataTier,
    EvidenceReference,
    ExperimentManifest,
    HardwareManifest,
    ProvenanceCategory,
    ProvenancedValue,
    SessionKind,
    SessionRecord,
    SessionStatus,
    TimePoint,
    unknown,
)


EVIDENCE = (EvidenceReference("synthetic-test", "test fixture"),)


def known(value, *, unit=None):
    return ProvenancedValue(value=value,
                            provenance=ProvenanceCategory.SIMULATED,
                            evidence=EVIDENCE, unit=unit)


class ProvenanceTest(unittest.TestCase):
    def test_unknown_is_null_not_sentinel(self):
        item = unknown(unit="N.m")
        self.assertIsNone(item.value)
        self.assertEqual(item.provenance, ProvenanceCategory.UNKNOWN)

    def test_unknown_cannot_contain_value(self):
        with self.assertRaises(ValueError):
            ProvenancedValue(value=0.0,
                              provenance=ProvenanceCategory.UNKNOWN)

    def test_known_value_requires_evidence(self):
        with self.assertRaises(ValueError):
            ProvenancedValue(value=1.0,
                              provenance=ProvenanceCategory.MEASURED)

    def test_derived_value_requires_method(self):
        with self.assertRaises(ValueError):
            ProvenancedValue(value=1.0,
                              provenance=ProvenanceCategory.DERIVED,
                              evidence=EVIDENCE)


class TimeTest(unittest.TestCase):
    def test_utc_must_be_timezone_aware_and_utc(self):
        with self.assertRaises(ValueError):
            TimePoint("clock-monotonic", 0, utc_iso8601="2026-01-01T00:00:00")
        with self.assertRaises(ValueError):
            TimePoint("clock-monotonic", 0,
                      utc_iso8601="2026-01-01T02:00:00+02:00")

    def test_monotonic_time_cannot_be_negative(self):
        with self.assertRaises(ValueError):
            TimePoint("clock-monotonic", -1)

    def test_monotonic_time_must_be_integer(self):
        with self.assertRaises(ValueError):
            TimePoint("clock-monotonic", 1.5)


class ManifestTest(unittest.TestCase):
    def _manifest(self):
        clock = ClockMetadata(
            clock_id="clock-monotonic",
            domain=ClockDomain.MONOTONIC,
            source=known("synthetic clock"),
            resolution_ns=known(1, unit="ns"),
        )
        artifact = DataArtifact(
            artifact_id="raw-state",
            tier=DataTier.RAW,
            uri="data/raw/synthetic.csv",
            media_type="text/csv",
            immutable=True,
        )
        session = SessionRecord(
            session_id="synthetic-session",
            study_id="schema-test",
            kind=known(SessionKind.SIMULATION),
            status=SessionStatus.COMPLETE,
            start=TimePoint("clock-monotonic", 0,
                            utc_iso8601="2026-01-01T00:00:00Z"),
            end=TimePoint("clock-monotonic", 1_000_000),
            hardware_manifest_id="hardware-empty",
            clock_ids=("clock-monotonic",),
            software_revision=known("synthetic-revision"),
            configuration_hash=unknown(),
            artifact_ids=("raw-state",),
        )
        return ExperimentManifest(
            schema_version="1.0.0",
            session=session,
            hardware=HardwareManifest("hardware-empty", ()),
            clocks=(clock,), signals=(), calibrations=(), trials=(),
            artifacts=(artifact,),
        )

    def test_manifest_is_json_serializable(self):
        payload = json.loads(self._manifest().to_json())
        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertIsNone(payload["session"]["configuration_hash"]["value"])
        self.assertEqual(
            payload["session"]["configuration_hash"]["provenance"],
            "UNKNOWN")

    def test_raw_artifact_must_be_immutable(self):
        with self.assertRaises(ValueError):
            DataArtifact("raw", DataTier.RAW, "data/raw/x.csv", "text/csv",
                         immutable=False)

    def test_missing_reference_is_rejected(self):
        manifest = self._manifest()
        bad_session = SessionRecord(
            session_id=manifest.session.session_id,
            study_id=manifest.session.study_id,
            kind=manifest.session.kind,
            status=manifest.session.status,
            start=manifest.session.start,
            hardware_manifest_id=manifest.session.hardware_manifest_id,
            clock_ids=("missing-clock",),
            software_revision=manifest.session.software_revision,
            configuration_hash=manifest.session.configuration_hash,
        )
        with self.assertRaises(ValueError):
            ExperimentManifest(
                "1.0.0", bad_session, manifest.hardware, manifest.clocks,
                (), (), (), manifest.artifacts)

    def test_duplicate_clock_id_is_rejected(self):
        manifest = self._manifest()
        with self.assertRaises(ValueError):
            ExperimentManifest(
                "1.0.0", manifest.session, manifest.hardware,
                (manifest.clocks[0], manifest.clocks[0]), (), (), (),
                manifest.artifacts)


if __name__ == "__main__":
    unittest.main()
