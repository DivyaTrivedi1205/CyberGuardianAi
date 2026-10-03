from typing import Optional, Dict, Any
from psycopg2.extras import RealDictCursor
from database.connection import db_connection


def check_community_reputation(
    indicator: str, indicator_type: str
) -> Optional[Dict[str, Any]]:
    """
    Checks if a URL or message has been reported as a threat in the community database.
    Uses parameterized queries to prevent SQL injection.
    """
    cleaned = indicator.strip()
    if not cleaned:
        return None

    # For URLs, downcase to normalize
    if indicator_type == "url":
        cleaned = cleaned.lower()

    with db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # Use parameterized queries — no string interpolation
            cursor.execute(
                """
                SELECT id, user_id, indicator_type, indicator_value, description, reports_count, status, created_at
                FROM community_reports
                WHERE indicator_type = %s AND (
                    indicator_value = %s OR
                    indicator_value LIKE %s OR
                    %s LIKE '%%' || indicator_value || '%%'
                )
                LIMIT 1
                """,
                (indicator_type, cleaned, f"%{cleaned}%", cleaned),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
    return None