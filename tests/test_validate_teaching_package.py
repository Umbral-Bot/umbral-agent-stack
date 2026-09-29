"""Tests for scripts/validate_teaching_package.py (synthetic data only)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "validate_teaching_package.py"
FIXTURES = REPO / "tests" / "fixtures" / "teaching_package"
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

sys.path.insert(0, str(REPO / "scripts"))
import validate_teaching_package as vtp  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_pkg(tmp_path: Path, files: dict[str, bytes]) -> Path:
    root = tmp_path / "pkg"
    root.mkdir()
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return root


def manifest_for(files: dict[str, bytes]) -> str:
    lines = ["ruta,bytes,sha256"]
    for rel, data in files.items():
        lines.append(f'"{rel}",{len(data)},{sha(data)}')
    return "\n".join(lines) + "\n"


def run(tmp_path: Path, root: Path, manifest_text: str | bytes, *extra: str,
        role: str = "teacher", name: str = "manifest.csv"):
    manifest = tmp_path / name
    if isinstance(manifest_text, str):
        manifest_text = manifest_text.encode("utf-8")
    manifest.write_bytes(manifest_text)
    out = tmp_path / "report.json"
    code = vtp.main([str(root), "--manifest", str(manifest), "--role", role,
                     "--json-out", str(out), *extra])
    report = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    return code, report


def codes(report: dict) -> list[str]:
    return sorted(f["code"] for f in report["findings"])


BASE = {
    "Guia 01.pdf": b"%PDF-1.4 synthetic\n",
    "datos/tabla.csv": b"a,b\n1,2\n",
    "modelo/casa.rvt": b"\x00\x01\x02 binary synthetic",
}


# --- positive paths ---------------------------------------------------------

def test_valid_package_passes_with_not_run_flags(tmp_path):
    root = make_pkg(tmp_path, BASE)
    code, report = run(tmp_path, root, manifest_for(BASE))
    assert code == 0
    assert report["status"] == "PASS"
    assert report["findings"] == []
    assert report["counts"]["files_hashed"] == 3
    assert report["native_gui"] == "NOT_RUN"
    assert report["student_download"] == "NOT_RUN"


def test_known_sha256_vector(tmp_path):
    root = make_pkg(tmp_path, {"a.txt": b"abc"})
    code, report = run(tmp_path, root, f"ruta,bytes,sha256\na.txt,3,{ABC_SHA256.upper()}\n")
    assert (code, report["status"]) == (0, "PASS")


def test_bom_quoting_spaces_windows_separators_and_extra_columns(tmp_path):
    files = {"sub dir/Guía, final.pdf": b"x" * 10, "sub dir/b.txt": b"b"}
    root = make_pkg(tmp_path, files)
    text = (
        "\ufeff Ruta , BYTES ,sha256,nota\r\n"
        f'"sub dir\\Guía, final.pdf", 10 , {sha(b"x" * 10)} ,"comentario, con coma"\r\n'
        f'"./sub dir//b.txt",1,{sha(b"b")},\r\n'
        "\r\n"
    )
    code, report = run(tmp_path, root, text)
    assert code == 0, report["findings"]


def test_manifest_inside_root_is_excluded_but_other_docs_are_not(tmp_path):
    root = make_pkg(tmp_path, BASE)
    (root / "LEEME.md").write_bytes(b"undeclared docs")
    manifest = root / "manifest.csv"
    manifest.write_text(manifest_for(BASE), encoding="utf-8")
    out = tmp_path / "r.json"
    code = vtp.main([str(root), "--manifest", str(manifest), "--role", "teacher",
                     "--json-out", str(out)])
    report = json.loads(out.read_text())
    assert code == 1
    assert [(f["code"], f["path"]) for f in report["findings"]] == [("extra_file", "LEEME.md")]


# --- integrity findings -----------------------------------------------------

def test_missing_extra_size_and_hash_corruption(tmp_path):
    root = make_pkg(tmp_path, BASE)
    (root / "datos/tabla.csv").write_bytes(b"a,b\n1,3\n")  # same size, different hash
    (root / "Guia 01.pdf").write_bytes(b"%PDF truncated")  # size and hash differ
    (root / "modelo/casa.rvt").unlink()
    (root / ".DS_Store").write_bytes(b"junk")
    code, report = run(tmp_path, root, manifest_for(BASE))
    assert code == 1
    assert codes(report) == ["extra_file", "hash_mismatch", "hash_mismatch",
                             "missing_file", "size_mismatch"]


def test_malformed_rows_invalid_hash_and_sizes(tmp_path):
    files = {"a.txt": b"a", "b.txt": b"b", "c.txt": b"c", "d.txt": b"d"}
    root = make_pkg(tmp_path, files)
    text = (
        "ruta,bytes,sha256\n"
        f"a.txt,-1,{sha(b'a')}\n"
        f"b.txt,1.0,{sha(b'b')}\n"
        "c.txt,1,not-a-hash\n"
        "d.txt,1\n"
    )
    code, report = run(tmp_path, root, text)
    assert code == 1
    by = {(f["code"], f.get("rule")) for f in report["findings"]}
    assert ("invalid_size", "negative") in by
    assert ("invalid_size", "not_a_non_negative_integer") in by
    assert ("invalid_hash", "expected_64_hex_chars") in by
    assert ("malformed_row", None) in by
    # d.txt row is malformed, so the file on disk is undeclared.
    assert ("extra_file", None) in by


def test_duplicate_and_case_collision(tmp_path):
    files = {"a.txt": b"a", "A.TXT": b"A"}
    root = make_pkg(tmp_path, files)
    text = manifest_for(files) + f"a.txt,1,{sha(b'a')}\n" + f".\\a.txt,1,{sha(b'a')}\n"
    code, report = run(tmp_path, root, text)
    assert code == 1
    assert codes(report) == ["case_collision", "duplicate_path", "duplicate_path"]


@pytest.mark.parametrize("raw,rule", [
    ("/etc/passwd", "absolute_posix"),
    ("C:\\Windows\\win.ini", "absolute_windows_drive"),
    ("c:/x.txt", "absolute_windows_drive"),
    ("\\\\server\\share\\x.txt", "absolute_unc"),
    ("../outside.txt", "parent_traversal"),
    ("sub\\..\\..\\outside.txt", "parent_traversal"),
])
def test_escaping_paths_rejected_before_reading(tmp_path, raw, rule, monkeypatch):
    root = make_pkg(tmp_path, {})
    (tmp_path / "outside.txt").write_bytes(b"secret-outside")
    opened: list[str] = []
    real_open = os.open
    monkeypatch.setattr(vtp.os, "open", lambda p, *a, **k: (opened.append(p), real_open(p, *a, **k))[1])
    code, report = run(tmp_path, root, f'ruta,bytes,sha256\n"{raw}",1,{"0" * 64}\n')
    assert code == 1
    assert report["findings"] == [{"code": "path_rejected", "severity": "error",
                                   "path": raw, "line": 2, "rule": rule, "detail": "not read"}]
    assert opened == []
    assert "secret-outside" not in json.dumps(report)


def test_empty_manifest_body_on_nonempty_root_fails(tmp_path):
    root = make_pkg(tmp_path, {"a.txt": b"a"})
    code, report = run(tmp_path, root, "ruta,bytes,sha256\n")
    assert code == 1 and codes(report) == ["extra_file"]


# --- symlinks ---------------------------------------------------------------

symlinks = pytest.mark.skipif(not hasattr(os, "symlink") or os.name == "nt",
                              reason="symlinks unsupported")


@symlinks
def test_symlink_escaping_root_is_not_followed(tmp_path, monkeypatch):
    root = make_pkg(tmp_path, {"a.txt": b"a"})
    secret = tmp_path / "outside-secret.txt"
    secret.write_bytes(b"TOP-SECRET-CONTENT")
    os.symlink(secret, root / "link.txt")
    os.symlink(tmp_path, root / "linkdir")
    hashed: list[str] = []
    real = vtp._sha256_file
    monkeypatch.setattr(vtp, "_sha256_file", lambda p: (hashed.append(p), real(p))[1])
    files = {"a.txt": b"a", "link.txt": b"TOP-SECRET-CONTENT"}
    text = manifest_for(files) + f"linkdir/outside-secret.txt,18,{sha(b'TOP-SECRET-CONTENT')}\n"
    code, report = run(tmp_path, root, text)
    assert code == 1
    rules = sorted((f["code"], f["path"], f["rule"]) for f in report["findings"])
    assert rules == [
        ("symlink_not_allowed", "link.txt", "symlink_escape"),
        ("symlink_not_allowed", "linkdir", "symlink_escape"),
        ("symlink_not_allowed", "linkdir/outside-secret.txt", "symlink_escape"),
    ]
    assert all("outside" not in p for p in hashed)
    assert "TOP-SECRET" not in json.dumps(report)


@symlinks
def test_internal_symlink_policy_is_fail_without_following(tmp_path):
    root = make_pkg(tmp_path, {"a.txt": b"a"})
    os.symlink("a.txt", root / "alias.txt")
    files = {"a.txt": b"a", "alias.txt": b"a"}
    code, report = run(tmp_path, root, manifest_for(files))
    assert code == 1
    assert [(f["code"], f["rule"]) for f in report["findings"]] == [
        ("symlink_not_allowed", "symlink_internal")]


# --- student mode -----------------------------------------------------------

def test_student_mode_flags_teacher_material_and_explicit_list(tmp_path):
    files = {
        "alumno/guia.pdf": b"g",
        "Docentes/notas.docx": b"n",
        "ejercicio_Solucionario.xlsx": b"s",
        "GuiaTeacher.pbix": b"t",
        "privado/rubrica.pdf": b"r",
    }
    root = make_pkg(tmp_path, files)
    forbidden = tmp_path / "forbidden.txt"
    forbidden.write_text("# lista\nprivado\n", encoding="utf-8")
    code, report = run(tmp_path, root, manifest_for(files), "--forbidden-list", str(forbidden),
                       role="student")
    assert code == 1
    got = {f["path"]: (f["code"], f["rule"]) for f in report["findings"]}
    assert got == {
        "Docentes/notas.docx": ("student_forbidden_convention",
                                "token 'docentes' starts with 'docente'"),
        "ejercicio_Solucionario.xlsx": ("student_forbidden_convention",
                                        "token 'solucionario' starts with 'solucion'"),
        "GuiaTeacher.pbix": ("student_forbidden_convention", "token 'teacher' starts with 'teacher'"),
        "privado/rubrica.pdf": ("student_forbidden_explicit", "forbidden 'privado'"),
    }


def test_student_mode_checks_undeclared_files_and_accents(tmp_path):
    files = {"a.pdf": b"a"}
    root = make_pkg(tmp_path, files)
    (root / "Solución Final.pdf").write_bytes(b"x")
    code, report = run(tmp_path, root, manifest_for(files), role="student")
    assert code == 1
    assert codes(report) == ["extra_file", "student_forbidden_convention"]


def test_student_mode_ambiguous_names_need_explicit_review(tmp_path):
    files = {"conceptos-clave.pdf": b"c", "hoja_respuestas.docx": b"h", "ok.pdf": b"o"}
    root = make_pkg(tmp_path, files)
    code, report = run(tmp_path, root, manifest_for(files), role="student")
    assert code == 1
    assert codes(report) == ["student_ambiguous_name"] * 2
    assert all("human review" in f["detail"] for f in report["findings"])

    code, report = run(tmp_path, root, manifest_for(files), "--reviewed-ok", "conceptos-clave.pdf",
                       "--reviewed-ok", "hoja_respuestas.docx", role="student", name="m2.csv")
    assert code == 0
    assert len(report["reviewed_overrides"]) == 2


def test_reviewed_ok_never_overrides_explicit_forbidden(tmp_path):
    files = {"x/clave.pdf": b"c"}
    root = make_pkg(tmp_path, files)
    code, report = run(tmp_path, root, manifest_for(files), "--forbid", "x",
                       "--reviewed-ok", "x/clave.pdf", role="student")
    assert code == 1 and codes(report) == ["student_forbidden_explicit"]


def test_teacher_mode_allows_teacher_material(tmp_path):
    files = {"docente/solucion.xlsx": b"s"}
    root = make_pkg(tmp_path, files)
    assert run(tmp_path, root, manifest_for(files))[0] == 0


# --- invocation errors (exit 2) ---------------------------------------------

def test_config_errors_exit_2(tmp_path, capsys):
    root = make_pkg(tmp_path, BASE)
    good = manifest_for(BASE)
    assert run(tmp_path, root, "path,size,hash\n")[0] == 2
    assert run(tmp_path, root, b"ruta,bytes,sha256\n\xff\xfe,1,x\n", name="bad.csv")[0] == 2
    assert run(tmp_path, root, "", name="empty.csv")[0] == 2
    m = tmp_path / "m.csv"
    m.write_text(good, encoding="utf-8")
    assert vtp.main([str(root), "--manifest", str(m), "--role", "teacher",
                     "--json-out", str(root / "report.json")]) == 2
    assert not (root / "report.json").exists()
    assert vtp.main([str(tmp_path / "nope"), "--manifest", str(m), "--role", "teacher"]) == 2
    assert vtp.main([str(root), "--manifest", str(m), "--role", "teacher", "--forbid", "x"]) == 2
    assert vtp.main([str(root), "--manifest", str(m), "--role", "student",
                     "--forbid", "../x"]) == 2
    with pytest.raises(SystemExit) as exc:
        vtp.main([str(root), "--manifest", str(m), "--role", "admin"])
    assert exc.value.code == 2


# --- read-only guarantee and real CLI ---------------------------------------

def _snapshot(base: Path) -> dict[str, tuple[bytes, int]]:
    return {str(p.relative_to(base)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(base.rglob("*")) if p.is_file() and not p.is_symlink()}


def test_inputs_are_byte_for_byte_untouched(tmp_path):
    files = dict(BASE, **{"docente/pauta.xlsx": b"p"})
    root = make_pkg(tmp_path, files)
    manifest = root / "manifest.csv"
    manifest.write_text(manifest_for(files), encoding="utf-8")
    before = _snapshot(root)
    listing_before = sorted(os.listdir(root))
    out = tmp_path / "out.json"
    code = vtp.main([str(root), "--manifest", str(manifest), "--role", "student",
                     "--json-out", str(out)])
    assert code == 1
    assert _snapshot(root) == before
    assert sorted(os.listdir(root)) == listing_before


def test_cli_subprocess_on_committed_fixture(tmp_path):
    root = FIXTURES / "sano"
    manifest = FIXTURES / "sano.csv"
    before = _snapshot(FIXTURES)
    proc = subprocess.run([sys.executable, str(SCRIPT), str(root), "--manifest", str(manifest),
                           "--role", "student"], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "PASS" and report["counts"]["files_hashed"] == 3
    assert "Teaching package: PASS" in proc.stderr
    assert _snapshot(FIXTURES) == before

    bad = tmp_path / "bad.csv"
    bad.write_text(manifest.read_text(encoding="utf-8").replace(",40,", ",41,", 1), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SCRIPT), str(root), "--manifest", str(bad),
                           "--role", "student"], capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["status"] == "FAIL"
