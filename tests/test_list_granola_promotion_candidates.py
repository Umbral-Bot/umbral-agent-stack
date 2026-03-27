import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_normalize_title_removes_accents_and_punctuation():
    module = _load_script_module(
        "list_granola_promotion_candidates_normalize",
        "scripts/list_granola_promotion_candidates.py",
    )

    assert module._normalize_title("Reunión Con Jorge de Boragó") == "reunion con jorge de borago"


def test_classify_raw_items_marks_promoted_duplicate_and_smoke():
    module = _load_script_module(
        "list_granola_promotion_candidates_classify",
        "scripts/list_granola_promotion_candidates.py",
    )

    raw_items = [
        {
            "page_id": "raw-promoted",
            "title": "Reunión Con Jorge de Boragó",
            "url": "https://notion.so/raw-promoted",
            "properties": {
                "Fecha": {"start": "2026-03-24"},
                "Fuente": "granola",
                "Estado": "Pendiente",
            },
        },
        {
            "page_id": "raw-duplicate",
            "title": "Reunión Con Jorge de Boragó",
            "url": "https://notion.so/raw-duplicate",
            "properties": {
                "Fecha": {"start": "2026-03-24"},
                "Fuente": "granola",
                "Estado": "Pendiente",
            },
        },
        {
            "page_id": "raw-smoke",
            "title": "smoke_test_20260317_183742",
            "url": "https://notion.so/raw-smoke",
            "properties": {
                "Fecha": {"start": "2026-03-17"},
                "Fuente": "granola",
                "Estado": "Pendiente",
            },
        },
        {
            "page_id": "raw-candidate",
            "title": "Asesoría discurso",
            "url": "https://notion.so/raw-candidate",
            "properties": {
                "Fecha": {"start": "2026-03-23"},
                "Fuente": "granola",
                "Estado": "Pendiente",
            },
        },
    ]
    curated_items = [
        {
            "properties": {
                "URL fuente": "https://notion.so/raw-promoted",
            }
        }
    ]

    result = module._classify_raw_items(raw_items, curated_items)
    classifications = {item["page_id"]: item["classification"] for item in result["items"]}

    assert classifications["raw-promoted"] == "promoted"
    assert classifications["raw-duplicate"] == "duplicate_of_promoted"
    assert classifications["raw-smoke"] == "smoke_or_test"
    assert classifications["raw-candidate"] == "candidate"
    assert result["summary"]["candidate_count"] == 1
