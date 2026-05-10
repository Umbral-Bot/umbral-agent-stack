-- 0001_referentes_signals.sql
-- Wave1 H2: snapshot de Referentes + raw signals discovery.
-- Idempotente: usar CREATE TABLE IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS referentes_snapshot (
    referente_id   TEXT NOT NULL,
    nombre         TEXT,
    canal_tipo     TEXT NOT NULL,   -- rss|web|youtube|linkedin
    canal_url      TEXT NOT NULL,
    snapshot_at    TEXT NOT NULL,
    PRIMARY KEY (referente_id, canal_tipo, canal_url)
);

CREATE INDEX IF NOT EXISTS idx_referentes_snapshot_canal_tipo
    ON referentes_snapshot(canal_tipo);

CREATE INDEX IF NOT EXISTS idx_referentes_snapshot_snapshot_at
    ON referentes_snapshot(snapshot_at);

CREATE TABLE IF NOT EXISTS signals_raw (
    signal_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    referente_id    TEXT NOT NULL,
    canal_tipo      TEXT NOT NULL,
    url             TEXT,
    canonical_url   TEXT,
    title           TEXT,
    excerpt         TEXT,
    published_at    TEXT,
    discovered_at   TEXT NOT NULL,
    dedup_hash      TEXT NOT NULL UNIQUE,
    source_status   TEXT NOT NULL    -- ok|http_404|http_5xx|http_error|timeout|robots_disallow|parse_error|linkedin_skip|out_of_scope_stage1
);

CREATE INDEX IF NOT EXISTS idx_signals_raw_referente
    ON signals_raw(referente_id);
CREATE INDEX IF NOT EXISTS idx_signals_raw_canal
    ON signals_raw(canal_tipo);
CREATE INDEX IF NOT EXISTS idx_signals_raw_discovered
    ON signals_raw(discovered_at);
CREATE INDEX IF NOT EXISTS idx_signals_raw_status
    ON signals_raw(source_status);
