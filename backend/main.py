from __future__ import annotations

import os
import re
import secrets
import smtplib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Iterator, Literal, Optional

import psycopg2
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


DATABASE_URL = os.getenv(
    "CYBERGUARDIAN_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/cyberguardian",
)
JWT_SECRET = os.getenv("CYBERGUARDIAN_JWT_SECRET", "cyberguardian-dev-secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_HOURS = 24
OTP_EXPIRES_MINUTES = 10
SMTP_HOST = os.getenv("CYBERGUARDIAN_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("CYBERGUARDIAN_SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("CYBERGUARDIAN_SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("CYBERGUARDIAN_SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("CYBERGUARDIAN_SMTP_FROM_NAME", "CyberGuardian AI")

app = FastAPI(title="CyberGuardian AI Auth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    identifier: str = Field(min_length=3)
    contact_mode: Literal["email", "phone"]
    purpose: Literal["login", "signup"]
    display_name: Optional[str] = None


class OtpVerifyRequest(BaseModel):
    identifier: str = Field(min_length=3)
    contact_mode: Literal["email", "phone"]
    purpose: Literal["login", "signup"]
    otp_code: str = Field(min_length=4, max_length=12)
    display_name: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    identifier: str
    identifier_type: Literal["email", "phone"]
    auth_provider: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    message: str


class OtpResponse(BaseModel):
    message: str
    otp_code: Optional[str] = None
    identifier: str
    contact_mode: Literal["email", "phone"]
    purpose: Literal["login", "signup"]


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

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_otp_lookup
                ON otp_challenges(identifier, identifier_type, purpose, code, consumed, expires_at)
                """
            )

        connection.commit()


def normalize_identifier(identifier: str, contact_mode: Literal["email", "phone"]) -> str:
    value = identifier.strip()

    if contact_mode == "email":
        return value.lower()

    return re.sub(r"[^\d+]", "", value)


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def send_email_otp(recipient: str, code: str, purpose: Literal["login", "signup"]) -> None:
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="Email OTP delivery is not configured. Set CYBERGUARDIAN_SMTP_USERNAME and CYBERGUARDIAN_SMTP_PASSWORD.",
        )

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


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "CyberGuardian AI Backend Running"}


@app.post("/auth/request-otp", response_model=OtpResponse)
def request_otp(payload: AuthRequest) -> OtpResponse:
    identifier = normalize_identifier(payload.identifier, payload.contact_mode)
    display_name = payload.display_name.strip() if payload.display_name else None
    code = generate_otp_code()

    if payload.contact_mode == "phone":
        raise HTTPException(
            status_code=400,
            detail="Phone OTP delivery is not wired yet. Add an SMS provider before using phone sign-in.",
        )

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
            send_email_otp(identifier, code, payload.purpose)
        except Exception:
            connection.rollback()
            raise

        connection.commit()

    return OtpResponse(
        message=f"OTP sent to {payload.contact_mode}.",
        identifier=identifier,
        contact_mode=payload.contact_mode,
        purpose=payload.purpose,
    )


@app.post("/auth/verify-otp", response_model=AuthResponse)
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


@app.post("/auth/google-demo", response_model=AuthResponse)
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


@app.get("/auth/me", response_model=UserOut)
def auth_me(current_user: UserOut = Depends(get_current_user)) -> UserOut:
    return current_user
