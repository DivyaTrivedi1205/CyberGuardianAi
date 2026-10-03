import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
import psycopg2
from dotenv import load_dotenv

# Load environment variables from the project root .env
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from config import settings

DATABASE_URL = settings.DATABASE_URL


def now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


@contextmanager
def db_connection() -> Iterator[psycopg2.extensions.connection]:
    connection = psycopg2.connect(DATABASE_URL)
    connection.autocommit = False
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            # Create users table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    identifier TEXT NOT NULL UNIQUE,
                    identifier_type TEXT NOT NULL,
                    auth_provider TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )

            # Create otp_challenges table
            cursor.execute(
                """
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
                )
                """
            )

            # Create index for otp lookup
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_otp_lookup
                ON otp_challenges(identifier, identifier_type, purpose, code, consumed, expires_at)
                """
            )

            # Create password_scans table for Phase 1 password logging
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS password_scans (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    password_length INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    grade TEXT NOT NULL,
                    feedback JSONB NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

            # Create index for password scans lookup
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_password_scans_user
                ON password_scans(user_id, created_at DESC)
                """
            )

            # Create url_scans table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS url_scans (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    prediction TEXT NOT NULL,
                    features JSONB NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

            # Create index for url scans lookup
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_url_scans_user
                ON url_scans(user_id, created_at DESC)
                """
            )

            # Create message_scans table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS message_scans (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                    message TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    prediction TEXT NOT NULL,
                    features JSONB NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

            # Create index for message scans lookup
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_message_scans_user
                ON message_scans(user_id, created_at DESC)
                """
            )

            # Create community_reports table for Phase 5 Community Intelligence
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS community_reports (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT,
                    indicator_type TEXT NOT NULL,
                    indicator_value TEXT NOT NULL,
                    description TEXT,
                    reports_count INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    created_at INTEGER NOT NULL
                )
                """
            )

            # Create unique index for community reports indicator values lookup
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_community_reports_value
                ON community_reports(indicator_value)
                """
            )

            # Create deepfake_scans table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS deepfake_scans (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    prediction TEXT NOT NULL,
                    features JSONB NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

            # Create index for deepfake scans lookup
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_deepfake_scans_user
                ON deepfake_scans(user_id, created_at DESC)
                """
            )

        connection.commit()
