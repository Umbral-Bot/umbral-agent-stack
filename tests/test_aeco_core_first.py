from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _Response:
    def __init__(self, status_code: int, content_type: str | None = None):
        self.status_code = status_code
        self.headers = {}
        if content_type is not None:
            self.headers["content-type"] = content_type


def _seed(mod, url: str, expected: str | None = None):
    return mod.Seed(
        url=url,
        doc_id="doc",
        version=None,
        valid_from=None,
        expected_content_type=expected,
        source_type="buildingsmart",
        jurisdiction="intl",
        doc_type="spec",
        default_lang="en",
    )


def test_source_crawler_preflight_rejects_404_seed():
    mod = _load_script_module("aeco_source_crawler_test", "scripts/aeco-kb/source_crawler.py")

    class Client:
        def head(self, url):
            return _Response(404, "text/html")

        def get(self, url, headers=None):
            raise AssertionError("GET fallback should not run after 404")

    result = mod.preflight_seed_url(Client(), _seed(mod, "https://example.test/missing.pdf"))

    assert result.ok is False
    assert result.status_code == 404
    assert result.error == "HTTP 404"


def test_source_crawler_preflight_accepts_exp_with_inferred_type():
    mod = _load_script_module("aeco_source_crawler_test2", "scripts/aeco-kb/source_crawler.py")

    class Client:
        def head(self, url):
            return _Response(200)

        def get(self, url, headers=None):
            return _Response(206)

    result = mod.preflight_seed_url(
        Client(),
        _seed(mod, "https://standards.buildingsmart.org/IFC4X3_ADD2.exp", "text/plain"),
    )

    assert result.ok is True
    assert result.content_type == "text/plain"
    assert mod.supported_extension(result.content_type, result.seed.url) == "txt"


def test_pdf_parser_extracts_text_from_html_and_ignores_scripts(monkeypatch):
    monkeypatch.setenv("LANG", "C.UTF-8")
    mod = _load_script_module("aeco_pdf_parser_test", "scripts/aeco-kb/pdf_parser.py")

    paragraphs, headings, tables = mod.parse_text_bytes(
        b"<html><body><h1>IFC Scope</h1><p>Building data model content.</p>"
        b"<script>secret()</script></body></html>",
        "aeco/raw/buildingsmart/scope.html",
    )

    assert headings == {}
    assert tables == []
    joined = "\n".join(paragraphs)
    assert "IFC Scope" in joined
    assert "Building data model content" in joined
    assert "secret()" not in joined
    assert mod.parse_args(["--source-type", "buildingsmart"]).lang == "en"


def test_verify_kb_alias_resolution_falls_back_after_bad_api(monkeypatch):
    mod = _load_script_module("aeco_verify_kb_test", "scripts/aeco-kb/verify_kb.py")
    responses = [
        httpx.Response(400, text="unsupported api-version"),
        httpx.Response(200, json={"indexes": ["aeco-kb-es-v20260603"]}),
    ]
    seen_urls: list[str] = []

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url, headers=None):
            seen_urls.append(url)
            return responses.pop(0)

    monkeypatch.setattr(httpx, "Client", Client)

    assert mod.get_active_index("svc", "aeco-kb-es-current", "token") == "aeco-kb-es-v20260603"
    assert "/aliases('" in seen_urls[0]
    assert len(seen_urls) == 2


def test_index_publisher_search_doc_uses_chunk_metadata_fallback():
    mod = _load_script_module("aeco_index_publisher_test", "scripts/aeco-kb/index_publisher.py")

    doc = mod.chunk_to_search_doc(
        {
            "content": "IFC wall content",
            "source_url": "https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/",
            "source_type": "buildingsmart",
            "jurisdiction": "intl",
            "doc_type": "spec",
            "version": "IFC-4.3.2.0",
            "lang": "en",
            "valid_from": "2024-04-01",
            "chunk_id": 7,
            "parent_doc_id": "IFC-4.3.2.0-overview",
        },
        "aeco-kb-es-v20260603",
    )

    assert doc["source_url"].startswith("https://standards.buildingsmart.org/")
    assert doc["jurisdiction"] == "intl"
    assert doc["doc_type"] == "spec"
    assert doc["version"] == "IFC-4.3.2.0"
    assert doc["lang"] == "en"
