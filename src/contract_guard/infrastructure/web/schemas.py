from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
import re


class MobileRequest(BaseModel):
    mobile: str

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value):
        value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if not re.fullmatch(r"09[0-9]{9}", value):
            raise ValueError("Invalid Iranian mobile number")
        return value


class VerifyRequest(MobileRequest):
    code: str = Field(min_length=4, max_length=10)


class ProfileUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=254)
    username: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if value is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid email")
        return value


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class UserResponse(BaseModel):
    id: UUID
    mobile_number: str
    email: str | None
    username: str | None


class TokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_at: datetime
    refresh_expires_at: datetime


class LoginResponse(TokensResponse):
    user: UserResponse
