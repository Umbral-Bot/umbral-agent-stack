"""Reading-format + closing-block contract for editorial copy (2026-09-02).

The live post ``bim-carbono-ciclo-de-vida-diseno`` shipped with the bare RICS
address and the brand slogan glued to it at the end of a wall of paragraphs.
These tests pin the three rules that make that state fail instead of ship:

- the ``Fuente:`` line carries ``[texto](url)``, never a bare address;
- the canonical slogan is the last non-empty line;
- a blank line or a markdown ``hr`` separates the slogan from what precedes it.

H2, blockquote and ``hr`` are formatting, not defects: they must never fail.

Run with:
    python -m pytest tests/test_editorial_copy_format.py -v
"""

from scripts.editorial.validate_editorial_copy import (
    CIERRE_CANONICO,
    validate_copy_text,
)

SOURCE_URL = (
    "https://www.rics.org/profession-standards/rics-standards-and-guidance/"
    "sector-standards/construction-standards/whole-life-carbon-assessment"
)
SOURCE_LINK = f"Fuente: [RICS, Whole Life Carbon Assessment]({SOURCE_URL})"

BODY = (
    "## La mesa de revisión\n\n"
    "Dos opciones de fachada cumplen el programa con distinta cantidad de material.\n\n"
    "> Esa diferencia debería estar sobre la mesa antes de cerrar el entregable.\n\n"
    "## Cómo empezar\n\n"
    "Comparar dos opciones y documentar cómo cambian sus cantidades.\n"
)


def _piece(closing: str) -> str:
    return f"{BODY}\n{closing}\n"


def _errors(text: str, channel: str = "blog") -> list[str]:
    return validate_copy_text(text, channel=channel).errors


class TestClosingBlock:
    def test_hyperlinked_source_and_separated_slogan_passes(self):
        result = validate_copy_text(
            _piece(f"{SOURCE_LINK}\n\n{CIERRE_CANONICO}"), channel="blog"
        )
        assert result.ok, result.errors
        assert result.errors == []

    def test_hr_also_counts_as_separation(self):
        result = validate_copy_text(
            _piece(f"{SOURCE_LINK}\n\n---\n\n{CIERRE_CANONICO}"), channel="blog"
        )
        assert result.ok, result.errors

    def test_slogan_glued_to_source_fails(self):
        errors = _errors(_piece(f"{SOURCE_LINK}\n{CIERRE_CANONICO}"))
        assert any("pegado" in e for e in errors), errors

    def test_slogan_not_last_fails(self):
        errors = _errors(
            _piece(f"{SOURCE_LINK}\n\n{CIERRE_CANONICO}\n\nUna coda que sigue el argumento.")
        )
        assert any("última línea" in e for e in errors), errors

    def test_missing_slogan_is_an_error_not_a_warning(self):
        result = validate_copy_text(_piece(SOURCE_LINK), channel="blog")
        assert not result.ok
        assert any("cierre canónico ausente" in e for e in result.errors)

    def test_channel_without_canonical_closing_is_exempt(self):
        # linkedin_empresa accompanies the company post; it carries no slogan.
        result = validate_copy_text(
            f"Un texto breve para compartir.\n\n{SOURCE_LINK}\n",
            channel="linkedin_empresa",
        )
        assert result.ok, result.errors


class TestSourceHyperlink:
    def test_raw_source_url_fails(self):
        errors = _errors(_piece(f"Fuente: {SOURCE_URL}\n\n{CIERRE_CANONICO}"))
        assert any("URL cruda" in e for e in errors), errors

    def test_same_source_pasted_bare_elsewhere_fails(self):
        text = (
            f"{BODY}\nMás contexto en {SOURCE_URL} para el equipo.\n\n"
            f"{SOURCE_LINK}\n\n{CIERRE_CANONICO}\n"
        )
        errors = _errors(text)
        assert any("fuera de un hipervínculo" in e for e in errors), errors

    def test_linkedin_uses_the_same_hyperlink_rule(self):
        ok_text = (
            "En una revisión de diseño, dos soluciones pueden cumplir el programa.\n\n"
            f"{SOURCE_LINK}\n\n{CIERRE_CANONICO}\n"
        )
        assert validate_copy_text(ok_text, channel="linkedin").ok
        bad_text = ok_text.replace(
            f"[RICS, Whole Life Carbon Assessment]({SOURCE_URL})", SOURCE_URL
        )
        assert not validate_copy_text(bad_text, channel="linkedin").ok

    def test_unrelated_url_is_not_a_source_url(self):
        # A published_url injected later by the RRSS worker is not the source
        # address and must not turn a valid copy into a failure.
        text = (
            f"{BODY}\n{SOURCE_LINK}\n\n{CIERRE_CANONICO}\n\n"
        ).replace(f"\n\n{CIERRE_CANONICO}\n\n", f"\n\n{CIERRE_CANONICO}\n")
        result = validate_copy_text(text, channel="blog")
        assert result.ok, result.errors


class TestMarkdownFormattingAllowed:
    def test_h2_blockquote_and_hr_do_not_fail(self):
        text = (
            "## Uno\n\nTexto.\n\n---\n\n> Cita del propio texto.\n\n"
            "## Dos\n\nTexto.\n\n"
            f"{SOURCE_LINK}\n\n{CIERRE_CANONICO}\n"
        )
        result = validate_copy_text(text, channel="blog")
        assert result.ok, result.errors

    def test_h2_count_outside_range_warns_without_failing(self):
        text = (
            "## Uno\n\nTexto.\n\n"
            f"{SOURCE_LINK}\n\n{CIERRE_CANONICO}\n"
        )
        result = validate_copy_text(text, channel="blog")
        assert result.ok, result.errors
        assert any("subtítulos H2" in w for w in result.warnings)
