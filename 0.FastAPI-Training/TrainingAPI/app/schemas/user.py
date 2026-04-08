from enum import Enum
from typing import Literal

from pydantic import BaseModel, EmailStr

from .common import PaginatedResponse


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel):
    role: UserRole


class UserListResponse(PaginatedResponse[UserResponse]):
    pass


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str


class TokenRefresh(BaseModel):
    refresh_token: str
