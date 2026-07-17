"""Tests for granola.capitalize_task_from_raw (P1 + P1.1 slices).

All hermetic: ``worker.tasks.granola_task_capitalize.notion_client`` and the
config bindings are mocked. No Notion, no network, no LLM.

Covers the mandatory P1 matrix (dry-run default with zero writes, fail-closed
binding, NOTION_TASKS_DB_ID never used, raw not found / wrong DB, wrong
Destino, unticked gate, anti-Comgrap with/without confirmation, safe dedup,
relation propagation only, invalid Trazabilidad, execute happy path with
verified re-read, the "log miente" regression, wrong URL/flags after re-read,
partial-failure technical close, retry idempotency) plus the P1.1 hardening
matrix:

- canonical identity by URL artefacto (create structurally impossible when the
  raw already points to a valid human task; observed candidate returned when
  expected_task_page_id is missing; mismatch / wrong DB / invalid / inaccessible
  pointers fail closed);
- safe update (human fields never overwritten by defaults; existing Estado
  never degraded; explicit update_fields allowlist with explicit values;
  update_fields=[] -> verified no-op with zero task patch; safe technical fill
  of empty URL fuente only);
- anti-Comgrap unchanged: a legit support Sesión with client+project signals is
  NOT blocked (only Reunión/Llamada trigger the guard).
"""

from __future__ import annotations

import inspect
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")

import worker.tasks.granola_task_capitalize as gtc  # noqa: E402
from worker.tasks.granola_task_capitalize import (  # noqa: E402
    CAPITALIZATION_MODE,
    handle_granola_capitalize_task_from_raw,
)

GRANOLA_DB_ID = "32650000-0000-0000-0000-000000000001"
HUMAN_TASKS_DB_ID = "517bfeb9-6758-4d33-bf6f-6ba1b853bb4a"
RAW_PAGE_ID = "39f50000-0000-0000-0000-00000000aaaa"
TASK_PAGE_ID = "aaaa0000-0000-0000-0000-00000000bbbb"
RAW_URL = "https://notion.so/raw-39f50000"
# Must be a real, parseable Notion page URL carrying TASK_PAGE_ID (P1.1
# canonical-identity extraction).
TASK_URL = f"https://www.notion.so/Reunion-X-{TASK_PAGE_ID.replace('-', '')}"

INGEST_BLOCK = "\n".join(
    [
        "shared_folder_path=G:/Mi unidad/Granola/reunion-x.md",
        "sha1=abc123def456",
        "ingest_path=granola.process_transcript",
        "content_hash=deadbeef",
        "char_count=15234",
        "segment_count=42",
        "ingested_at=2026-07-14T10:00:00Z",
        "truncation_detected=false",
    ]
)

TASKS_DB_SCHEMA = {
    "Nombre": "title",
    "Dominio": "select",
    "Estado": "select",
    "Prioridad": "select",
    "Fecha objetivo": "date",
    "Origen": "select",
    "URL fuente": "url",
    "Notas": "rich_text",
    "Proyecto": "relation",
}

PROCESSED_AT = "2026-07-17T12:00:00+00:00"


# ---------------------------------------------------------------------------
# Raw / task page factories (Notion get_page shape)
# ---------------------------------------------------------------------------


def _title(text):
    return {"type": "title", "title": [{"plain_text": text, "text": {"content": text}}]}


def _select(name):
    return {"type": "select", "select": {"name": name} if name else None}


def _rich(text):
    return {"type": "rich_text", "rich_text": [{"plain_text": text, "text": {"content": text}}] if text else []}


def _checkbox(value):
    return {"type": "checkbox", "checkbox": bool(value)}


def _url(value):
    return {"type": "url", "url": value or None}


def _date(value):
    return {"type": "date", "date": {"start": value} if value else None}


def _relation(ids):
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def make_raw_page(
    *,
    destino="Tarea",
    procesar=True,
    trazabilidad=INGEST_BLOCK,
    cliente_ids=(),
    tipo="Otro",
    proyecto_text="",
    proyecto_rel_ids=(),
    parent_db=GRANOLA_DB_ID,
    estado="Pendiente",
    estado_agente="Pendiente",
    accion_agente="Sin accion",
    url_artefacto="",
    fuente="granola_drive_md",
):
    return {
        "id": RAW_PAGE_ID,
        "url": RAW_URL,
        "parent": {"type": "database_id", "database_id": parent_db},
        "properties": {
            "Nombre": _title("Reunion X"),
            "Fecha": _date("2026-07-10"),
            "Fuente": _select(fuente),
            "Destino canonico": _select(destino),
            "Dominio propuesto": _select("Operacion"),
            "Tipo propuesto": _select(tipo),
            "Resumen agente": _rich("Resumen corto."),
            "Estado": _select(estado),
            "Estado agente": _select(estado_agente),
            "Accion agente": _select(accion_agente),
            "Procesar con agente": _checkbox(procesar),
            "URL artefacto": _url(url_artefacto),
            "Trazabilidad": _rich(trazabilidad),
            "Proyecto": _rich(proyecto_text),
            "Proyecto relacionado": _relation(list(proyecto_rel_ids)),
            "Cliente/Partner relacionado": _relation(list(cliente_ids)),
            "Fecha de acción derivada": _date("2026-07-20"),
            "Estado revisión": _select("No aplica"),
            "Motivo revisión": _select(""),
            "Pregunta de revisión": _rich(""),
            "Recomendación agente": _rich(""),
        },
    }


def make_task_page(
    *,
    title="Reunion X",
    url=TASK_URL,
    project_ids=(),
    parent_db=HUMAN_TASKS_DB_ID,
    estado=None,
    prioridad=None,
    notas=None,
    url_fuente=None,
):
    props = {"Nombre": _title(title)}
    if project_ids:
        props["Proyecto"] = _relation(list(project_ids))
    if estado:
        props["Estado"] = _select(estado)
    if prioridad:
        props["Prioridad"] = _select(prioridad)
    if notas:
        props["Notas"] = _rich(notas)
    if url_fuente:
        props["URL fuente"] = _url(url_fuente)
    return {
        "id": TASK_PAGE_ID,
        "url": url,
        "parent": {"type": "database_id", "database_id": parent_db},
        "properties": props,
    }


def make_closed_raw_page(*, trazabilidad, task_url=TASK_URL, procesar=False, **overrides):
    """Raw page as it should look AFTER a successful close."""
    kwargs = dict(
        destino="Tarea",
        procesar=procesar,
        trazabilidad=trazabilidad,
        estado="Procesada",
        estado_agente="Procesada",
        accion_agente="Capitalizado",
        url_artefacto=task_url,
    )
    kwargs.update(overrides)
    return make_raw_page(**kwargs)


def _final_traceability(canonical_name="Reunion X"):
    from worker.tasks.granola_capitalization import append_capitalization_traceability

    return append_capitalization_traceability(
        INGEST_BLOCK,
        source="granola_drive_md",
        capitalization_mode=CAPITALIZATION_MODE,
        canonical_target_type="task",
        canonical_target_name=canonical_name,
        processed_at=PROCESSED_AT,
    ).text


# ---------------------------------------------------------------------------
# Mock wiring
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setattr(gtc.config, "NOTION_HUMAN_TASKS_DB_ID", HUMAN_TASKS_DB_ID, raising=False)
    monkeypatch.setattr(gtc.config, "NOTION_GRANOLA_DB_ID", GRANOLA_DB_ID, raising=False)
    # Poisoned sentinel: any accidental use of the stack tasks DB must surface.
    monkeypatch.setattr(gtc.config, "NOTION_TASKS_DB_ID", "POISONED-DO-NOT-USE", raising=False)
    yield


@pytest.fixture
def mock_nc(mock_env):
    nc = MagicMock()
    with patch.object(gtc, "notion_client", nc):
        nc.read_database.return_value = {"schema": dict(TASKS_DB_SCHEMA)}
        nc.query_database.return_value = []
        nc.read_page.return_value = {"plain_text": "x" * 500, "title": "Reunion X"}
        yield nc


def wire_pages(nc, *pages_by_id):
    """get_page returns pages by (normalized) id from an ordered mapping list."""
    mapping = {}
    for page in pages_by_id:
        mapping[page["id"].replace("-", "")] = page

    def _get_page(page_id_or_url):
        key = str(page_id_or_url).replace("-", "")
        if key in mapping:
            return mapping[key]
        raise RuntimeError(f"Notion API error (404) during get_page: {page_id_or_url[:8]}")

    nc.get_page.side_effect = _get_page


def assert_no_writes(nc):
    nc.create_database_page.assert_not_called()
    nc.update_page_properties.assert_not_called()


def task_writes(nc):
    return [
        c for c in nc.update_page_properties.call_args_list
        if str(c.args[0] if c.args else c.kwargs.get("page_id_or_url", "")).replace("-", "")
        == TASK_PAGE_ID.replace("-", "")
    ]


def raw_writes(nc):
    return [
        c for c in nc.update_page_properties.call_args_list
        if str(c.args[0] if c.args else c.kwargs.get("page_id_or_url", "")).replace("-", "")
        == RAW_PAGE_ID.replace("-", "")
    ]


# ---------------------------------------------------------------------------
# Safety / preflight
# ---------------------------------------------------------------------------


class TestSafetyAndPreflight:
    def test_registered_in_task_handlers(self):
        from worker.tasks import TASK_HANDLERS

        assert TASK_HANDLERS["granola.capitalize_task_from_raw"] is handle_granola_capitalize_task_from_raw

    def test_module_never_references_stack_tasks_binding(self):
        source = inspect.getsource(gtc)
        # Only allowed inside comments/docstrings that explain the prohibition:
        for line in source.splitlines():
            code = line.split("#", 1)[0]
            if "NOTION_TASKS_DB_ID" in code:
                # Must be inside a string (docstring/error message), never an attribute access.
                assert "config.NOTION_TASKS_DB_ID" not in code

    def test_dry_run_is_default_and_performs_zero_writes(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["dry_run"] is True
        assert result["capitalized"] is False
        assert result["action"] == "create"
        assert result["canonical_identity_source"] == "new"
        assert_no_writes(mock_nc)

    def test_missing_human_tasks_binding_fails_closed(self, mock_env, monkeypatch):
        monkeypatch.setattr(gtc.config, "NOTION_HUMAN_TASKS_DB_ID", None, raising=False)
        nc = MagicMock()
        with patch.object(gtc, "notion_client", nc):
            with pytest.raises(RuntimeError, match="NOTION_HUMAN_TASKS_DB_ID"):
                handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})
        nc.get_page.assert_not_called()
        assert_no_writes(nc)

    def test_never_queries_the_poisoned_stack_tasks_db(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())

        handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        for call in mock_nc.query_database.call_args_list:
            db = call.kwargs.get("database_id") or (call.args[0] if call.args else "")
            assert db == HUMAN_TASKS_DB_ID
        for call in mock_nc.read_database.call_args_list:
            db = call.args[0] if call.args else call.kwargs.get("database_id_or_url", "")
            assert "POISONED" not in str(db)

    def test_raw_not_found_returns_error_without_writes(self, mock_nc):
        wire_pages(mock_nc)  # empty mapping -> 404

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["ok"] is False
        assert result["action"] == "error"
        assert result["reason"] == "raw_page_not_accessible"
        assert_no_writes(mock_nc)

    def test_raw_in_wrong_database_returns_error(self, mock_nc):
        wire_pages(mock_nc, make_raw_page(parent_db="99990000-0000-0000-0000-000000000099"))

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["ok"] is False
        assert result["reason"] == "raw_not_in_transcripciones_granola"
        assert_no_writes(mock_nc)

    def test_destino_not_tarea_is_refused(self, mock_nc):
        wire_pages(mock_nc, make_raw_page(destino="Proyecto"))

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["ok"] is False
        assert result["action"] == "error"
        assert result["reason"] == "destino_canonico_not_tarea"
        assert_no_writes(mock_nc)

    def test_procesar_con_agente_false_is_refused(self, mock_nc):
        wire_pages(mock_nc, make_raw_page(procesar=False))

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["ok"] is False
        assert result["reason"] == "procesar_con_agente_not_set"
        assert_no_writes(mock_nc)

    def test_insufficient_evidence_routes_to_review(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())
        mock_nc.read_page.return_value = {"plain_text": "corto", "title": "Reunion X"}

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["ok"] is False
        assert result["action"] == "review"
        assert result["reason"] == "insufficient_evidence"
        assert result["motivo_revision"] == "Falta evidencia"
        assert result["planned_raw_close"]["_not_written_by_p1"] is True
        assert_no_writes(mock_nc)

    def test_invalid_traceability_routes_to_review_without_write(self, mock_nc):
        wire_pages(mock_nc, make_raw_page(trazabilidad="- residuo legacy markdown"))

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["ok"] is False
        assert result["action"] == "review"
        assert result["reason"] == "invalid_traceability"
        assert result["motivo_revision"] == "Bloqueo técnico"
        assert_no_writes(mock_nc)


class TestAntiComgrap:
    def _commercial_raw(self):
        return make_raw_page(
            cliente_ids=("client-1",),
            tipo="Reunión",
            proyecto_rel_ids=("proj-1",),
        )

    def test_commercial_signals_without_confirmation_route_to_review(self, mock_nc):
        wire_pages(mock_nc, self._commercial_raw())

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["ok"] is False
        assert result["action"] == "review"
        assert result["reason"] == "anti_comgrap_requires_confirmation"
        assert result["motivo_revision"] == "Duda de clasificación"
        assert_no_writes(mock_nc)

    def test_commercial_signals_with_confirmation_proceed(self, mock_nc):
        wire_pages(mock_nc, self._commercial_raw())

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "human_confirmed_task": True}
        )

        assert result["action"] == "create"
        assert result["dry_run"] is True
        assert_no_writes(mock_nc)

    def test_partial_signals_do_not_trigger_guard(self, mock_nc):
        # Client + Reunión but NO project signal -> guard must not fire.
        wire_pages(mock_nc, make_raw_page(cliente_ids=("client-1",), tipo="Reunión"))

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["action"] == "create"

    def test_support_session_with_full_signals_is_not_blocked(self, mock_nc):
        """P1.1 regression: a legit support/training Sesión (e.g. WSP) with a
        client relation AND a project signal must NOT trigger the guard — only
        Reunión/Llamada session types do. Tipo=Sesión is deliberately excluded."""
        wire_pages(
            mock_nc,
            make_raw_page(cliente_ids=("client-wsp",), tipo="Sesión", proyecto_rel_ids=("proj-wsp",)),
        )

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["reason"] != "anti_comgrap_requires_confirmation"
        assert result["action"] == "create"
        assert result["preflight"]["anti_comgrap_signals"]["triggered"] is False


# ---------------------------------------------------------------------------
# P1.1 — Canonical identity by URL artefacto
# ---------------------------------------------------------------------------


class TestCanonicalIdentity:
    """URL artefacto identifies the canonical task: create is structurally
    impossible and title dedup is never consulted."""

    def test_url_artefacto_with_different_title_never_plans_create(self, mock_nc):
        # Raw title "Reunion X" != canonical task title. Old behavior planned a
        # duplicate create; P1.1 must return review (missing expected id).
        wire_pages(
            mock_nc,
            make_raw_page(url_artefacto=TASK_URL),
            make_task_page(title="Titulo canonico distinto"),
        )

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["action"] != "create"
        assert result["action"] == "review"
        assert result["reason"] == "canonical_identity_requires_confirmation"
        assert result["canonical_identity_source"] == "url_artefacto"
        mock_nc.query_database.assert_not_called()  # titles never consulted
        assert_no_writes(mock_nc)

    def test_url_valid_without_expected_returns_observed_candidate(self, mock_nc):
        wire_pages(
            mock_nc,
            make_raw_page(url_artefacto=TASK_URL),
            make_task_page(title="Titulo canonico distinto"),
        )

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        candidate = result["canonical_identity"]["observed_candidate"]
        assert candidate["task_page_id"] == TASK_PAGE_ID
        assert candidate["task_title"] == "Titulo canonico distinto"
        assert result["motivo_revision"] == "Ambigüedad de match"
        assert_no_writes(mock_nc)

    def test_url_valid_with_correct_expected_plans_noop_update(self, mock_nc):
        wire_pages(
            mock_nc,
            make_raw_page(url_artefacto=TASK_URL),
            make_task_page(title="Titulo canonico distinto", url_fuente=RAW_URL),
        )

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "expected_task_page_id": TASK_PAGE_ID}
        )

        assert result["action"] == "update_noop_verified"
        assert result["canonical_identity_source"] == "url_artefacto"
        assert result["canonical_identity"]["task_title"] == "Titulo canonico distinto"
        assert result["update_plan"]["patch_fields"] == []
        assert result["task_name"] == "Titulo canonico distinto"  # observed, not raw title
        mock_nc.query_database.assert_not_called()
        assert_no_writes(mock_nc)

    def test_wrong_expected_id_routes_to_review(self, mock_nc):
        wire_pages(
            mock_nc,
            make_raw_page(url_artefacto=TASK_URL),
            make_task_page(),
        )

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "expected_task_page_id": "11110000-0000-0000-0000-000000009999"}
        )

        assert result["action"] == "review"
        assert result["reason"] == "canonical_identity_mismatch"
        assert_no_writes(mock_nc)

    def test_url_pointing_to_wrong_database_routes_to_review(self, mock_nc):
        wire_pages(
            mock_nc,
            make_raw_page(url_artefacto=TASK_URL),
            make_task_page(parent_db="99990000-0000-0000-0000-000000000099"),
        )

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "expected_task_page_id": TASK_PAGE_ID}
        )

        assert result["action"] == "review"
        assert result["reason"] == "canonical_identity_wrong_database"
        assert result["motivo_revision"] == "Bloqueo técnico"
        assert_no_writes(mock_nc)

    @pytest.mark.parametrize(
        "bad_url",
        [
            "https://example.com/no-es-notion-aaaa000000000000000000000000bbbb",
            "https://www.notion.so/",
            "https://www.notion.so/sin-id-hexadecimal",
            "notion.so/sin-esquema-aaaa000000000000000000000000bbbb",
        ],
    )
    def test_invalid_url_artefacto_routes_to_review(self, mock_nc, bad_url):
        wire_pages(mock_nc, make_raw_page(url_artefacto=bad_url))

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["action"] == "review"
        assert result["reason"] == "canonical_identity_invalid_url"
        assert result["motivo_revision"] == "Bloqueo técnico"
        assert_no_writes(mock_nc)

    def test_inaccessible_url_artefacto_routes_to_review(self, mock_nc):
        # Only the raw is wired; the task page 404s on re-read.
        wire_pages(mock_nc, make_raw_page(url_artefacto=TASK_URL))

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["action"] == "review"
        assert result["reason"] == "canonical_identity_inaccessible"
        assert_no_writes(mock_nc)


# ---------------------------------------------------------------------------
# P1.1 — Safe / idempotent update
# ---------------------------------------------------------------------------


class TestSafeUpdate:
    def _wire_identity_update(self, nc, **task_kwargs):
        task_kwargs.setdefault("title", "Titulo canonico")
        task = make_task_page(**task_kwargs)
        wire_pages(nc, make_raw_page(url_artefacto=TASK_URL), task)
        return task

    def test_existing_estado_never_degraded_by_raw_defaults(self, mock_nc):
        self._wire_identity_update(
            mock_nc, estado="Completada", url_fuente=RAW_URL
        )

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "expected_task_page_id": TASK_PAGE_ID}
        )

        assert result["action"] == "update_noop_verified"
        assert result["planned_task_properties"] == {}
        assert "Estado" in result["update_plan"]["preserved_fields"]

    def test_existing_human_fields_and_relations_preserved(self, mock_nc):
        self._wire_identity_update(
            mock_nc,
            estado="En progreso",
            prioridad="Alta",
            notas="Notas escritas a mano por David",
            url_fuente=RAW_URL,
            project_ids=("proj-human-1",),
        )

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "expected_task_page_id": TASK_PAGE_ID}
        )

        assert result["action"] == "update_noop_verified"
        preserved = set(result["update_plan"]["preserved_fields"])
        assert {"Nombre", "Estado", "Prioridad", "Notas", "URL fuente", "Proyecto"}.issubset(preserved)
        assert result["planned_task_properties"] == {}

    def test_explicit_values_without_allowlist_never_overwrite(self, mock_nc):
        """Defaults / loose inputs do not authorize an overwrite: without
        update_fields the values are ignored on an existing task."""
        self._wire_identity_update(mock_nc, estado="Completada", url_fuente=RAW_URL)

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "expected_task_page_id": TASK_PAGE_ID,
                "estado": "Pendiente",
                "priority": "Baja",
                "notes": "esto no debe escribirse",
            }
        )

        assert result["action"] == "update_noop_verified"
        assert result["planned_task_properties"] == {}

    def test_allowlist_modifies_only_authorized_fields(self, mock_nc):
        self._wire_identity_update(
            mock_nc, estado="Pendiente", notas="Notas humanas", url_fuente=RAW_URL
        )

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "expected_task_page_id": TASK_PAGE_ID,
                "update_fields": ["Estado"],
                "estado": "En progreso",
                "notes": "esto NO esta allowlisted y no debe escribirse",
            }
        )

        assert result["action"] == "update_safe_patch"
        assert result["update_plan"]["patch_fields"] == ["Estado"]
        assert result["update_plan"]["patch_reasons"]["Estado"] == "explicit_update_fields_allowlist"
        assert result["planned_task_properties"] == {"Estado": {"select": {"name": "En progreso"}}}
        assert "Notas" in result["update_plan"]["preserved_fields"]

    def test_allowlisted_field_without_explicit_value_fails_closed(self, mock_nc):
        self._wire_identity_update(mock_nc, url_fuente=RAW_URL)

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "expected_task_page_id": TASK_PAGE_ID,
                "update_fields": ["Estado"],  # no 'estado' value provided
            }
        )

        assert result["ok"] is False
        assert result["action"] == "error"
        assert result["reason"] == "update_field_without_explicit_value"
        assert_no_writes(mock_nc)

    def test_unknown_update_field_fails_closed(self, mock_nc):
        self._wire_identity_update(mock_nc, url_fuente=RAW_URL)

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "expected_task_page_id": TASK_PAGE_ID,
                "update_fields": ["Transcript"],
            }
        )

        assert result["ok"] is False
        assert result["reason"] == "invalid_update_fields"
        assert_no_writes(mock_nc)

    def test_safe_fill_of_empty_url_fuente_only(self, mock_nc):
        # Task WITHOUT URL fuente -> the only default-mode patch allowed is the
        # technical fill of that empty field.
        self._wire_identity_update(mock_nc, estado="Completada")  # no url_fuente

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "expected_task_page_id": TASK_PAGE_ID}
        )

        assert result["action"] == "update_safe_patch"
        assert result["update_plan"]["patch_fields"] == ["URL fuente"]
        assert result["update_plan"]["patch_reasons"]["URL fuente"] == "safe_fill_empty_technical_field"
        assert "Estado" in result["update_plan"]["preserved_fields"]

    def test_nombre_allowlisted_updates_title_expectations(self, mock_nc):
        self._wire_identity_update(mock_nc, url_fuente=RAW_URL)

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "expected_task_page_id": TASK_PAGE_ID,
                "update_fields": ["Nombre"],
                "task_name": "Titulo corregido explicitamente",
            }
        )

        assert result["action"] == "update_safe_patch"
        assert "Nombre" in result["update_plan"]["patch_fields"]
        assert result["task_name"] == "Titulo corregido explicitamente"

    def test_dedup_path_update_also_uses_safe_update(self, mock_nc):
        """Title-dedup update (raw without URL artefacto) goes through the same
        conservative planner: no default overwrites."""
        task = make_task_page(title="Reunion X", estado="Completada", url_fuente=RAW_URL)
        wire_pages(mock_nc, make_raw_page(), task)
        mock_nc.query_database.return_value = [{"id": TASK_PAGE_ID}]

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "expected_task_page_id": TASK_PAGE_ID}
        )

        assert result["action"] == "update_noop_verified"
        assert result["canonical_identity_source"] == "title_dedup"
        assert result["planned_task_properties"] == {}
        assert "Estado" in result["update_plan"]["preserved_fields"]


# ---------------------------------------------------------------------------
# Dedup (create path: raw without URL artefacto)
# ---------------------------------------------------------------------------


class TestDedup:
    def test_zero_matches_plans_create(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())
        mock_nc.query_database.return_value = []

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["action"] == "create"
        assert result["canonical_identity_source"] == "new"
        assert result["dedup"]["matches"] == []

    def test_single_match_without_expected_id_routes_to_review(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())
        mock_nc.query_database.return_value = [{"id": TASK_PAGE_ID}]

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["action"] == "review"
        assert result["reason"] == "single_match_requires_expected_task_page_id"
        assert result["motivo_revision"] == "Ambigüedad de match"
        assert_no_writes(mock_nc)

    def test_wrong_expected_id_routes_to_review(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())
        mock_nc.query_database.return_value = [{"id": TASK_PAGE_ID}]

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "expected_task_page_id": "0000-otro-id"}
        )

        assert result["action"] == "review"
        assert result["reason"] == "expected_task_page_id_mismatch"
        assert_no_writes(mock_nc)

    def test_multiple_matches_route_to_review(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())
        mock_nc.query_database.return_value = [{"id": TASK_PAGE_ID}, {"id": "otra-tarea"}]

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert result["action"] == "review"
        assert result["reason"] == "multiple_exact_title_matches"
        assert_no_writes(mock_nc)


# ---------------------------------------------------------------------------
# Plan contents (dry-run, create path)
# ---------------------------------------------------------------------------


class TestDryRunPlan:
    def test_relations_are_propagated_from_raw_never_invented(self, mock_nc):
        wire_pages(mock_nc, make_raw_page(proyecto_rel_ids=("proj-raw-1",)))

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "human_confirmed_task": True}
        )

        planned = result["planned_task_properties"]
        assert planned["Proyecto"] == {"relation": [{"id": "proj-raw-1"}]}

    def test_no_relation_when_raw_has_none_and_no_explicit_input(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())

        result = handle_granola_capitalize_task_from_raw({"transcript_page_id": RAW_PAGE_ID})

        assert "Proyecto" not in result["planned_task_properties"]

    def test_explicit_project_page_id_wins(self, mock_nc):
        wire_pages(mock_nc, make_raw_page(proyecto_rel_ids=("proj-raw-1",)))

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "human_confirmed_task": True,
                "project_page_id": "proj-explicit-9",
            }
        )

        assert result["planned_task_properties"]["Proyecto"] == {"relation": [{"id": "proj-explicit-9"}]}

    def test_dry_run_never_claims_success_and_reports_exact_plan(self, mock_nc):
        wire_pages(mock_nc, make_raw_page())

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "processed_at": PROCESSED_AT}
        )

        assert result["capitalized"] is False
        assert "verification" not in result
        assert result["planned_traceability_preview"]["preserved_ingest_lines"] == len(
            INGEST_BLOCK.splitlines()
        )
        close = result["planned_raw_close"]
        assert close["Estado"] == {"select": {"name": "Procesada"}}
        assert close["Estado agente"] == {"select": {"name": "Procesada"}}
        assert close["Accion agente"] == {"select": {"name": "Capitalizado"}}
        assert close["Procesar con agente"] == {"checkbox": False}
        assert close["Estado revisión"] == {"select": {"name": "No aplica"}}
        trazabilidad_chunks = close["Trazabilidad"]["rich_text"]
        joined = "".join(chunk["text"]["content"] for chunk in trazabilidad_chunks)
        assert joined.startswith(INGEST_BLOCK)
        assert "canonical_target_url" not in joined


# ---------------------------------------------------------------------------
# Execute + verify-after-write
# ---------------------------------------------------------------------------


class TestExecute:
    def _wire_happy_execute(self, nc, *, task_relations=(), raw_relations=()):
        raw_open = make_raw_page(proyecto_rel_ids=raw_relations)
        final_trace = _final_traceability()
        raw_closed = make_closed_raw_page(trazabilidad=final_trace, proyecto_rel_ids=raw_relations)
        task_final = make_task_page(project_ids=task_relations)

        nc.query_database.return_value = []
        nc.create_database_page.return_value = {"page_id": TASK_PAGE_ID, "url": TASK_URL, "created": True}
        nc.update_page_properties.return_value = {"page_id": RAW_PAGE_ID, "updated": True}

        state = {"raw_calls": 0}

        def _get_page(page_id_or_url):
            key = str(page_id_or_url).replace("-", "")
            if key == RAW_PAGE_ID.replace("-", ""):
                state["raw_calls"] += 1
                return raw_open if state["raw_calls"] == 1 else raw_closed
            if key == TASK_PAGE_ID.replace("-", ""):
                return task_final
            raise RuntimeError("404")

        nc.get_page.side_effect = _get_page
        return raw_closed, task_final

    def test_create_with_verified_reread_passes(self, mock_nc):
        self._wire_happy_execute(mock_nc)

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "dry_run": False, "processed_at": PROCESSED_AT}
        )

        assert result["ok"] is True
        assert result["capitalized"] is True
        assert result["action"] == "create"
        assert result["verification"]["ok"] is True
        mock_nc.create_database_page.assert_called_once()
        db_used = mock_nc.create_database_page.call_args.args[0]
        assert db_used == HUMAN_TASKS_DB_ID

    def test_noop_update_executes_zero_task_patch_and_verifies(self, mock_nc):
        """P1.1: update_fields=[] over a canonical identity -> the task is never
        patched; only the raw is closed/reconciled and both re-reads verify."""
        observed_title = "Titulo canonico distinto"
        final_trace = _final_traceability(canonical_name=observed_title)
        raw_gated = make_raw_page(url_artefacto=TASK_URL, procesar=True)
        raw_after = make_closed_raw_page(trazabilidad=final_trace)
        task_final = make_task_page(title=observed_title, url_fuente=RAW_URL, estado="Completada")

        state = {"raw_calls": 0}

        def _get_page(page_id_or_url):
            key = str(page_id_or_url).replace("-", "")
            if key == RAW_PAGE_ID.replace("-", ""):
                state["raw_calls"] += 1
                return raw_gated if state["raw_calls"] == 1 else raw_after
            if key == TASK_PAGE_ID.replace("-", ""):
                return task_final
            raise RuntimeError("404")

        mock_nc.get_page.side_effect = _get_page

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "dry_run": False,
                "expected_task_page_id": TASK_PAGE_ID,
                "processed_at": PROCESSED_AT,
            }
        )

        assert result["ok"] is True
        assert result["capitalized"] is True
        assert result["action"] == "update_noop_verified"
        assert task_writes(mock_nc) == []  # the task was NEVER patched
        mock_nc.create_database_page.assert_not_called()
        assert len(raw_writes(mock_nc)) == 1  # only the raw close

    def test_safe_patch_update_writes_only_the_allowlisted_field(self, mock_nc):
        observed_title = "Titulo canonico distinto"
        final_trace = _final_traceability(canonical_name=observed_title)
        raw_gated = make_raw_page(url_artefacto=TASK_URL, procesar=True)
        raw_after = make_closed_raw_page(trazabilidad=final_trace)
        task_final = make_task_page(title=observed_title, url_fuente=RAW_URL, estado="En progreso")

        state = {"raw_calls": 0}

        def _get_page(page_id_or_url):
            key = str(page_id_or_url).replace("-", "")
            if key == RAW_PAGE_ID.replace("-", ""):
                state["raw_calls"] += 1
                return raw_gated if state["raw_calls"] == 1 else raw_after
            if key == TASK_PAGE_ID.replace("-", ""):
                return task_final
            raise RuntimeError("404")

        mock_nc.get_page.side_effect = _get_page

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "dry_run": False,
                "expected_task_page_id": TASK_PAGE_ID,
                "update_fields": ["Estado"],
                "estado": "En progreso",
                "processed_at": PROCESSED_AT,
            }
        )

        assert result["ok"] is True
        assert result["action"] == "update_safe_patch"
        writes = task_writes(mock_nc)
        assert len(writes) == 1
        patched = writes[0].kwargs.get("properties") or writes[0].args[1]
        assert patched == {"Estado": {"select": {"name": "En progreso"}}}

    def test_log_miente_relation_not_persisted_fails_verification(self, mock_nc):
        # Raw carries a project relation -> the task write claims it, but the
        # re-read task page comes back WITHOUT the relation.
        self._wire_happy_execute(mock_nc, task_relations=(), raw_relations=("proj-raw-1",))

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "dry_run": False, "processed_at": PROCESSED_AT,
             "human_confirmed_task": True}
        )

        assert result["ok"] is False
        assert result["capitalized"] is False
        assert result["reason"] == "verification_failed"
        fields = {m["field"] for m in result["verification"]["mismatches"]}
        assert "relation:task:Proyecto" in fields
        assert result["technical_review_close_applied"] is True

    def test_wrong_url_artefacto_after_reread_fails(self, mock_nc):
        raw_open = make_raw_page()
        final_trace = _final_traceability()
        raw_closed = make_closed_raw_page(trazabilidad=final_trace, task_url="https://notion.so/OTRA-pagina")
        task_final = make_task_page()

        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {"page_id": TASK_PAGE_ID, "url": TASK_URL, "created": True}
        state = {"raw_calls": 0}

        def _get_page(page_id_or_url):
            key = str(page_id_or_url).replace("-", "")
            if key == RAW_PAGE_ID.replace("-", ""):
                state["raw_calls"] += 1
                return raw_open if state["raw_calls"] == 1 else raw_closed
            return task_final

        mock_nc.get_page.side_effect = _get_page

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "dry_run": False, "processed_at": PROCESSED_AT}
        )

        assert result["ok"] is False
        fields = {m["field"] for m in result["verification"]["mismatches"]}
        assert "URL artefacto" in fields

    def test_procesar_flag_not_reset_after_reread_fails(self, mock_nc):
        raw_open = make_raw_page()
        final_trace = _final_traceability()
        raw_closed = make_closed_raw_page(trazabilidad=final_trace, procesar=True)
        task_final = make_task_page()

        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {"page_id": TASK_PAGE_ID, "url": TASK_URL, "created": True}
        state = {"raw_calls": 0}

        def _get_page(page_id_or_url):
            key = str(page_id_or_url).replace("-", "")
            if key == RAW_PAGE_ID.replace("-", ""):
                state["raw_calls"] += 1
                return raw_open if state["raw_calls"] == 1 else raw_closed
            return task_final

        mock_nc.get_page.side_effect = _get_page

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "dry_run": False, "processed_at": PROCESSED_AT}
        )

        assert result["ok"] is False
        fields = {m["field"] for m in result["verification"]["mismatches"]}
        assert "Procesar con agente" in fields

    def test_partial_failure_task_reread_404_closes_technically(self, mock_nc):
        """Task write 'succeeds' but the task re-read 404s -> structured error +
        technical review close on the raw; never a success, never an unhandled raise."""
        raw_open = make_raw_page()

        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {"page_id": TASK_PAGE_ID, "url": TASK_URL, "created": True}

        def _get_page(page_id_or_url):
            key = str(page_id_or_url).replace("-", "")
            if key == RAW_PAGE_ID.replace("-", ""):
                return raw_open
            raise RuntimeError("Notion API error (404) during get_page")

        mock_nc.get_page.side_effect = _get_page

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "dry_run": False, "processed_at": PROCESSED_AT}
        )

        assert result["ok"] is False
        assert result["capitalized"] is False
        assert result["reason"] == "partial_execution_failure"
        assert result["technical_review_close_applied"] is True
        # The only raw write is the technical review close (Bloqueo técnico),
        # never the success close.
        writes = raw_writes(mock_nc)
        assert len(writes) == 1
        props = writes[0].kwargs.get("properties") or writes[0].args[1]
        assert props["Estado agente"] == {"select": {"name": "Revision requerida"}}
        assert props["Motivo revisión"] == {"select": {"name": "Bloqueo técnico"}}
        assert props["Procesar con agente"] == {"checkbox": False}

    def test_task_write_failure_leaves_raw_untouched(self, mock_nc):
        """If the task create itself fails, the raw is not mutated at all."""
        wire_pages(mock_nc, make_raw_page())
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.side_effect = RuntimeError("Notion API error (500)")

        result = handle_granola_capitalize_task_from_raw(
            {"transcript_page_id": RAW_PAGE_ID, "dry_run": False, "processed_at": PROCESSED_AT}
        )

        assert result["ok"] is False
        assert result["reason"] == "task_write_failed"
        mock_nc.update_page_properties.assert_not_called()

    def test_retry_over_capitalized_row_is_verified_noop(self, mock_nc):
        """Second run over an already-capitalized, re-gated row: the canonical
        identity resolves via URL artefacto, the task is NOT touched, and the
        traceability is reconciled in place (no duplicate block, no new task)."""
        final_trace = _final_traceability()  # canonical name = observed title "Reunion X"
        raw_regated = make_closed_raw_page(trazabilidad=final_trace, procesar=True)
        raw_after = make_closed_raw_page(trazabilidad=final_trace)
        task_final = make_task_page(url_fuente=RAW_URL)

        state = {"raw_calls": 0}

        def _get_page(page_id_or_url):
            key = str(page_id_or_url).replace("-", "")
            if key == RAW_PAGE_ID.replace("-", ""):
                state["raw_calls"] += 1
                return raw_regated if state["raw_calls"] == 1 else raw_after
            if key == TASK_PAGE_ID.replace("-", ""):
                return task_final
            raise RuntimeError("404")

        mock_nc.get_page.side_effect = _get_page

        result = handle_granola_capitalize_task_from_raw(
            {
                "transcript_page_id": RAW_PAGE_ID,
                "dry_run": False,
                "expected_task_page_id": TASK_PAGE_ID,
                "processed_at": PROCESSED_AT,
            }
        )

        assert result["ok"] is True
        assert result["action"] == "update_noop_verified"
        assert result["canonical_identity_source"] == "url_artefacto"
        mock_nc.create_database_page.assert_not_called()
        assert task_writes(mock_nc) == []

        # The traceability written to the raw must equal the reconciled block —
        # same line count, no duplicated capitalization keys.
        raw_write = raw_writes(mock_nc)[0]
        written_props = raw_write.kwargs.get("properties") or raw_write.args[1]
        written_trace = "".join(
            chunk["text"]["content"] for chunk in written_props["Trazabilidad"]["rich_text"]
        )
        assert written_trace == final_trace
        assert written_trace.count("processed_at=") == 1
        assert written_trace.count("capitalization_mode=") == 1
