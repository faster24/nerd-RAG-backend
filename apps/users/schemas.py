from pydantic import BaseModel, EmailStr, validator
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None

    @validator("password")
    def validate_password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "display_name": "John Doe",
            }
        }


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    class Config:
        schema_extra = {
            "example": {"email": "user@example.com", "password": "securepassword123"}
        }


class UserResponse(BaseModel):
    uid: str
    email: str
    email_verified: bool
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    provider_id: str
    created_at: str

    class Config:
        schema_extra = {
            "example": {
                "uid": "abc123xyz",
                "email": "user@example.com",
                "email_verified": True,
                "display_name": "John Doe",
                "photo_url": None,
                "provider_id": "password",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }


class AuthTokens(BaseModel):
    id_token: str
    refresh_token: str
    access_token: Optional[str] = None
    expires_in: int
    token_type: str = "Bearer"

    class Config:
        schema_extra = {
            "example": {
                "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAifQ...",
                "refresh_token": "AMf4BbI2qjL...Z5y7w",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        }


class LoginResponse(BaseModel):
    user: UserResponse
    tokens: AuthTokens

    class Config:
        schema_extra = {
            "example": {
                "user": {
                    "uid": "abc123xyz",
                    "email": "user@example.com",
                    "email_verified": True,
                    "display_name": "John Doe",
                    "photo_url": None,
                    "provider_id": "password",
                    "created_at": "2024-01-01T00:00:00Z",
                },
                "tokens": {
                    "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAifQ...",
                    "refresh_token": "AMf4BbI2qjL...Z5y7w",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            }
        }


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    class Config:
        schema_extra = {
            "example": {"refresh_token": "AMf4BbI2qjL...Z5y7w"}
        }


class RefreshTokenResponse(BaseModel):
    id_token: str
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"

    class Config:
        schema_extra = {
            "example": {
                "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAifQ...",
                "access_token": "ya29.a0AfH6SMB...",
                "refresh_token": "AMf4BbI2qjL...Z5y7w",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        }


class PasswordResetRequest(BaseModel):
    email: EmailStr

    class Config:
        schema_extra = {"example": {"email": "user@example.com"}}


class PasswordResetConfirm(BaseModel):
    oob_code: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

    class Config:
        schema_extra = {
            "example": {
                "oob_code": "ABC123XYZ",
                "new_password": "newpassword123",
            }
        }


class MessageResponse(BaseModel):
    message: str

    class Config:
        schema_extra = {"example": {"message": "Operation successful"}}


class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "error": "Invalid credentials",
                "details": "The email or password is incorrect",
            }
        }