from typing import List, Optional
import json
import os
import pickle
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from psycopg2.extras import RealDictCursor
from database.connection import db_connection, now_ts
from models.auth import UserOut
from models.security import (
    PasswordAnalysisRequest,
    PasswordAnalysisResponse,
    PasswordScanHistoryItem,
)
from models.security_schemas import (
    UrlAnalysisRequest,
    UrlAnalysisResponse,
    UrlScanHistoryItem,
    MessageAnalysisRequest,
    MessageAnalysisResponse,
    MessageScanHistoryItem,
    DeepfakeAnalysisResponse,
    DeepfakeScanHistoryItem,
)
from routes.auth import (
    get_current_user,
    token_from_authorization,
    get_user_by_id,
    build_user_out,
    JWT_SECRET,
    JWT_ALGORITHM,
)
from services.password_service import (
    score_password,
    save_password_scan,
    get_password_scans_history,
)
from services.url_feature_extractor import extract_features_from_url
from services.message_analyzer import analyze_message_text
from services.scam_psychology import analyze_scam_psychology
from services.community_reputation import check_community_reputation

from services.deepfake_analyzer import analyze_deepfake
from jose import jwt

router = APIRouter(prefix="/security", tags=["security"])

# Load URL model data
URL_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "models", "url_classifier.pkl")
)
_url_model_data = None


def get_url_model():
    global _url_model_data
    if _url_model_data is None:
        if os.path.exists(URL_MODEL_PATH):
            with open(URL_MODEL_PATH, "rb") as f:
                _url_model_data = pickle.load(f)
        else:
            raise FileNotFoundError(
                f"URL classifier model not found at {URL_MODEL_PATH}"
            )
    return _url_model_data


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[UserOut]:
    token = token_from_authorization(authorization)
    if token is None:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        with db_connection() as connection:
            user_row = get_user_by_id(connection, user_id)
        if user_row is None:
            return None
        return build_user_out(user_row)
    except Exception:
        return None


@router.post("/analyze-password", response_model=PasswordAnalysisResponse)
def analyze_password(
    payload: PasswordAnalysisRequest,
    current_user: Optional[UserOut] = Depends(get_optional_user),
) -> PasswordAnalysisResponse:
    # Run the scoring service
    analysis = score_password(payload.password)

    # Save the scan history if the user is authenticated and password is not empty
    if current_user and payload.password:
        with db_connection() as connection:
            try:
                save_password_scan(
                    connection,
                    user_id=current_user.id,
                    password_length=len(payload.password),
                    score=analysis["score"],
                    grade=analysis["grade"],
                    feedback=analysis["feedback"],
                )
                connection.commit()
            except Exception as exc:
                connection.rollback()
                # We fail open for the analysis itself if DB logging fails, but raise for debugging
                raise HTTPException(
                    status_code=500, detail=f"Failed to save scan history: {exc}"
                )

    return PasswordAnalysisResponse(
        score=analysis["score"], grade=analysis["grade"], feedback=analysis["feedback"]
    )


@router.get("/password-scans", response_model=List[PasswordScanHistoryItem])
def get_password_scans(
    current_user: UserOut = Depends(get_current_user),
) -> List[PasswordScanHistoryItem]:
    with db_connection() as connection:
        history = get_password_scans_history(connection, current_user.id)
    return [
        PasswordScanHistoryItem(
            id=item["id"],
            user_id=item["user_id"],
            password_length=item["password_length"],
            score=item["score"],
            grade=item["grade"],
            feedback=item["feedback"],
            created_at=item["created_at"],
        )
        for item in history
    ]


# URL Risk Analyzer Endpoints
@router.post("/analyze-url", response_model=UrlAnalysisResponse)
def analyze_url(
    payload: UrlAnalysisRequest,
    current_user: Optional[UserOut] = Depends(get_optional_user),
) -> UrlAnalysisResponse:
    # 0. Check community blocklist
    pending_warning = None
    try:
        reputation = check_community_reputation(payload.url, "url")
        if reputation:
            if reputation["status"] == "verified_threat":
                risk_score = 100
                prediction = "Phishing"
                explanations = [
                    f"CrowdShield Blocklist: Reported by community users and verified as a threat (Reason: {reputation['description'] or 'No details provided'})."
                ]

                model_data = get_url_model()
                features = {feat: -1 for feat in model_data["features"]}

                if current_user and payload.url:
                    with db_connection() as connection:
                        try:
                            timestamp = now_ts()
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    """
                                    INSERT INTO url_scans (user_id, url, risk_score, prediction, features, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    """,
                                    (
                                        current_user.id,
                                        payload.url,
                                        risk_score,
                                        prediction,
                                        json.dumps(features),
                                        timestamp,
                                    ),
                                )
                            connection.commit()
                        except Exception:
                            connection.rollback()

                scam_analysis = analyze_scam_psychology(payload.url)
                return UrlAnalysisResponse(
                    url=payload.url,
                    risk_score=risk_score,
                    prediction=prediction,
                    features=features,
                    feedback=explanations,
                    scam_psychology=scam_analysis,
                )
            elif reputation["status"] == "pending":
                pending_warning = f"CrowdShield Alert: This URL has been reported by community users and is pending verification (Reports: {reputation['reports_count']})."
    except Exception as e:
        print(f"Reputation lookup failed: {e}")

    # 1. Extract features and explanations from URL
    try:
        features, explanations = extract_features_from_url(payload.url)
        if pending_warning:
            explanations.insert(0, pending_warning)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process URL: {e}")

    # 2. Predict probability of phishing using trained XGBoost model
    try:
        model_data = get_url_model()
        model = model_data["model"]
        feature_names = model_data["features"]

        # Order features exactly as expected by the trained model
        vector = [features[feat] for feat in feature_names]
        prob = model.predict_proba([vector])[0][1]
        risk_score = int(prob * 100)
    except Exception as e:
        print(f"Error predicting URL: {e}")
        # Heuristic fallback if model is missing or fails
        risk_score = 50 if explanations else 15

    if risk_score >= 70:
        prediction = "Phishing"
    elif risk_score >= 35:
        prediction = "Suspicious"
    else:
        prediction = "Legitimate"

    if not explanations:
        explanations = ["No obvious threat indicators were found in this URL."]

    # 3. Log scan history for authenticated users
    if current_user and payload.url:
        with db_connection() as connection:
            try:
                timestamp = now_ts()
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO url_scans (user_id, url, risk_score, prediction, features, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            current_user.id,
                            payload.url,
                            risk_score,
                            prediction,
                            json.dumps(features),
                            timestamp,
                        ),
                    )
                connection.commit()
            except Exception as exc:
                connection.rollback()
                raise HTTPException(
                    status_code=500, detail=f"Failed to save URL scan: {exc}"
                )

    # 4. Analyze scam psychology triggers on the URL itself
    scam_analysis = analyze_scam_psychology(payload.url)

    return UrlAnalysisResponse(
        url=payload.url,
        risk_score=risk_score,
        prediction=prediction,
        features=features,
        feedback=explanations,
        scam_psychology=scam_analysis,
    )


@router.get("/url-scans", response_model=List[UrlScanHistoryItem])
def get_url_scans(
    current_user: UserOut = Depends(get_current_user),
) -> List[UrlScanHistoryItem]:
    with db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, user_id, url, risk_score, prediction, features, created_at
                FROM url_scans
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (current_user.id,),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                record = dict(row)
                if isinstance(record["features"], str):
                    record["features"] = json.loads(record["features"])
                # Compute scam psychology on the fly for history listings
                record["scam_psychology"] = analyze_scam_psychology(record["url"])
                results.append(record)
            return results


# Message/Email Risk Analyzer Endpoints
@router.post("/analyze-message", response_model=MessageAnalysisResponse)
def analyze_message(
    payload: MessageAnalysisRequest,
    current_user: Optional[UserOut] = Depends(get_optional_user),
) -> MessageAnalysisResponse:
    # 0. Check community blocklist
    pending_warning = None
    try:
        reputation = check_community_reputation(payload.message, "message")
        if reputation:
            if reputation["status"] == "verified_threat":
                risk_score = 100
                prediction = "Phishing/Spam"
                feedback = [
                    f"CrowdShield Blocklist: Reported by community users and verified as a threat (Reason: {reputation['description'] or 'No details provided'})."
                ]

                if current_user and payload.message:
                    with db_connection() as connection:
                        try:
                            timestamp = now_ts()
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    """
                                    INSERT INTO message_scans (user_id, message, risk_score, prediction, features, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    """,
                                    (
                                        current_user.id,
                                        payload.message,
                                        risk_score,
                                        prediction,
                                        json.dumps({}),
                                        timestamp,
                                    ),
                                )
                            connection.commit()
                        except Exception:
                            connection.rollback()

                scam_analysis = analyze_scam_psychology(payload.message)
                return MessageAnalysisResponse(
                    message=payload.message,
                    risk_score=risk_score,
                    prediction=prediction,
                    feedback=feedback,
                    scam_psychology=scam_analysis,
                )
            elif reputation["status"] == "pending":
                pending_warning = f"CrowdShield Alert: This message has been reported by community users and is pending verification (Reports: {reputation['reports_count']})."
    except Exception as e:
        print(f"Reputation lookup failed: {e}")

    # 1. Analyze message text using the trained model and heuristics
    try:
        analysis = analyze_message_text(payload.message)
        if pending_warning:
            analysis["feedback"].insert(0, pending_warning)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process message: {e}")

    # 2. Run Scam Psychology Analysis on the message
    scam_analysis = analyze_scam_psychology(payload.message)

    # 3. Log message scan history for authenticated users
    if current_user and payload.message:
        with db_connection() as connection:
            try:
                timestamp = now_ts()
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO message_scans (user_id, message, risk_score, prediction, features, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            current_user.id,
                            payload.message,
                            analysis["risk_score"],
                            analysis["prediction"],
                            json.dumps({}),
                            timestamp,
                        ),
                    )
                connection.commit()
            except Exception as exc:
                connection.rollback()
                raise HTTPException(
                    status_code=500, detail=f"Failed to save message scan: {exc}"
                )

    return MessageAnalysisResponse(
        message=payload.message,
        risk_score=analysis["risk_score"],
        prediction=analysis["prediction"],
        feedback=analysis["feedback"],
        scam_psychology=scam_analysis,
    )


@router.get("/message-scans", response_model=List[MessageScanHistoryItem])
def get_message_scans(
    current_user: UserOut = Depends(get_current_user),
) -> List[MessageScanHistoryItem]:
    with db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, user_id, message, risk_score, prediction, features, created_at
                FROM message_scans
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (current_user.id,),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                record = dict(row)
                if isinstance(record["features"], str):
                    record["features"] = json.loads(record["features"])
                # Compute scam psychology on the fly for history listings
                record["scam_psychology"] = analyze_scam_psychology(record["message"])
                results.append(record)
            return results


@router.post("/analyze-deepfake", response_model=DeepfakeAnalysisResponse)
async def analyze_deepfake_endpoint(
    file: UploadFile = File(...),
    current_user: Optional[UserOut] = Depends(get_optional_user),
) -> DeepfakeAnalysisResponse:
    content = await file.read()

    # Run analysis
    analysis = analyze_deepfake(content, file.filename, file.content_type)

    # Save search history if authenticated
    if current_user:
        with db_connection() as connection:
            try:
                timestamp = now_ts()
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO deepfake_scans (user_id, file_name, file_type, risk_score, prediction, features, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            current_user.id,
                            analysis["metadata"]["file_name"],
                            analysis["file_type"],
                            analysis["risk_score"],
                            analysis["prediction"],
                            json.dumps(analysis["features"]),
                            timestamp,
                        ),
                    )
                connection.commit()
            except Exception as exc:
                connection.rollback()
                raise HTTPException(
                    status_code=500, detail=f"Failed to save deepfake scan: {exc}"
                )

    return DeepfakeAnalysisResponse(
        file_name=analysis["metadata"]["file_name"],
        file_type=analysis["file_type"],
        risk_score=analysis["risk_score"],
        prediction=analysis["prediction"],
        feedback=analysis["feedback"],
        features=analysis["features"],
        metadata=analysis["metadata"],
    )


@router.get("/deepfake-scans", response_model=List[DeepfakeScanHistoryItem])
def get_deepfake_scans(
    current_user: UserOut = Depends(get_current_user),
) -> List[DeepfakeScanHistoryItem]:
    with db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, user_id, file_name, file_type, risk_score, prediction, features, created_at
                FROM deepfake_scans
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (current_user.id,),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                record = dict(row)
                if isinstance(record["features"], str):
                    record["features"] = json.loads(record["features"])
                results.append(record)
            return results
