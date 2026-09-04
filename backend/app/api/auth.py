from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, field_validator
from supabase_auth.errors import AuthApiError

from app.db.supabase import create_supabase_client
from app.core.errors import AppError

router = APIRouter(prefix="/auth/v1", tags=["auth"])


class AuthRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


@router.post("/signup", status_code=201)
def signup(body: AuthRequest):
    try:
        client = create_supabase_client()
        response = client.auth.sign_up({"email": body.email, "password": body.password})
        if response.session is None:
            return {
                "access_token": None,
                "message": "Signup successful. Please check your email to confirm your account.",
                "user": {"id": response.user.id, "email": response.user.email},
            }
        return {
            "access_token": response.session.access_token,
            "message": "Signup successful.",
            "user": {"id": response.user.id, "email": response.user.email},
        }
    except AuthApiError as e:
        raise AppError(e.message, status_code=e.status, code="AUTH_ERROR")


@router.post("/login")
def login(body: AuthRequest):
    try:
        client = create_supabase_client()
        response = client.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {
            "access_token": response.session.access_token,
            "message": "Login successful.",
            "user": {"id": response.user.id, "email": response.user.email},
        }
    except AuthApiError as e:
        status = e.status or 400
        code = "INVALID_CREDENTIALS" if status == 400 else "AUTH_ERROR"
        raise AppError(e.message, status_code=status, code=code)
