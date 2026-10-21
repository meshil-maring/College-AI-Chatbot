"""Authentication request models and password validation constraints."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


PASSWORD_MIN_LENGTH = 8

PASSWORD_MAX_LENGTH = 128


class AuthRequest(BaseModel):
    """Login / signup payload.

    ``extra="forbid"`` — clients can NEVER inject ``role``, ``scope_type``,
    ``scope_id``, ``institution_id``, ``organization_id``, ``status``, or any
    other authorization-control field. Role and scope are resolved ONLY from
    trusted server-side records after authentication.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=6, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class PasswordRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    confirm_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("confirm_password")
    @classmethod
    def confirm_matches(cls, value: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password is not None and value != new_password:
            raise ValueError("Passwords do not match")
        return value


class PasswordResetCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    confirm_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("confirm_password")
    @classmethod
    def confirm_matches(cls, value: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password is not None and value != new_password:
            raise ValueError("Passwords do not match")
        return value


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=4096)
