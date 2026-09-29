#!/usr/bin/env python3
"""Offline, read-only validator for a teaching package against a CSV manifest.

Usage:
    python scripts/validate_teaching_package.py ROOT --manifest MANIFEST.csv \
        --role {teacher,student} [--forbid PATH ...] [--forbidden-list FILE] \
        [--reviewed-ok PATH ...] [--json-out FILE]

The manifest is UTF-8 (BOM allowed) CSV with the columns ``ruta,bytes,sha256``
(extra columns are ignored). ``ruta`` is relative to ROOT and may use ``/`` or
``\\`` as separator.

Output: JSON report to stdout (human summary to stderr), or JSON to
``--json-out`` (must be outside ROOT) with the human summary to stdout.

Exit codes: 0 = PASS, 1 = FAIL (findings), 2 = invalid invocation/config.

Scope: byte-level integrity of the package only. It never modifies, extracts or
executes package files, never follows symlinks, and never prints file content.
``native_gui`` and ``student_download`` are always ``NOT_RUN``: integrity does
not prove that Power BI/Revit files open, that students can access the
download, or that a Drive copy is in sync. See
docs/operations/teaching-package-validator.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import stat
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

REPORT_VERSION = 1
CHUNK_SIZE = 1024 * 1024
REQUIRED_COLUMNS = ("ruta", "bytes", "sha256")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SIZE_RE = re.compile(r"^[0-9]+$")
DRIVE_RE = re.compile(r"^[A-Za-z]:")
MAX_SHOWN_PATH = 240

# Student-mode naming conventions (path components, accent/case-insensitive).
# Strong: a token that *starts with* one of these marks teacher-only material.
STRONG_TERMS = ("docente", "teacher", "solucion", "solution", "profesor", "instructor")
# Ambiguous: exact tokens that often, but not always, mean answer keys
# ("conceptos clave", "hoja de respuestas" for students, "pauta de trabajo").
AMBIGUOUS_TERMS = frozenset(
    {"clave", "claves", "pauta", "pautas", "key", "keys",
     "answer", "answers", "respuesta", "respuestas"}
)


class ConfigError(Exception):
    """Invalid invocation or configuration (exit 2)."""


@dataclass
class Finding:
    code: str
    path: str | None = None
    line: int | None = None
    rule: str | None = None
    detail: str = ""
    severity: str = "error"

    def as_dict(self) -> dict:
        out = {"code": self.code, "severity": self.severity}
        if self.path is not None:
            out["path"] = self.path
        if self.line is not None:
            out["line"] = self.line
        if self.rule is not None:
            out["rule"] = self.rule
        if self.detail:
            out["detail"] = self.detail
        return out


@dataclass
class Entry:
    line: int
    path: str
    size: int
    sha256: str


@dataclass
class Result:
    findings: list[Finding] = field(default_factory=list)
    reviewed: list[dict] = field(default_factory=list)
    rows: int = 0
    valid_rows: int = 0
    verified: int = 0
    files_on_disk: int = 0


def _shown(path: str) -> str:
    return path if len(path) <= MAX_SHOWN_PATH else path[:MAX_SHOWN_PATH] + "..."


def normalize_rel_path(raw: str) -> tuple[str | None, str | None]:
    """Return (normalized_posix_path, None) or (None, rejection_rule).

    Pure string check: runs before any filesystem access for that row.
    """
    value = raw.strip()
    if not value:
        return None, "empty_path"
    if "\x00" in value:
        return None, "nul_byte"
    if value.startswith("\\\\") or value.startswith("//"):
        return None, "absolute_unc"
    if DRIVE_RE.match(value):
        return None, "absolute_windows_drive"
    unified = value.replace("\\", "/")
    if unified.startswith("/"):
        return None, "absolute_posix"
    parts = [p for p in unified.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None, "parent_traversal"
    if not parts:
        return None, "empty_path"
    return "/".join(parts), None


def _is_within(child: str, parent: str) -> bool:
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def _symlink_rule(link_path: str, real_root: str) -> str:
    target = os.path.realpath(link_path)
    return "symlink_internal" if _is_within(target, real_root) else "symlink_escape"


# Windows: junctions/mount points and symlinks are *name-surrogate* reparse
# points (they redirect to another path). Cloud placeholders (OneDrive/Drive
# hydration, IO_REPARSE_TAG_CLOUD_*) are not name surrogates and stay allowed.
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
REPARSE_NAME_SURROGATE_BIT = 0x20000000


def is_redirect(st: os.stat_result) -> bool:
    """True for a symlink, junction or other name-surrogate reparse point."""
    if stat.S_ISLNK(st.st_mode):
        return True
    attrs = getattr(st, "st_file_attributes", 0) or 0
    if not attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    tag = getattr(st, "st_reparse_tag", 0) or 0
    return bool(tag & REPARSE_NAME_SURROGATE_BIT)


def load_manifest(manifest: Path, result: Result) -> list[Entry]:
    try:
        raw = manifest.read_bytes()
    except OSError as exc:
        raise ConfigError(f"cannot read manifest: {exc.strerror or exc}") from None
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ConfigError("manifest is not valid UTF-8") from None

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
    except StopIteration:
        raise ConfigError("manifest is empty") from None
    except csv.Error as exc:
        raise ConfigError(f"manifest header is not valid CSV: {exc}") from None
    columns = [h.strip().lower() for h in header]
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        raise ConfigError(f"manifest header missing columns: {', '.join(missing)}")
    idx = {c: columns.index(c) for c in REQUIRED_COLUMNS}

    entries: list[Entry] = []
    seen: dict[str, int] = {}
    seen_folded: dict[str, tuple[str, int]] = {}
    while True:
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            result.rows += 1
            result.findings.append(
                Finding("malformed_row", line=reader.line_num, detail=f"CSV error: {exc}")
            )
            break  # csv state is unreliable after a quoting error
        line = reader.line_num
        if not row or all(not c.strip() for c in row):
            continue
        result.rows += 1
        if len(row) != len(columns):
            result.findings.append(
                Finding("malformed_row", line=line,
                        detail=f"expected {len(columns)} fields, got {len(row)}")
            )
            continue

        rel, rule = normalize_rel_path(row[idx["ruta"]])
        if rel is None:
            result.findings.append(
                Finding("path_rejected", path=_shown(row[idx["ruta"]].strip()),
                        line=line, rule=rule, detail="not read")
            )
            continue

        row_ok = True
        size_raw = row[idx["bytes"]].strip()
        if not SIZE_RE.match(size_raw):
            rule = "negative" if size_raw.startswith("-") else "not_a_non_negative_integer"
            result.findings.append(Finding("invalid_size", path=rel, line=line, rule=rule))
            row_ok = False
        sha_raw = row[idx["sha256"]].strip().lower()
        if not SHA256_RE.match(sha_raw):
            result.findings.append(
                Finding("invalid_hash", path=rel, line=line, rule="expected_64_hex_chars")
            )
            row_ok = False

        if rel in seen:
            result.findings.append(
                Finding("duplicate_path", path=rel, line=line,
                        detail=f"first declared on line {seen[rel]}")
            )
            continue
        seen[rel] = line
        folded = rel.casefold()
        if folded in seen_folded:
            other, other_line = seen_folded[folded]
            result.findings.append(
                Finding("case_collision", path=rel, line=line,
                        detail=f"collides with '{_shown(other)}' (line {other_line}) "
                               "on case-insensitive filesystems")
            )
        else:
            seen_folded[folded] = (rel, line)

        if row_ok:
            entries.append(Entry(line, rel, int(size_raw), sha_raw))
            result.valid_rows += 1
        else:
            # Still counts as declared (no extra_file noise), but not verified.
            entries.append(Entry(line, rel, -1, ""))
    return entries


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_entry(entry: Entry, real_root: str, result: Result) -> None:
    current = real_root
    parts = entry.path.split("/")
    for i, part in enumerate(parts):
        current = os.path.join(current, part)
        try:
            st = os.lstat(current)
        except FileNotFoundError:
            result.findings.append(Finding("missing_file", path=entry.path, line=entry.line))
            return
        except OSError as exc:
            result.findings.append(
                Finding("unreadable_file", path=entry.path, line=entry.line,
                        detail=exc.strerror or type(exc).__name__)
            )
            return
        if is_redirect(st):
            result.findings.append(
                Finding("symlink_not_allowed", path=entry.path, line=entry.line,
                        rule=_symlink_rule(current, real_root), detail="not followed")
            )
            return
        last = i == len(parts) - 1
        if not last and not stat.S_ISDIR(st.st_mode):
            result.findings.append(Finding("missing_file", path=entry.path, line=entry.line,
                                           detail="a parent component is not a directory"))
            return
    if not stat.S_ISREG(st.st_mode):
        kind = "directory" if stat.S_ISDIR(st.st_mode) else "special_file"
        result.findings.append(
            Finding("not_regular_file", path=entry.path, line=entry.line, rule=kind)
        )
        return
    if entry.size < 0:
        return  # row already reported as invalid; existence checked only
    # Defence in depth against redirections not visible in lstat (e.g. an
    # unknown reparse type or a mount): the resolved file must stay in root.
    if not _is_within(os.path.realpath(current), real_root):
        result.findings.append(
            Finding("symlink_not_allowed", path=entry.path, line=entry.line,
                    rule="redirect_escape", detail="resolves outside root; not read")
        )
        return
    try:
        actual_hash = _sha256_file(current)
    except OSError as exc:
        result.findings.append(
            Finding("unreadable_file", path=entry.path, line=entry.line,
                    detail=exc.strerror or type(exc).__name__)
        )
        return
    result.verified += 1
    if st.st_size != entry.size:
        result.findings.append(
            Finding("size_mismatch", path=entry.path, line=entry.line,
                    detail=f"expected {entry.size}, actual {st.st_size}")
        )
    if actual_hash != entry.sha256:
        result.findings.append(
            Finding("hash_mismatch", path=entry.path, line=entry.line,
                    detail=f"expected {entry.sha256}, actual {actual_hash}")
        )


def inventory(real_root: str, result: Result) -> tuple[list[str], dict[str, str]]:
    """Return (file rel paths, redirect rel path -> rule). Never reads content.

    Unlike os.walk, enumeration errors are not swallowed: any unlistable
    directory or unstat-able entry becomes an ``inventory_incomplete`` finding.
    Redirects (symlinks, junctions) are recorded and never descended into.
    """
    files: list[str] = []
    links: dict[str, str] = {}
    pending = [(real_root, "")]
    while pending:
        dirpath, rel_dir = pending.pop()
        try:
            with os.scandir(dirpath) as it:
                entries = list(it)
        except OSError as exc:
            result.findings.append(
                Finding("inventory_incomplete", path=rel_dir.rstrip("/") or ".",
                        detail=f"cannot list directory: {exc.strerror or type(exc).__name__}")
            )
            continue
        for entry in entries:
            rel = rel_dir + entry.name
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as exc:
                result.findings.append(
                    Finding("inventory_incomplete", path=rel,
                            detail=f"cannot stat entry: {exc.strerror or type(exc).__name__}")
                )
                continue
            if is_redirect(st):
                links[rel] = _symlink_rule(entry.path, real_root)
            elif stat.S_ISDIR(st.st_mode):
                pending.append((entry.path, rel + "/"))
            else:
                files.append(rel)
    return sorted(files), links


def _tokens(component: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", component)
    ascii_ = "".join(
        c for c in unicodedata.normalize("NFKD", spaced) if not unicodedata.combining(c)
    ).lower()
    return [t for t in re.split(r"[^a-z0-9]+", ascii_) if t]


def classify_student_path(rel: str) -> tuple[str, str] | None:
    """Return (code, rule) for a teacher-material naming hit, or None."""
    ambiguous: str | None = None
    for component in rel.split("/"):
        for token in _tokens(component):
            for term in STRONG_TERMS:
                if token.startswith(term):
                    return "student_forbidden_convention", f"token '{token}' starts with '{term}'"
                if term in token and ambiguous is None:
                    ambiguous = f"token '{token}' contains '{term}' (not at start)"
            if token in AMBIGUOUS_TERMS and ambiguous is None:
                ambiguous = f"ambiguous token '{token}'"
    if ambiguous:
        return "student_ambiguous_name", ambiguous
    return None


def _normalize_cli_paths(values: list[str], source: str) -> list[str]:
    out = []
    for value in values:
        rel, rule = normalize_rel_path(value)
        if rel is None:
            raise ConfigError(f"invalid {source} path ({rule}): {_shown(value)!r}")
        out.append(rel)
    return out


def load_forbidden_list(path: Path) -> list[str]:
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"cannot read forbidden list: {exc}") from None
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def student_checks(paths: list[str], forbidden: list[str], reviewed_ok: set[str],
                   result: Result) -> None:
    for rel in paths:
        hit = next((f for f in forbidden if rel == f or rel.startswith(f + "/")), None)
        if hit is not None:
            result.findings.append(
                Finding("student_forbidden_explicit", path=rel, rule=f"forbidden '{hit}'")
            )
            continue
        verdict = classify_student_path(rel)
        if verdict is None:
            continue
        code, rule = verdict
        if rel in reviewed_ok:
            result.reviewed.append({"path": rel, "code": code, "rule": rule})
            continue
        detail = ("teacher-only naming convention" if code == "student_forbidden_convention"
                  else "no certainty: human review required (rename, or --reviewed-ok)")
        result.findings.append(Finding(code, path=rel, rule=rule, detail=detail))


def validate(root: Path, manifest: Path, role: str, forbidden: list[str],
             reviewed_ok: set[str]) -> Result:
    result = Result()
    real_root = os.path.realpath(root)
    entries = load_manifest(manifest, result)

    for entry in entries:
        verify_entry(entry, real_root, result)

    files, links = inventory(real_root, result)
    manifest_abs = os.path.realpath(manifest)
    manifest_rel = None
    if _is_within(manifest_abs, real_root):
        manifest_rel = os.path.relpath(manifest_abs, real_root).replace(os.sep, "/")
    declared = {e.path for e in entries}
    on_disk = [f for f in files if f != manifest_rel]
    result.files_on_disk = len(on_disk)
    for rel in on_disk:
        if rel not in declared:
            result.findings.append(Finding("extra_file", path=rel, detail="not in manifest"))
    for rel, rule in sorted(links.items()):
        if rel not in declared:
            result.findings.append(
                Finding("symlink_not_allowed", path=rel, rule=rule,
                        detail="undeclared; not followed")
            )

    if role == "student":
        candidates = sorted(declared | set(on_disk) | set(links))
        student_checks(candidates, forbidden, reviewed_ok, result)
    return result


def build_report(result: Result, root: Path, manifest: Path, role: str) -> dict:
    by_code: dict[str, int] = {}
    for f in result.findings:
        by_code[f.code] = by_code.get(f.code, 0) + 1
    status = "FAIL" if any(f.severity == "error" for f in result.findings) else "PASS"
    return {
        "tool": "validate_teaching_package",
        "report_version": REPORT_VERSION,
        "status": status,
        "role": role,
        "root": str(root),
        "manifest": str(manifest),
        "counts": {
            "manifest_rows": result.rows,
            "valid_rows": result.valid_rows,
            "files_hashed": result.verified,
            "files_on_disk": result.files_on_disk,
            "findings": len(result.findings),
            "by_code": dict(sorted(by_code.items())),
        },
        "findings": [f.as_dict() for f in result.findings],
        "reviewed_overrides": result.reviewed,
        "native_gui": "NOT_RUN",
        "student_download": "NOT_RUN",
        "scope": ("byte integrity only; does not prove native apps open the files, "
                  "student access, or Drive synchronization"),
    }


def render_summary(report: dict) -> str:
    c = report["counts"]
    lines = [
        f"Teaching package: {report['status']}  (role={report['role']})",
        f"rows={c['manifest_rows']} valid={c['valid_rows']} hashed={c['files_hashed']} "
        f"on_disk={c['files_on_disk']} findings={c['findings']}",
        f"native_gui={report['native_gui']} student_download={report['student_download']} "
        "(integrity only)",
    ]
    for f in report["findings"]:
        loc = f.get("path", "-")
        if "line" in f:
            loc += f" (line {f['line']})"
        extra = " ".join(x for x in (f.get("rule"), f.get("detail")) if x)
        lines.append(f"- [{f['code']}] {loc}" + (f": {extra}" if extra else ""))
    for r in report["reviewed_overrides"]:
        lines.append(f"~ [reviewed-ok] {r['path']}: {r['code']} {r['rule']}")
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("root", type=Path, help="package root directory")
    p.add_argument("--manifest", type=Path, required=True, help="CSV manifest (ruta,bytes,sha256)")
    p.add_argument("--role", choices=("teacher", "student"), required=True)
    p.add_argument("--forbid", action="append", default=[], metavar="PATH",
                   help="student mode: relative path/folder that must not ship (repeatable)")
    p.add_argument("--forbidden-list", type=Path,
                   help="student mode: text file with one forbidden relative path per line")
    p.add_argument("--reviewed-ok", action="append", default=[], metavar="PATH",
                   help="student mode: path whose naming hit was reviewed by a human "
                        "(never overrides explicit forbidden paths)")
    p.add_argument("--json-out", type=Path,
                   help="write JSON to a NEW file outside ROOT (existing files are never "
                        "overwritten); summary goes to stdout")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if not args.root.is_dir():
            raise ConfigError(f"root is not a directory: {args.root}")
        if not args.manifest.is_file():
            raise ConfigError(f"manifest is not a file: {args.manifest}")
        if args.role == "teacher" and (args.forbid or args.forbidden_list or args.reviewed_ok):
            raise ConfigError("--forbid/--forbidden-list/--reviewed-ok require --role student")
        forbidden = _normalize_cli_paths(args.forbid, "--forbid")
        if args.forbidden_list:
            forbidden += _normalize_cli_paths(load_forbidden_list(args.forbidden_list),
                                              "--forbidden-list")
        reviewed_ok = set(_normalize_cli_paths(args.reviewed_ok, "--reviewed-ok"))
        if args.json_out is not None:
            out_abs = os.path.realpath(args.json_out)
            if _is_within(out_abs, os.path.realpath(args.root)):
                raise ConfigError("--json-out must be outside the package root")
            # Exclusive-create policy: never overwrite, so a hardlink/symlink
            # alias of any input (inside or outside ROOT) cannot be clobbered.
            if os.path.lexists(args.json_out):
                raise ConfigError("--json-out already exists; refusing to overwrite")
        result = validate(args.root, args.manifest, args.role, forbidden, reviewed_ok)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = build_report(result, args.root, args.manifest, args.role)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    summary = render_summary(report)
    if args.json_out is not None:
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            with os.fdopen(os.open(args.json_out, flags, 0o644), "wb") as fh:
                fh.write(payload.encode("utf-8"))
        except OSError as exc:
            print(f"error: cannot write --json-out: {exc.strerror or exc}", file=sys.stderr)
            return 2
        print(summary)
    else:
        sys.stdout.write(payload)
        print(summary, file=sys.stderr)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
