"""Offline characterization of matching and query coverage. No runtime imports."""
import ast
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest import TestCase, main
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]

def functions(path, names, bindings):
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), bindings)
    return bindings

class DetectionContract(TestCase):
    def test_existing_matching_and_ambiguity_characterization(self):
        g = functions(ROOT / "worker/tasks/granola.py",
                      {"_normalize_lookup_text", "_select_preferred_raw_candidate", "_find_existing_raw_candidate"},
                      {"unicodedata": unicodedata, "Dict": Dict, "Any": Any})
        args = dict(title="Synthetic", transcript_date="2026-11-15", granola_document_id="doc-a",
                    source_url="", source_updated_at="", export_signature="", content_hash="", shared_folder_path="", sha1="")
        a = dict(page_id="a", title="Synthetic", normalized_title="synthetic", date="2026-11-15", granola_document_id="doc-a")
        find = g["_find_existing_raw_candidate"]
        self.assertEqual(find([a], **args)[1], "granola_document_id")
        self.assertEqual(find([{**a, "granola_document_id": "other"}], **args), (None, ""))
        legacy = {**a, "granola_document_id": ""}
        self.assertEqual(find([legacy], **args)[1], "exact_title_date")
        # Current gaps documented explicitly, NOT a safe-to-create contract:
        self.assertEqual(find([legacy, {**legacy, "page_id": "b"}], **args), (None, ""))
        self.assertEqual(find([a, {**a, "page_id": "b"}], **args)[0]["page_id"], "a")

    def query(self, replies):
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        response = Mock(side_effect=replies)
        g = functions(ROOT / "worker/notion_client.py", {"query_database"},
                      {"Any": Any, "config": SimpleNamespace(NOTION_API_KEY="synthetic"),
                       "httpx": SimpleNamespace(Client=Mock(return_value=client)), "TIMEOUT": 1,
                       "NOTION_BASE_URL": "https://synthetic.invalid", "_headers": lambda: {},
                       "_check_response": response, "logger": Mock()})
        return g["query_database"], client

    def test_complete_pagination(self):
        query, client = self.query([
            {"results": [{"id": "a"}], "has_more": True, "next_cursor": "next"},
            {"results": [{"id": "b"}], "has_more": False, "next_cursor": None}])
        self.assertEqual(query("synthetic"), [{"id": "a"}, {"id": "b"}])
        self.assertEqual(client.post.call_args_list[1].kwargs["json"], {"start_cursor": "next"})

    def test_second_page_failure_does_not_return_partial_result(self):
        query, _ = self.query([
            {"results": [{"id": "a"}], "has_more": True, "next_cursor": "next"},
            RuntimeError("synthetic partial read")])
        with self.assertRaises(RuntimeError):
            query("synthetic")

    def test_inconsistent_pagination_current_gap(self):
        query, client = self.query([{"results": [{"id": "a"}], "has_more": True, "next_cursor": None}])
        # Characterization: today partial coverage is indistinguishable from completion.
        # A future fail-closed contract must replace this with an exception assertion.
        self.assertEqual(query("synthetic"), [{"id": "a"}])
        client.post.assert_called_once()

if __name__ == "__main__":
    main()
