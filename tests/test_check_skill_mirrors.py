import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(module_name: str):
    script_path = REPO_ROOT / "scripts" / "maintenance" / "check_skill_mirrors.py"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _seed_repos(tmp_path: Path):
    uas = tmp_path / "umbral-agent-stack"
    notion = tmp_path / "notion-governance"
    registry = tmp_path / "umbral-skills-registry"

    checker = uas / "scripts" / "maintenance" / "check_skill_mirrors.py"
    checker.parent.mkdir(parents=True)
    checker.write_text("# marker\n", encoding="utf-8")

    (notion / ".agents" / "skills").mkdir(parents=True)
    canonical = (
        registry
        / "notion-governance-skills"
        / "secret-output-guard"
        / "SKILL.md"
    )
    canonical.parent.mkdir(parents=True)
    canonical.write_text("guardrail\n", encoding="utf-8")
    ship = registry / "tools" / "ship_skill.py"
    ship.parent.mkdir(parents=True)
    ship.write_text("# marker\n", encoding="utf-8")
    return uas, notion, registry, canonical


def _set_repo_env(monkeypatch, module, uas: Path, notion: Path, registry: Path):
    monkeypatch.setenv(module.UMBRAL_AGENT_STACK_ENV, str(uas))
    monkeypatch.setenv(module.NOTION_GOVERNANCE_ENV, str(notion))
    monkeypatch.setenv(module.UMBRAL_SKILLS_REGISTRY_ENV, str(registry))


def test_topology_has_one_registry_source_and_only_two_repo_mirrors(
    tmp_path, monkeypatch
):
    module = _load_module("check_skill_mirrors_topology")
    uas, notion, registry, canonical = _seed_repos(tmp_path)
    _set_repo_env(monkeypatch, module, uas, notion, registry)

    mappings = module.build_mirrored_skills()

    assert list(mappings) == [canonical]
    assert mappings[canonical] == [
        notion / ".agents" / "skills" / "secret-output-guard" / "SKILL.md",
        uas / ".agents" / "skills" / "secret-output-guard" / "SKILL.md",
    ]
    all_paths = [canonical, *mappings[canonical]]
    assert all(".codex" not in path.parts for path in all_paths)
    assert all(".copilot" not in path.parts for path in all_paths)


def test_hash_normalizes_crlf_and_lf(tmp_path):
    module = _load_module("check_skill_mirrors_line_endings")
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"one\ntwo\n")
    crlf.write_bytes(b"one\r\ntwo\r\n")

    assert module.sha256_prefix(lf) == module.sha256_prefix(crlf)


def test_check_reports_semantic_drift(tmp_path, monkeypatch, capsys):
    module = _load_module("check_skill_mirrors_drift")
    canonical = tmp_path / "canonical.md"
    mirror = tmp_path / "mirror.md"
    canonical.write_text("canonical\n", encoding="utf-8")
    mirror.write_text("different\n", encoding="utf-8")
    monkeypatch.setattr(module, "build_mirrored_skills", lambda: {canonical: [mirror]})

    assert module.check(fix=False) == 1
    captured = capsys.readouterr()
    assert "[DRIFT]" in captured.err


def test_fix_updates_only_the_supplied_repo_mirror(tmp_path, monkeypatch):
    module = _load_module("check_skill_mirrors_fix")
    canonical = tmp_path / "registry" / "SKILL.md"
    mirror = tmp_path / "repo-mirror" / "SKILL.md"
    canonical.parent.mkdir()
    mirror.parent.mkdir()
    canonical.write_text("canonical\n", encoding="utf-8")
    mirror.write_text("different\n", encoding="utf-8")
    monkeypatch.setattr(module, "build_mirrored_skills", lambda: {canonical: [mirror]})

    assert module.check(fix=True) == 0
    assert mirror.read_bytes() == canonical.read_bytes()
