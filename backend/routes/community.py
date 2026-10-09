from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field, validator
from psycopg2.extras import RealDictCursor
from database.connection import db_connection, now_ts
from models.auth import UserOut
from routes.auth import get_current_user
from config import settings

router = APIRouter(prefix="/community", tags=["community"])

class ReportRequest(BaseModel):
    indicator_type: str = Field(..., description="E.g., url or message")
    indicator_value: str = Field(..., min_length=3)
    description: Optional[str] = Field(None, max_length=500)

    @validator("indicator_type")
    def type_must_be_supported(cls, v):
        if v not in ["url", "message"]:
            raise ValueError("must be 'url' or 'message'")
        return v

class ReportResponse(BaseModel):
    id: int
    indicator_type: str
    indicator_value: str
    reports_count: int
    status: str
    message: str

def get_user_reputation(user_id: str) -> int:
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT reputation_score FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return row[0]
            return 100

def update_user_reputation(user_id: Optional[str], change: int):
    if not user_id: return
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET reputation_score = reputation_score + %s WHERE id = %s", (change, user_id))
        conn.commit()

# Basic rate limit tracking (in-memory for phase 9 simple abuse prevention)
_USER_REPORT_TIMESTAMPS: Dict[str, List[int]] = {}

def check_rate_limit(user_id: str):
    now = now_ts()
    # Keep only timestamps from last hour (3600s)
    if user_id in _USER_REPORT_TIMESTAMPS:
        _USER_REPORT_TIMESTAMPS[user_id] = [t for t in _USER_REPORT_TIMESTAMPS[user_id] if now - t < 3600]
        if len(_USER_REPORT_TIMESTAMPS[user_id]) >= 20: # 20 reports per hour
            raise HTTPException(status_code=429, detail="Rate limit exceeded for community reporting. Please try again later.")
    else:
        _USER_REPORT_TIMESTAMPS[user_id] = []

    _USER_REPORT_TIMESTAMPS[user_id].append(now)

@router.post("/report", response_model=ReportResponse)
def create_report(
    req: ReportRequest,
    current_user: UserOut = Depends(get_current_user)
):
    check_rate_limit(current_user.id)

    rep_score = get_user_reputation(current_user.id)
    if rep_score < 20:
        raise HTTPException(status_code=403, detail="Your community reputation is too low to submit reports.")

    cleaned_val = req.indicator_value.strip()
    if req.indicator_type == "url":
        cleaned_val = cleaned_val.lower()

    with db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if this indicator already exists
            cur.execute("SELECT * FROM community_reports WHERE indicator_value = %s AND indicator_type = %s", (cleaned_val, req.indicator_type))
            existing_report = cur.fetchone()

            if existing_report:
                # Check if this user already voted
                cur.execute("SELECT id FROM community_report_votes WHERE report_id = %s AND user_id = %s", (existing_report["id"], current_user.id))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="You have already reported this threat.")

                # Add vote
                cur.execute(
                    "INSERT INTO community_report_votes (report_id, user_id, vote_type, created_at) VALUES (%s, %s, %s, %s)",
                    (existing_report["id"], current_user.id, "upvote", now_ts())
                )

                # Update report
                new_count = existing_report["reports_count"] + 1

                # Promote to verified_threat if threshold met (e.g. 3 users)
                new_status = existing_report["status"]
                if new_status == "pending" and new_count >= 3:
                    new_status = "verified_threat"
                    # Reward the original reporter
                    update_user_reputation(existing_report["user_id"], 10)

                cur.execute(
                    "UPDATE community_reports SET reports_count = %s, status = %s WHERE id = %s RETURNING *",
                    (new_count, new_status, existing_report["id"])
                )
                updated_report = cur.fetchone()
                conn.commit()

                return ReportResponse(
                    id=updated_report["id"],
                    indicator_type=updated_report["indicator_type"],
                    indicator_value=updated_report["indicator_value"],
                    reports_count=updated_report["reports_count"],
                    status=updated_report["status"],
                    message="Threat report updated successfully."
                )

            else:
                # Create a new report
                cur.execute(
                    """
                    INSERT INTO community_reports (user_id, indicator_type, indicator_value, description, created_at)
                    VALUES (%s, %s, %s, %s, %s) RETURNING *
                    """,
                    (current_user.id, req.indicator_type, cleaned_val, req.description, now_ts())
                )
                new_report = cur.fetchone()

                # Add automatic initial vote
                cur.execute(
                    "INSERT INTO community_report_votes (report_id, user_id, vote_type, created_at) VALUES (%s, %s, %s, %s)",
                    (new_report["id"], current_user.id, "upvote", now_ts())
                )

                conn.commit()

                # Increase reputation slightly for proactive reporting
                update_user_reputation(current_user.id, 2)

                return ReportResponse(
                    id=new_report["id"],
                    indicator_type=new_report["indicator_type"],
                    indicator_value=new_report["indicator_value"],
                    reports_count=new_report["reports_count"],
                    status=new_report["status"],
                    message="Threat reported successfully."
                )

@router.get("/reports", response_model=List[Dict[str, Any]])
def list_reports(current_user: UserOut = Depends(get_current_user)):
    with db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM community_reports ORDER BY created_at DESC LIMIT 50")
            return [dict(r) for r in cur.fetchall()]