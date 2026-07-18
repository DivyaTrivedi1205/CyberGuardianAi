-- CyberGuardian AI Database Schema

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    identifier TEXT NOT NULL UNIQUE,
    identifier_type TEXT NOT NULL,
    auth_provider TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS otp_challenges (
    id BIGSERIAL PRIMARY KEY,
    identifier TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    purpose TEXT NOT NULL,
    code TEXT NOT NULL,
    display_name TEXT,
    expires_at INTEGER NOT NULL,
    consumed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_otp_lookup
ON otp_challenges(identifier, identifier_type, purpose, code, consumed, expires_at);

CREATE TABLE IF NOT EXISTS password_scans (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    password_length INTEGER NOT NULL,
    score INTEGER NOT NULL,
    grade TEXT NOT NULL,
    feedback JSONB NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_password_scans_user
ON password_scans(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS url_scans (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    prediction TEXT NOT NULL,
    features JSONB NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_url_scans_user
ON url_scans(user_id, created_at DESC);

