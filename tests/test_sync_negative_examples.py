"""
Tests for scripts/editorial/sync_negative_examples.py (P2.5 — local,
file-based negative-examples store consumable by rick-qa/generation, and the
consult path that demonstrates a negative "blocks/repeats a pattern").
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from scripts.editorial import sync_negative_examples as sne


# ---------------------------------------------------------------------------
# normalize_topic_key (pure function — mirrors worker/tasks/editorial_dedupe.py)
# ---------------------------------------------------------------------------


def test_normalize_topic_key_casefolds_and_strips_accents():
    assert sne.normalize_topic_key("Gobernanza en BIM") == sne.normalize_topic_key("gobernanza  en bim.")


def test_normalize_topic_key_empty_for_falsy_input():
    assert sne.normalize_topic_key(None) == ""
    assert sne.normalize_topic_key("") == ""


# ---------------------------------------------------------------------------
# extract_negative_examples
# ---------------------------------------------------------------------------


def _item(page_id="shortlist-1", ejemplo_negativo=True, **props):
    base = {
        "ejemplo_negativo": ejemplo_negativo,
        "alternativa_id": "ALT-001",
        "Título": "Un ángulo descartado",
        "motivo_descarte": "Fuente es la home, no la pieza concreta.",
        "error_kind": ["fuente_home_no_pieza"],
        "fuente_pieza_url": "https://example.org/piece",
    }
    base.update(props)
    return {"page_id": page_id, "properties": base}


def test_extract_negative_examples_filters_to_ejemplo_negativo_true():
    items = [_item(page_id="a", ejemplo_negativo=True), _item(page_id="b", ejemplo_negativo=False)]
    records = sne.extract_negative_examples(items)
    assert len(records) == 1
    assert records[0]["page_id"] == "a"


def test_extract_negative_examples_shapes_record_fields():
    records = sne.extract_negative_examples([_item()])
    record = records[0]
    assert record["alternativa_id"] == "ALT-001"
    assert record["titulo"] == "Un ángulo descartado"
    assert record["topic_key"] == sne.normalize_topic_key("Un ángulo descartado")
    assert record["motivo_descarte"] == "Fuente es la home, no la pieza concreta."
    assert record["error_kind"] == ["fuente_home_no_pieza"]
    assert record["fuente_pieza_url"] == "https://example.org/piece"


def test_extract_negative_examples_falls_back_to_alternativa_id_when_no_page_id():
    records = sne.extract_negative_examples([{"properties": {"ejemplo_negativo": True, "alternativa_id": "ALT-9"}}])
    assert records[0]["alternativa_id"] == "ALT-9"


# ---------------------------------------------------------------------------
# load / append (JSONL persistence, idempotent)
# ---------------------------------------------------------------------------


def test_load_negative_examples_returns_empty_for_missing_file(tmp_path):
    assert sne.load_negative_examples(tmp_path / "missing.jsonl") == []


def test_append_new_examples_writes_and_is_idempotent(tmp_path):
    path = tmp_path / "negatives.jsonl"
    records = sne.extract_negative_examples([_item()])

    appended_first = sne.append_new_examples(path, records)
    assert appended_first == 1
    assert len(sne.load_negative_examples(path)) == 1

    appended_second = sne.append_new_examples(path, records)
    assert appended_second == 0
    assert len(sne.load_negative_examples(path)) == 1


def test_append_new_examples_only_appends_genuinely_new_records(tmp_path):
    path = tmp_path / "negatives.jsonl"
    first_batch = sne.extract_negative_examples([_item(page_id="a")])
    sne.append_new_examples(path, first_batch)

    second_batch = sne.extract_negative_examples(
        [_item(page_id="a"), _item(page_id="b", alternativa_id="ALT-002")]
    )
    appended = sne.append_new_examples(path, second_batch)
    assert appended == 1
    assert len(sne.load_negative_examples(path)) == 2


def test_append_new_examples_skips_records_without_a_key(tmp_path):
    path = tmp_path / "negatives.jsonl"
    appended = sne.append_new_examples(path, [{"alternativa_id": "", "page_id": ""}])
    assert appended == 0
    assert not path.exists()


# ---------------------------------------------------------------------------
# find_similar_negatives — the actual "blocks/repeats a pattern" consult path
# ---------------------------------------------------------------------------


def test_find_similar_negatives_matches_by_normalized_topic():
    examples = [{"topic_key": sne.normalize_topic_key("Gobernanza en BIM"), "error_kind": []}]
    matches = sne.find_similar_negatives("gobernanza  en  BIM!", [], examples)
    assert matches == examples


def test_find_similar_negatives_matches_by_error_kind_overlap():
    examples = [{"topic_key": "tema completamente distinto", "error_kind": ["fuente_home_no_pieza"]}]
    matches = sne.find_similar_negatives("otro tema", ["fuente_home_no_pieza"], examples)
    assert matches == examples


def test_find_similar_negatives_no_match_returns_empty():
    examples = [{"topic_key": "tema a", "error_kind": ["arco_confuso"]}]
    matches = sne.find_similar_negatives("tema b", ["tono_generico"], examples)
    assert matches == []


def test_find_similar_negatives_empty_candidate_topic_does_not_match_empty_topic_examples():
    # Guard against a vacuous "" == "" match when neither candidate nor
    # example carries a real topic_key.
    examples = [{"topic_key": "", "error_kind": []}]
    matches = sne.find_similar_negatives("", [], examples)
    assert matches == []


# ---------------------------------------------------------------------------
# main() — dry-run sync + local --check-topic-key (no Notion call)
# ---------------------------------------------------------------------------


def test_main_check_topic_key_reads_local_file_only(monkeypatch, capsys, tmp_path):
    path = tmp_path / "negatives.jsonl"
    sne.append_new_examples(path, sne.extract_negative_examples([_item()]))

    monkeypatch.setattr(
        "sys.argv",
        [
            "sync_negative_examples.py",
            "--negatives-path", str(path),
            "--check-topic-key", "Un ángulo descartado",
        ],
    )
    exit_code = sne.main()
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "SIMILAR_NEGATIVES_FOUND count=1" in out


def test_main_check_topic_key_no_match(monkeypatch, capsys, tmp_path):
    path = tmp_path / "negatives.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        ["sync_negative_examples.py", "--negatives-path", str(path), "--check-topic-key", "tema inexistente"],
    )
    exit_code = sne.main()
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "NO_SIMILAR_NEGATIVES" in out


def test_main_requires_shortlist_ds_id_for_sync(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("NOTION_SHORTLIST_DS_ID", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["sync_negative_examples.py", "--negatives-path", str(tmp_path / "negatives.jsonl")],
    )
    exit_code = sne.main()
    err = capsys.readouterr().err
    assert exit_code == 2
    assert "shortlist-ds-id" in err


def test_main_dry_run_sync_previews_without_writing(monkeypatch, capsys, tmp_path):
    path = tmp_path / "negatives.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "sync_negative_examples.py",
            "--negatives-path", str(path),
            "--shortlist-ds-id", "shortlist-ds",
            "--dry-run",
        ],
    )
    fake_wc = MagicMock()
    fake_wc.run.return_value = {"result": {"items": [_item()]}}
    with patch("scripts.editorial.sync_negative_examples._resolve_worker_client", return_value=fake_wc):
        exit_code = sne.main()

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "DRY_RUN scanned=1 negatives_found=1 new=1" in out
    assert not path.exists()


def test_main_sync_appends_to_file(monkeypatch, capsys, tmp_path):
    path = tmp_path / "negatives.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        ["sync_negative_examples.py", "--negatives-path", str(path), "--shortlist-ds-id", "shortlist-ds"],
    )
    fake_wc = MagicMock()
    fake_wc.run.return_value = {"result": {"items": [_item()]}}
    with patch("scripts.editorial.sync_negative_examples._resolve_worker_client", return_value=fake_wc):
        exit_code = sne.main()

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "SYNCED scanned=1 negatives_found=1 appended=1" in out
    assert path.is_file()
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["alternativa_id"] == "ALT-001"
