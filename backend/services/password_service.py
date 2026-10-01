import json
import re
from typing import List, Dict, Any
from psycopg2.extras import RealDictCursor
from database.connection import now_ts


def score_password(value: str) -> Dict[str, Any]:
    score = 0
    feedback = []

    if len(value) >= 12:
        score += 30
    elif len(value) >= 8:
        score += 18
    elif len(value) > 0:
        feedback.append("Use at least 12 characters for stronger protection.")

    if re.search(r"[a-z]", value):
        score += 10
    elif len(value) > 0:
        feedback.append("Add lowercase letters.")

    if re.search(r"[A-Z]", value):
        score += 10
    elif len(value) > 0:
        feedback.append("Add uppercase letters.")

    if re.search(r"\d", value):
        score += 15
    elif len(value) > 0:
        feedback.append("Add numbers.")

    if re.search(r"[^A-Za-z0-9]", value):
        score += 15
    elif len(value) > 0:
        feedback.append("Add a symbol or punctuation mark.")

    # Check for repeating characters (e.g., "aaa")
    if re.search(r"(.)\1\1", value):
        score -= 10
        feedback.append("Avoid repeated characters or obvious patterns.")

    # Check for common password keywords
    if re.search(r"password|welcome|admin|qwerty|letmein", value, re.IGNORECASE):
        score -= 20
        feedback.append("Remove common password words or keyboard patterns.")

    clamped = max(0, min(100, score))
    grade = (
        "Strong"
        if clamped >= 80
        else "Moderate"
        if clamped >= 55
        else "Weak"
        if clamped >= 30
        else "Critical"
    )

    if len(value) == 0:
        return {
            "score": 0,
            "grade": "Critical",
            "feedback": ["Password is empty. Please enter a password."],
        }

    return {
        "score": clamped,
        "grade": grade,
        "feedback": feedback
        if len(feedback) > 0
        else ["This password looks stronger than average in this quick check."],
    }


def save_password_scan(
    connection,
    *,
    user_id: str,
    password_length: int,
    score: int,
    grade: str,
    feedback: List[str],
) -> None:
    timestamp = now_ts()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO password_scans (user_id, password_length, score, grade, feedback, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, password_length, score, grade, json.dumps(feedback), timestamp),
        )


def get_password_scans_history(connection, user_id: str) -> List[Dict[str, Any]]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, password_length, score, grade, feedback, created_at
            FROM password_scans
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (user_id,),
        )
        rows = cursor.fetchall()

        # Parse feedback field from JSON/JSONB string to Python list
        results = []
        for row in rows:
            record = dict(row)
            if isinstance(record["feedback"], str):
                record["feedback"] = json.loads(record["feedback"])
            results.append(record)
        return results
