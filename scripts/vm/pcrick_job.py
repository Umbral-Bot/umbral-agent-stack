"""Durable, transport-neutral admission for PCRick CLI jobs (stdlib only).

Run through the existing authenticated SSH/OpenClaw transport. This is not a
daemon, scheduler, credential store or authorization boundary. A local SQLite
transaction fences cooperating submitters; process output stays private on disk.
No timestamp/PID heuristic releases a reservation. Exited jobs need an explicit
review/close before another job can use the same workspace or GUI desktop.
"""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import threading
import uuid

ACTORS = {"rick", "rick-grok"}
RUNNERS = {"codex", "claude", "antigravity"}
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")


class JobError(ValueError):
    """A stable diagnostic code; do not embed raw tool output in this error."""


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def process_user():
    """OS identity, not caller-controlled USER/USERNAME environment strings."""
    if os.name == "nt":
        import ctypes
        size = ctypes.c_ulong(257)
        name = ctypes.create_unicode_buffer(size.value)
        if not ctypes.windll.advapi32.GetUserNameW(name, ctypes.byref(size)):
            raise JobError("PROCESS_IDENTITY_UNAVAILABLE")
        return name.value
    import pwd
    return pwd.getpwuid(os.geteuid()).pw_name


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def real_path(value, *, directory=False):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise JobError("ABSOLUTE_PATH_REQUIRED")
    path = Path(value).resolve(strict=True)
    if directory != path.is_dir() or (not directory and not path.is_file()):
        raise JobError("PATH_TYPE_INVALID")
    return path


def validated_request(raw):
    """Keep only contract fields; hashes pin content, not a 'latest' label."""
    if not isinstance(raw, dict):
        raise JobError("REQUEST_INVALID")
    required = {"job_id", "requester", "owner", "runner", "workspace", "prompt_path",
                "prompt_sha256", "skills_commit", "skills", "acceptance", "gui", "target_host", "target_user", "outputs"}
    if set(raw) != required:
        raise JobError("REQUEST_FIELDS_INVALID")
    req = dict(raw)
    if not isinstance(req["job_id"], str) or not IDENT.fullmatch(req["job_id"]):
        raise JobError("JOB_ID_INVALID")
    if any(not isinstance(req[k], str) for k in ("requester", "owner", "runner")) or req["requester"] not in ACTORS or req["owner"] not in ACTORS or req["runner"] not in RUNNERS:
        raise JobError("ACTOR_OR_RUNNER_INVALID")
    if not isinstance(req["target_host"], str) or req["target_host"].casefold() != socket.gethostname().casefold():
        raise JobError("WRONG_HOST")
    if not isinstance(req["target_user"], str) or req["target_user"].casefold() != process_user().casefold():
        raise JobError("WRONG_PROCESS_USER")
    if type(req["gui"]) is not bool:
        raise JobError("GUI_BOOLEAN_REQUIRED")
    if not isinstance(req["acceptance"], str) or not req["acceptance"].strip() or len(req["acceptance"]) > 2000:
        raise JobError("ACCEPTANCE_REQUIRED")
    if not isinstance(req["skills_commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", req["skills_commit"]):
        raise JobError("SKILLS_PIN_REQUIRED")
    if not isinstance(req["skills"], list) or not req["skills"]:
        raise JobError("SKILLS_REQUIRED")
    if not isinstance(req["prompt_sha256"], str) or not SHA.fullmatch(req["prompt_sha256"]):
        raise JobError("PROMPT_HASH_REQUIRED")
    req["workspace"] = str(real_path(req["workspace"], directory=True))
    req["prompt_path"] = str(real_path(req["prompt_path"]))
    if not isinstance(req["outputs"], list) or not 1 <= len(req["outputs"]) <= 1000:
        raise JobError("OUTPUTS_REQUIRED")
    for name in req["outputs"]:
        if not isinstance(name, str) or not name or "\x00" in name or Path(name).is_absolute() or ".." in Path(name).parts or name == ".":
            raise JobError("OUTPUT_PATH_INVALID")
    if len(set(req["outputs"])) != len(req["outputs"]):
        raise JobError("OUTPUT_PATH_DUPLICATE")
    seen = set()
    selected = []
    for skill in req["skills"]:
        if not isinstance(skill, dict) or set(skill) != {"name", "path", "sha256"}:
            raise JobError("SKILL_FIELDS_INVALID")
        if not isinstance(skill["name"], str) or not IDENT.fullmatch(skill["name"]) or skill["name"] in seen:
            raise JobError("SKILL_NAME_INVALID")
        if not isinstance(skill["sha256"], str) or not SHA.fullmatch(skill["sha256"]):
            raise JobError("SKILL_HASH_REQUIRED")
        seen.add(skill["name"])
        selected.append({**skill, "path": str(real_path(skill["path"]))})
    req["skills"] = sorted(selected, key=lambda x: x["name"])
    verify_inputs(req)
    return req


def verify_inputs(req):
    if Path(req["prompt_path"]).stat().st_size > 1_000_000:
        raise JobError("PROMPT_CHANGED_OR_OVERSIZE")
    prompt = Path(req["prompt_path"]).read_bytes()
    if len(prompt) > 1_000_000 or digest_bytes(prompt) != req["prompt_sha256"]:
        raise JobError("PROMPT_CHANGED_OR_OVERSIZE")
    prompt.decode("utf-8-sig")
    for skill in req["skills"]:
        if digest_file(skill["path"]) != skill["sha256"]:
            raise JobError("SKILL_CHANGED")
    return prompt


def artifact_inventory(workspace, names):
    root = Path(workspace).resolve(strict=True)
    result = []
    for name in names:
        path = (root / name).resolve()
        item = {"relative_path": name}
        if not path.is_relative_to(root):
            item["state"] = "OUTSIDE_WORKSPACE"
        elif not path.exists():
            item["state"] = "MISSING"
        elif not path.is_file():
            item["state"] = "NOT_FILE"
        else:
            item.update(state="PRESENT", sha256=digest_file(path), bytes=path.stat().st_size)
        result.append(item)
    return result


class Registry:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "jobs.sqlite3"
        with closing(self.connect()) as cx:
            cx.executescript("""
              CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, spec TEXT NOT NULL, spec_hash TEXT NOT NULL,
                owner TEXT NOT NULL, generation INTEGER NOT NULL, state TEXT NOT NULL,
                nonce TEXT NOT NULL, receipt TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS resources (name TEXT PRIMARY KEY, job_id TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
                at TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
            """)

    def connect(self):
        cx = sqlite3.connect(self.db, timeout=15)
        cx.row_factory = sqlite3.Row
        return cx

    @contextmanager
    def transaction(self):
        cx = self.connect()
        try:
            cx.execute("BEGIN IMMEDIATE")
            yield cx
            cx.commit()
        except BaseException:
            cx.rollback()
            raise
        finally:
            cx.close()

    def event(self, cx, job, kind, detail):
        cx.execute("INSERT INTO events(job_id,at,kind,detail) VALUES(?,?,?,?)", (job, utc(), kind, json_bytes(detail).decode()))

    def status(self, job_id):
        with closing(self.connect()) as cx:
            row = cx.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise JobError("JOB_NOT_FOUND")
            receipt = json.loads(row["receipt"])
            receipt.update(owner=row["owner"], generation=row["generation"], state=row["state"])
            receipt["liveness"] = "NOT_CHECKED"
            receipt["resources"] = [r[0] for r in cx.execute("SELECT name FROM resources WHERE job_id=? ORDER BY name", (job_id,))]
            return receipt

    def reserve(self, request, profile_hash):
        req = validated_request(request)
        spec = json_bytes({"request": req, "profile_sha256": profile_hash}).decode()
        spec_hash = digest_bytes(spec.encode())
        job = req["job_id"]
        # Normalize Windows case and aliases before making the exclusion key.
        resources = ["workspace:" + os.path.normcase(req["workspace"])]
        if req["gui"]:
            resources.append("gui:" + socket.gethostname().lower())
        with self.transaction() as cx:
            previous = cx.execute("SELECT spec_hash FROM jobs WHERE id=?", (job,)).fetchone()
            if previous:
                if previous[0] != spec_hash:
                    raise JobError("JOB_ID_CONFLICT")
                return False, None
            for name in resources:
                if cx.execute("SELECT job_id FROM resources WHERE name=?", (name,)).fetchone():
                    raise JobError("RESOURCE_BUSY")
            current_workspace = os.path.normcase(req["workspace"])
            for active in cx.execute("SELECT name FROM resources WHERE name LIKE 'workspace:%'"):
                other = active[0][len("workspace:"):]
                try:
                    common = os.path.commonpath([current_workspace, other])
                except ValueError:  # separate Windows drives
                    continue
                if common in {current_workspace, other}:
                    raise JobError("RESOURCE_BUSY")
            nonce = uuid.uuid4().hex
            receipt = {"job_id": job, "requester": req["requester"], "runner": req["runner"],
                       "host": socket.gethostname(), "user": process_user(), "created_at": utc(),
                       "origin_authentication": "EXTERNAL_TRANSPORT_REQUIRED",
                       "spec_sha256": spec_hash, "profile_sha256": profile_hash,
                       "prompt_sha256": req["prompt_sha256"], "skills_commit": req["skills_commit"],
                       "outputs_before": artifact_inventory(req["workspace"], req["outputs"]),
                       "session_id": None, "exit_code": None, "acceptance": "NOT_REVIEWED"}
            cx.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)", (job, spec, spec_hash, req["owner"], 1, "RESERVED", nonce, json_bytes(receipt).decode()))
            cx.executemany("INSERT INTO resources VALUES(?,?)", [(r, job) for r in resources])
            self.event(cx, job, "RESERVED", {"owner": req["owner"], "generation": 1})
        return True, nonce

    def transition(self, job, nonce, expected, state, details):
        with self.transaction() as cx:
            row = cx.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            if row is None or row["nonce"] != nonce or row["state"] not in expected:
                raise JobError("STALE_EXECUTION")
            receipt = json.loads(row["receipt"])
            receipt.update(details)
            cx.execute("UPDATE jobs SET state=?,receipt=? WHERE id=?", (state, json_bytes(receipt).decode(), job))
            self.event(cx, job, state, details)

    def launch(self, job, nonce, spawn):
        """Serialize the final admission check, actual spawn and PID receipt.

        STARTING was committed before this transaction, so a crash/DB error
        after Popen never makes the same job eligible for another launch.
        close() either wins before this transaction (no spawn), or waits until
        this process has been launched and recorded. There is no late launch
        after CLOSED released a resource.
        """
        with self.transaction() as cx:
            row = cx.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            if row is None or row["nonce"] != nonce or row["state"] != "STARTING":
                raise JobError("STALE_EXECUTION")
            process = spawn()
            details = {"pid": process.pid, "launched_at": utc()}
            receipt = json.loads(row["receipt"])
            receipt.update(details)
            cx.execute("UPDATE jobs SET state='RUNNING',receipt=? WHERE id=?", (json_bytes(receipt).decode(), job))
            self.event(cx, job, "RUNNING", details)
        return process

    def job_dir(self, job_id):
        # SQLite IDs are case-sensitive while NTFS usually is not. Hashing the
        # exact ID also avoids DOS device names and trailing-dot aliases.
        return self.root / "jobs" / digest_bytes(job_id.encode("utf-8"))

    def close(self, job, owner, generation, evidence, *, reconciled=False):
        """Operator attests result/process-tree reconciliation; no auto-unlock."""
        path = real_path(evidence)
        if not path.stat().st_size:
            raise JobError("RECONCILIATION_EVIDENCE_EMPTY")
        proof = {"path": str(path), "sha256": digest_file(path)}
        with self.transaction() as cx:
            row = cx.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            if row is None or row["owner"] != owner or row["generation"] != generation:
                raise JobError("STALE_OWNER")
            if row["state"] == "CLOSED":
                return
            if row["state"] != "PROCESS_EXITED" and not reconciled:
                raise JobError("RECONCILIATION_REQUIRED")
            receipt = json.loads(row["receipt"])
            receipt.update(closed_at=utc(), review_evidence=proof, acceptance="REVIEW_RECORDED")
            cx.execute("UPDATE jobs SET state='CLOSED',receipt=? WHERE id=?", (json_bytes(receipt).decode(), job))
            cx.execute("DELETE FROM resources WHERE job_id=?", (job,))
            self.event(cx, job, "CLOSED", {"owner": owner, "generation": generation, "reconciled": reconciled, "evidence": proof})

    def handoff(self, job, owner, generation, new_owner, evidence):
        if new_owner not in ACTORS or new_owner == owner:
            raise JobError("NEW_OWNER_INVALID")
        path = real_path(evidence)
        if not path.stat().st_size:
            raise JobError("HANDOFF_EVIDENCE_EMPTY")
        with self.transaction() as cx:
            row = cx.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            if row is None or row["owner"] != owner or row["generation"] != generation:
                raise JobError("STALE_OWNER")
            if row["state"] not in {"PROCESS_EXITED", "CLOSED"}:
                raise JobError("ACTIVE_HANDOFF_FORBIDDEN")
            cx.execute("UPDATE jobs SET owner=?,generation=generation+1 WHERE id=?", (new_owner, job))
            self.event(cx, job, "HANDOFF", {"from": owner, "to": new_owner, "generation": generation + 1,
                                           "evidence_sha256": digest_file(path)})


def validated_profile(profile, runner):
    """Local operator config supplies observed argv; never accept request argv."""
    if not isinstance(profile, dict) or set(profile) != {"runner", "argv", "input_mode"}:
        raise JobError("PROFILE_INVALID")
    if profile["runner"] != runner or profile["input_mode"] not in {"stdin", "last_arg"}:
        raise JobError("PROFILE_RUNNER_OR_MODE_INVALID")
    argv = profile["argv"]
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or "\x00" in a for a in argv):
        raise JobError("PROFILE_ARGV_INVALID")
    executable = real_path(argv[0])
    if executable.suffix.lower() in {".cmd", ".bat", ".ps1"}:
        raise JobError("DIRECT_EXECUTABLE_REQUIRED")
    return profile


def execute(registry, request, profile, nonce):
    job = request["job_id"]
    # A detached bootstrap is a transport artifact, not a second source of truth.
    with closing(registry.connect()) as cx:
        record = cx.execute("SELECT spec FROM jobs WHERE id=?", (job,)).fetchone()
        expected = {"request": request, "profile_sha256": digest_bytes(json_bytes(profile))}
        if record is None or json.loads(record["spec"]) != expected:
            raise JobError("BOOTSTRAP_SPEC_MISMATCH")
    try:
        registry.transition(job, nonce, {"RESERVED"}, "STARTING", {"supervisor_pid": os.getpid(), "started_at": utc()})
    except JobError:
        # Duplicate child or old generation: never execute.
        return registry.status(job)
    outdir = registry.job_dir(job)
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        if validated_request(request) != request:  # also checks host/user and resolved paths
            raise JobError("INPUT_PATH_CHANGED")
        prompt = verify_inputs(request)
        argv = list(validated_profile(profile, request["runner"])["argv"])
        mode = profile["input_mode"]
        if mode == "last_arg":
            argv.append(prompt.decode("utf-8-sig"))
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        with (outdir / "stdout.log").open("xb") as stdout, (outdir / "stderr.log").open("xb") as stderr:
            process = registry.launch(job, nonce, lambda: subprocess.Popen(
                argv, cwd=request["workspace"], stdin=subprocess.PIPE if mode == "stdin" else subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, shell=False, creationflags=flags))
            process.communicate(input=prompt if mode == "stdin" else None)
        logs = {name: {"path": str(outdir / name), "sha256": digest_file(outdir / name)}
                for name in ("stdout.log", "stderr.log")}
        # No claim that exit 0 means the desired artifact/tools succeeded.
        registry.transition(job, nonce, {"RUNNING"}, "PROCESS_EXITED", {"exit_code": process.returncode, "exited_at": utc(), "logs": logs,
                                                                     "session_id": session_from_log(outdir / "stdout.log", request["runner"]),
                                                                     "outputs_after": artifact_inventory(request["workspace"], request["outputs"])})
    except Exception as exc:
        try:
            registry.transition(job, nonce, {"STARTING", "RUNNING"}, "UNKNOWN", {"error_type": type(exc).__name__, "observed_at": utc()})
        except JobError as stale:
            if str(stale) != "STALE_EXECUTION":
                raise
    return registry.status(job)


def session_from_log(path, runner):
    """Known structured events only; no inference from free-form prose."""
    ids = set()
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if len(line) > 1_000_000:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            value = None
            if runner == "codex" and event.get("type") == "thread.started":
                value = event.get("thread_id")
            if runner == "claude" and event.get("type") in {"system", "result"}:
                value = event.get("session_id")
            # Antigravity schema must first be observed in the installed CLI.
            if isinstance(value, str) and IDENT.fullmatch(value):
                ids.add(value)
    return next(iter(ids)) if len(ids) == 1 else None


def submit(registry, request, profile, *, background=False):
    req = validated_request(request)
    profile = validated_profile(profile, req["runner"])
    created, nonce = registry.reserve(req, digest_bytes(json_bytes(profile)))
    if not created:
        return registry.status(req["job_id"])
    if not background:
        return execute(registry, req, profile, nonce)
    outdir = registry.job_dir(req["job_id"])
    bootstrap = outdir / "bootstrap.json"
    flags = (getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)) if os.name == "nt" else 0
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        with bootstrap.open("xb") as stream:
            stream.write(json_bytes({"request": req, "profile": profile, "nonce": nonce}))
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--root", str(registry.root), "_execute", "--bootstrap", str(bootstrap)],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=flags, start_new_session=os.name != "nt", close_fds=True)
        # Reap if this caller stays alive; this optional thread never supervises
        # the work and is not required after the launching command has exited.
        threading.Thread(target=child.wait, daemon=True).start()
    except Exception as exc:
        registry.transition(req["job_id"], nonce, {"RESERVED"}, "UNKNOWN", {"error_type": type(exc).__name__})
    return registry.status(req["job_id"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "start"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--request", required=True)
        cmd.add_argument("--profile", required=True)
    cmd = sub.add_parser("_execute")
    cmd.add_argument("--bootstrap", required=True)
    for name in ("status", "close", "handoff"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--job-id", required=True)
        if name != "status":
            cmd.add_argument("--owner", choices=sorted(ACTORS), required=True)
            cmd.add_argument("--generation", type=int, required=True)
            cmd.add_argument("--evidence", required=True)
        if name == "close":
            cmd.add_argument("--reconciled", action="store_true")
        if name == "handoff":
            cmd.add_argument("--new-owner", choices=sorted(ACTORS), required=True)
    args = parser.parse_args(argv)
    try:
        registry = Registry(args.root)
        if args.command in {"run", "start"}:
            result = submit(registry, read_json(args.request), read_json(args.profile), background=args.command == "start")
        elif args.command == "_execute":
            boot = read_json(args.bootstrap)
            result = execute(registry, boot["request"], boot["profile"], boot["nonce"])
        elif args.command == "close":
            registry.close(args.job_id, args.owner, args.generation, args.evidence, reconciled=args.reconciled)
            result = registry.status(args.job_id)
        elif args.command == "handoff":
            registry.handoff(args.job_id, args.owner, args.generation, args.new_owner, args.evidence)
            result = registry.status(args.job_id)
        else:
            result = registry.status(args.job_id)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (JobError, OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc) if isinstance(exc, JobError) else type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
