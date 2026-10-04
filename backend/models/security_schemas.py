from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# URL Analysis Schemas
class UrlAnalysisRequest(BaseModel):
    url: str

class UrlAnalysisResponse(BaseModel):
    url: str
    risk_score: int
    prediction: str
    features: Dict[str, int]
    feedback: List[str]
    scam_psychology: Optional[Dict[str, Any]] = None

class UrlScanHistoryItem(BaseModel):
    id: int
    user_id: Optional[str]
    url: str
    risk_score: int
    prediction: str
    features: Dict[str, int]
    created_at: int

# Message Analysis Schemas
class MessageAnalysisRequest(BaseModel):
    message: str

class MessageAnalysisResponse(BaseModel):
    message: str
    risk_score: int
    prediction: str
    feedback: List[str]
    scam_psychology: Optional[Dict[str, Any]] = None

class MessageScanHistoryItem(BaseModel):
    id: int
    user_id: Optional[str]
    message: str
    risk_score: int
    prediction: str
    features: Dict[str, Any]
    created_at: int

# Evidence categories for deepfake analysis
class EvidenceItem(BaseModel):
    frame: Optional[int] = None
    timestamp: Optional[float] = None
    indicator: Optional[str] = None
    feature: Optional[str] = None
    value: Optional[Any] = None
    prediction: Optional[str] = None
    face_index: Optional[int] = None
    risk: Optional[int] = None
    indicators: Optional[List[str]] = None

class DeepfakeEvidence(BaseModel):
    metadata: List[Dict[str, Any]]
    forensics: List[Dict[str, Any]]
    model: List[Dict[str, Any]]
    faces: List[Dict[str, Any]]
    temporal: List[Dict[str, Any]]

class DeepfakeAnalysisResponse(BaseModel):
    file_name: str
    file_type: str
    risk_score: int
    prediction: str
    feedback: List[str]
    features: Dict[str, int]
    metadata: Dict[str, Any]
    evidence: Optional[Dict[str, Any]] = None
    suspicious_frames: Optional[List[Dict[str, Any]]] = None

class DeepfakeScanHistoryItem(BaseModel):
    id: int
    user_id: str
    file_name: str
    file_type: str
    risk_score: int
    prediction: str
    features: Dict[str, Any]
    created_at: int

# Password Analysis Schemas - Enhanced with detailed findings
class PasswordAnalysisRequest(BaseModel):
    password: str

class PasswordAnalysisResponse(BaseModel):
    score: int
    strength: str
    feedback: List[str]
    recommendations: List[str]
    length: int
    character_classes: Dict[str, int]
    patterns_detected: List[Dict[str, Any]]
    common_password: bool
    entropy_estimate: float
    crack_time_estimate: Optional[Dict[str, Any]] = None
