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
        # Ambiguity is explicit rather than absence or an arbitrary selected page:
        self.assertEqual(find([legacy, {**legacy, "page_id": "b"}], **args), (None, "ambiguous"))
        self.assertEqual(find([a, {**a, "page_id": "b"}], **args), (None, "ambiguous"))

    def query(self, replies):
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        response = Mock(side_effect=replies)
        g = functions(ROOT / "worker/notion_client.py", {"query_database_with_coverage"},
                      {"Any": Any, "config": SimpleNamespace(NOTION_API_KEY="synthetic"),
                       "httpx": SimpleNamespace(Client=Mock(return_value=client)), "TIMEOUT": 1,
                       "NOTION_BASE_URL": "https://synthetic.invalid", "_headers": lambda: {},
                       "_check_response": response, "logger": Mock()})
        return g["query_database_with_coverage"], client

    def test_complete_pagination(self):
        query, client = self.query([
            {"results": [{"id": "a"}], "has_more": True, "next_cursor": "next"},
            {"results": [{"id": "b"}], "has_more": False, "next_cursor": None}])
        self.assertEqual(query("synthetic"), {"complete": True, "results": [{"id": "a"}, {"id": "b"}], "reason": ""})
        self.assertEqual(client.post.call_args_list[1].kwargs["json"], {"start_cursor": "next"})

    def test_second_page_failure_does_not_return_partial_result(self):
        query, _ = self.query([
            {"results": [{"id": "a"}], "has_more": True, "next_cursor": "next"},
            RuntimeError("synthetic partial read")])
        result = query("synthetic")
        self.assertFalse(result["complete"])
        self.assertEqual(result["results"], [])

    def test_inconsistent_pagination_fails_closed(self):
        query, client = self.query([{"results": [{"id": "a"}], "has_more": True, "next_cursor": None}])
        result = query("synthetic")
        self.assertFalse(result["complete"])
        self.assertEqual(result["results"], [])
        client.post.assert_called_once()

    def test_repeated_cursor_fails_closed(self):
        query, _ = self.query([
            {"results": [{"id": "a"}], "has_more": True, "next_cursor": "same"},
            {"results": [{"id": "b"}], "has_more": True, "next_cursor": "same"}])
        self.assertEqual(query("synthetic")["reason"], "repeated_cursor")

    def test_invalid_and_duplicate_page_fail_closed(self):
        for page in (None, {}, {"id": "a"}):
            query, _ = self.query([{"results": [{"id": "a"}, page], "has_more": False, "next_cursor": None}])
            self.assertFalse(query("synthetic")["complete"])

    def test_real_lookup_and_caller_never_write_on_incomplete_coverage(self):
        from test_granola_raw_preservation_isolated import RawPreservation
        harness = RawPreservation()
        for replies in (
            [{"results": [], "has_more": True, "next_cursor": None}],
            [{"results": [], "has_more": True, "next_cursor": "same"},
             {"results": [], "has_more": True, "next_cursor": "same"}],
            [RuntimeError("synthetic transport failure")],
        ):
            for force in (False, True):
                g, client = harness.harness("create", existing=False)
                strict, transport = self.query(replies)
                client.query_database_with_coverage.side_effect = strict
                result = harness.run_handler(g, force_reconcile=force)
                self.assertTrue(result["deferred"])
                self.assertEqual(result["reconciliation"]["reason"], "raw_lookup_incomplete")
                self.assertFalse(result["notification_sent"])
                harness.assert_no_writes(g, client)
                g["decide_reconciliation"].assert_not_called()

    def test_real_ambiguous_match_and_caller_never_write(self):
        from test_granola_raw_preservation_isolated import RawPreservation
        harness = RawPreservation()
        for doc_id in ("synthetic", ""):
            g, client = harness.harness("create", existing=False)
            g["unicodedata"] = unicodedata
            functions(ROOT / "worker/tasks/granola.py",
                      {"_normalize_lookup_text", "_select_preferred_raw_candidate", "_find_existing_raw_candidate"}, g)
            candidate = {"page_id": "a", "title": "Synthetic", "normalized_title": "synthetic",
                         "date": "2026-11-15", "granola_document_id": doc_id}
            client.query_database_with_coverage.return_value = {
                "complete": True, "results": [candidate, {**candidate, "page_id": "b"}]}
            g["_build_existing_raw_candidate"].side_effect = lambda page: page
            result = harness.run_handler(g, force_reconcile=True)
            self.assertTrue(result["deferred"])
            self.assertEqual(result["reconciliation"]["reason"], "raw_match_ambiguous")
            self.assertEqual(result["action_items_created"], 0)
            harness.assert_no_writes(g, client)
            g["decide_reconciliation"].assert_not_called()

if __name__ == "__main__":
    main()
