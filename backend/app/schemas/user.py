"""
用户相关 Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = None
    full_name: Optional[str] = None
    grade: Optional[str] = Field(None, description="学段：高一/高二/高三")


class SendCodeRequest(BaseModel):
    email: str = Field(..., description="邮箱地址")


class APIRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    email: str = Field(..., description="邮箱地址")
    verification_code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")
    full_name: Optional[str] = None
    grade: Optional[str] = Field(None, description="学段：高一/高二/高三")


class UserLogin(BaseModel):
    username: str
    password: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., description="注册邮箱")
    verification_code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    grade: Optional[str] = None
    role: str
    class_id: Optional[int] = None
    is_active: bool
    must_change_password: bool = False
    tag: str = "normal"
    api_call_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    grade: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ImportResult(BaseModel):
    total: int
    success: int
    failed: int
    details: list[str]
