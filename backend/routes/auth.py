import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from jose import JWTError, jwt
from psycopg2.extras import RealDictCursor

from backend.database.connection import db_connection, now_ts
from backend.models.auth import (
    AuthRequest,
    OtpVerifyRequest,
    GoogleAuthRequest,
    UserOut,
    AuthResponse,
    OtpResponse,
    GoogleVerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.getenv("CYBERGUARDIAN_JWT_SECRET", "cyberguardian-dev-secret")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "48190723181-pf48lpee9226voi06h554qq5r93hchbb.apps.googleusercontent.com")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_HOURS = 24
OTP_EXPIRES_MINUTES = 10
SMTP_HOST = os.getenv("CYBERGUARDIAN_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("CYBERGUARDIAN_SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("CYBERGUARDIAN_SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("CYBERGUARDIAN_SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("CYBERGUARDIAN_SMTP_FROM_NAME", "CyberGuardian AI")

def normalize_identifier(identifier: str, contact_mode: Literal["email", "phone"]) -> str:
    value = identifier.strip()
    if contact_mode == "email":
        return value.lower()
    return re.sub(r"[^\d+]", "", value)

def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

def send_email_otp(recipient: str, code: str, purpose: Literal["login", "signup"]) -> None:
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"\n[DEVELOPMENT VERIFICATION] Simulated Email OTP for {recipient}: {code} (Purpose: {purpose})\n")
        return

    subject = f"CyberGuardian AI verification code for {purpose}"
    body = (
        f"Your CyberGuardian AI verification code is {code}.\n\n"
        f"This code expires in {OTP_EXPIRES_MINUTES} minutes.\n"
        "If you did not request this code, you can ignore this email."
    )

    message = EmailMessage()
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_USERNAME}>"
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as client:
        client.starttls()
        client.login(SMTP_USERNAME, SMTP_PASSWORD)
        client.send_message(message)

def build_user_out(row: dict) -> UserOut:
    return UserOut(
        id=row["id"],
        name=row["name"],
        identifier=row["identifier"],
        identifier_type=row["identifier_type"],
        auth_provider=row["auth_provider"],
    )

def create_access_token(user: UserOut) -> str:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(hours=ACCESS_TOKEN_EXPIRES_HOURS)
    payload = {
        "sub": user.id,
        "name": user.name,
        "identifier": user.identifier,
        "identifier_type": user.identifier_type,
        "auth_provider": user.auth_provider,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_user_by_identifier(connection, identifier: str) -> Optional[dict]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM users WHERE identifier = %s LIMIT 1", (identifier,))
        return cursor.fetchone()

def get_user_by_id(connection, user_id: str) -> Optional[dict]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (user_id,))
        return cursor.fetchone()

def upsert_user(
    connection,
    *,
    identifier: str,
    identifier_type: Literal["email", "phone"],
    name: str,
    auth_provider: str,
) -> dict:
    existing = get_user_by_identifier(connection, identifier)
    timestamp = now_ts()

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        if existing is None:
            user_id = f"usr_{secrets.token_hex(8)}"
            cursor.execute(
                """
                INSERT INTO users (id, name, identifier, identifier_type, auth_provider, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, name, identifier, identifier_type, auth_provider, timestamp, timestamp),
            )
        else:
            user_id = existing["id"]
            cursor.execute(
                """
                UPDATE users
                SET name = %s, identifier_type = %s, auth_provider = %s, updated_at = %s
                WHERE id = %s
                """,
                (name, identifier_type, auth_provider, timestamp, user_id),
            )

        cursor.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (user_id,))
        user_row = cursor.fetchone()

    assert user_row is not None
    return user_row

def save_otp_challenge(
    connection,
    *,
    identifier: str,
    identifier_type: Literal["email", "phone"],
    purpose: Literal["login", "signup"],
    code: str,
    display_name: Optional[str],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM otp_challenges WHERE identifier = %s AND identifier_type = %s AND purpose = %s AND consumed = FALSE",
            (identifier, identifier_type, purpose),
        )
        cursor.execute(
            """
            INSERT INTO otp_challenges (identifier, identifier_type, purpose, code, display_name, expires_at, consumed, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s)
            """,
            (
                identifier,
                identifier_type,
                purpose,
                code,
                display_name,
                now_ts() + (OTP_EXPIRES_MINUTES * 60),
                now_ts(),
            ),
        )

def verify_otp_challenge(
    connection,
    *,
    identifier: str,
    identifier_type: Literal["email", "phone"],
    purpose: Literal["login", "signup"],
    code: str,
) -> Optional[dict]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT * FROM otp_challenges
            WHERE identifier = %s AND identifier_type = %s AND purpose = %s AND code = %s AND consumed = FALSE
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (identifier, identifier_type, purpose, code),
        )
        challenge = cursor.fetchone()

        if challenge is None:
            return None

        if challenge["expires_at"] < now_ts():
            return None

        cursor.execute("UPDATE otp_challenges SET consumed = TRUE WHERE id = %s", (challenge["id"],))

    return challenge

def token_from_authorization(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token

def get_current_user(authorization: Optional[str] = Header(default=None)) -> UserOut:
    token = token_from_authorization(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="Authorization token missing.")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    with db_connection() as connection:
        user_row = get_user_by_id(connection, user_id)

    if user_row is None:
        raise HTTPException(status_code=401, detail="User not found.")

    return build_user_out(user_row)


@router.post("/request-otp", response_model=OtpResponse)
def request_otp(payload: AuthRequest) -> OtpResponse:
    identifier = normalize_identifier(payload.identifier, payload.contact_mode)
    display_name = payload.display_name.strip() if payload.display_name else None
    code = generate_otp_code()

    with db_connection() as connection:
        existing_user = get_user_by_identifier(connection, identifier)

        if payload.purpose == "login" and existing_user is None:
            raise HTTPException(status_code=404, detail="No account found for that identifier.")

        if payload.purpose == "signup" and existing_user is not None:
            raise HTTPException(status_code=409, detail="An account already exists for that identifier. Sign in instead.")

        save_otp_challenge(
            connection,
            identifier=identifier,
            identifier_type=payload.contact_mode,
            purpose=payload.purpose,
            code=code,
            display_name=display_name,
        )

        try:
            if payload.contact_mode == "email":
                send_email_otp(identifier, code, payload.purpose)
            else:
                # Phone OTP simulation
                print(f"\n[DEVELOPMENT VERIFICATION] Simulated Phone OTP for {identifier}: {code} (Purpose: {payload.purpose})\n")
        except Exception:
            connection.rollback()
            raise

        connection.commit()

    is_simulated = not SMTP_USERNAME or not SMTP_PASSWORD or payload.contact_mode == "phone"
    if is_simulated:
        msg = f"Simulated verification code: {code} (This code has been printed to the server terminal too)."
    else:
        msg = f"Verification code sent to your {payload.contact_mode}."

    return OtpResponse(
        message=msg,
        identifier=identifier,
        contact_mode=payload.contact_mode,
        purpose=payload.purpose,
    )


@router.post("/verify-otp", response_model=AuthResponse)
def verify_otp(payload: OtpVerifyRequest) -> AuthResponse:
    identifier = normalize_identifier(payload.identifier, payload.contact_mode)
    name = payload.display_name.strip() if payload.display_name else None

    with db_connection() as connection:
        challenge = verify_otp_challenge(
            connection,
            identifier=identifier,
            identifier_type=payload.contact_mode,
            purpose=payload.purpose,
            code=payload.otp_code.strip(),
        )

        if challenge is None:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

        if payload.purpose == "signup":
            user_name = name or challenge["display_name"] or "CyberGuardian user"
            user_row = upsert_user(
                connection,
                identifier=identifier,
                identifier_type=payload.contact_mode,
                name=user_name,
                auth_provider="otp",
            )
        else:
            user_row = get_user_by_identifier(connection, identifier)
            if user_row is None:
                raise HTTPException(status_code=404, detail="No account found for that identifier.")

        connection.commit()

    user = build_user_out(user_row)
    token = create_access_token(user)
    return AuthResponse(access_token=token, user=user, message="Authenticated successfully.")


@router.post("/google-demo", response_model=AuthResponse)
def google_demo_login(payload: GoogleAuthRequest) -> AuthResponse:
    identifier = (payload.email.lower() if payload.email else f"google-{secrets.token_hex(6)}@cyberguardian.local")
    name = payload.display_name.strip() if payload.display_name else "Google user"

    with db_connection() as connection:
        user_row = upsert_user(
            connection,
            identifier=identifier,
            identifier_type="email",
            name=name,
            auth_provider="google",
        )
        connection.commit()

    user = build_user_out(user_row)
    token = create_access_token(user)
    return AuthResponse(access_token=token, user=user, message="Google demo sign-in successful. This is not Google OAuth.")


@router.post("/google", response_model=AuthResponse)
def google_login(payload: GoogleVerifyRequest) -> AuthResponse:
    import urllib.request
    import urllib.parse
    import json

    credential = payload.credential.strip()
    if not credential:
        raise HTTPException(status_code=400, detail="Google credential token cannot be empty.")

    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(credential)}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            info = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to verify Google token: {e}")

    aud = info.get("aud")
    if aud != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Google Client ID audience mismatch.")

    email = info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google email address not found in token.")

    name = info.get("name", "Google User")

    with db_connection() as connection:
        user_row = upsert_user(
            connection,
            identifier=email.lower().strip(),
            identifier_type="email",
            name=name,
            auth_provider="google",
        )
        connection.commit()

    user = build_user_out(user_row)
    token = create_access_token(user)
    return AuthResponse(access_token=token, user=user, message="Google authentication successful.")


@router.get("/me", response_model=UserOut)
def auth_me(current_user: UserOut = Depends(get_current_user)) -> UserOut:
    return current_user
