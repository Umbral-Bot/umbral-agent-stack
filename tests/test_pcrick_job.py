"""Offline subprocess/SQLite tests. No CLIs, cloud, VM or account required."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "scripts/vm/pcrick_job.py"
spec = importlib.util.spec_from_file_location("pcrick_job", MODULE)
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class PCRickJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcrick-job-test-")
        self.base = Path(self.temp.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.prompt = self.base / "prompt.txt"
        self.prompt.write_text("Return the hash of the artifact.\n", encoding="utf-8")
        self.skill = self.base / "SKILL.md"
        self.skill.write_text("# Fixture method\n", encoding="utf-8")
        self.proof = self.base / "review.md"
        self.proof.write_text("Fixture reviewed. Process tree quiescent.\n", encoding="utf-8")
        self.registry = job.Registry(self.base / "registry")
        self.req = {
            "job_id": "C23-admission-01", "owner": "rick-grok", "requester": "rick-grok",
            "runner": "codex", "workspace": str(self.workspace),
            "target_host": job.socket.gethostname(), "target_user": job.process_user(),
            "prompt_path": str(self.prompt), "prompt_sha256": job.digest_bytes(self.prompt.read_bytes()),
            "skills_commit": "a" * 40, "skills": [{"name": "fixture", "path": str(self.skill), "sha256": job.digest_bytes(self.skill.read_bytes())}],
            "acceptance": "Output artifact is reviewed independently.", "gui": False,
            "outputs": ["effects.txt"],
        }
        self.profile = {"runner": "codex", "input_mode": "stdin", "argv": [sys.executable, "-c",
            "import sys,pathlib,json; p=sys.stdin.read(); f=pathlib.Path('effects.txt'); "
            "f.open('a').write('once\\n'); print(json.dumps({'type':'thread.started','thread_id':'fixture-thread'})); print(len(p))"]}

    def tearDown(self):
        self.temp.cleanup()

    def reserve(self, req=None):
        return self.registry.reserve(req or self.req, job.digest_bytes(job.json_bytes(self.profile)))

    def new_request(self, job_id="other", gui=False):
        req = deepcopy(self.req)
        req["job_id"] = job_id
        req["gui"] = gui
        path = self.base / job_id
        path.mkdir(exist_ok=True)
        req["workspace"] = str(path)
        return req

    def test_actual_process_stdin_eof_and_dedup_after_restart(self):
        first = job.submit(self.registry, self.req, self.profile)
        second = job.submit(job.Registry(self.registry.root), self.req, self.profile)
        self.assertEqual(first["state"], "PROCESS_EXITED")
        self.assertEqual(second["pid"], first["pid"])
        self.assertEqual((self.workspace / "effects.txt").read_text(), "once\n")
        self.assertEqual(first["exit_code"], 0)
        self.assertEqual(first["session_id"], "fixture-thread")
        self.assertEqual(first["acceptance"], "NOT_REVIEWED")
        self.assertTrue(first["resources"])
        self.assertEqual(first["outputs_before"][0]["state"], "MISSING")
        self.assertEqual(first["outputs_after"][0]["state"], "PRESENT")
        self.assertEqual(first["outputs_after"][0]["sha256"], job.digest_file(self.workspace / "effects.txt"))

    def test_stdout_body_not_returned_in_receipt(self):
        receipt = job.submit(self.registry, self.req, self.profile)
        self.assertEqual(set(receipt["logs"]["stdout.log"]), {"path", "sha256"})
        self.assertNotIn("prompt_path", receipt)
        self.assertNotIn("argv", receipt)

    def test_job_reused_with_changed_contract_rejected(self):
        self.reserve()
        req = dict(self.req, acceptance="Different intent")
        with self.assertRaisesRegex(job.JobError, "JOB_ID_CONFLICT"):
            self.reserve(req)

    def test_profile_change_conflicts_same_id(self):
        self.reserve()
        with self.assertRaisesRegex(job.JobError, "JOB_ID_CONFLICT"):
            self.registry.reserve(self.req, "b" * 64)

    def test_only_one_submitter_wins_same_workspace(self):
        req2 = dict(self.req, job_id="other-job", owner="rick", requester="rick")
        def attempt(req):
            try:
                return self.reserve(req)[0]
            except job.JobError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(attempt, (self.req, req2)))
        self.assertCountEqual(answers, [True, "RESOURCE_BUSY"])

    def test_same_id_parallel_submission_has_one_admission(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.reserve()[0], range(4)))
        self.assertEqual(results.count(True), 1)

    def test_gui_is_shared_between_workspaces_and_owners(self):
        self.reserve(dict(self.req, gui=True))
        req2 = self.new_request(gui=True)
        req2["owner"] = req2["requester"] = "rick"
        with self.assertRaisesRegex(job.JobError, "RESOURCE_BUSY"):
            self.reserve(req2)

    def test_independent_cli_workspaces_can_coexist(self):
        self.reserve()
        self.assertTrue(self.reserve(self.new_request())[0])

    def test_nested_workspace_is_exclusive(self):
        self.reserve()
        child = self.workspace / "nested"
        child.mkdir()
        with self.assertRaisesRegex(job.JobError, "RESOURCE_BUSY"):
            self.reserve(dict(self.req, job_id="child-job", workspace=str(child)))

    def test_old_missing_pid_does_not_release_resource(self):
        _, nonce = self.reserve()
        self.registry.transition(self.req["job_id"], nonce, {"RESERVED"}, "RUNNING", {"pid": 999999999, "started_at": "2000-01-01T00:00:00Z"})
        restored = job.Registry(self.registry.root)
        self.assertEqual(restored.status(self.req["job_id"])["state"], "RUNNING")
        with self.assertRaisesRegex(job.JobError, "RESOURCE_BUSY"):
            self.reserve(dict(self.req, job_id="steal"))

    def test_close_unknown_requires_explicit_reconciliation(self):
        _, nonce = self.reserve()
        self.registry.transition(self.req["job_id"], nonce, {"RESERVED"}, "UNKNOWN", {})
        with self.assertRaisesRegex(job.JobError, "RECONCILIATION_REQUIRED"):
            self.registry.close(self.req["job_id"], "rick-grok", 1, str(self.proof))
        self.registry.close(self.req["job_id"], "rick-grok", 1, str(self.proof), reconciled=True)
        self.assertEqual(self.registry.status(self.req["job_id"])["resources"], [])

    def test_handoff_revokes_previous_owner_generation(self):
        job.submit(self.registry, self.req, self.profile)
        self.registry.handoff(self.req["job_id"], "rick-grok", 1, "rick", str(self.proof))
        with self.assertRaisesRegex(job.JobError, "STALE_OWNER"):
            self.registry.close(self.req["job_id"], "rick-grok", 1, str(self.proof))
        self.registry.close(self.req["job_id"], "rick", 2, str(self.proof))
        self.assertEqual(self.registry.status(self.req["job_id"])["state"], "CLOSED")

    def test_active_handoff_forbidden(self):
        self.reserve()
        with self.assertRaisesRegex(job.JobError, "ACTIVE_HANDOFF_FORBIDDEN"):
            self.registry.handoff(self.req["job_id"], "rick-grok", 1, "rick", str(self.proof))

    def test_close_preserves_original_receipt_for_repeated_submit(self):
        first = job.submit(self.registry, self.req, self.profile)
        self.registry.close(self.req["job_id"], "rick-grok", 1, str(self.proof))
        again = job.submit(self.registry, self.req, self.profile)
        self.assertEqual(again["state"], "CLOSED")
        self.assertEqual(first["pid"], again["pid"])
        self.assertEqual((self.workspace / "effects.txt").read_text(), "once\n")

    def test_prompt_drift_rejected_before_admission(self):
        self.prompt.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(job.JobError, "PROMPT_CHANGED"):
            self.reserve()
        with self.assertRaisesRegex(job.JobError, "JOB_NOT_FOUND"):
            self.registry.status(self.req["job_id"])

    def test_skill_drift_after_reserve_keeps_hold(self):
        _, nonce = self.reserve()
        self.skill.write_text("different", encoding="utf-8")
        receipt = job.execute(self.registry, self.req, self.profile, nonce)
        self.assertEqual(receipt["state"], "UNKNOWN")
        self.assertFalse((self.workspace / "effects.txt").exists())
        self.assertTrue(receipt["resources"])

    def test_bootstrap_cannot_replace_reserved_profile(self):
        _, nonce = self.reserve()
        changed = deepcopy(self.profile)
        changed["argv"].append("unexpected")
        with self.assertRaisesRegex(job.JobError, "BOOTSTRAP_SPEC_MISMATCH"):
            job.execute(self.registry, self.req, changed, nonce)
        self.assertFalse((self.workspace / "effects.txt").exists())

    def test_duplicate_supervisor_cannot_reexecute(self):
        _, nonce = self.reserve()
        job.execute(self.registry, self.req, self.profile, nonce)
        job.execute(self.registry, self.req, self.profile, nonce)
        self.assertEqual((self.workspace / "effects.txt").read_text(), "once\n")

    def test_invalid_types_ids_and_unknown_fields_rejected(self):
        for change in ({"gui": "false"}, {"job_id": "../bad"}, {"job_id": "bad\n"}, {"owner": "david"},
                       {"skills_commit": "latest"}, {"secret": "not-accepted"}, {"skills": []}):
            with self.subTest(change=change), self.assertRaises(job.JobError):
                self.reserve(dict(self.req, **change))

    def test_wrong_destination_is_not_admitted(self):
        for change in ({"target_host": "not-this-host"}, {"target_user": "not-this-user"}):
            with self.subTest(change=change), self.assertRaises(job.JobError):
                self.reserve(dict(self.req, **change))

    def test_output_escape_rejected_and_missing_output_not_hidden(self):
        with self.assertRaisesRegex(job.JobError, "OUTPUT_PATH_INVALID"):
            self.reserve(dict(self.req, outputs=["../outside.txt"]))
        receipt = job.submit(self.registry, dict(self.req, outputs=["not-created.txt"]), self.profile)
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["outputs_after"][0]["state"], "MISSING")
        self.assertEqual(receipt["acceptance"], "NOT_REVIEWED")

    def test_last_arg_mode_closes_stdin(self):
        profile = {"runner": "codex", "input_mode": "last_arg", "argv": [sys.executable, "-c", "import sys; assert sys.stdin.read()==''; assert sys.argv[-1].startswith('Return'); print('ok')"]}
        receipt = job.submit(self.registry, self.req, profile)
        self.assertEqual(receipt["exit_code"], 0)

    def test_nonzero_is_reported_not_accepted(self):
        profile = {"runner": "codex", "input_mode": "stdin", "argv": [sys.executable, "-c", "raise SystemExit(7)"]}
        receipt = job.submit(self.registry, self.req, profile)
        self.assertEqual(receipt["exit_code"], 7)
        self.assertEqual(receipt["acceptance"], "NOT_REVIEWED")

    def test_session_parser_does_not_guess_and_rejects_conflict(self):
        path = self.base / "trace.jsonl"
        path.write_text('{"type":"thread.started","thread_id":"one"}\n{"type":"thread.started","thread_id":"two"}\n', encoding="utf-8")
        self.assertIsNone(job.session_from_log(path, "codex"))
        self.assertIsNone(job.session_from_log(path, "antigravity"))
        path.write_text('{"type":"system","session_id":"session-one"}\n', encoding="utf-8")
        self.assertEqual(job.session_from_log(path, "claude"), "session-one")

    def test_agy_session_schema_observed_in_windows_cli_1_2_3(self):
        # Synthetic IDs with the structure observed in real AGY init/result.
        path = self.base / "agy.jsonl"
        init = {"event": "init", "conversation_id": "agy-session-one",
                "init": {"cwd": str(self.workspace), "permission_mode": "always-proceed"}}
        result = {"event": "result", "result": {"conversation_id": "agy-session-one",
                  "status": "SUCCESS", "num_turns": 2}}
        for events in ([init], [result], [init, result, result]):
            with self.subTest(events=events):
                path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
                self.assertEqual(job.session_from_log(path, "antigravity"), "agy-session-one")

    def test_agy_ambiguous_or_missing_session_stays_unknown(self):
        path = self.base / "agy.jsonl"
        cases = [
            [{"event": "init", "conversation_id": "first"},
             {"event": "result", "result": {"conversation_id": "second", "status": "SUCCESS"}}],
            [{"event": "result", "result": {"conversation_id": "", "status": "ERROR",
              "error": "authentication failed or timed out", "num_turns": 0}}],
            [{"event": "result", "result": None}],
            [{"event": "result", "result": ["not-a-session-record"]}],
            [{"event": "init", "conversation_id": {"invalid": "shape"}}],
            [{"event": "init", "conversation_id": "invalid session"}],
            [{"event": "step_update", "step_update": {"conversation_id": "not-terminal"}},
             {"event": "agent_response", "conversation_id": "not-a-known-event"}],
        ]
        for events in cases:
            with self.subTest(events=events):
                path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
                self.assertIsNone(job.session_from_log(path, "antigravity"))

    def test_agy_subprocess_receipt_records_native_session(self):
        req = dict(self.req, runner="antigravity")
        profile = {"runner": "antigravity", "input_mode": "stdin", "argv": [sys.executable, "-c",
            "import sys,pathlib,json; sys.stdin.read(); pathlib.Path('effects.txt').write_text('once\\n'); "
            "print(json.dumps({'event':'init','conversation_id':'agy-fixture'})); "
            "print(json.dumps({'event':'result','result':{'conversation_id':'agy-fixture','status':'SUCCESS'}}))"]}
        receipt = job.submit(self.registry, req, profile)
        self.assertEqual(receipt["state"], "PROCESS_EXITED")
        self.assertEqual(receipt["session_id"], "agy-fixture")
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["outputs_after"][0]["state"], "PRESENT")
        self.assertEqual(receipt["acceptance"], "NOT_REVIEWED")

    def test_async_start_has_durable_status_without_daemon(self):
        receipt = job.submit(self.registry, self.req, self.profile, background=True)
        self.assertIn(receipt["state"], {"RESERVED", "STARTING", "RUNNING", "PROCESS_EXITED"})
        limit = time.monotonic() + 10
        while time.monotonic() < limit:
            receipt = self.registry.status(self.req["job_id"])
            if receipt["state"] in {"PROCESS_EXITED", "UNKNOWN"}:
                break
            time.sleep(0.05)
        self.assertEqual(receipt["state"], "PROCESS_EXITED")
        self.assertEqual((self.workspace / "effects.txt").read_text(), "once\n")

    def test_reconciled_close_before_spawn_fences_pending_supervisor(self):
        _, nonce = self.reserve()
        original_launch = self.registry.launch
        def close_first_then_launch(job_id, supplied_nonce, spawn):
            self.registry.close(job_id, "rick-grok", 1, str(self.proof), reconciled=True)
            return original_launch(job_id, supplied_nonce, spawn)
        with patch.object(self.registry, "launch", side_effect=close_first_then_launch), patch.object(job.subprocess, "Popen") as spawn:
            result = job.execute(self.registry, self.req, self.profile, nonce)
        spawn.assert_not_called()
        self.assertEqual(result["state"], "CLOSED")
        self.assertFalse((self.workspace / "effects.txt").exists())

    def test_spawn_and_pid_receipt_hold_same_fence_against_close(self):
        _, nonce = self.reserve()
        self.registry.transition(self.req["job_id"], nonce, {"RESERVED"}, "STARTING", {})
        entered = threading.Event()
        allow_spawn_return = threading.Event()
        close_started = threading.Event()
        def spawn():
            entered.set()
            self.assertTrue(allow_spawn_return.wait(5))
            return SimpleNamespace(pid=777)
        def close():
            close_started.set()
            self.registry.close(self.req["job_id"], "rick-grok", 1, str(self.proof), reconciled=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            launched = pool.submit(self.registry.launch, self.req["job_id"], nonce, spawn)
            self.assertTrue(entered.wait(5))
            closed = pool.submit(close)
            self.assertTrue(close_started.wait(5))
            time.sleep(0.1)
            self.assertFalse(closed.done())
            allow_spawn_return.set()
            self.assertEqual(launched.result(5).pid, 777)
            closed.result(5)
        result = self.registry.status(self.req["job_id"])
        self.assertEqual(result["pid"], 777)
        self.assertEqual(result["state"], "CLOSED")

    def test_case_different_ids_use_distinct_log_directories(self):
        first_req = dict(self.req, job_id="Route-Case")
        second_req = self.new_request("second-workspace")
        second_req["job_id"] = "route-case"
        first = job.submit(self.registry, first_req, self.profile)
        second = job.submit(self.registry, second_req, self.profile)
        self.assertEqual(first["state"], "PROCESS_EXITED")
        self.assertEqual(second["state"], "PROCESS_EXITED")
        self.assertNotEqual(first["logs"]["stdout.log"]["path"].casefold(), second["logs"]["stdout.log"]["path"].casefold())

    def test_bootstrap_directory_failure_has_durable_unknown_receipt(self):
        directory = self.registry.job_dir(self.req["job_id"])
        directory.parent.mkdir(parents=True, exist_ok=True)
        directory.write_text("pre-existing fixture obstruction", encoding="utf-8")
        with patch.object(job.subprocess, "Popen") as spawn:
            result = job.submit(self.registry, self.req, self.profile, background=True)
        spawn.assert_not_called()
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertTrue(result["resources"])
        self.assertEqual(result["error_type"], "FileExistsError")

    def test_bootstrap_exclusive_write_failure_has_durable_unknown_receipt(self):
        directory = self.registry.job_dir(self.req["job_id"])
        directory.mkdir(parents=True)
        bootstrap = directory / "bootstrap.json"
        bootstrap.write_text("pre-existing fixture", encoding="utf-8")
        with patch.object(job.subprocess, "Popen") as spawn:
            result = job.submit(self.registry, self.req, self.profile, background=True)
        spawn.assert_not_called()
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(bootstrap.read_text(encoding="utf-8"), "pre-existing fixture")


if __name__ == "__main__":
    unittest.main()
