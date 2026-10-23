import json
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List

def save_url_scan(connection, user_id, url, risk_score, prediction, features, created_at):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO url_scans (user_id, url, risk_score, prediction, features, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, url, risk_score, prediction, json.dumps(features), created_at)
        )

def get_url_scans_history(connection, user_id) -> List[Dict[str, Any]]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, url, risk_score, prediction, features, created_at
            FROM url_scans
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            record = dict(row)
            if isinstance(record["features"], str):
                record["features"] = json.loads(record["features"])
            results.append(record)
        return results

def save_message_scan(connection, user_id, message, risk_score, prediction, features, created_at):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO message_scans (user_id, message, risk_score, prediction, features, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, message, risk_score, prediction, json.dumps(features), created_at)
        )

def get_message_scans_history(connection, user_id) -> List[Dict[str, Any]]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, message, risk_score, prediction, features, created_at
            FROM message_scans
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            record = dict(row)
            if isinstance(record["features"], str):
                record["features"] = json.loads(record["features"])
            results.append(record)
        return results

def save_deepfake_scan(connection, user_id, file_name, file_type, risk_score, prediction, features, created_at):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO deepfake_scans (user_id, file_name, file_type, risk_score, prediction, features, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, file_name, file_type, risk_score, prediction, json.dumps(features), created_at)
        )

def get_deepfake_scans_history(connection, user_id) -> List[Dict[str, Any]]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, file_name, file_type, risk_score, prediction, features, created_at
            FROM deepfake_scans
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            record = dict(row)
            if isinstance(record["features"], str):
                record["features"] = json.loads(record["features"])
            results.append(record)
        return results
