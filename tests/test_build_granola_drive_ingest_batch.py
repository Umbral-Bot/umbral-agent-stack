"""
Tests for scripts/build_granola_drive_ingest_batch.py (P1.1b Phase 3 batch builder).
"""

from scripts.build_granola_drive_ingest_batch import build_batch


def _drive_record(relative_path, title, date, sha1="aaa"):
    return {
        "filename": relative_path.split("/")[-1],
        "relative_path": relative_path,
        "size_bytes": 500,
        "sha1": sha1,
        "parsed": {
            "title": title,
            "normalized_title": title.lower(),
            "date": date,
            "participants": [],
            "transcript": "Me: hola",
            "char_count": 8,
        },
    }


class TestBuildBatch:
    def test_includes_create_and_update_excludes_skip_and_ambiguous(self):
        drive_records = [
            _drive_record("Granola/a.md", "A", "2026-01-01"),
            _drive_record("Granola/b.md", "B", "2026-01-02"),
            _drive_record("Granola/c.md", "C", "2026-01-03"),
            _drive_record("Granola/d.md", "D", "2026-01-04"),
        ]
        gap_items = [
            {"relative_path": "Granola/a.md", "action": "create"},
            {"relative_path": "Granola/b.md", "action": "update_transcript", "match_strategy": "normalized_title_date"},
            {"relative_path": "Granola/c.md", "action": "skip"},
            {"relative_path": "Granola/d.md", "action": "review_ambiguous"},
        ]
        batch = build_batch(drive_records, gap_items)
        paths = {b["relative_path"] for b in batch}
        assert paths == {"Granola/a.md", "Granola/b.md"}

    def test_payload_has_dry_run_true_by_default(self):
        drive_records = [_drive_record("Granola/a.md", "A", "2026-01-01")]
        gap_items = [{"relative_path": "Granola/a.md", "action": "create"}]
        batch = build_batch(drive_records, gap_items)
        assert batch[0]["payload"]["dry_run"] is True

    def test_dry_run_false_when_requested(self):
        drive_records = [_drive_record("Granola/a.md", "A", "2026-01-01")]
        gap_items = [{"relative_path": "Granola/a.md", "action": "create"}]
        batch = build_batch(drive_records, gap_items, dry_run=False)
        assert batch[0]["payload"]["dry_run"] is False

    def test_skips_gap_item_with_no_matching_drive_record(self):
        gap_items = [{"relative_path": "Granola/missing.md", "action": "create"}]
        batch = build_batch([], gap_items)
        assert batch == []

    def test_title_override_replaces_payload_title_and_preserves_original(self):
        drive_records = [_drive_record("Granola/BIM Forum 2.md", "BIM FOurm", "2026-03-18")]
        gap_items = [
            {
                "relative_path": "Granola/BIM Forum 2.md",
                "action": "update_transcript",
                "match_strategy": "manual_override",
                "matched_page": {"page_id": "real-page", "url": "https://notion.so/real-page"},
                "title_override": "BIM Forum",
            }
        ]
        batch = build_batch(drive_records, gap_items)
        payload = batch[0]["payload"]
        assert payload["title"] == "BIM Forum"
        assert payload["metadata"]["drive_original_title"] == "BIM FOurm"

    def test_no_title_override_leaves_payload_title_untouched(self):
        drive_records = [_drive_record("Granola/a.md", "A", "2026-01-01")]
        gap_items = [{"relative_path": "Granola/a.md", "action": "create"}]
        batch = build_batch(drive_records, gap_items)
        assert batch[0]["payload"]["title"] == "A"
        assert "drive_original_title" not in batch[0]["payload"]["metadata"]

    def test_payload_carries_match_metadata(self):
        drive_records = [_drive_record("Granola/a.md", "A", "2026-01-01")]
        gap_items = [
            {
                "relative_path": "Granola/a.md",
                "action": "update_transcript",
                "match_strategy": "normalized_title_date",
                "matched_page": {"page_id": "p1", "url": "https://notion.so/p1"},
            }
        ]
        batch = build_batch(drive_records, gap_items)
        assert batch[0]["match_strategy"] == "normalized_title_date"
        assert batch[0]["matched_page"]["page_id"] == "p1"
