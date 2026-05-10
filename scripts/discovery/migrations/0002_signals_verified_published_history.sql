-- 0002_signals_verified_published_history.sql
--
-- Stage 2 (Hilo 3 / wave1) — Source Verification & Dedup contract.
--
-- Builds on top of migration 0001_referentes_signals.sql which already
-- defines `signals_raw` (signal_id INTEGER PK AUTOINCREMENT, url TEXT,
-- canonical_url TEXT, title TEXT, excerpt TEXT, dedup_hash TEXT UNIQUE,
-- source_status TEXT, ...).
--
-- Stage 2's own `source_status` enum is RICHER (paywall / redirect /
-- timeout / etc.) and is stored separately in `signals_verified` to
-- avoid colliding with Hilo 2's ingest-time status.
--
-- All statements are idempotent (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS signals_verified (
    signal_id          INTEGER PRIMARY KEY,                   -- FK → signals_raw.signal_id
    canonical_url      TEXT    NOT NULL,
    source_status      TEXT    NOT NULL,                      -- ok|redirect|404|410|paywall|timeout|blocked
    content_hash       TEXT    NOT NULL,
    idempotency_key    TEXT    NOT NULL,
    paywall_detected   INTEGER NOT NULL DEFAULT 0,            -- 0|1 sqlite bool
    verified_at        TEXT    NOT NULL,                      -- ISO-8601 UTC
    http_status        INTEGER,
    final_url          TEXT,
    error              TEXT
);

CREATE INDEX IF NOT EXISTS idx_signals_verified_content_hash
    ON signals_verified(content_hash);

CREATE INDEX IF NOT EXISTS idx_signals_verified_idempotency_key
    ON signals_verified(idempotency_key);

CREATE INDEX IF NOT EXISTS idx_signals_verified_status
    ON signals_verified(source_status);


CREATE TABLE IF NOT EXISTS published_history (
    content_hash   TEXT PRIMARY KEY,
    published_url  TEXT NOT NULL,
    published_at   TEXT NOT NULL,                             -- ISO-8601 UTC
    platform       TEXT NOT NULL                              -- linkedin|notion|...
);

CREATE INDEX IF NOT EXISTS idx_published_history_platform
    ON published_history(platform);
