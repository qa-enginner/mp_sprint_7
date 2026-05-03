import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import check_password_hash, generate_password_hash

from db.postgres import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True),
                primary_key=True,
                default=uuid.uuid4,
                unique=True,
                nullable=False)
    login = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __init__(self,
                 login: str,
                 email: str,
                 password: str,
                 first_name: str,
                 last_name: str) -> None:
        self.login = login
        self.email = email
        self.password = generate_password_hash(password)
        self.first_name = first_name
        self.last_name = last_name

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    def __repr__(self) -> str:
        return f'<User {self.login}>'


class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id = Column(UUID(as_uuid=True),
                primary_key=True,
                default=uuid.uuid4,
                unique=True,
                nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    token = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)


class LoginHistory(Base):
    __tablename__ = 'login_history'

    id = Column(UUID(as_uuid=True),
                primary_key=True,
                default=uuid.uuid4,
                unique=True,
                nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    ip_address = Column(String(255), nullable=False)
    user_agent = Column(String(255), nullable=False)
    time = Column(DateTime, default=datetime.utcnow)


class SocialAccount(Base):
    __tablename__ = 'social_accounts'

    id = Column(UUID(as_uuid=True),
                primary_key=True,
                default=uuid.uuid4,
                unique=True,
                nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    provider = Column(String(50), nullable=False)  # yandex, google, etc.
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Уникальный индекс на комбинацию provider + provider_user_id
    __table_args__ = (
        UniqueConstraint(
            'provider', 'provider_user_id', name='uq_provider_user'
        ),
    )

    def __repr__(self) -> str:
        return f'<SocialAccount {self.provider}:{self.provider_user_id}>'
