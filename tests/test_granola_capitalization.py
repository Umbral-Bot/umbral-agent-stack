"""Tests for worker.tasks.granola_capitalization (P0 slice).

Covers:

- append_capitalization_traceability: ingest preservation, idempotent retries,
  rejection of compacted/legacy/markdown content, no canonical_target_url ever.
- verify_task_capitalization: every mismatch category from the P0 mission,
  including the "log miente" regression (relation claimed but not persisted).

No Notion, no LLM, no network — every input is a plain dict/string built here.
"""

from __future__ import annotations

import inspect

import pytest

from worker.tasks.granola_capitalization import (
    CAPITALIZATION_TRACEABILITY_KEYS,
    ERR_COMPACTED_LINE,
    ERR_DUPLICATE_KEY,
    ERR_FORBIDDEN_NEW_VALUE,
    ERR_INVALID_FORMAT,
    ERR_LEGACY_AMBIGUOUS_CONTENT,
    ExpectedCapitalization,
    RelationExpectation,
    append_capitalization_traceability,
    verify_task_capitalization,
)

# ---------------------------------------------------------------------------
# Fixtures: a realistic P1.1b Drive-ingest Trazabilidad block (V2.1.1 Enmienda)
# ---------------------------------------------------------------------------

P1_1B_INGEST_BLOCK = "\n".join(
    [
        "shared_folder_path=G:/Mi unidad/Perfil de David Moreira/Granola/2026-07/reunion-x.md",
        "sha1=abc123def4567890",
        "ingest_path=granola.process_transcript",
        "content_hash=deadbeef00112233",
        "char_count=15234",
        "segment_count=42",
        "ingested_at=2026-07-14T10:00:00Z",
        "truncation_detected=false",
    ]
)


def _default_capitalization_kwargs(**overrides):
    kwargs = dict(
        source="granola",
        capitalization_mode="task_from_raw_v1",
        canonical_target_type="task",
        canonical_target_name="Tarea X",
        processed_at="2026-07-17T10:00:00Z",
    )
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# append_capitalization_traceability
# ---------------------------------------------------------------------------


class TestAppendCapitalizationTraceability:
    def test_preserves_p1_1b_block_byte_for_byte_and_appends_in_order(self):
        result = append_capitalization_traceability(
            P1_1B_INGEST_BLOCK, **_default_capitalization_kwargs()
        )

        assert result.ok is True
        assert result.error is None

        original_lines = P1_1B_INGEST_BLOCK.splitlines()
        result_lines = result.text.splitlines()

        assert result_lines[: len(original_lines)] == original_lines
        assert result_lines[len(original_lines):] == [
            "source=granola",
            "capitalization_mode=task_from_raw_v1",
            "canonical_target_type=task",
            "canonical_target_name=Tarea X",
            "processed_at=2026-07-17T10:00:00Z",
        ]
        assert result.preserved_lines == tuple(original_lines)
        assert result.appended_keys == CAPITALIZATION_TRACEABILITY_KEYS
        assert result.updated_keys == ()

    def test_truncation_reason_is_optional_and_preserved_when_present(self):
        block_with_reason = P1_1B_INGEST_BLOCK + "\ntruncation_reason=contenido corta a mitad de frase"

        result = append_capitalization_traceability(
            block_with_reason, **_default_capitalization_kwargs()
        )

        assert result.ok is True
        assert "truncation_reason=contenido corta a mitad de frase" in result.preserved_lines

    def test_retry_is_idempotent_no_duplicate_block(self):
        first = append_capitalization_traceability(
            P1_1B_INGEST_BLOCK, **_default_capitalization_kwargs()
        )
        second = append_capitalization_traceability(
            first.text, **_default_capitalization_kwargs()
        )

        assert second.ok is True
        assert second.text == first.text
        assert second.appended_keys == ()
        assert second.updated_keys == ()
        assert len(second.text.splitlines()) == len(first.text.splitlines())

    def test_processed_at_updates_in_place_without_duplicating(self):
        first = append_capitalization_traceability(
            P1_1B_INGEST_BLOCK, **_default_capitalization_kwargs(processed_at="2026-07-17T10:00:00Z")
        )
        second = append_capitalization_traceability(
            first.text, **_default_capitalization_kwargs(processed_at="2026-07-17T11:30:00Z")
        )

        assert second.ok is True
        lines = second.text.splitlines()
        processed_at_lines = [line for line in lines if line.startswith("processed_at=")]
        assert processed_at_lines == ["processed_at=2026-07-17T11:30:00Z"]
        assert second.updated_keys == ("processed_at",)
        assert second.appended_keys == ()
        assert len(lines) == len(first.text.splitlines())

    def test_never_emits_canonical_target_url_and_signature_has_no_such_param(self):
        result = append_capitalization_traceability(
            P1_1B_INGEST_BLOCK, **_default_capitalization_kwargs()
        )
        assert "canonical_target_url" not in result.text

        sig = inspect.signature(append_capitalization_traceability)
        assert "canonical_target_url" not in sig.parameters

    def test_rejects_forbidden_marker_in_a_new_value(self):
        result = append_capitalization_traceability(
            "",
            **_default_capitalization_kwargs(
                canonical_target_name="Ver https://notion.so/abc123"
            ),
        )
        assert result.ok is False
        assert result.error.code == ERR_FORBIDDEN_NEW_VALUE

    def test_rejects_compacted_line(self):
        compacted = "granola_document_id=abc123\nsource=x capitalization_mode=y"
        result = append_capitalization_traceability(
            compacted, **_default_capitalization_kwargs()
        )
        assert result.ok is False
        assert result.error.code == ERR_COMPACTED_LINE

    def test_rejects_duplicate_ingest_key(self):
        dup = "sha1=abc123\nsha1=def456"
        result = append_capitalization_traceability(
            dup, **_default_capitalization_kwargs()
        )
        assert result.ok is False
        assert result.error.code == ERR_DUPLICATE_KEY

    def test_rejects_url_embedded_in_an_existing_value(self):
        existing = "canonical_target_name=Ver https://notion.so/abc123\nprocessed_at=2026-01-01T00:00:00Z"
        result = append_capitalization_traceability(
            existing, **_default_capitalization_kwargs()
        )
        assert result.ok is False
        assert result.error.code == ERR_LEGACY_AMBIGUOUS_CONTENT

    @pytest.mark.parametrize(
        "legacy_text",
        [
            "**Resumen:** sesion intermedia creada y verificada",
            "- Nota antigua sobre la reunion",
            '<mention-page id="abc">Tarea</mention-page>',
            "Ver [la tarea](https://notion.so/abc123)",
            "# Encabezado legacy",
        ],
    )
    def test_rejects_markdown_mention_html_legacy_content(self, legacy_text):
        result = append_capitalization_traceability(
            legacy_text, **_default_capitalization_kwargs()
        )
        assert result.ok is False
        assert result.error.code in (ERR_INVALID_FORMAT, ERR_LEGACY_AMBIGUOUS_CONTENT)

    def test_does_not_mutate_input_string(self):
        original = str(P1_1B_INGEST_BLOCK)
        append_capitalization_traceability(original, **_default_capitalization_kwargs())
        assert original == P1_1B_INGEST_BLOCK

    def test_empty_existing_text_produces_only_the_capitalization_block(self):
        result = append_capitalization_traceability("", **_default_capitalization_kwargs())
        assert result.ok is True
        assert result.preserved_lines == ()
        assert result.appended_keys == CAPITALIZATION_TRACEABILITY_KEYS


# ---------------------------------------------------------------------------
# verify_task_capitalization — page builders
# ---------------------------------------------------------------------------


def _title_prop(text: str) -> dict:
    return {"type": "title", "title": [{"plain_text": text, "text": {"content": text}}]}


def _select_prop(name: str) -> dict:
    return {"type": "select", "select": {"name": name}}


def _rich_text_prop(text: str) -> dict:
    return {"type": "rich_text", "rich_text": [{"plain_text": text, "text": {"content": text}}]}


def _checkbox_prop(value: bool) -> dict:
    return {"type": "checkbox", "checkbox": bool(value)}


def _url_prop(url: str) -> dict:
    return {"type": "url", "url": url}


def _relation_prop(ids: list[str]) -> dict:
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def _raw_page(
    *,
    destino: str,
    estado: str,
    estado_agente: str,
    accion_agente: str,
    procesar: bool,
    url_artefacto: str,
    trazabilidad: str,
    dominio: str,
    tipo: str,
    resumen: str,
    relations: dict | None = None,
) -> dict:
    props = {
        "Nombre": _title_prop("Reunion X"),
        "Destino canonico": _select_prop(destino),
        "Estado": _select_prop(estado),
        "Estado agente": _select_prop(estado_agente),
        "Accion agente": _select_prop(accion_agente),
        "Procesar con agente": _checkbox_prop(procesar),
        "URL artefacto": _url_prop(url_artefacto),
        "Trazabilidad": _rich_text_prop(trazabilidad),
        "Dominio propuesto": _select_prop(dominio),
        "Tipo propuesto": _select_prop(tipo),
        "Resumen agente": _rich_text_prop(resumen),
    }
    for name, ids in (relations or {}).items():
        props[name] = _relation_prop(ids)
    return {"id": "raw-page-id", "url": "https://notion.so/raw-page-id", "properties": props}


def _task_page(*, title: str, url: str, relations: dict | None = None) -> dict:
    props = {"Nombre": _title_prop(title)}
    for name, ids in (relations or {}).items():
        props[name] = _relation_prop(ids)
    return {"id": "task-page-id", "url": url, "properties": props}


_HAPPY_RAW_DEFAULTS = dict(
    destino="Tarea",
    estado="Procesada",
    estado_agente="Procesada",
    accion_agente="Capitalizado",
    procesar=False,
    dominio="Operacion",
    tipo="Reunión",
    resumen="Seguimiento con cliente X",
)


# ---------------------------------------------------------------------------
# verify_task_capitalization
# ---------------------------------------------------------------------------


class TestVerifyTaskCapitalization:
    def test_full_happy_path_is_ok_true(self):
        ingest_lines_before = tuple(P1_1B_INGEST_BLOCK.splitlines())
        cap = append_capitalization_traceability(
            P1_1B_INGEST_BLOCK, **_default_capitalization_kwargs()
        )
        assert cap.ok is True

        raw_page = _raw_page(
            **_HAPPY_RAW_DEFAULTS,
            url_artefacto="https://notion.so/task-x-real",
            trazabilidad=cap.text,
            relations={"Proyecto relacionado": ["proj-1"]},
        )
        task_page = _task_page(
            title="Tarea X",
            url="https://notion.so/task-x-real",
            relations={"Proyecto": ["proj-1"]},
        )
        expected = ExpectedCapitalization(
            task_title="Tarea X",
            ingest_lines_before=ingest_lines_before,
            capitalization_mode="task_from_raw_v1",
            canonical_target_type="task",
            canonical_target_name="Tarea X",
            processed_at="2026-07-17T10:00:00Z",
            expected_relations=(
                RelationExpectation(page="raw", property_name="Proyecto relacionado", expected_ids=("proj-1",)),
                RelationExpectation(page="task", property_name="Proyecto", expected_ids=("proj-1",)),
            ),
        )

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is True
        assert result.mismatches == ()

    def test_detects_missing_task_page(self):
        raw_page = _raw_page(
            **_HAPPY_RAW_DEFAULTS,
            url_artefacto="",
            trazabilidad="",
        )
        expected = ExpectedCapitalization(task_title="Tarea X")

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=None)

        assert result.ok is False
        assert "task_page" in {m.field for m in result.mismatches}

    def test_detects_wrong_task_title(self):
        raw_page = _raw_page(**_HAPPY_RAW_DEFAULTS, url_artefacto="https://notion.so/task-x", trazabilidad="")
        task_page = _task_page(title="Titulo incorrecto", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(task_title="Tarea X")

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "task_title" in {m.field for m in result.mismatches}

    def test_detects_wrong_destino_canonico(self):
        raw_page = _raw_page(
            **{**_HAPPY_RAW_DEFAULTS, "destino": "Proyecto"},
            url_artefacto="https://notion.so/task-x",
            trazabilidad="",
        )
        task_page = _task_page(title="Tarea X", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(task_title="Tarea X")

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "Destino canonico" in {m.field for m in result.mismatches}

    def test_detects_procesar_con_agente_not_reset(self):
        raw_page = _raw_page(
            **{**_HAPPY_RAW_DEFAULTS, "procesar": True},
            url_artefacto="https://notion.so/task-x",
            trazabilidad="",
        )
        task_page = _task_page(title="Tarea X", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(task_title="Tarea X")  # expects procesar_con_agente=False

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "Procesar con agente" in {m.field for m in result.mismatches}

    def test_detects_wrong_url_artefacto(self):
        raw_page = _raw_page(
            **_HAPPY_RAW_DEFAULTS,
            url_artefacto="https://notion.so/WRONG-page",
            trazabilidad="",
        )
        task_page = _task_page(title="Tarea X", url="https://notion.so/task-x-real")
        expected = ExpectedCapitalization(task_title="Tarea X")

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "URL artefacto" in {m.field for m in result.mismatches}

    def test_detects_missing_required_v2_field(self):
        raw_page = _raw_page(
            **{**_HAPPY_RAW_DEFAULTS, "resumen": ""},
            url_artefacto="https://notion.so/task-x",
            trazabilidad="",
        )
        task_page = _task_page(title="Tarea X", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(task_title="Tarea X")

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "Resumen agente" in {m.field for m in result.mismatches}

    def test_detects_malformed_trazabilidad_on_reread(self):
        raw_page = _raw_page(
            **_HAPPY_RAW_DEFAULTS,
            url_artefacto="https://notion.so/task-x",
            trazabilidad="algun texto narrativo sin formato clave=valor",
        )
        task_page = _task_page(title="Tarea X", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(task_title="Tarea X")

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "Trazabilidad_format" in {m.field for m in result.mismatches}

    def test_detects_missing_ingest_key_after_capitalization(self):
        """Regression: a capitalization pass must never drop an ingest key."""
        ingest_lines_before = tuple(P1_1B_INGEST_BLOCK.splitlines())
        cap = append_capitalization_traceability(
            P1_1B_INGEST_BLOCK, **_default_capitalization_kwargs()
        )
        corrupted_text = "\n".join(
            line for line in cap.text.splitlines() if not line.startswith("content_hash=")
        )

        raw_page = _raw_page(
            **_HAPPY_RAW_DEFAULTS,
            url_artefacto="https://notion.so/task-x",
            trazabilidad=corrupted_text,
        )
        task_page = _task_page(title="Tarea X", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(
            task_title="Tarea X",
            ingest_lines_before=ingest_lines_before,
            capitalization_mode="task_from_raw_v1",
            canonical_target_type="task",
            canonical_target_name="Tarea X",
            processed_at="2026-07-17T10:00:00Z",
        )

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "Trazabilidad_ingest_lines" in {m.field for m in result.mismatches}

    def test_detects_reordered_ingest_lines(self):
        ingest_lines_before = tuple(P1_1B_INGEST_BLOCK.splitlines())
        cap = append_capitalization_traceability(
            P1_1B_INGEST_BLOCK, **_default_capitalization_kwargs()
        )
        cap_block_lines = [line for line in cap.text.splitlines() if line not in ingest_lines_before]
        reordered_ingest = list(ingest_lines_before)
        reordered_ingest[0], reordered_ingest[1] = reordered_ingest[1], reordered_ingest[0]
        reordered_text = "\n".join(reordered_ingest + cap_block_lines)

        raw_page = _raw_page(
            **_HAPPY_RAW_DEFAULTS,
            url_artefacto="https://notion.so/task-x",
            trazabilidad=reordered_text,
        )
        task_page = _task_page(title="Tarea X", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(
            task_title="Tarea X",
            ingest_lines_before=ingest_lines_before,
            capitalization_mode="task_from_raw_v1",
            canonical_target_type="task",
            canonical_target_name="Tarea X",
            processed_at="2026-07-17T10:00:00Z",
        )

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "Trazabilidad_ingest_lines_order" in {m.field for m in result.mismatches}

    def test_detects_relation_claimed_but_not_persisted_log_miente_regression(self):
        """The exact 'log miente' pattern from the Notion pilot: the run claims a
        relation was written but the re-read shows it empty."""
        raw_page = _raw_page(
            **_HAPPY_RAW_DEFAULTS,
            url_artefacto="https://notion.so/task-x",
            trazabilidad="",
            relations={"Cliente/Partner relacionado": []},  # claimed written, actually empty
        )
        task_page = _task_page(title="Tarea X", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(
            task_title="Tarea X",
            expected_relations=(
                RelationExpectation(
                    page="raw",
                    property_name="Cliente/Partner relacionado",
                    expected_ids=("client-page-id-123",),
                ),
            ),
        )

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        assert "relation:raw:Cliente/Partner relacionado" in {m.field for m in result.mismatches}

    def test_reports_every_mismatch_not_just_the_first(self):
        raw_page = _raw_page(
            destino="Proyecto",  # wrong
            estado="Pendiente",  # wrong
            estado_agente="Pendiente",  # wrong
            accion_agente="Sin accion",  # wrong
            procesar=True,  # wrong (expects False)
            url_artefacto="https://notion.so/WRONG",  # wrong
            trazabilidad="",
            dominio="Operacion",
            tipo="Reunión",
            resumen="",  # missing
        )
        task_page = _task_page(title="Titulo incorrecto", url="https://notion.so/task-x")
        expected = ExpectedCapitalization(task_title="Tarea X")

        result = verify_task_capitalization(expected, raw_page=raw_page, task_page=task_page)

        assert result.ok is False
        fields = {m.field for m in result.mismatches}
        assert {
            "task_title",
            "Destino canonico",
            "Estado",
            "Estado agente",
            "Accion agente",
            "Procesar con agente",
            "URL artefacto",
            "Resumen agente",
        }.issubset(fields)
