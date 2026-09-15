"""Offline package/supervisor tests: no VM, model, MCP, Task Scheduler or network."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "vm"))
import pcrick_interactive as launcher


class InteractiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcrick-interactive-")
        self.base = Path(self.temp.name)
        self.package = self.base / "package"
        self.registry = self.base / "registry"
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.prompt = self.base / "prompt.txt"
        self.prompt.write_text("Use an absolute Windows path: C:\\Users\\Rick\\test\n", encoding="utf-8")
        self.skill = self.base / "SKILL.md"
        self.skill.write_text("# Fixture", encoding="utf-8")
        for name in ("pythonw.exe", "python.exe", "codex.exe"):
            (self.base / name).write_bytes(b"offline-not-an-executable")
        self.ctx = {"host": "PCRick", "user": "Rick", "sid": "S-1-5-21-1-2-3-1001", "session_id": 1, "elevated": True, "pid": 4242}
        self.patches = [patch.object(launcher, "windows_context", return_value=self.ctx),
                        patch.object(launcher.job.socket, "gethostname", return_value="PCRick"),
                        patch.object(launcher.job, "process_user", return_value="Rick")]
        for p in self.patches:
            p.start()
        self.req = {"job_id": "TEST-CODEX-02", "owner": "rick-grok", "requester": "rick-grok", "runner": "codex",
                    "workspace": str(self.workspace), "target_host": "PCRick", "target_user": "Rick",
                    "prompt_path": str(self.prompt), "prompt_sha256": launcher.job.digest_file(self.prompt),
                    "skills_commit": "a" * 40, "skills": [{"name": "fixture", "path": str(self.skill), "sha256": launcher.job.digest_file(self.skill)}],
                    "acceptance": "Inspect actual output", "outputs": ["result.txt"], "gui": False}
        self.profile = {"runner": "codex", "argv": [str(self.base / "codex.exe"), "exec", "--json", "--dangerously-bypass-approvals-and-sandbox", "-"], "input_mode": "stdin"}
        self.kw = {"package": str(self.package), "registry": str(self.registry), "pythonw": str(self.base / "pythonw.exe")}

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def prepared(self, **kwargs):
        launcher.prepare(self.req, self.profile, **self.kw, write=True, **kwargs)
        return self.package / "manifest.json"

    def records(self):
        return [json.loads(p.read_text()) for p in self.package.glob("task-attempts/*/supervisor.json")]

    def test_plan_has_no_writes_registry_dispatch_or_task_registration(self):
        before = sorted(str(p) for p in self.base.rglob("*"))
        with patch.object(launcher.subprocess, "Popen") as popen, patch.object(launcher.job, "Registry") as registry:
            result = launcher.prepare(self.req, self.profile, **self.kw)
            popen.assert_not_called()
            registry.assert_not_called()
        self.assertEqual(result["state"], "PLAN_ONLY")
        self.assertFalse(result["dispatch"])
        self.assertEqual(before, sorted(str(p) for p in self.base.rglob("*")))

    def test_extra_request_schema_rejected_before_any_write(self):
        for field in ("schema", "argv", "model"):
            with self.subTest(field=field), self.assertRaisesRegex(launcher.job.JobError, "REQUEST_FIELDS_INVALID"):
                launcher.prepare({**self.req, field: "extra"}, self.profile, **self.kw, write=True)
            self.assertFalse(self.package.exists())
            self.assertFalse(self.registry.exists())

    def test_bad_profile_and_prompt_hash_rejected_before_write(self):
        with self.assertRaisesRegex(launcher.job.JobError, "PROFILE_INVALID"):
            launcher.prepare(self.req, {**self.profile, "schema": 1}, **self.kw, write=True)
        with self.assertRaisesRegex(launcher.job.JobError, "PROMPT_CHANGED"):
            launcher.prepare({**self.req, "prompt_sha256": "b" * 64}, self.profile, **self.kw, write=True)
        self.assertFalse(self.package.exists())

    def test_prepare_is_immutable_even_before_admission(self):
        self.prepared()
        before = {p.name: p.read_bytes() for p in self.package.iterdir()}
        with self.assertRaisesRegex(launcher.job.JobError, "PACKAGE_EXISTS_USE_STATUS"):
            launcher.prepare(self.req, self.profile, **self.kw, write=True)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.package.iterdir()})
        self.assertFalse(self.registry.exists())

    def test_json_roundtrip_and_task_xml_windows_spaces_quotes_unicode(self):
        manifest_path = self.prepared()
        m = launcher.job.read_json(manifest_path)
        m["package"] = "C:\\Users\\Rick\\job á & b"
        m["supervisor"] = "C:\\Users\\Rick\\my tools\\pcrick_interactive.py"
        xml = ET.fromstring(launcher.task_xml(m, "ignored"))
        ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
        self.assertEqual(xml.findtext("t:Actions/t:Exec/t:Arguments", namespaces=ns), subprocess.list2cmdline([m["supervisor"], "supervise", "--manifest", str(Path(m["package"]) / "manifest.json")]))
        self.assertEqual(xml.findtext("t:Settings/t:ExecutionTimeLimit", namespaces=ns), "PT0S")
        self.assertEqual(xml.findtext("t:Settings/t:MultipleInstancesPolicy", namespaces=ns), "IgnoreNew")
        self.assertEqual(xml.findtext("t:Principals/t:Principal/t:RunLevel", namespaces=ns), "HighestAvailable")
        self.assertEqual(xml.findtext("t:Principals/t:Principal/t:LogonType", namespaces=ns), "InteractiveToken")
        self.assertEqual(len(xml.find("t:Triggers", ns)), 0)
        self.assertEqual(json.loads(launcher.job.json_bytes(m)), m)
        self.assertFalse(list(self.package.glob("*.py")))

    def test_wrong_runtime_context_never_launches(self):
        manifest = self.prepared()
        for change in ({"host": "TARRO"}, {"user": "David"}, {"session_id": 0}, {"elevated": False}, {"sid": "S-1-5-21-1-2-3-1002"}):
            with self.subTest(change=change), patch.object(launcher, "windows_context", return_value={**self.ctx, **change}), patch.object(launcher.subprocess, "Popen") as popen:
                with self.assertRaises(launcher.job.JobError):
                    launcher.supervise(manifest)
                popen.assert_not_called()
                self.assertFalse((self.package / "task-attempts").exists())

    def test_profile_hash_drift_and_missing_hash_never_launch(self):
        manifest = self.prepared()
        original = (self.package / "profile.json").read_bytes()
        (self.package / "profile.json").write_bytes(original + b"\n")
        with patch.object(launcher.subprocess, "Popen") as popen:
            self.assertEqual(launcher.supervise(manifest), 1)
            self.assertEqual(self.records()[0]["diagnostic_code"], "PACK_HASH_CHANGED")
            self.assertEqual(self.records()[0]["state"], "FAILED_BEFORE_LAUNCH")
            popen.assert_not_called()
        (self.package / "profile.json").write_bytes(original)
        m = launcher.job.read_json(manifest)
        del m["expected_sha256"][m["runner"]]
        manifest.write_bytes(launcher.job.json_bytes(m))
        with self.assertRaisesRegex(launcher.job.JobError, "MANIFEST_HASH_SET_INVALID"):
            launcher.validate_manifest(manifest)

    def test_replay_delegates_same_job_to_existing_runner_without_second_ledger(self):
        manifest = self.prepared()
        child = Mock(pid=9876, returncode=0)
        with patch.object(launcher.subprocess, "Popen", return_value=child) as popen, patch.object(launcher.job, "Registry") as registry:
            self.assertEqual(launcher.supervise(manifest), 0)
            self.assertEqual(launcher.supervise(manifest), 0)
            self.assertEqual(popen.call_args_list[0].args, popen.call_args_list[1].args)
            self.assertIn("run", popen.call_args.args[0])
            self.assertNotIn("start", popen.call_args.args[0])
            registry.assert_not_called()
        records = self.records()
        self.assertEqual(len(records), 2)
        self.assertEqual(len({r["attempt_id"] for r in records}), 2)
        self.assertTrue(all(r["pid"] == 4242 and r["runner_pid"] == 9876 for r in records))
        self.assertFalse(self.registry.exists())

    def test_timeout_persists_uncertainty_waits_and_never_kills_closes_or_releases(self):
        manifest = self.prepared()
        child = Mock(pid=1111, returncode=0)
        waits = []
        def wait(timeout=None):
            waits.append(timeout)
            if timeout is not None:
                raise subprocess.TimeoutExpired("fixture", timeout)
            self.assertEqual(self.records()[0]["state"], "TIMEOUT_UNRECONCILED")
            return 0
        child.wait.side_effect = wait
        with patch.object(launcher.subprocess, "Popen", return_value=child) as popen, patch.object(launcher.job.Registry, "close") as close:
            self.assertEqual(launcher.supervise(manifest), 0)
            self.assertEqual(popen.call_count, 1)
            close.assert_not_called()
        self.assertEqual(waits, [720, None])
        child.kill.assert_not_called()
        child.terminate.assert_not_called()
        self.assertEqual(self.records()[0]["state"], "PROCESS_EXITED_AFTER_TIMEOUT")
        self.assertFalse(self.registry.exists())

    def test_popen_failure_keeps_failed_before_launch_evidence(self):
        manifest = self.prepared()
        with patch.object(launcher.subprocess, "Popen", side_effect=OSError("sensitive message")):
            self.assertEqual(launcher.supervise(manifest), 1)
        record = self.records()[0]
        self.assertEqual(record["state"], "FAILED_BEFORE_LAUNCH")
        self.assertEqual(record["error_type"], "OSError")
        self.assertNotIn("sensitive", json.dumps(record))

    def test_repeated_checkpoint_failure_after_spawn_still_waits_for_live_child(self):
        manifest = self.prepared()
        child = Mock(pid=3333, returncode=None)
        child.poll.return_value = None
        started = False
        original = launcher.atomic_json
        def spawn(*args, **kwargs):
            nonlocal started
            started = True
            return child
        def atomic(path, value):
            if started:
                raise OSError("fixture receipt write unavailable")
            return original(path, value)
        def wait():
            child.returncode = 0
            child.poll.return_value = 0
        child.wait.side_effect = wait
        with patch.object(launcher.subprocess, "Popen", side_effect=spawn) as popen, patch.object(launcher, "atomic_json", side_effect=atomic), patch.object(launcher.job.Registry, "close") as close:
            self.assertEqual(launcher.supervise(manifest), 1)
            popen.assert_called_once()
            child.wait.assert_called_once_with()
            close.assert_not_called()
        child.kill.assert_not_called()
        child.terminate.assert_not_called()
        self.assertEqual(self.records()[0]["state"], "ADMISSION_PENDING")
        self.assertFalse(self.registry.exists())

    def policy(self):
        config = self.base / "config.toml"
        config.write_text("[mcp_servers.Revit]\ncommand='does-not-exist'\n", encoding="utf-8")
        return {"observed_servers": ["Revit", "node_repl"], "enabled_servers": [], "config_path": str(config), "config_sha256": launcher.job.digest_file(config)}

    def test_mcp_override_argv_is_exact_preserves_permissions_and_does_not_launch(self):
        policy = self.policy()
        config_before = Path(policy["config_path"]).read_bytes()
        with patch.object(launcher.subprocess, "Popen") as popen:
            manifest = self.prepared(mcp_policy=policy)
            popen.assert_not_called()
        profile = launcher.job.read_json(self.package / "profile.json")
        self.assertEqual(profile["argv"], [self.profile["argv"][0], "-c", "mcp_servers.Revit.enabled=false", "-c", "mcp_servers.node_repl.enabled=false", *self.profile["argv"][1:]])
        launcher.validate_manifest(manifest)
        self.assertEqual(Path(policy["config_path"]).read_bytes(), config_before)

    def test_mcp_unknown_dotted_or_quoted_ids_fail_closed(self):
        for bad in ("Revit.foo", '"Revit"', "Revit foo"):
            policy = {**self.policy(), "observed_servers": [bad]}
            with self.subTest(bad=bad), self.assertRaisesRegex(launcher.job.JobError, "MCP_IDS_INVALID"):
                launcher.prepare(self.req, self.profile, **self.kw, mcp_policy=policy, write=True)
        with self.assertRaisesRegex(launcher.job.JobError, "MCP_UNKNOWN_ENABLED_ID"):
            launcher.prepare(self.req, self.profile, **self.kw, mcp_policy={**self.policy(), "enabled_servers": ["unknown"]}, write=True)
        self.assertFalse(self.package.exists())

    def test_mcp_config_drift_is_checked_at_launch(self):
        policy = self.policy()
        manifest = self.prepared(mcp_policy=policy)
        Path(policy["config_path"]).write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(launcher.job.JobError, "PACK_HASH_CHANGED"):
            launcher.validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
