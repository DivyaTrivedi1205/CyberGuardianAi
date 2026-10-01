from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
from database.connection import db_connection, now_ts
from models.auth import UserOut
from routes.auth import get_current_user
from routes.security import get_optional_user

router = APIRouter(prefix="/community", tags=["community"])


class CommunityReportRequest(BaseModel):
    indicator_type: str  # 'url' or 'message'
    indicator_value: str
    description: Optional[str] = None


class CommunityReportResponse(BaseModel):
    id: int
    user_id: Optional[str]
    indicator_type: str
    indicator_value: str
    description: Optional[str]
    reports_count: int
    status: str
    created_at: int


@router.post("/report", response_model=CommunityReportResponse)
def report_threat(
    payload: CommunityReportRequest,
    current_user: Optional[UserOut] = Depends(get_optional_user),
) -> CommunityReportResponse:
    val = payload.indicator_value.strip()
    if not val:
        raise HTTPException(status_code=400, detail="Indicator value cannot be empty.")

    ind_type = payload.indicator_type.strip().lower()
    if ind_type not in ["url", "message"]:
        raise HTTPException(
            status_code=400, detail="Indicator type must be 'url' or 'message'."
        )

    # Normalize url to lowercase
    if ind_type == "url":
        val = val.lower()

    uid = current_user.id if current_user else "anonymous"
    timestamp = now_ts()

    with db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if it already exists
            cursor.execute(
                """
                SELECT id, user_id, indicator_type, indicator_value, description, reports_count, status, created_at
                FROM community_reports
                WHERE indicator_value = %s AND indicator_type = %s
                """,
                (val, ind_type),
            )
            row = cursor.fetchone()
            if row:
                # Update existing
                cursor.execute(
                    """
                    UPDATE community_reports
                    SET reports_count = reports_count + 1,
                        status = CASE WHEN reports_count + 1 >= 3 THEN 'verified_threat' ELSE status END
                    WHERE id = %s
                    RETURNING id, user_id, indicator_type, indicator_value, description, reports_count, status, created_at
                    """,
                    (row["id"],),
                )
                updated_row = cursor.fetchone()
                connection.commit()
                return CommunityReportResponse(**dict(updated_row))
            else:
                # Insert new
                cursor.execute(
                    """
                    INSERT INTO community_reports (user_id, indicator_type, indicator_value, description, reports_count, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, indicator_type, indicator_value, description, reports_count, status, created_at
                    """,
                    (uid, ind_type, val, payload.description, 1, "pending", timestamp),
                )
                new_row = cursor.fetchone()
                connection.commit()
                return CommunityReportResponse(**dict(new_row))


@router.get("/reports", response_model=List[CommunityReportResponse])
def get_reports() -> List[CommunityReportResponse]:
    with db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, user_id, indicator_type, indicator_value, description, reports_count, status, created_at
                FROM community_reports
                ORDER BY created_at DESC
                LIMIT 50
                """
            )
            rows = cursor.fetchall()
            return [CommunityReportResponse(**dict(row)) for row in rows]


@router.post("/verify/{report_id}", response_model=CommunityReportResponse)
def verify_threat(
    report_id: int, current_user: UserOut = Depends(get_current_user)
) -> CommunityReportResponse:
    """
    Allows a signed-in user to verify a community reported threat, immediately promoting it to a 'verified_threat'.
    """
    with db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id FROM community_reports WHERE id = %s
                """,
                (report_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Threat report not found.")

            cursor.execute(
                """
                UPDATE community_reports
                SET status = 'verified_threat',
                    reports_count = reports_count + 1
                WHERE id = %s
                RETURNING id, user_id, indicator_type, indicator_value, description, reports_count, status, created_at
                """,
                (report_id,),
            )
            updated_row = cursor.fetchone()
            connection.commit()
            return CommunityReportResponse(**dict(updated_row))
