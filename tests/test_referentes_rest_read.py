from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.smoke import referentes_rest_read as smoke


def _prop_title(value: str) -> dict:
    return {"type": "title", "title": [{"plain_text": value}]}


def _prop_url(value: str | None) -> dict:
    return {"type": "url", "url": value}


def _prop_rich_text(value: str) -> dict:
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def _prop_select(value: str | None) -> dict:
    return {"type": "select", "select": {"name": value} if value else None}


def _prop_multi_select(values: list[str]) -> dict:
    return {"type": "multi_select", "multi_select": [{"name": value} for value in values]}


def _prop_date(value: str) -> dict:
    return {"type": "date", "date": {"start": value}}


def _referente_row(
    index: int,
    confianza: str,
    *,
    flags: list[str] | None = None,
    linkedin_url: str | None = None,
) -> dict:
    properties = {
        "Nombre": _prop_title(f"Referente {index:02d}"),
        "LinkedIn activity feed": _prop_url(linkedin_url),
        "YouTube channel": _prop_url(f"https://youtube.com/@referente{index:02d}"),
        "Web / Newsletter": _prop_url(f"https://example.com/ref-{index:02d}"),
        "RSS feed": _prop_url(None),
        "Otros canales": _prop_rich_text(""),
        "Última actividad detectada": _prop_rich_text("May 2026"),
        "Confianza canales": _prop_select(confianza),
        "Flags canales": _prop_multi_select(flags or []),
        "Notas canales": _prop_rich_text(""),
        "Última auditoría canales": _prop_date("2026-05-05"),
    }
    return {
        "id": f"00000000-0000-0000-0000-{index:012d}",
        "url": f"https://notion.so/ref-{index:02d}",
        "properties": properties,
    }


def _registry_yaml(path: Path) -> Path:
    path.write_text(
        """
critical_databases:
  another_surface:
    data_source_id: "unused"
reference_systems:
  referencias_referentes:
    database_id: "05f04d48c44943e8b4acc572a4ec6f19"
    data_source_id: "afc8d960-086c-4878-b562-7511dd02ff76"
    runtime_notes:
      population_2026_05_05: 26
      schema_extension_2026_05_05:
        new_columns:
          - name: "LinkedIn activity feed"
            type: "url"
          - name: "YouTube channel"
            type: "url"
          - name: "Web / Newsletter"
            type: "url"
          - name: "RSS feed"
            type: "url"
          - name: "Otros canales"
            type: "rich_text"
          - name: "Última actividad detectada"
            type: "rich_text"
          - name: "Confianza canales"
            type: "select"
            values: ["ALTA", "MEDIA", "BAJA", "DUPLICADO"]
          - name: "Flags canales"
            type: "multi_select"
            values: ["ACTIVIDAD_BAJA", "POSIBLE_INACTIVO", "SLUG_DIFIERE", "DUP", "RSS_NO_CONFIRMADO", "REQUIERE_VERIFICACION_MANUAL", "SIN_LINKEDIN", "CAMBIO_DE_PLATAFORMA"]
          - name: "Notas canales"
            type: "rich_text"
          - name: "Última auditoría canales"
            type: "date"
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _data_source() -> dict:
    return {"properties": {column: {"name": column} for column in smoke.NEW_CHANNEL_COLUMNS}}


def test_load_registry_entry_reads_referentes_data_source(tmp_path: Path) -> None:
    registry = smoke.load_registry_entry(_registry_yaml(tmp_path / "registry.yaml"))

    assert registry.data_source_id == "afc8d960-086c-4878-b562-7511dd02ff76"
    assert registry.database_id == "05f04d48c44943e8b4acc572a4ec6f19"
    assert registry.expected_row_count == 26
    assert registry.expected_columns == smoke.NEW_CHANNEL_COLUMNS
    assert registry.expected_confianza == {"ALTA", "MEDIA", "BAJA", "DUPLICADO"}
    assert registry.expected_flags == smoke.ALLOWED_FLAGS


def test_resolve_registry_path_fails_cleanly_when_sibling_is_missing(tmp_path: Path) -> None:
    with pytest.raises(smoke.SmokeSetupError, match="Missing notion-governance registry"):
        smoke.resolve_registry_path(str(tmp_path / "missing.yaml"))


def test_build_report_passes_with_expected_rows(tmp_path: Path) -> None:
    registry = smoke.load_registry_entry(_registry_yaml(tmp_path / "registry.yaml"))
    rows = [
        _referente_row(1, "ALTA", linkedin_url="https://www.linkedin.com/in/a/recent-activity/all/"),
        _referente_row(2, "MEDIA", flags=["RSS_NO_CONFIRMADO"]),
        _referente_row(3, "DUPLICADO", flags=["DUP"]),
    ]
    rows.extend(_referente_row(index, "BAJA") for index in range(4, 27))

    report = smoke.build_report(registry=registry, data_source=_data_source(), rows=rows)

    assert report["overall_pass"] is True
    assert all(check["pass"] for check in report["checks"].values())
    assert report["row_count"] == 26
    assert report["observed_enums"]["confianza_canales"] == [
        "ALTA",
        "BAJA",
        "DUPLICADO",
        "MEDIA",
    ]
    assert report["observed_enums"]["flags_canales"] == ["DUP", "RSS_NO_CONFIRMADO"]
    assert len(report["sample_rows"]) == 3
    json.dumps(report)


def test_build_report_flags_invalid_enums_and_urls(tmp_path: Path) -> None:
    registry = smoke.load_registry_entry(_registry_yaml(tmp_path / "registry.yaml"))
    rows = [
        _referente_row(1, "ALTA", linkedin_url="not a url"),
        _referente_row(2, "MEDIA", flags=["FLAG_NUEVO"]),
        _referente_row(3, "DUPLICADO"),
    ]
    rows.extend(_referente_row(index, "FUERA_ENUM") for index in range(4, 27))

    report = smoke.build_report(registry=registry, data_source=_data_source(), rows=rows)

    assert report["overall_pass"] is False
    assert report["checks"]["c_linkedin_activity_feed_urls"]["pass"] is False
    assert report["checks"]["d_confianza_enum"]["pass"] is False
    assert report["checks"]["e_flags_enum"]["pass"] is False
    assert report["invalid_urls"][0]["field"] == "LinkedIn activity feed"
    assert report["checks"]["d_confianza_enum"]["invalid_values"] == ["FUERA_ENUM"]
    assert report["checks"]["e_flags_enum"]["invalid_values"] == ["FLAG_NUEVO"]
    json.dumps(report)
