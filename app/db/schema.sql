-- ─────────────────────────────────────────
-- TABLE: users
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                   TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name                 TEXT    NOT NULL,
    email                TEXT    NOT NULL UNIQUE,
    password_hash        TEXT    NOT NULL,
    baseline_bpm         INTEGER DEFAULT 72,
    threshold_config     TEXT    NOT NULL DEFAULT '{}',
    session_count        INTEGER NOT NULL DEFAULT 0,
    profile_status       TEXT    NOT NULL DEFAULT 'new'
                         CHECK (profile_status IN ('new', 'calibrating', 'stable')),
    last_stability_check TEXT    DEFAULT NULL,
    last_login           TEXT    DEFAULT NULL,
    encryption_key       TEXT    DEFAULT NULL,
    created_at           TEXT    NOT NULL
                         DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ─────────────────────────────────────────
-- TABLE: refresh_tokens
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id     TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT    NOT NULL UNIQUE,
    expires_at  TEXT    NOT NULL,
    revoked     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);

-- ─────────────────────────────────────────
-- TABLE: analysis_sessions
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analysis_sessions (
    id                TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id           TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp         TEXT    NOT NULL
                      DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    verdict           TEXT    NOT NULL CHECK (verdict IN ('Fit', 'Unfit')),
    stress_level      TEXT    NOT NULL CHECK (stress_level IN ('Low', 'Moderate', 'High')),
    traffic_light     TEXT    NOT NULL CHECK (traffic_light IN ('Green', 'Yellow', 'Red')),
    weather_snapshot  TEXT    NOT NULL DEFAULT '{}',
    weather_impact    TEXT    DEFAULT NULL,
    risk_score        REAL    DEFAULT NULL,
    confidence_score  REAL    DEFAULT NULL,
    tags              TEXT    NOT NULL DEFAULT '[]',
    processing_status TEXT    NOT NULL DEFAULT 'completed'
                      CHECK (processing_status IN ('processing', 'completed', 'failed')),
    error_code        TEXT    DEFAULT NULL,
    created_at        TEXT    NOT NULL
                      DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id   ON analysis_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status    ON analysis_sessions(processing_status);
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON analysis_sessions(timestamp);

-- ─────────────────────────────────────────
-- TABLE: biometric_data_raw
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS biometric_data_raw (
    id                 TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    session_id         TEXT    NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    timestamp          TEXT    NOT NULL,
    bpm_encrypted      TEXT    NOT NULL,
    iv_encrypted       TEXT    NOT NULL,
    relative_timestamp INTEGER DEFAULT NULL,
    source             TEXT    NOT NULL DEFAULT 'Manual'
                       CHECK (source IN ('Sensor', 'API', 'Manual'))
);
CREATE INDEX IF NOT EXISTS idx_biometric_session ON biometric_data_raw(session_id);

-- ─────────────────────────────────────────
-- TABLE: weather_cache
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weather_cache (
    coordinates_key   TEXT PRIMARY KEY,
    weather_data_json TEXT NOT NULL,
    expires_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_weather_cache_expires ON weather_cache(expires_at);

-- ─────────────────────────────────────────
-- TABLE: trusted_contacts
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trusted_contacts (
    id         TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id    TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    email      TEXT    NOT NULL,
    phone      TEXT    DEFAULT NULL,
    created_at TEXT    NOT NULL
               DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_contacts_user ON trusted_contacts(user_id);

-- ─────────────────────────────────────────
-- TABLE: audit_logs
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id            TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id       TEXT    DEFAULT NULL
                  REFERENCES users(id) ON DELETE SET NULL,
    timestamp     TEXT    NOT NULL
                  DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    event_type    TEXT    NOT NULL,
    model_status  TEXT    DEFAULT NULL
                  CHECK (model_status IN ('Success', 'Fallback', 'Error')),
    error_message TEXT    DEFAULT NULL,
    details       TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_user      ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_event     ON audit_logs(event_type);
