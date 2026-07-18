from typing import List
from pydantic import BaseModel

class PasswordAnalysisRequest(BaseModel):
    password: str

class PasswordAnalysisResponse(BaseModel):
    score: int
    grade: str
    feedback: List[str]

class PasswordScanHistoryItem(BaseModel):
    id: int
    user_id: str
    password_length: int
    score: int
    grade: str
    feedback: List[str]
    created_at: int
