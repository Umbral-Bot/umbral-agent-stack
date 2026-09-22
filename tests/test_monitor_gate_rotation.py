"""The gate must survive log rotation without hiding genuine duplicate alerts."""

import contextlib
import gzip
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.vps import verify_monitor_gate as gate


class GateRotationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.start = datetime(2026, 9, 19, 14, 15, 18, tzinfo=timezone.utc)
        self.release = "release-under-test"

    def ts(self, minutes=0):
        return (self.start + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def fixture(self):
        events = [{"ts": self.ts(), "kind": "release_deploy", "sha": self.release}]
        for slot in range(48):
            ts = (self.start.replace(minute=30, second=9) + timedelta(minutes=30 * slot)).strftime("%Y-%m-%dT%H:%M:%SZ")
            events.extend([
                {"ts": ts, "kind": "health_check", "release": self.release, "status": "ok"},
                {"ts": ts, "kind": "canary_inference", "release": self.release,
                 "status": "ok", "provider": "anthropic", "fallback_used": True},
            ])
        return events

    def write(self, name, events):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "".join(json.dumps(e) + "\n" for e in events)
        if path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as f:
                f.write(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    def test_split_window_recovers_real_deployment_and_all_48_slots(self):
        events = self.fixture()
        archived = self.write("external/ops_log.jsonl.1.gz", events[:51])
        active = self.write("ops_log.jsonl", list(reversed(events[51:])))
        self.assertIsNone(gate.ultimo_despliegue(active, self.release))
        sources = gate.Registro((active, archived))
        self.assertEqual(gate.ultimo_despliegue(sources, self.release), self.ts())
        self.assertEqual(gate.evaluar(sources, self.ts(), 24, self.release, True), [])
        self.assertEqual(len(gate.leer(sources, self.ts(), self.ts(1440), {"health_check"})), 48)

    def test_overlapping_archives_do_not_inflate_cycles_or_alerts(self):
        events = self.fixture()
        alert = {"ts": events[1]["ts"], "kind": "monitor_alert", "release": self.release,
                 "monitor": "m", "severity": "warn", "reavisos": 0, "fingerprint": "fp"}
        events.append(alert)
        a = self.write("ops_log.jsonl", events)
        b = self.write("ops_log.jsonl.1.gz", list(reversed(events[:60])) + [alert])
        sources = gate.Registro((a, b, a))
        self.assertEqual(sources.duplicates, 61)
        self.assertEqual(len(sources.events), len(events))
        self.assertEqual(gate.evaluar(sources, self.ts(), 24, self.release, True), [])
        self.assertTrue(all(len(m["sha256"]) == 64 for m in sources.manifests))

    def test_real_duplicate_within_one_source_remains_a_failure(self):
        events = self.fixture()
        alert = {"ts": events[1]["ts"], "kind": "monitor_alert", "release": self.release,
                 "monitor": "m", "severity": "warn", "reavisos": 0, "fingerprint": "fp"}
        a = self.write("ops_log.jsonl", events + [alert, alert])
        b = self.write("old.gz", events + [alert])
        sources = gate.Registro((a, b))
        alerts = gate.leer(sources, self.ts(), self.ts(1440), {"monitor_alert"})
        self.assertEqual(len(alerts), 2)
        self.assertTrue(any("duplicado" in x for x in gate.evaluar(sources, self.ts(), 24, self.release, True)))

    def test_different_events_with_same_timestamp_are_never_collapsed(self):
        ok = self.fixture()[1]
        failed = {**ok, "status": "fail"}
        a = self.write("ops_log.jsonl", self.fixture())
        b = self.write("old.gz", [failed])
        sources = gate.Registro((a, b))
        self.assertTrue(any("alarma" in x for x in gate.evaluar(sources, self.ts(), 24, self.release, True)))

    def alert(self, minutes, fingerprint, severity="warn", monitor="m"):
        return {"ts": self.ts(minutes), "kind": "monitor_alert", "release": self.release,
                "monitor": monitor, "severity": severity, "reavisos": 0,
                "fingerprint": fingerprint}

    def test_equal_timestamp_keeps_line_order_and_repeated_occurrences(self):
        warning = self.alert(15, "new")
        recovery = self.alert(15, "recovery", "info")
        suppressed = {"ts": self.ts(16), "kind": "monitor_alert_suppressed"}
        active = self.write("ops_log.jsonl", self.fixture() +
                            [warning, recovery, warning, suppressed])
        sources = gate.Registro((active,))
        self.assertEqual(gate.leer(sources, self.ts(), self.ts(1440), {"monitor_alert"}),
                         [warning, recovery, warning])
        self.assertEqual(gate.evaluar(sources, self.ts(), 24, self.release, True), [])

    def test_rotation_tie_cannot_hide_duplicate_after_recovery(self):
        old = self.alert(0, "old")
        recovery = self.alert(15, "recovery", "info")
        warning = self.alert(15, "new")
        duplicate = self.alert(15.5, "new")
        suppressed = {"ts": self.ts(16), "kind": "monitor_alert_suppressed"}
        archive = self.write("external/ops_log.jsonl.1.gz", self.fixture() + [old, recovery])
        active = self.write("ops_log.jsonl", [warning, duplicate, suppressed])
        sources = gate.Registro((active, archive))
        self.assertEqual(gate.leer(sources, self.ts(), self.ts(1440), {"monitor_alert"}),
                         [old, recovery, warning, duplicate])
        self.assertTrue(any("duplicado" in x for x in
                            gate.evaluar(sources, self.ts(), 24, self.release, True)))

    def test_external_tie_requires_order_only_for_the_same_monitor(self):
        warning = self.alert(15, "new")
        recovery = self.alert(15, "recovery", "info")
        active = self.write("ops_log.jsonl", [warning])
        external = self.write("unknown-origin.gz", [recovery])
        with self.assertRaisesRegex(gate.RegistroInvalido, "orden ambiguo"):
            gate.Registro((active, external))
        # An overlapping source can supply the missing order without any new
        # chronology configuration. Different monitors need no tie-breaker.
        external = self.write("unknown-origin.gz", [recovery, warning])
        self.assertEqual(gate.Registro((active, external)).events, [recovery, warning])
        other = self.alert(15, "other", monitor="independent")
        external = self.write("unknown-origin.gz", [other])
        self.assertEqual(len(gate.Registro((active, external)).events), 2)

    def test_conflicting_overlap_order_fails_closed(self):
        warning = self.alert(15, "new")
        recovery = self.alert(15, "recovery", "info")
        active = self.write("ops_log.jsonl", [warning, recovery])
        archive = self.write("ops_log.jsonl.1.gz", [recovery, warning])
        with self.assertRaisesRegex(gate.RegistroInvalido, "orden contradictorio"):
            gate.Registro((active, archive))

    def test_latest_deploy_is_chronological_not_file_or_line_order(self):
        deploy = self.fixture()[0]
        a = self.write("ops_log.jsonl", [{**deploy, "ts": self.ts(-10)}])
        b = self.write("old.gz", [deploy, {**deploy, "ts": self.ts(-20)}])
        self.assertEqual(gate.ultimo_despliegue(gate.Registro((a, b)), self.release), self.ts())

    def test_missing_corrupt_and_malformed_sources_fail_closed(self):
        bad_gz = self.root / "bad.gz"
        bad_gz.write_bytes(b"not gzip")
        bad_json = self.root / "bad.jsonl"
        bad_json.write_text('{"kind":', encoding="utf-8")
        for path in [self.root / "missing", bad_gz, bad_json]:
            with self.subTest(path=path), self.assertRaises(gate.RegistroInvalido):
                gate.Registro((path,))

    def test_cli_discovers_adjacent_archive_and_reports_historical_scope(self):
        events = self.fixture()
        self.write("ops_log.jsonl.1.gz", events[:51])
        active = self.write("ops_log.jsonl", events[51:])
        p = subprocess.run([sys.executable, str(Path(gate.__file__)), "--ops", str(active),
                            "--release", self.release], capture_output=True, text=True, encoding="utf-8",
                           env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(self.ts(), p.stdout)
        self.assertIn("GATE 24 h: SUPERADO", p.stdout)
        self.assertIn("no cierra incidentes", p.stdout)

    def test_existing_14_acceptance_cases_still_pass(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(gate.autoprueba(), 0)
        self.assertIn("14/14", output.getvalue())


if __name__ == "__main__":
    unittest.main()
