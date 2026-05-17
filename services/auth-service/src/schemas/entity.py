from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
import re


class UserCreate(BaseModel):
    login: str = Field(
        ..., min_length=3, max_length=255,
        description="Username, only letters, numbers and underscore"
    )
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(
        ..., min_length=8, description="Password at least 8 characters"
    )
    first_name: str = Field(
        ..., max_length=50,
        description="First name, letters, spaces and hyphens"
    )
    last_name: str = Field(
        ..., max_length=50,
        description="Last name, letters, spaces and hyphens"
    )

    @field_validator('login')
    @classmethod
    def login_alphanumeric(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError(
                'Login must contain only letters, numbers and underscore'
            )
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def name_letters(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', v):
            raise ValueError(
                'Name must contain only letters, spaces and hyphens'
            )
        return v

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email address')
        return v

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserInDB(BaseModel):
    id: UUID
    login: str
    email: str
    first_name: str
    last_name: str
    is_superuser: bool = False

    model_config = ConfigDict(
        from_attributes=True
    )


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email address for login")
    password: str = Field(..., description="Password")


class UserUpdateLogin(BaseModel):
    new_login: str = Field(
        ..., min_length=3, max_length=255,
        description="New username, only letters, numbers and underscore"
    )

    @field_validator('new_login')
    @classmethod
    def login_alphanumeric(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError(
                'Login must contain only letters, numbers and underscore'
            )
        return v


class UserUpdatePassword(BaseModel):
    current_password: str = Field(
        ..., min_length=1, description="Current password for verification"
    )
    new_password: str = Field(
        ..., min_length=8, description="New password at least 8 characters"
    )

    @field_validator('new_password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdateSuperuser(BaseModel):
    is_superuser: bool = Field(
        ..., description="Set superuser status (true/false)"
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    """Данные, извлеченные из токена."""
    user_id: str
    token: str


class LoginHistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    ip_address: str
    user_agent: str
    time: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class PaginatedResponse(BaseModel):
    """
    Стандартный ответ с пагинацией.

    Используется для эндпоинтов, возвращающих списки с разбивкой на страницы.
    """
    items: list
    page: int
    size: int
    total: int
    pages: int

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
