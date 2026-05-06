"""Unit tests for scripts/discovery/stage3_promote.py."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from discovery import stage3_promote as s3  # noqa: E402

NOW = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)


def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE discovered_items (
            url_canonica TEXT PRIMARY KEY,
            referente_id TEXT NOT NULL,
            referente_nombre TEXT NOT NULL,
            canal TEXT NOT NULL,
            titulo TEXT,
            publicado_en TEXT,
            primera_vez_visto TEXT NOT NULL,
            promovido_a_candidato_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return db


def _insert(db: Path, **fields):
    defaults = {
        "url_canonica": "https://example.com/x",
        "referente_id": "ref-1",
        "referente_nombre": "Ref One",
        "canal": "youtube",
        "titulo": "Title",
        "publicado_en": "Wed, 29 Apr 2026 22:54:14 GMT",
        "primera_vez_visto": "2026-05-06T00:00:00Z",
        "promovido_a_candidato_at": None,
    }
    defaults.update(fields)
    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO discovered_items
           (url_canonica, referente_id, referente_nombre, canal, titulo,
            publicado_en, primera_vez_visto, promovido_a_candidato_at)
           VALUES (:url_canonica, :referente_id, :referente_nombre, :canal,
                   :titulo, :publicado_en, :primera_vez_visto,
                   :promovido_a_candidato_at)""",
        defaults,
    )
    conn.commit()
    conn.close()


# ---------- parse_pub_date ----------


class TestParsePubDate:
    def test_rfc822_gmt(self):
        dt = s3.parse_pub_date("Wed, 29 Apr 2026 22:54:14 GMT")
        assert dt == datetime(2026, 4, 29, 22, 54, 14, tzinfo=timezone.utc)

    def test_rfc822_with_offset(self):
        dt = s3.parse_pub_date("Wed, 24 Apr 2019 08:56:33 +0000")
        assert dt == datetime(2019, 4, 24, 8, 56, 33, tzinfo=timezone.utc)

    def test_iso_with_z(self):
        dt = s3.parse_pub_date("2026-04-29T22:54:14Z")
        assert dt == datetime(2026, 4, 29, 22, 54, 14, tzinfo=timezone.utc)

    def test_iso_with_offset(self):
        dt = s3.parse_pub_date("2026-04-29T22:54:14+02:00")
        assert dt == datetime(2026, 4, 29, 20, 54, 14, tzinfo=timezone.utc)

    def test_iso_naive_assumed_utc(self):
        dt = s3.parse_pub_date("2026-04-29T22:54:14")
        assert dt == datetime(2026, 4, 29, 22, 54, 14, tzinfo=timezone.utc)

    def test_invalid_returns_none(self):
        assert s3.parse_pub_date("not-a-date") is None

    def test_empty_returns_none(self):
        assert s3.parse_pub_date("") is None
        assert s3.parse_pub_date(None) is None


# ---------- classify (eligibility + reasons) ----------


def _item(**kw):
    base = dict(
        url_canonica="https://example.com/x",
        referente_id="ref-1",
        referente_nombre="Ref One",
        canal="youtube",
        titulo="A real title",
        publicado_en="2026-04-29T22:54:14Z",  # 7 days before NOW
        promovido_a_candidato_at=None,
    )
    base.update(kw)
    return s3.Item(**base)


class TestClassify:
    def test_happy_path_eligible(self):
        c = s3.classify(_item(), now=NOW, max_age_days=90)
        assert c.eligible is True
        assert c.reason is None
        assert c.pub_dt is not None

    def test_ya_promovido(self):
        c = s3.classify(
            _item(promovido_a_candidato_at="2026-05-01T00:00:00Z"),
            now=NOW,
            max_age_days=90,
        )
        assert c.eligible is False and c.reason == "ya_promovido"

    def test_canal_no_elegible(self):
        c = s3.classify(_item(canal="linkedin"), now=NOW, max_age_days=90)
        assert c.eligible is False and c.reason == "canal_no_elegible"

    def test_titulo_vacio(self):
        c = s3.classify(_item(titulo="   "), now=NOW, max_age_days=90)
        assert c.eligible is False and c.reason == "titulo_vacio"

    def test_titulo_none(self):
        c = s3.classify(_item(titulo=None), now=NOW, max_age_days=90)
        assert c.eligible is False and c.reason == "titulo_vacio"

    def test_fecha_invalida(self):
        c = s3.classify(_item(publicado_en="garbage"), now=NOW, max_age_days=90)
        assert c.eligible is False and c.reason == "fecha_invalida"

    def test_fecha_none(self):
        c = s3.classify(_item(publicado_en=None), now=NOW, max_age_days=90)
        assert c.eligible is False and c.reason == "fecha_invalida"

    def test_fuera_ventana(self):
        c = s3.classify(
            _item(publicado_en="2019-04-24T08:56:33Z"),
            now=NOW,
            max_age_days=90,
        )
        assert c.eligible is False and c.reason == "fuera_ventana_90d"
        assert c.pub_dt is not None

    def test_rss_canal_eligible(self):
        c = s3.classify(_item(canal="rss"), now=NOW, max_age_days=90)
        assert c.eligible is True


# ---------- order_eligible ----------


class TestOrderEligible:
    def test_orders_desc_by_date_then_url_asc(self):
        c1 = s3.classify(_item(url_canonica="https://a.com/2",
                               publicado_en="2026-04-29T10:00:00Z"),
                         now=NOW, max_age_days=90)
        c2 = s3.classify(_item(url_canonica="https://a.com/1",
                               publicado_en="2026-05-01T10:00:00Z"),
                         now=NOW, max_age_days=90)
        c3 = s3.classify(_item(url_canonica="https://a.com/3",
                               publicado_en="2026-04-29T10:00:00Z"),
                         now=NOW, max_age_days=90)
        ordered = s3.order_eligible([c1, c2, c3])
        assert [c.item.url_canonica for c in ordered] == [
            "https://a.com/1", "https://a.com/2", "https://a.com/3",
        ]


# ---------- end-to-end run with SQLite ----------


def _run(db: Path, tmp_path: Path, *extra) -> tuple[int, dict]:
    out = tmp_path / f"report-{len(list(tmp_path.glob('report-*.json')))}.json"
    rc = s3.main([
        "--sqlite", str(db),
        "--max-age-days", "90",
        "--output", str(out),
        *extra,
    ])
    return rc, json.loads(out.read_text())


class TestRun:
    def test_dry_run_does_not_mutate(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, url_canonica="https://a.com/fresh",
                publicado_en="2026-04-29T22:54:14Z")
        _insert(db, url_canonica="https://a.com/stale",
                publicado_en="2019-04-24T08:56:33Z")

        rc, report = _run(db, tmp_path)
        assert rc == 0
        assert report["overall_pass"] is True
        assert report["mode"] == "dry-run"
        assert report["summary"]["pending_total"] == 2
        assert report["summary"]["eligible"] == 1
        assert report["summary"]["promoted_this_run"] == 0
        assert report["summary"]["discarded_total"] == 1
        assert report["summary"]["discarded_by_reason"]["fuera_ventana_90d"] == 1

        conn = sqlite3.connect(db)
        n = conn.execute(
            "SELECT COUNT(*) FROM discovered_items WHERE promovido_a_candidato_at IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        assert n == 0

    def test_commit_mutates_exactly_selected(self, tmp_path: Path):
        db = _make_db(tmp_path)
        for i in range(5):
            _insert(db, url_canonica=f"https://a.com/{i}",
                    publicado_en=f"2026-05-0{i+1}T00:00:00Z")

        rc, report = _run(db, tmp_path, "--commit", "--limit", "3")
        assert rc == 0
        assert report["overall_pass"] is True
        assert report["mode"] == "commit"
        assert report["summary"]["promoted_this_run"] == 3

        conn = sqlite3.connect(db)
        n = conn.execute(
            "SELECT COUNT(*) FROM discovered_items WHERE promovido_a_candidato_at IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        assert n == 3

    def test_idempotent_commit(self, tmp_path: Path):
        db = _make_db(tmp_path)
        for i in range(3):
            _insert(db, url_canonica=f"https://a.com/{i}",
                    publicado_en=f"2026-05-0{i+1}T00:00:00Z")

        rc1, r1 = _run(db, tmp_path, "--commit")
        assert rc1 == 0 and r1["summary"]["promoted_this_run"] == 3

        rc2, r2 = _run(db, tmp_path, "--commit")
        assert rc2 == 0
        # Second run sees 0 pending → 0 eligible → 0 promoted.
        assert r2["summary"]["pending_total"] == 0
        assert r2["summary"]["eligible"] == 0
        assert r2["summary"]["promoted_this_run"] == 0

    def test_consistency_eligible_plus_discarded_equals_pending(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, url_canonica="https://a.com/ok",
                publicado_en="2026-05-01T00:00:00Z")
        _insert(db, url_canonica="https://a.com/stale",
                publicado_en="2019-01-01T00:00:00Z")
        _insert(db, url_canonica="https://a.com/bad-canal", canal="linkedin")
        _insert(db, url_canonica="https://a.com/bad-titulo", titulo="")
        _insert(db, url_canonica="https://a.com/bad-fecha", publicado_en="x")

        rc, report = _run(db, tmp_path)
        assert rc == 0
        s = report["summary"]
        assert s["pending_total"] == 5
        assert s["eligible"] + s["discarded_total"] == s["pending_total"]
        # Each discarded item carries one of the whitelisted reasons.
        for c in report["discarded_sample"]:
            assert c["reason"] in s3.DISCARD_REASONS

    def test_drift_missing_column_aborts(self, tmp_path: Path):
        db = tmp_path / "broken.sqlite"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE discovered_items (url_canonica TEXT PRIMARY KEY)")
        conn.commit()
        conn.close()
        out = tmp_path / "report.json"
        rc = s3.main(["--sqlite", str(db), "--max-age-days", "90",
                      "--output", str(out)])
        assert rc == 2  # Stage3Error
