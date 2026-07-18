from typing import Literal, Optional
from pydantic import BaseModel, Field

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

class GoogleVerifyRequest(BaseModel):
    credential: str
