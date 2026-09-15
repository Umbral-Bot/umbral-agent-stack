"""Prepare (never dispatch) and supervise an Interactive PCRick job package.

Only pcrick_job owns admission and resource reservations. All generated input is
JSON/XML, not Python or shell source containing interpolated Windows paths.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

import pcrick_job as job

MANIFEST_FIELDS = {"schema", "job_id", "package", "runner", "registry", "request",
                   "profile", "python", "pythonw", "supervisor", "target_sid",
                   "timeout_seconds", "expected_sha256", "mcp_selection"}


def windows_context():
    """Identity from the process token; no USERNAME/SESSIONNAME environment trust."""
    if os.name != "nt":
        raise job.JobError("WINDOWS_REQUIRED")
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
    adv.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(w.LPWSTR)]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    token, size, sid_text = w.HANDLE(), w.DWORD(), w.LPWSTR()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise job.JobError("PROCESS_TOKEN_UNAVAILABLE")
    try:
        adv.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buffer, size.value, ctypes.byref(size)):
            raise job.JobError("PROCESS_SID_UNAVAILABLE")
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        if not adv.ConvertSidToStringSidW(sid, ctypes.byref(sid_text)):
            raise job.JobError("PROCESS_SID_UNAVAILABLE")
        user_sid = sid_text.value
    finally:
        if sid_text:
            kernel.LocalFree(ctypes.cast(sid_text, ctypes.c_void_p))
        kernel.CloseHandle(token)
    session = w.DWORD()
    if not kernel.ProcessIdToSessionId(os.getpid(), ctypes.byref(session)):
        raise job.JobError("PROCESS_SESSION_UNAVAILABLE")
    return {"host": socket.gethostname(), "user": job.process_user(), "sid": user_sid,
            "session_id": session.value, "elevated": bool(ctypes.windll.shell32.IsUserAnAdmin()),
            "pid": os.getpid()}


def check_context(context, *, interactive=False, sid=None):
    if context["host"].casefold() != "pcrick" or context["user"].casefold() != "rick":
        raise job.JobError("PCRICK_RICK_REQUIRED")
    if not re.fullmatch(r"S-1-5-21-(?:\d+-){3}\d+", context["sid"]):
        raise job.JobError("LOCAL_USER_SID_REQUIRED")
    if sid is not None and context["sid"] != sid:
        raise job.JobError("TASK_SID_CHANGED")
    if interactive and (context["session_id"] == 0 or not context["elevated"]):
        raise job.JobError("INTERACTIVE_HIGHEST_REQUIRED")


def absolute_path(value):
    if not isinstance(value, str) or not Path(value).is_absolute() or value.startswith(("\\\\", "//")):
        raise job.JobError("ABSOLUTE_LOCAL_PATH_REQUIRED")
    return str(Path(value).resolve())


def selected_profile(profile, policy):
    """Codex 0.154 accepts simple ID overrides; reject ambiguous key syntax."""
    if policy is None:
        return profile, None
    required = {"observed_servers", "enabled_servers", "config_path", "config_sha256"}
    if profile["runner"] != "codex" or not isinstance(policy, dict) or set(policy) != required:
        raise job.JobError("MCP_POLICY_INVALID")
    for key in ("observed_servers", "enabled_servers"):
        ids = policy[key]
        if not isinstance(ids, list) or any(not isinstance(i, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", i) for i in ids) or len(set(ids)) != len(ids):
            raise job.JobError("MCP_IDS_INVALID")
    if not set(policy["enabled_servers"]) <= set(policy["observed_servers"]):
        raise job.JobError("MCP_UNKNOWN_ENABLED_ID")
    path = str(job.real_path(policy["config_path"]))
    if job.digest_file(path) != policy["config_sha256"]:
        raise job.JobError("MCP_CONFIG_CHANGED")
    # Fixed native executable, never insert into node.exe's own argument list.
    if Path(profile["argv"][0]).name.casefold() != "codex.exe":
        raise job.JobError("MCP_NATIVE_CODEX_REQUIRED")
    disabled = sorted(set(policy["observed_servers"]) - set(policy["enabled_servers"]))
    if any("mcp_servers" in arg for arg in profile["argv"][1:]):
        raise job.JobError("MCP_OVERRIDE_ALREADY_PRESENT")
    flags = [arg for name in disabled for arg in ("-c", f"mcp_servers.{name}.enabled=false")]
    return {**profile, "argv": [profile["argv"][0], *flags, *profile["argv"][1:]]}, {**policy, "config_path": path}


def task_xml(manifest, task_name):
    ns = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    ET.register_namespace("", ns)
    def add(parent, tag, text=None, **attrs):
        node = ET.SubElement(parent, "{" + ns + "}" + tag, attrs)
        node.text = text
        return node
    root = ET.Element("{" + ns + "}Task", {"version": "1.4"})
    add(add(root, "RegistrationInfo"), "Description", "PCRick prepared job " + manifest["job_id"])
    add(root, "Triggers")
    principal = add(add(root, "Principals"), "Principal", id="Rick")
    add(principal, "UserId", manifest["target_sid"])
    add(principal, "LogonType", "InteractiveToken")
    add(principal, "RunLevel", "HighestAvailable")
    settings = add(root, "Settings")
    add(settings, "MultipleInstancesPolicy", "IgnoreNew")
    add(settings, "ExecutionTimeLimit", "PT0S")
    add(settings, "DisallowStartIfOnBatteries", "false")
    add(settings, "StopIfGoingOnBatteries", "false")
    action = add(add(root, "Actions", Context="Rick"), "Exec")
    add(action, "Command", manifest["pythonw"])
    add(action, "Arguments", subprocess.list2cmdline([manifest["supervisor"], "supervise", "--manifest", str(Path(manifest["package"]) / "manifest.json")]))
    add(action, "WorkingDirectory", manifest["package"])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def prepare(request, profile, *, package, registry, pythonw, timeout_seconds=720, mcp_policy=None, write=False):
    context = windows_context()
    check_context(context)
    req = job.validated_request(request)  # exact existing contract, before ANY write
    profile = job.validated_profile(profile, req["runner"])
    profile, policy = selected_profile(profile, mcp_policy)
    package, registry = absolute_path(package), absolute_path(registry)
    if package == registry or Path(package).is_relative_to(registry) or Path(registry).is_relative_to(package):
        raise job.JobError("PACKAGE_REGISTRY_OVERLAP")
    pythonw = str(job.real_path(pythonw))
    if Path(pythonw).name.casefold() != "pythonw.exe":
        raise job.JobError("PYTHONW_REQUIRED")
    python = str(job.real_path(str(Path(pythonw).with_name("python.exe"))))
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 86400:
        raise job.JobError("TIMEOUT_INVALID")
    if Path(package).exists():
        raise job.JobError("PACKAGE_EXISTS_USE_STATUS")
    runner, supervisor = str(Path(job.__file__).resolve()), str(Path(__file__).resolve())
    files = {str(Path(package) / "request.json"): job.json_bytes(req),
             str(Path(package) / "profile.json"): job.json_bytes(profile)}
    expected = {path: job.digest_bytes(data) for path, data in files.items()}
    for path in [runner, supervisor, python, pythonw, req["prompt_path"], *[s["path"] for s in req["skills"]], *([policy["config_path"]] if policy else [])]:
        expected[path] = job.digest_file(path)
    manifest = {"schema": 1, "job_id": req["job_id"], "package": package, "runner": runner,
                "registry": registry, "request": str(Path(package) / "request.json"),
                "profile": str(Path(package) / "profile.json"), "python": python, "pythonw": pythonw,
                "supervisor": supervisor, "target_sid": context["sid"], "timeout_seconds": timeout_seconds,
                "expected_sha256": expected, "mcp_selection": policy}
    name = "Umbral-PCRick-" + job.digest_bytes(req["job_id"].encode())[:24]
    files[str(Path(package) / "manifest.json")] = job.json_bytes(manifest)
    files[str(Path(package) / "task.xml")] = task_xml(manifest, name)
    summary = {"state": "PREPARED_NOT_REGISTERED" if write else "PLAN_ONLY", "job_id": req["job_id"],
               "task_name": name, "package": package, "registry": registry,
               "files": sorted(files), "dispatch": False, "admitted": False}
    if write:
        Path(package).mkdir(parents=True, exist_ok=False)
        for path, data in files.items():
            with Path(path).open("xb") as stream:
                stream.write(data)
    return summary


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with tmp.open("xb") as stream:
        stream.write(job.json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def validate_manifest(path):
    path = job.real_path(str(path))
    m = job.read_json(path)
    if not isinstance(m, dict) or set(m) != MANIFEST_FIELDS or type(m["schema"]) is not int or m["schema"] != 1:
        raise job.JobError("MANIFEST_INVALID")
    if Path(absolute_path(m["package"])) != path.parent or path.name != "manifest.json":
        raise job.JobError("MANIFEST_LOCATION_CHANGED")
    context = windows_context()
    check_context(context, interactive=True, sid=m["target_sid"])
    for key in ("request", "profile"):
        if Path(m[key]) != path.parent / (key + ".json"):
            raise job.JobError("PACKAGE_INPUT_LOCATION_CHANGED")
    if m["runner"] != str(Path(job.__file__).resolve()) or m["supervisor"] != str(Path(__file__).resolve()):
        raise job.JobError("LAUNCHER_LOCATION_CHANGED")
    if type(m["timeout_seconds"]) is not int or not 1 <= m["timeout_seconds"] <= 86400:
        raise job.JobError("TIMEOUT_INVALID")
    absolute_path(m["registry"])
    req = job.validated_request(job.read_json(m["request"]))
    job.validated_profile(job.read_json(m["profile"]), req["runner"])
    if req["job_id"] != m["job_id"]:
        raise job.JobError("JOB_ID_CHANGED")
    expected = m["expected_sha256"]
    required = {m[k] for k in ("request", "profile", "runner", "supervisor", "python", "pythonw")}
    required |= {req["prompt_path"], *[s["path"] for s in req["skills"]]}
    policy = m["mcp_selection"]
    if policy is not None:
        if not isinstance(policy, dict) or not isinstance(policy.get("config_path"), str):
            raise job.JobError("MCP_POLICY_INVALID")
        required.add(policy["config_path"])
    if not isinstance(expected, dict) or set(expected) != required:
        raise job.JobError("MANIFEST_HASH_SET_INVALID")
    for filename, digest in expected.items():
        if not isinstance(digest, str) or not job.SHA.fullmatch(digest) or job.digest_file(job.real_path(filename)) != digest:
            raise job.JobError("PACK_HASH_CHANGED")
    return m, context


def supervise(manifest_path):
    # The trusted local Task action supplies this path. Preflight failures also
    # need durable diagnostics because pythonw has no console. No admission occurs.
    manifest_path = job.real_path(str(manifest_path))
    if manifest_path.name != "manifest.json":
        raise job.JobError("MANIFEST_LOCATION_CHANGED")
    context = windows_context()
    check_context(context, interactive=True)
    package = manifest_path.parent
    attempt_id = uuid.uuid4().hex
    attempt = package / "task-attempts" / attempt_id
    attempt.mkdir(parents=True, exist_ok=False)
    record = {**context, "attempt_id": attempt_id, "job_id": "UNVALIDATED", "utc_started": job.utc(),
              "origin_authentication": "EXTERNAL_TRANSPORT_REQUIRED", "admission": "EXISTING_RUNNER_ONLY"}
    process, timed_out = None, False
    def checkpoint(state, error=None):
        update = {**record, "state": state, "utc_observed": job.utc()}
        if process is not None:
            update["runner_pid"] = process.pid  # observed PID, never a liveness claim
        if error:
            update["error_type"] = error
        atomic_json(attempt / "supervisor.json", update)
    try:
        checkpoint("VALIDATING")
        m, context = validate_manifest(manifest_path)
        record["job_id"] = m["job_id"]
        argv = [m["python"], m["runner"], "--root", m["registry"], "run", "--request", m["request"], "--profile", m["profile"]]
        atomic_json(attempt / "command.json", {"argv": argv})
        checkpoint("ADMISSION_PENDING")
        with (attempt / "stdout.json").open("xb") as out, (attempt / "stderr.txt").open("xb") as err:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       cwd=package, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            checkpoint("RUNNING")
            try:
                process.wait(timeout=m["timeout_seconds"])
            except subprocess.TimeoutExpired:
                timed_out = True
                checkpoint("TIMEOUT_UNRECONCILED", "TimeoutExpired")
                process.wait()  # no kill, close, retry or lease operation
        record["exit_code"] = process.returncode
        checkpoint("PROCESS_EXITED_AFTER_TIMEOUT" if timed_out else "PROCESS_EXITED")
        return process.returncode
    except Exception as exc:
        if isinstance(exc, job.JobError):
            record["diagnostic_code"] = str(exc)
        checkpoint("FAILED_UNRECONCILED" if process is not None else "FAILED_BEFORE_LAUNCH", type(exc).__name__)
        if process is not None and process.poll() is None:
            process.wait()
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Validate and show plan; --write creates package only")
    for arg in ("request", "profile", "package", "registry", "pythonw"):
        prep.add_argument("--" + arg, required=True)
    prep.add_argument("--timeout-seconds", type=int, default=720)
    prep.add_argument("--mcp-policy")
    prep.add_argument("--write", action="store_true")
    run = sub.add_parser("supervise")
    run.add_argument("--manifest", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "supervise":
            return supervise(args.manifest)
        result = prepare(job.read_json(args.request), job.read_json(args.profile), package=args.package,
                         registry=args.registry, pythonw=args.pythonw, timeout_seconds=args.timeout_seconds,
                         mcp_policy=job.read_json(args.mcp_policy) if args.mcp_policy else None, write=args.write)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"state": "FAILED", "error": str(exc) if isinstance(exc, job.JobError) else type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
