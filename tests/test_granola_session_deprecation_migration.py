import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(module_name: str):
    script_path = REPO_ROOT / "scripts" / "run_granola_session_deprecation_migration.py"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_match_raw_record_prefers_source_url():
    module = _load_script_module("granola_session_migration_match_source")
    raw_records = [
        {
            "page_id": "raw-a",
            "url": "https://notion.so/raw-a",
            "title": "Sesion A",
            "date": "2026-04-01",
            "properties": {module.RAW_ARTIFACT_URL_FIELD: ""},
        },
        {
            "page_id": "raw-b",
            "url": "https://notion.so/raw-b",
            "title": "Sesion B",
            "date": "2026-04-01",
            "properties": {module.RAW_ARTIFACT_URL_FIELD: ""},
        },
    ]
    session_record = {
        "page_id": "session-1",
        "url": "https://notion.so/session-1",
        "title": "Sesion B",
        "date": "2026-04-01",
        "properties": {"URL fuente": "https://notion.so/raw-a"},
    }

    match, method = module._match_raw_record(session_record, raw_records)

    assert match["page_id"] == "raw-a"
    assert method == "url_fuente"


def test_match_raw_record_falls_back_to_raw_artifact_url():
    module = _load_script_module("granola_session_migration_match_artifact")
    raw_records = [
        {
            "page_id": "raw-a",
            "url": "https://notion.so/raw-a",
            "title": "Otra sesion",
            "date": "2026-04-01",
            "properties": {module.RAW_ARTIFACT_URL_FIELD: "https://notion.so/session-2"},
        }
    ]
    session_record = {
        "page_id": "session-2",
        "url": "https://notion.so/session-2",
        "title": "Sesion distinta",
        "date": "2026-04-02",
        "properties": {"URL fuente": ""},
    }

    match, method = module._match_raw_record(session_record, raw_records)

    assert match["page_id"] == "raw-a"
    assert method == "raw_url_artefacto"


def test_match_raw_record_uses_normalized_title_and_date():
    module = _load_script_module("granola_session_migration_match_normalized")
    raw_records = [
        {
            "page_id": "raw-a",
            "url": "https://notion.so/raw-a",
            "title": "Asesoria Discurso",
            "date": "2026-04-01",
            "properties": {module.RAW_ARTIFACT_URL_FIELD: ""},
        }
    ]
    session_record = {
        "page_id": "session-1",
        "url": "https://notion.so/session-1",
        "title": "Asesoría Discurso",
        "date": "2026-04-01",
        "properties": {"URL fuente": ""},
    }

    match, method = module._match_raw_record(session_record, raw_records)

    assert match["page_id"] == "raw-a"
    assert method == "titulo_fecha_normalizados"


def test_body_is_shell_detects_blank_or_notes_only():
    module = _load_script_module("granola_session_migration_shell")

    assert module._body_is_shell("", "Resumen corto", "Sesion A", "2026-04-01") is True
    assert module._body_is_shell("Resumen corto", "Resumen corto", "Sesion A", "2026-04-01") is True
    assert module._body_is_shell("Resumen\nResumen corto", "Resumen corto", "Sesion A", "2026-04-01") is True
    assert module._body_is_shell("Decision importante distinta", "Resumen corto", "Sesion A", "2026-04-01") is False


def test_load_db_schema_unions_database_and_row_properties(monkeypatch):
    module = _load_script_module("granola_session_migration_schema_union")

    monkeypatch.setattr(
        module.notion_client,
        "read_database",
        lambda database_id, max_items=1: {"schema": {module.RAW_PROPOSED_DOMAIN_FIELD: "select"}},
    )
    monkeypatch.setattr(
        module.notion_client,
        "query_database",
        lambda database_id: [
            {
                "properties": {
                    module.RAW_PROGRAM_RELATION_FIELD: {"type": "relation"},
                    module.RAW_RESOURCE_RELATION_FIELD: {"type": "relation"},
                }
            }
        ],
    )

    schema = module._load_db_schema("db-1")

    assert schema[module.RAW_PROPOSED_DOMAIN_FIELD] == "select"
    assert schema[module.RAW_PROGRAM_RELATION_FIELD] == "relation"
    assert schema[module.RAW_RESOURCE_RELATION_FIELD] == "relation"


def test_build_raw_update_from_session_backfills_raw_and_replaces_session_artifact():
    module = _load_script_module("granola_session_migration_backfill")

    raw_record = {
        "page_id": "raw-1",
        "url": "https://notion.so/raw-1",
        "title": "Sesion A",
        "date": "2026-04-01",
        "properties": {
            module.RAW_AGENT_SUMMARY_FIELD: "Resumen agente",
            module.RAW_AGENT_LOG_FIELD: "log previo",
            module.RAW_ARTIFACT_URL_FIELD: "https://notion.so/session-1",
        },
    }
    session_record = {
        "page_id": "session-1",
        "url": "https://notion.so/session-1",
        "title": "Sesion A",
        "date": "2026-04-01",
        "properties": {
            "Dominio": "Operacion",
            "Tipo": "Reunión",
            "Proyecto": ["proj-1"],
            "Programa": [],
            "Recurso relacionado": [],
            "Notas": "Nota migrada",
        },
    }
    raw_schema = {
        module.RAW_PROPOSED_DOMAIN_FIELD: "select",
        module.RAW_PROPOSED_TYPE_FIELD: "select",
        module.RAW_PROJECT_RELATION_FIELD: "relation",
        module.RAW_PROGRAM_RELATION_FIELD: "relation",
        module.RAW_RESOURCE_RELATION_FIELD: "relation",
        module.RAW_TEXT_PROJECT_FIELD: "rich_text",
    }
    page_cache = {
        "proj-1": {"title": "Proyecto Uno", "url": "https://notion.so/proj-1"},
        "program-1": {"title": "Programa Uno", "url": "https://notion.so/program-1"},
        "resource-1": {"title": "Recurso Uno", "url": "https://notion.so/resource-1"},
    }

    properties, requires_review = module._build_raw_update_from_session(
        raw_record=raw_record,
        session_record=session_record,
        raw_schema=raw_schema,
        page_cache=page_cache,
    )

    assert requires_review is False
    assert properties[module.RAW_PROPOSED_DOMAIN_FIELD]["select"]["name"] == "Operacion"
    assert properties[module.RAW_PROPOSED_TYPE_FIELD]["select"]["name"] == "Reunión"
    assert properties[module.RAW_PROJECT_RELATION_FIELD]["relation"] == [{"id": "proj-1"}]
    assert properties[module.RAW_TEXT_PROJECT_FIELD]["rich_text"][0]["text"]["content"] == "Proyecto Uno"
    assert properties[module.RAW_ARTIFACT_URL_FIELD]["url"] == "https://notion.so/proj-1"
    assert "Nota migrada" in properties[module.RAW_AGENT_LOG_FIELD]["rich_text"][0]["text"]["content"]


def test_build_raw_update_from_session_marks_review_when_session_artifact_cannot_be_replaced():
    module = _load_script_module("granola_session_migration_review")

    raw_record = {
        "page_id": "raw-1",
        "url": "https://notion.so/raw-1",
        "title": "Sesion A",
        "date": "2026-04-01",
        "properties": {
            module.RAW_AGENT_SUMMARY_FIELD: "",
            module.RAW_AGENT_LOG_FIELD: "",
            module.RAW_ARTIFACT_URL_FIELD: "https://notion.so/session-1",
        },
    }
    session_record = {
        "page_id": "session-1",
        "url": "https://notion.so/session-1",
        "title": "Sesion A",
        "date": "2026-04-01",
        "properties": {
            "Dominio": "Operacion",
            "Tipo": "Reunión",
            "Proyecto": [],
            "Programa": [],
            "Recurso relacionado": [],
            "Notas": "",
        },
    }
    raw_schema = {
        module.RAW_PROPOSED_DOMAIN_FIELD: "select",
        module.RAW_PROPOSED_TYPE_FIELD: "select",
    }

    properties, requires_review = module._build_raw_update_from_session(
        raw_record=raw_record,
        session_record=session_record,
        raw_schema=raw_schema,
        page_cache={},
    )

    assert requires_review is True
    assert properties[module.RAW_ARTIFACT_URL_FIELD]["url"] is None
    assert properties[module.RAW_AGENT_STATE_FIELD]["select"]["name"] == "Revision requerida"
    assert properties[module.RAW_AGENT_ACTION_FIELD]["select"]["name"] == "Bloqueado por ambiguedad"
