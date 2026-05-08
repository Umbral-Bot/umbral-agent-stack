"""Tests for scripts/discovery/stage7_5_copy_writer.py."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from scripts.discovery import stage7_5_copy_writer as mod


# ---------- Fixtures ----------

def _create_proposals_table(db: Path) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titular TEXT NOT NULL,
            hook TEXT, angulo TEXT,
            fuentes_urls TEXT NOT NULL,
            disciplinas TEXT NOT NULL,
            score REAL, ts INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            notion_page_id TEXT, last_error TEXT,
            image_status TEXT, image_last_attempt_at INTEGER
        )"""
    )
    conn.commit()
    conn.close()


def _insert(db: Path, **kwargs) -> int:
    defaults = {
        "titular": "Mi titular sobre BIM y AI",
        "hook": "hook frase",
        "angulo": "por qué importa",
        "fuentes_urls": json.dumps(["https://src.test/article"]),
        "disciplinas": json.dumps(["BIM", "IA"]),
        "score": 0.7,
        "ts": int(time.time()),
        "status": "published",
        "notion_page_id": "page-default",
        "image_status": "ok",
    }
    defaults.update(kwargs)
    cols = list(defaults.keys())
    placeholders = ",".join("?" * len(cols))
    conn = sqlite3.connect(db)
    conn.execute(
        f"INSERT INTO proposals ({','.join(cols)}) VALUES ({placeholders})",
        tuple(defaults[c] for c in cols),
    )
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return pid


@pytest.fixture
def state_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    _create_proposals_table(db)
    mod.ensure_copy_columns(db)
    return db


@pytest.fixture(autouse=True)
def _bypass_source_verifier(monkeypatch):
    """Existing fixtures use ``https://src.test/article`` which is rightly
    blocklisted by the new pre-LLM source verifier. These tests were written
    for the prior pipeline and exercise validation/persistence semantics, NOT
    source verification — so we stub the verifier to always pass. Tests that
    need to exercise the gate live further down (``test_source_gate_*``) and
    explicitly disable this autouse via ``monkeypatch.undo()``.
    """
    if mod._source_verifier is None:
        return
    monkeypatch.setattr(
        mod._source_verifier,
        "verify_source",
        lambda url, **kw: {
            "ok": True,
            "url": url,
            "reason": "",
            "warnings": [],
            "details": {"host": "src.test", "from_cache": False, "cache_age_s": None},
        },
    )


def _set_copy_status(db: Path, pid: int, status: str,
                     attempt_at: int | None = None) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE proposals SET copy_status=?, copy_last_attempt_at=? WHERE id=?",
        (status, attempt_at, pid),
    )
    conn.commit()
    conn.close()


def _make_page(*, copy_linkedin: str = "",
               source: str = "https://src.test/article",
               body_raw: str = "Body raw text para el LLM.",
               estado_type: str = "status") -> dict:
    props: dict = {
        "Título": {"type": "title", "title": [{"plain_text": "Título"}]},
        "Fuente primaria": {"type": "url", "url": source},
        "Body raw": {"type": "rich_text", "rich_text": [{"plain_text": body_raw}]},
    }
    if estado_type == "status":
        props["Estado"] = {"type": "status", "status": {"name": "Aprobado"}}
    else:
        props["Estado"] = {"type": "select", "select": {"name": "Aprobado"}}
    if copy_linkedin:
        props["Copy LinkedIn"] = {
            "type": "rich_text",
            "rich_text": [{"plain_text": copy_linkedin}],
        }
    else:
        props["Copy LinkedIn"] = {"type": "rich_text", "rich_text": []}
    return {"id": "page-default", "properties": props}


def _good_schema(*, with_copy: bool = True, with_estado: bool = True,
                 estado_options: list[str] | None = None,
                 estado_type: str = "status") -> dict:
    schema: dict = {}
    if with_copy:
        schema["Copy LinkedIn"] = {"type": "rich_text"}
    if with_estado:
        schema["Estado"] = {
            "type": estado_type,
            "options": estado_options if estado_options is not None
            else ["Borrador", "Aprobado", "Autorizado", "En revisión"],
        }
    return schema


def _good_copy(source: str = "https://src.test/article") -> str:
    """Build a copy that passes all validators."""
    body = (
        "Hook editorial directo sobre BIM y AI. "
        "Esto es un cuerpo extenso que describe el ángulo y por qué "
        "importa ahora en el sector AECO. " * 12
    )
    tail = f"\nFuente: {source}\n#BIM #AECO #IA #Construccion"
    text = (body + tail).strip()
    assert mod.POST_MIN_CHARS <= len(text) <= mod.POST_MAX_CHARS, len(text)
    assert source in text
    return text


def _fake_notion(*, page: dict, schema: dict | None = None,
                 patch_side_effect=None) -> MagicMock:
    client = MagicMock()
    client.get.return_value = page
    if patch_side_effect is not None:
        client.patch.side_effect = patch_side_effect
    else:
        client.patch.return_value = {"object": "page"}
    return client


# ---------- Tests ----------

def test_migration_idempotent(state_db: Path):
    mod.ensure_copy_columns(state_db)
    mod.ensure_copy_columns(state_db)  # second pass must not raise
    conn = sqlite3.connect(state_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(proposals)")}
    conn.close()
    for c in mod.COPY_COLUMNS:
        assert c in cols, c


def test_candidate_selection_requires_image_ok(state_db: Path):
    p_ok = _insert(state_db, titular="OK", notion_page_id="page-ok",
                   image_status="ok")
    _insert(state_db, titular="No image", notion_page_id="page-noimg",
            image_status=None)
    _insert(state_db, titular="No notion page", notion_page_id=None,
            image_status="ok")
    rows = mod.read_pending_proposals(state_db, force=False, limit=10)
    assert [r["id"] for r in rows] == [p_ok]


def test_skip_when_already_copy_ready(state_db: Path):
    pid = _insert(state_db, titular="Already done")
    _set_copy_status(state_db, pid, "copy_ready", int(time.time()))
    rows = mod.read_pending_proposals(state_db, force=False, limit=10)
    assert rows == []
    rows_force = mod.read_pending_proposals(state_db, force=True, limit=10)
    assert [r["id"] for r in rows_force] == [pid]


def test_failed_retry_after_24h(state_db: Path):
    pid_old = _insert(state_db, titular="Old failed", notion_page_id="p1")
    pid_recent = _insert(state_db, titular="Recent failed", notion_page_id="p2")
    now = int(time.time())
    _set_copy_status(state_db, pid_old, "failed", now - (25 * 3600))
    _set_copy_status(state_db, pid_recent, "failed", now - (1 * 3600))
    rows = mod.read_pending_proposals(state_db, force=False, limit=10)
    assert [r["id"] for r in rows] == [pid_old]


def test_force_overrides_retry_guard(state_db: Path):
    pid = _insert(state_db, titular="Recent fail")
    _set_copy_status(state_db, pid, "failed", int(time.time()))
    rows_no_force = mod.read_pending_proposals(state_db, force=False, limit=10)
    rows_force = mod.read_pending_proposals(state_db, force=True, limit=10)
    assert rows_no_force == []
    assert [r["id"] for r in rows_force] == [pid]


def test_skip_silent_when_existing_copy(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Has human copy", notion_page_id="page-H1")
    monkeypatch.setenv("NOTION_API_KEY", "test-key")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "gw-tok")
    page = _make_page(copy_linkedin="Texto humano ya pegado en Notion. " * 5)
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    monkeypatch.setattr(mod, "llm_call", lambda **kw: pytest.fail("LLM should not run"))

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 0
    fake.patch.assert_not_called()
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_text FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "copy_ready"
    assert row[1].startswith("Texto humano")


def test_force_overwrite_replaces_existing(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Overwrite me", notion_page_id="page-O1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "gw-tok")
    page = _make_page(copy_linkedin="vieja basura")
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    new_copy = _good_copy()
    monkeypatch.setattr(mod, "llm_call", lambda **kw: new_copy)

    rc = mod.main(["--state-db", str(state_db), "--force-overwrite"])
    assert rc == 0
    fake.patch.assert_called_once()
    payload = fake.patch.call_args.args[1]
    assert "Copy LinkedIn" in payload["properties"]
    assert payload["properties"]["Estado"] == {"status": {"name": "En revisión"}}
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_text FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "copy_ready"
    assert row[1] == new_copy


def test_validation_too_short(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Too short", notion_page_id="page-S1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page()
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    monkeypatch.setattr(mod, "llm_call", lambda **kw: "demasiado corto")

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    fake.patch.assert_not_called()
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "too_short" in (row[1] or "")


def test_validation_too_long(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Too long", notion_page_id="page-L1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page()
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    monkeypatch.setattr(mod, "llm_call",
                        lambda **kw: "x" * (mod.POST_MAX_CHARS + 50))

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "too_long" in (row[1] or "")


def test_validation_missing_source(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="No source", notion_page_id="page-N1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page()
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    # Long enough text but no source URL inside
    monkeypatch.setattr(mod, "llm_call", lambda **kw: ("a" * 800))

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "missing_source_url" in (row[1] or "")


def test_validation_allow_no_source(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="OK no source", notion_page_id="page-AN1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page()
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    monkeypatch.setattr(mod, "llm_call", lambda **kw: ("a" * 800))

    rc = mod.main(["--state-db", str(state_db), "--allow-no-source"])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "copy_ready"


def test_validation_prohibited_token(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Has TODO", notion_page_id="page-T1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page()
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    bad = _good_copy().replace("Hook", "Hook [TODO]")
    monkeypatch.setattr(mod, "llm_call", lambda **kw: bad)

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "prohibited_token" in (row[1] or "")


def test_property_missing_aborts_row(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="No property", notion_page_id="page-P1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    schema = _good_schema(with_copy=False)
    fake = MagicMock()
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: schema)
    monkeypatch.setattr(mod, "llm_call", lambda **kw: pytest.fail("no LLM"))

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "notion_property_missing:Copy LinkedIn" in (row[1] or "")


def test_estado_option_missing(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="No En revisión option",
                  notion_page_id="page-E1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    schema = _good_schema(estado_options=["Borrador", "Autorizado"])
    fake = MagicMock()
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: schema)
    monkeypatch.setattr(mod, "llm_call", lambda **kw: pytest.fail("no LLM"))

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "notion_estado_option_missing:En revisión" in (row[1] or "")


def test_cost_guard_aborts(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Cost guard", notion_page_id="page-C1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    huge_body = "y" * (mod.COST_GUARD_MAX_INPUT_TOKENS * mod.APPROX_CHARS_PER_TOKEN + 100)
    page = _make_page(body_raw=huge_body)

    def patched_prompt(proposal_row, page_props):
        return (
            mod.SYSTEM_PROMPT,
            "x" * (mod.COST_GUARD_MAX_INPUT_TOKENS * mod.APPROX_CHARS_PER_TOKEN + 200),
        )
    monkeypatch.setattr(mod, "build_copy_prompt", patched_prompt)

    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    monkeypatch.setattr(mod, "llm_call", lambda **kw: pytest.fail("LLM must NOT run"))

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    fake.patch.assert_not_called()
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "cost_guard_aborted" in (row[1] or "")


def test_dry_run_no_llm_no_notion_write(state_db: Path, monkeypatch, capsys):
    _insert(state_db, titular="Dry-run row", notion_page_id="page-DR")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")

    def boom(*a, **k):
        pytest.fail("Notion client must not be constructed in --dry-run")
    monkeypatch.setattr(mod, "NotionClient", boom)
    monkeypatch.setattr(mod, "llm_call", lambda **kw: pytest.fail("no LLM"))

    rc = mod.main(["--state-db", str(state_db), "--dry-run"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "dry-run: 1 candidate" in captured.out
    assert "dry_run=True" in captured.out


def test_cache_hit_skips_llm(state_db: Path, tmp_path: Path, monkeypatch):
    pid = _insert(state_db, titular="Cached candidate", notion_page_id="page-CA")
    cache_db = tmp_path / "llm_cache.sqlite"
    canned = _good_copy()
    page = _make_page()

    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())

    call_count = {"n": 0}

    def fake_llm(**kw):
        call_count["n"] += 1
        return canned
    monkeypatch.setattr(mod, "llm_call", fake_llm)

    rc1 = mod.main(["--state-db", str(state_db),
                    "--cache-db", str(cache_db)])
    assert rc1 == 0
    assert call_count["n"] == 1

    # Reset copy_status to allow re-processing without --force.
    _set_copy_status(state_db, pid, None, None)
    rc2 = mod.main(["--state-db", str(state_db),
                    "--cache-db", str(cache_db)])
    assert rc2 == 0
    assert call_count["n"] == 1, "second run should hit cache"


def test_notion_429_then_success_retries(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="429 retry", notion_page_id="page-RL1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")

    page = _make_page()
    schema = _good_schema()

    # Build a fake transport via httpx.MockTransport.
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        url = str(request.url)
        if request.method == "GET" and url.endswith(f"/data_sources/{mod.DEFAULT_PUBLICACIONES_DS_ID}"):
            # Build a real data_source response from our schema.
            properties: dict = {}
            for name, meta in schema.items():
                if meta["type"] in ("status", "select"):
                    properties[name] = {
                        "type": meta["type"],
                        meta["type"]: {
                            "options": [{"name": n} for n in meta.get("options", [])],
                        },
                    }
                else:
                    properties[name] = {"type": meta["type"], meta["type"]: {}}
            return httpx.Response(200, json={"properties": properties})
        if request.method == "GET" and "/pages/" in url:
            return httpx.Response(200, json=page)
        if request.method == "PATCH" and "/pages/" in url:
            if calls["n"] <= 3:  # first PATCH attempt -> 429
                return httpx.Response(429, json={"message": "rate limit"})
            return httpx.Response(200, json={"object": "page"})
        return httpx.Response(404, json={"err": "unknown"})

    transport = httpx.MockTransport(handler)
    real_client_cls = mod.NotionClient

    def patched_init(self, token, *, timeout_s: float = 30.0):
        self._token = token
        self._client = httpx.Client(
            base_url=mod.NOTION_API_BASE,
            headers={"Authorization": f"Bearer {token}",
                     "Notion-Version": mod.NOTION_VERSION,
                     "Content-Type": "application/json"},
            transport=transport,
            timeout=timeout_s,
        )
    monkeypatch.setattr(real_client_cls, "__init__", patched_init)
    # Speed up retries.
    monkeypatch.setattr(mod, "RATE_LIMIT_SLEEP_S", 0.0)
    monkeypatch.setattr(mod, "NOTION_BACKOFF_BASE_S", 0.0)

    monkeypatch.setattr(mod, "llm_call", lambda **kw: _good_copy())

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "copy_ready"


def test_rich_text_chunked_to_2000(state_db: Path, monkeypatch):
    _insert(state_db, titular="Chunk me", notion_page_id="page-CH1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page()
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    long_copy = _good_copy()  # ~1100 chars; force >2000 by repeating
    long_copy = (long_copy + " ") * 3  # > 3000? careful
    # Trim to within max.
    long_copy = long_copy[: mod.POST_MAX_CHARS - 1]
    assert "https://src.test/article" in long_copy
    assert len(long_copy) > 2000
    monkeypatch.setattr(mod, "llm_call", lambda **kw: long_copy)

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 0
    payload = fake.patch.call_args.args[1]
    segments = payload["properties"]["Copy LinkedIn"]["rich_text"]
    assert len(segments) >= 2
    for seg in segments:
        assert len(seg["text"]["content"]) <= mod.NOTION_RICH_TEXT_SEGMENT_MAX


def test_max_copies_caps_run(state_db: Path, monkeypatch):
    for i in range(5):
        _insert(state_db, titular=f"row {i}", notion_page_id=f"page-MC-{i}")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page()
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    monkeypatch.setattr(mod, "llm_call", lambda **kw: _good_copy())

    rc = mod.main(["--state-db", str(state_db), "--max-copies", "2"])
    assert rc == 0
    conn = sqlite3.connect(state_db)
    n = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE copy_status='copy_ready'"
    ).fetchone()[0]
    conn.close()
    assert n == 2


def test_proposal_id_filter(state_db: Path, monkeypatch):
    p1 = _insert(state_db, titular="row1", notion_page_id="page-PI-1")
    p2 = _insert(state_db, titular="row2", notion_page_id="page-PI-2")
    rows = mod.read_pending_proposals(
        state_db, force=False, limit=10, only_proposal_id=p2,
    )
    assert [r["id"] for r in rows] == [p2]
    assert p1  # silence unused


# ---------- Source verifier gate (Stage 7.5 pre-LLM hard block) ----------

def _run_with_verifier(state_db, monkeypatch, *, page, schema, verifier_result,
                       extra_args=None, llm_called=None, tmp_path=None):
    """Run mod.main() once with a stubbed verifier returning ``verifier_result``.

    Returns ``(rc, fake_notion_client)``. The default autouse
    ``_bypass_source_verifier`` fixture is overridden here. A per-test
    ``--cache-db`` is required because the LLM cache is keyed by prompt
    content; sharing the user's real cache across tests causes ``llm_call``
    to be skipped on cache hits and breaks call-count assertions.
    """
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "gw-tok")
    fake = _fake_notion(page=page)
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: schema)

    def _llm(**kw):
        if llm_called is not None:
            llm_called["called"] = True
        return _good_copy()
    monkeypatch.setattr(mod, "llm_call", _llm)

    # Override the autouse bypass so the real gate logic is exercised.
    monkeypatch.setattr(
        mod._source_verifier, "verify_source",
        lambda url, **kw: verifier_result,
    )

    args = ["--state-db", str(state_db)]
    if tmp_path is not None:
        args += ["--cache-db", str(tmp_path / "llm_cache.sqlite")]
    args += list(extra_args or [])
    rc = mod.main(args)
    return rc, fake


def test_source_gate_blocks_on_blocklist_domain(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Bad source", notion_page_id="page-bl",
                  fuentes_urls=json.dumps(["https://example.com/x"]))
    page = _make_page(source="https://example.com/x")
    schema = _good_schema()
    llm_flag = {"called": False}
    rc, fake = _run_with_verifier(
        state_db, monkeypatch, page=page, schema=schema,
        verifier_result={
            "ok": False, "url": "https://example.com/x",
            "reason": "blocklist_domain", "warnings": [],
            "details": {"host": "example.com"},
        },
        llm_called=llm_flag,
    )
    assert rc == 1
    assert llm_flag["called"] is False, "LLM must not run when source blocked"
    fake.patch.assert_not_called(), "Notion must not be patched on source block"
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed_source_unverified"
    assert "blocklist_domain" in (row[1] or "")


def test_source_gate_blocks_on_http_404(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Dead link", notion_page_id="page-404")
    page = _make_page()
    llm_flag = {"called": False}
    rc, fake = _run_with_verifier(
        state_db, monkeypatch, page=page, schema=_good_schema(),
        verifier_result={
            "ok": False, "url": "https://src.test/article",
            "reason": "http_404", "warnings": [],
            "details": {"host": "src.test", "status_code": 404},
        },
        llm_called=llm_flag,
    )
    assert rc == 1
    assert llm_flag["called"] is False
    fake.patch.assert_not_called()
    conn = sqlite3.connect(state_db)
    status = conn.execute("SELECT copy_status FROM proposals WHERE id=?", (pid,)).fetchone()[0]
    conn.close()
    assert status == "failed_source_unverified"


def test_source_gate_passes_when_verifier_ok(state_db: Path, monkeypatch, tmp_path):
    pid = _insert(state_db, titular="Good", notion_page_id="page-ok")
    page = _make_page()
    llm_flag = {"called": False}
    rc, fake = _run_with_verifier(
        state_db, monkeypatch, page=page, schema=_good_schema(),
        verifier_result={
            "ok": True, "url": "https://src.test/article",
            "reason": "", "warnings": [],
            "details": {"host": "src.test"},
        },
        llm_called=llm_flag,
        tmp_path=tmp_path,
    )
    assert rc == 0
    assert llm_flag["called"] is True
    fake.patch.assert_called_once()
    assert pid


def test_source_gate_skip_flag_bypasses(state_db: Path, monkeypatch, tmp_path):
    pid = _insert(state_db, titular="Skip", notion_page_id="page-skip")
    page = _make_page()
    llm_flag = {"called": False}

    def _explode(url, **kw):
        pytest.fail("verifier must not be called when --skip-source-verify is set")

    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "gw-tok")
    fake = _fake_notion(page=page)
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    def _llm(**kw):
        llm_flag["called"] = True
        return _good_copy()
    monkeypatch.setattr(mod, "llm_call", _llm)
    monkeypatch.setattr(mod._source_verifier, "verify_source", _explode)

    rc = mod.main([
        "--state-db", str(state_db),
        "--cache-db", str(tmp_path / "llm_cache.sqlite"),
        "--skip-source-verify",
    ])
    assert rc == 0
    assert llm_flag["called"] is True
    assert pid


def test_source_gate_verifier_crash_fails_closed(state_db: Path, monkeypatch):
    pid = _insert(state_db, titular="Crash", notion_page_id="page-crash")
    page = _make_page()
    llm_flag = {"called": False}

    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "gw-tok")
    fake = _fake_notion(page=page)
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: _good_schema())
    def _llm(**kw):
        llm_flag["called"] = True
        return _good_copy()
    monkeypatch.setattr(mod, "llm_call", _llm)

    def _crash(url, **kw):
        raise RuntimeError("unexpected verifier failure")
    monkeypatch.setattr(mod._source_verifier, "verify_source", _crash)

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    assert llm_flag["called"] is False, "LLM must not run when verifier crashes (fail-closed)"
    fake.patch.assert_not_called()
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed_source_unverified"
    assert "verifier_crash" in (row[1] or "")


def test_source_gate_logs_blocked_event(state_db: Path, monkeypatch, tmp_path):
    """The hook must emit ``stage7_5.source_blocked`` to the ops log."""
    ops = tmp_path / "ops.jsonl"
    monkeypatch.setattr(mod, "DEFAULT_OPS_LOG", ops)
    _insert(state_db, titular="Log", notion_page_id="page-log",
            fuentes_urls=json.dumps(["https://example.com/x"]))
    page = _make_page(source="https://example.com/x")
    rc, _ = _run_with_verifier(
        state_db, monkeypatch, page=page, schema=_good_schema(),
        verifier_result={
            "ok": False, "url": "https://example.com/x",
            "reason": "blocklist_domain", "warnings": [],
            "details": {"host": "example.com"},
        },
        extra_args=["--ops-log", str(ops)],
    )
    assert rc == 1
    lines = [
        json.loads(line) for line in ops.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    blocked = [r for r in lines if r["event"] == "stage7_5.source_blocked"]
    assert blocked, lines
    assert blocked[0]["reason"] == "blocklist_domain"



# ---------- Hilo D integration: canonical prompt + ESTADO_LIVE_MAP ---------- #

def test_estado_live_map_constants():
    """Spec→live mapping is the single source of truth, applied at write."""
    assert mod.ESTADO_TARGET == "En revisión"
    assert mod.ESTADO_LIVE_MAP == {
        "En revisión": "Revisión pendiente",
        "Rechazado": "Descartado",
    }
    assert mod.estado_live_name("En revisión") == "Revisión pendiente"
    assert mod.estado_live_name("Rechazado") == "Descartado"
    # Unknown names pass through.
    assert mod.estado_live_name("Aprobado") == "Aprobado"


def test_build_copy_prompt_uses_canonical_files():
    """build_copy_prompt must delegate to prompts/rick/linkedin-copy-*.md.

    Smoke contract: system prompt must contain known anchors from the
    canonical voice doc (Hilo B), proving the wiring is real and not the
    old inline placeholder.
    """
    proposal_row = {
        "id": 99,
        "titular": "BIM coordinado en obra",
        "angulo": "por qué importa",
        "disciplinas": ["BIM", "IFC"],
        "fuentes_urls": ["https://src.test/article"],
        "key_points": ["punto A", "punto B"],
    }
    page_props = {
        "Título": {"type": "title", "title": [{"plain_text": "T"}]},
        "Fuente primaria": {"type": "url", "url": "https://src.test/article"},
        "Body raw": {"type": "rich_text",
                     "rich_text": [{"plain_text": "Resumen body."}]},
    }
    system, user = mod.build_copy_prompt(proposal_row, page_props)
    # Anchors that only exist in the canonical system prompt.
    assert "Sos Rick" in system
    assert "AECO" in system
    assert "Tuteo" in system
    # User-prompt placeholders were filled.
    assert "BIM coordinado en obra" in user
    assert "https://src.test/article" in user
    assert "BIM, IFC" in user
    assert "punto A" in user


def test_e2e_integration_status_writes_revision_pendiente(
    state_db: Path, monkeypatch
):
    """End-to-end: stub LLM, status-typed Estado → PATCH ships live name."""
    pid = _insert(state_db, titular="E2E status", notion_page_id="page-E2ES")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page(estado_type="status")
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema",
                        lambda c, ds: _good_schema(estado_type="status"))
    canned = _good_copy()
    monkeypatch.setattr(mod, "llm_call", lambda **kw: canned)

    rc = mod.main(["--state-db", str(state_db), "--proposal-id", str(pid)])
    assert rc == 0
    fake.patch.assert_called_once()
    payload = fake.patch.call_args.args[1]
    estado = payload["properties"]["Estado"]
    assert estado == {"status": {"name": "Revisión pendiente"}}
    # Must NOT ship the spec name.
    assert "En revisión" not in json.dumps(estado, ensure_ascii=False)


def test_e2e_integration_select_writes_revision_pendiente(
    state_db: Path, monkeypatch
):
    """Same end-to-end path but with select-typed Estado prop."""
    pid = _insert(state_db, titular="E2E select", notion_page_id="page-E2EL")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    page = _make_page(estado_type="select")
    fake = _fake_notion(page=page)
    fake.get.return_value = page
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema",
                        lambda c, ds: _good_schema(estado_type="select"))
    canned = _good_copy()
    monkeypatch.setattr(mod, "llm_call", lambda **kw: canned)

    rc = mod.main(["--state-db", str(state_db), "--proposal-id", str(pid)])
    assert rc == 0
    payload = fake.patch.call_args.args[1]
    assert payload["properties"]["Estado"] == {
        "select": {"name": "Revisión pendiente"}
    }


def test_schema_validation_uses_live_name(state_db: Path, monkeypatch):
    """If live option name is missing, abort with the live name in error."""
    pid = _insert(state_db, titular="Live name missing",
                  notion_page_id="page-LN1")
    monkeypatch.setenv("NOTION_API_KEY", "k")
    monkeypatch.setattr(mod, "_gateway_token", lambda: "tok")
    # Schema still has spec name "En revisión" but NOT live "Revisión pendiente".
    schema = _good_schema(
        estado_options=["Borrador", "Autorizado", "En revisión"],
    )
    fake = MagicMock()
    monkeypatch.setattr(mod, "NotionClient", lambda token: fake)
    monkeypatch.setattr(mod, "fetch_publicaciones_schema", lambda c, ds: schema)
    monkeypatch.setattr(mod, "llm_call", lambda **kw: pytest.fail("no LLM"))

    rc = mod.main(["--state-db", str(state_db)])
    assert rc == 1
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_last_error FROM proposals WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    assert row[0] == "failed"
    assert "notion_estado_option_missing:Revisión pendiente" in (row[1] or "")
