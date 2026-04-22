"""
Tests for the Publicaciones Notion DB schema spec and validator.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from infra.notion_schema import (
    VALID_PROPERTY_TYPES,
    load_schema,
    summarize_schema,
    validate_database_metadata,
    validate_invariants,
    validate_properties,
    validate_schema,
    validate_state_machine,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCHEMA_PATH = _REPO_ROOT / "notion" / "schemas" / "publicaciones.schema.yaml"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def schema():
    return load_schema(_SCHEMA_PATH)


# ---------------------------------------------------------------------------
# Schema loads
# ---------------------------------------------------------------------------


class TestSchemaLoads:
    def test_schema_loads(self, schema):
        assert isinstance(schema, dict)
        assert "database" in schema
        assert "properties" in schema

    def test_database_name(self, schema):
        assert schema["database"]["name"] == "Publicaciones"

    def test_database_version(self, schema):
        assert schema["database"]["version"] == "0.1.0"

    def test_database_status_draft(self, schema):
        assert schema["database"]["status"] == "draft"


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_has_title_property(self, schema):
        props = schema["properties"]
        titles = [p for p in props if p["type"] == "title"]
        assert len(titles) == 1, "Exactly one title property required"

    def test_all_property_types_valid(self, schema):
        for prop in schema["properties"]:
            assert prop["type"] in VALID_PROPERTY_TYPES, (
                f"Invalid type '{prop['type']}' for property '{prop['name']}'"
            )

    def test_no_duplicate_property_names(self, schema):
        names = [p["name"] for p in schema["properties"]]
        assert len(names) == len(set(names)), "Duplicate property names found"

    def test_has_publication_id(self, schema):
        names = {p["name"] for p in schema["properties"]}
        assert "publication_id" in names

    def test_has_content_hash(self, schema):
        names = {p["name"] for p in schema["properties"]}
        assert "content_hash" in names

    def test_has_idempotency_key(self, schema):
        names = {p["name"] for p in schema["properties"]}
        assert "idempotency_key" in names

    def test_has_canal_select(self, schema):
        canal = next(
            (p for p in schema["properties"] if p["name"] == "Canal"), None
        )
        assert canal is not None
        assert canal["type"] == "select"
        option_names = {o["name"] for o in canal["options"]}
        assert "blog" in option_names
        assert "linkedin" in option_names
        assert "x" in option_names

    def test_has_estado_status(self, schema):
        estado = next(
            (p for p in schema["properties"] if p["name"] == "Estado"), None
        )
        assert estado is not None
        assert estado["type"] == "status"

    def test_has_visual_brief_inline(self, schema):
        names = {p["name"] for p in schema["properties"]}
        assert "Visual brief" in names
        assert "Visual asset URL" in names
        assert "visual_hitl_required" in names

    def test_no_separate_assets_db_property(self, schema):
        """Assets are inline — no relation to a separate Assets DB."""
        for prop in schema["properties"]:
            if prop["type"] == "relation":
                rel_db = prop.get("relation_database", "")
                assert "asset" not in rel_db.lower(), (
                    f"Found relation to assets DB: {rel_db} — v1 uses inline assets"
                )


# ---------------------------------------------------------------------------
# Human gates
# ---------------------------------------------------------------------------


class TestHumanGates:
    def test_has_aprobado_contenido(self, schema):
        prop = next(
            (p for p in schema["properties"] if p["name"] == "aprobado_contenido"),
            None,
        )
        assert prop is not None
        assert prop["type"] == "checkbox"

    def test_has_autorizar_publicacion(self, schema):
        prop = next(
            (p for p in schema["properties"] if p["name"] == "autorizar_publicacion"),
            None,
        )
        assert prop is not None
        assert prop["type"] == "checkbox"

    def test_has_gate_invalidado(self, schema):
        prop = next(
            (p for p in schema["properties"] if p["name"] == "gate_invalidado"),
            None,
        )
        assert prop is not None
        assert prop["type"] == "checkbox"


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class TestStateMachine:
    def test_has_state_machine(self, schema):
        assert "state_machine" in schema

    def test_initial_state(self, schema):
        assert schema["state_machine"]["initial"] == "Idea"

    def test_has_transitions(self, schema):
        transitions = schema["state_machine"]["transitions"]
        assert len(transitions) >= 5

    def test_all_transition_statuses_valid(self, schema):
        errors = validate_state_machine(schema)
        assert errors == [], f"State machine errors: {errors}"

    def test_can_reach_publicado(self, schema):
        """Verify there's a path to Publicado status."""
        transitions = schema["state_machine"]["transitions"]
        to_states = {t["to"] for t in transitions}
        assert "Publicado" in to_states

    def test_can_reach_descartado(self, schema):
        transitions = schema["state_machine"]["transitions"]
        to_states = {t["to"] for t in transitions}
        assert "Descartado" in to_states

    def test_gate_invalidation_transition_exists(self, schema):
        """Aprobado -> Revisión pendiente transition exists for gate invalidation."""
        transitions = schema["state_machine"]["transitions"]
        found = any(
            t.get("to") == "Revisión pendiente"
            and ("Aprobado" in (t.get("from") if isinstance(t.get("from"), list) else [t.get("from", "")]))
            for t in transitions
        )
        assert found, "Missing Aprobado -> Revisión pendiente transition"


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_has_invariants(self, schema):
        assert "invariants" in schema
        assert len(schema["invariants"]) >= 5

    def test_invariant_names_unique(self, schema):
        names = [inv["name"] for inv in schema["invariants"]]
        assert len(names) == len(set(names))

    def test_no_publish_without_gates_invariant(self, schema):
        names = {inv["name"] for inv in schema["invariants"]}
        assert "no_publish_without_gates" in names

    def test_gate_invalidation_invariant(self, schema):
        names = {inv["name"] for inv in schema["invariants"]}
        assert "gate_invalidation_on_comment" in names

    def test_linkedin_x_hitl_invariant(self, schema):
        names = {inv["name"] for inv in schema["invariants"]}
        assert "linkedin_x_require_hitl" in names

    def test_no_separate_assets_db_invariant(self, schema):
        names = {inv["name"] for inv in schema["invariants"]}
        assert "no_separate_assets_db_v1" in names

    def test_referente_not_source_invariant(self, schema):
        names = {inv["name"] for inv in schema["invariants"]}
        assert "referente_is_discovery_not_source" in names


# ---------------------------------------------------------------------------
# Source tracking
# ---------------------------------------------------------------------------


class TestSourceTracking:
    def test_has_fuente_primaria(self, schema):
        names = {p["name"] for p in schema["properties"]}
        assert "Fuente primaria" in names

    def test_has_fuente_referente(self, schema):
        names = {p["name"] for p in schema["properties"]}
        assert "Fuente referente" in names

    def test_has_fuentes_confiables_relation(self, schema):
        prop = next(
            (p for p in schema["properties"] if p["name"] == "Fuentes confiables"),
            None,
        )
        assert prop is not None
        assert prop["type"] == "relation"


# ---------------------------------------------------------------------------
# Parent policy
# ---------------------------------------------------------------------------


class TestParentPolicy:
    def test_has_parent_policy(self, schema):
        policy = schema["database"].get("parent_policy")
        assert policy is not None

    def test_forbidden_parents(self, schema):
        forbidden = schema["database"]["parent_policy"]["forbidden_parents"]
        assert "Control Room" in forbidden
        assert "Bandeja de revisión - Rick" in forbidden

    def test_recommended_parent(self, schema):
        parent = schema["database"]["parent_policy"]["recommended_parent"]
        assert parent == "Sistema Editorial Automatizado Umbral"


# ---------------------------------------------------------------------------
# Full validation
# ---------------------------------------------------------------------------


class TestFullValidation:
    def test_validate_schema_clean(self, schema):
        errors = validate_schema(schema)
        assert errors == [], f"Validation errors: {errors}"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary(self, schema):
        summary = summarize_schema(schema)
        assert summary["name"] == "Publicaciones"
        assert summary["total_properties"] >= 15
        assert "blog" in summary["channels"]
        assert "linkedin" in summary["channels"]
        assert len(summary["statuses"]) >= 5
        assert summary["transitions"] >= 5
        assert summary["invariants"] >= 5


# ---------------------------------------------------------------------------
# Validator error detection
# ---------------------------------------------------------------------------


class TestValidatorErrorDetection:
    def test_catches_missing_database(self):
        errors = validate_database_metadata({})
        assert any("database" in e.lower() for e in errors)

    def test_catches_missing_properties(self):
        errors = validate_properties({"properties": "not a list"})
        assert any("properties" in e.lower() for e in errors)

    def test_catches_invalid_property_type(self):
        schema = {
            "properties": [
                {"name": "Bad", "type": "nonexistent_type"},
                {"name": "Title", "type": "title"},
            ]
        }
        errors = validate_properties(schema)
        assert any("nonexistent_type" in e for e in errors)

    def test_catches_duplicate_property_name(self):
        schema = {
            "properties": [
                {"name": "Dup", "type": "rich_text"},
                {"name": "Dup", "type": "rich_text"},
                {"name": "Title", "type": "title"},
            ]
        }
        errors = validate_properties(schema)
        assert any("Duplicate" in e for e in errors)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_cli_returns_0(self):
        from scripts.validate_notion_schema import main
        ret = main(["--schema", str(_SCHEMA_PATH)])
        assert ret == 0

    def test_cli_returns_1_for_missing(self):
        from scripts.validate_notion_schema import main
        ret = main(["--schema", "/nonexistent/path.yaml"])
        assert ret == 1
