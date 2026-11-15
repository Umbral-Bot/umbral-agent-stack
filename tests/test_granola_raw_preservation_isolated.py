"""No runtime imports, credentials or network: exercise exact production functions."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock
from typing import Any, Dict

SOURCE = Path(__file__).resolve().parents[1] / "worker/tasks/granola.py"

class RawPreservation(TestCase):
    def harness(self, action="reconcile", existing=True):
        tree = ast.parse(SOURCE.read_text())
        names = {"_upsert_raw_transcript_page", "handle_granola_process_transcript"}
        subset = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
        client = Mock()
        client.read_database.return_value = {"schema": {}}
        client.query_database.return_value = []
        client.create_database_page.return_value = {"page_id": "new", "created": True}
        candidate = {"page_id": "original", "title": "Synthetic", "url": "synthetic"} if existing else None
        decision = SimpleNamespace(action=action, as_dict=lambda: {"action": action, "reason": "test", "new_metrics": {}})
        g = dict(Dict=Dict, Any=Any, notion_client=client,
            config=SimpleNamespace(NOTION_GRANOLA_DB_ID="synthetic-db"),
            logger=Mock(), decide_reconciliation=Mock(return_value=decision),
            _build_existing_raw_candidate=Mock(), _find_existing_raw_candidate=Mock(return_value=(candidate, "test")),
            _resolve_new_raw_title=Mock(return_value="Synthetic"),
            _iso_now_utc=Mock(return_value="2026-11-15T00:00:00Z"),
            _parse_traceability_text=Mock(return_value={}),
            _build_transcript_paragraph_blocks=Mock(return_value=[]),
            _build_raw_transcript_properties=Mock(return_value=({}, [])),
            _sync_visible_notion_page_id=Mock(return_value={}),
            _verify_raw_page_persistence=Mock(return_value={"ok": True}),
            _alert_raw_integrity_failure=Mock(),
            _resolve_granola_document_id=Mock(return_value="synthetic"),
            _resolve_source_updated_at=Mock(return_value=""),
            _resolve_source_url=Mock(return_value=""),
            _resolve_metadata_value=Mock(return_value=""),
            _build_raw_traceability_text=Mock(return_value="synthetic trace"),
            _extract_action_items_from_content=Mock(return_value=[]),
            _build_action_item_task_id=Mock(return_value="synthetic-task"),
            handle_notion_upsert_task=Mock())
        exec(compile(subset, str(SOURCE), "exec"), g)
        return g, client

    def run_handler(self, g, **extra):
        return g["handle_granola_process_transcript"]({
            "title": "Synthetic", "content": "original plus annotation", "date": "2026-11-15",
            "allow_legacy_raw_task_writes": True, "notify_enlace": True,
            "action_items": [{"text": "synthetic task"}], **extra})

    def assert_no_writes(self, g, client):
        self.assertEqual([c[0] for c in client.mock_calls], ["read_database", "query_database"])
        for name in ("_sync_visible_notion_page_id", "_verify_raw_page_persistence",
                     "_alert_raw_integrity_failure", "handle_notion_upsert_task",
                     "_build_raw_transcript_properties", "_build_transcript_paragraph_blocks"):
            g[name].assert_not_called()

    def test_existing_reconcile_defers_before_all_writes_and_downstream(self):
        for force in (False, True):
            for dry_run in (False, True):
                with self.subTest(force=force, dry_run=dry_run):
                    g, client = self.harness()
                    r = self.run_handler(g, force_reconcile=force, dry_run=dry_run)
                    self.assertTrue(r["deferred"])
                    self.assertTrue(r["reconciliation"]["review_required"])
                    self.assertEqual(r["reconciliation"]["reason"], "raw_existing_reconciliation_requires_review")
                    self.assertEqual(r["action_items_created"], 0)
                    self.assertFalse(r["notification_sent"])
                    self.assertFalse(r["traceability_written"])
                    self.assert_no_writes(g, client)

    def test_existing_noop_and_defer_preserved(self):
        for action in ("noop", "defer"):
            g, client = self.harness(action)
            r = self.run_handler(g)
            self.assertEqual(r["reconciliation_action"], action)
            self.assertEqual(r["reconciliation"]["reason"], "test")
            self.assertFalse(r["traceability_written"])
            self.assert_no_writes(g, client)

    def test_creation_and_downstream_preserved(self):
        g, client = self.harness("create", existing=False)
        r = self.run_handler(g)
        client.create_database_page.assert_called_once()
        client.update_page_properties.assert_not_called()
        client.replace_blocks_in_page.assert_not_called()
        g["handle_notion_upsert_task"].assert_called_once()
        client.add_comment.assert_called_once()
        self.assertEqual(r["action_items_created"], 1)
        self.assertTrue(r["notification_sent"])

    def test_creation_dry_run_no_writes(self):
        g, client = self.harness("create", existing=False)
        r = self.run_handler(g, dry_run=True)
        self.assertFalse(r["traceability_written"])
        self.assertEqual([c[0] for c in client.mock_calls], ["read_database", "query_database"])
        g["handle_notion_upsert_task"].assert_not_called()
        self.assertFalse(r["notification_sent"])

    def test_traceability_requires_actual_property_write(self):
        for field in ("Trazabilidad", "Traceability", None):
            with self.subTest(field=field):
                g, client = self.harness("create", existing=False)
                properties = {field: {"rich_text": [{"text": {"content": "synthetic trace"}}]}} if field else {}
                g["_build_raw_transcript_properties"].return_value = (properties, [field] if field else [])
                r = self.run_handler(g)
                self.assertEqual(r["traceability_written"], field is not None)
                client.create_database_page.assert_called_once()
                self.assertEqual(client.create_database_page.call_args.kwargs["properties"], properties)

    def test_read_failure_propagates_before_writes(self):
        g, client = self.harness()
        client.query_database.side_effect = RuntimeError("synthetic read failure")
        with self.assertRaises(RuntimeError):
            self.run_handler(g)
        self.assert_no_writes(g, client)

    def test_unexpected_existing_create_cannot_overwrite(self):
        g, client = self.harness("create", existing=True)
        self.assertTrue(self.run_handler(g)["deferred"])
        self.assert_no_writes(g, client)

if __name__ == "__main__":
    main()
