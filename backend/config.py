import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the project root .env
# config.py is in backend/, so project root is parents[1]
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Base directory
BASE_DIR = Path(__file__).resolve().parent


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default."""
    return os.getenv(key, default)


def get_env_str(key: str, required: bool = True) -> str:
    """Get environment variable, raising if missing and required."""
    val = os.getenv(key)
    if val is None:
        if required:
            raise ValueError(f"Required environment variable not set: {key}")
        return ""
    return val


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    val = os.getenv(key, str(default)).lower()
    return val in ("1", "true", "yes", "y", "on")


def get_env_int(key: str, default: int, required: bool = False) -> int:
    """Get environment variable as int."""
    val = os.getenv(key)
    if val is None:
        if required:
            raise ValueError(f"Required environment variable not set: {key}")
        return default
    try:
        return int(val)
    except ValueError:
        raise ValueError(f"Environment variable {key} must be an integer, got: {val!r}")


class Settings:
    """Centralized, security-first settings for CyberGuardian AI.

    Required security settings have NO insecure fallback — they fail-fast
    at import time in production and are documented for local dev via .env.
    """

    # --- Authentication ---
    JWT_SECRET: str = ""  # Must be set via CYBERGUARDIAN_JWT_SECRET — no fallback
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRES_HOURS: int = get_env_int("ACCESS_TOKEN_EXPIRES_HOURS", 24)
    OTP_EXPIRES_MINUTES: int = get_env_int("OTP_EXPIRES_MINUTES", 10)

    # --- Database ---
    DATABASE_URL: str = get_env_str("CYBERGUARDIAN_DATABASE_URL")

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = get_env_str("GOOGLE_CLIENT_ID", required=False)
    GOOGLE_CLIENT_SECRET: str = get_env_str("GOOGLE_CLIENT_SECRET", required=False)

    # --- SMTP ---
    SMTP_HOST: str = get_env_str("CYBERGUARDIAN_SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = get_env_int("CYBERGUARDIAN_SMTP_PORT", 587)
    SMTP_USERNAME: str = get_env_str("CYBERGUARDIAN_SMTP_USERNAME", required=False)
    SMTP_PASSWORD: str = get_env_str("CYBERGUARDIAN_SMTP_PASSWORD", required=False)
    SMTP_FROM_NAME: str = get_env_str("CYBERGUARDIAN_SMTP_FROM_NAME", "CyberGuardian AI")

    # --- CORS ---
    ALLOWED_ORIGINS: List[str] = []

    # --- Rate Limiting ---
    OTP_RATE_LIMIT: int = get_env_int("OTP_RATE_LIMIT", 5)  # per minute
    OTP_VERIFY_RATE_LIMIT: int = get_env_int("OTP_VERIFY_RATE_LIMIT", 10)  # per hour
    ANALYSIS_RATE_LIMIT: int = get_env_int("ANALYSIS_RATE_LIMIT", 60)  # per hour
    COMMUNITY_REPORT_RATE_LIMIT: int = get_env_int("COMMUNITY_REPORT_RATE_LIMIT", 10)  # per hour

    # --- Security ---
    MAX_UPLOAD_SIZE: int = get_env_int("MAX_UPLOAD_SIZE", 10)  # MB
    SSRF_BLOCKED_SCHEMES: List[str] = ["file", "ftp", "sftp", "smb"]
    SSRF_BLOCKED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
    MAX_URL_FETCH_TIMEOUT: float = float(get_env("MAX_URL_FETCH_TIMEOUT", "10.0"))
    MAX_URL_REDIRECTS: int = get_env_int("MAX_URL_REDIRECTS", 5)
    MAX_RESPONSE_SIZE: int = get_env_int("MAX_RESPONSE_SIZE", 10)  # MB
    DEEPFAKE_DATASET_DIR: str = os.getenv("DEEPFAKE_DATASET_DIR", "")  # Path to real deepfake dataset
    DEV_OTP_MODE: bool = get_env_bool("DEV_OTP_MODE", False)  # Return OTP in response for local dev

    @classmethod
    def initialize_from_env(cls) -> None:
        """Validate and set security-critical settings. Must be called at startup."""
        jwt_secret = os.getenv("CYBERGUARDIAN_JWT_SECRET")
        if not jwt_secret:
            raise RuntimeError(
                "CYBERGUARDIAN_JWT_SECRET environment variable is required. "
                "Set it in your .env or environment. No insecure fallback is provided."
            )
        cls.JWT_SECRET = jwt_secret

        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        if google_client_id:
            cls.GOOGLE_CLIENT_ID = google_client_id
        # else: GOOGLE_CLIENT_ID stays "" — caller decides whether Google auth is needed

        origins_str = os.getenv("ALLOWED_ORIGINS", "")
        if origins_str:
            cls.ALLOWED_ORIGINS = [o.strip() for o in origins_str.split(",") if o.strip()]
        else:
            # Explicit local-dev defaults — never fall back to wildcard
            cls.ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

        if not cls.DATABASE_URL:
            raise RuntimeError("CYBERGUARDIAN_DATABASE_URL environment variable is required.")


# Initialize settings at import time — fail fast if required security config is missing
Settings.initialize_from_env()
settings = Settings()

# Module-level aliases for backward compatibility (consumers import these directly)
JWT_SECRET: str = settings.JWT_SECRET
JWT_ALGORITHM: str = settings.JWT_ALGORITHM