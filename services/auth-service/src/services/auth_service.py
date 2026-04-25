import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from asyncpg import UniqueViolationError
from fastapi import HTTPException, Request, status
from jose import jwt

from core.config import settings
from db import redis_db
from models.entity import User, LoginHistory
from schemas.entity import UserCreate, UserInDB, UserLogin, TokenResponse


ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30


class AuthService:
    @staticmethod
    async def create_user(user_create: UserCreate,
                          db: AsyncSession) -> UserInDB:
        # Проверяем, существует ли пользователь с таким логином
        existing_login = await db.execute(
            User.__table__.select().where(User.login == user_create.login)
        )
        if existing_login.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this login already exists"
            )

        # Проверяем, существует ли пользователь с таким email
        existing_email = await db.execute(
            User.__table__.select().where(User.email == user_create.email)
        )
        if existing_email.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )

        user = User(**user_create.dict())
        db.add(user)
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            if isinstance(e.orig, UniqueViolationError):
                # Determine which constraint violated
                error_msg = str(e.orig)
                if 'login' in error_msg:
                    detail = "User with this login already exists"
                elif 'email' in error_msg:
                    detail = "User with this email already exists"
                else:
                    detail = "Duplicate key violation"
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=detail
                )
            raise e
        await db.refresh(user)
        return UserInDB.from_orm(user)

    @staticmethod
    def create_access_token(user_id: uuid.UUID) -> str:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode = {"sub": str(user_id), "exp": expire}
        encoded_jwt = jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.algorithm
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: uuid.UUID) -> str:
        expire = datetime.utcnow() + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
        encoded_jwt = jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.algorithm
        )
        return encoded_jwt, expire

    @staticmethod
    async def login(user_login: UserLogin,
                    request: Request,
                    db: AsyncSession) -> TokenResponse:
        from sqlalchemy import select
        stmt = select(User).where(User.email == user_login.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        if not user.check_password(user_login.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        # Создаем токен доступа
        access_token = AuthService.create_access_token(user.id)
        refresh_token, expire = AuthService.create_refresh_token(user.id)

        # Сохраняем токен обновления в Redis
        if redis_db.redis:
            key = f"{user.id}_refresh"
            # Вычисляем TTL в секундах
            ttl = int((expire - datetime.utcnow()).total_seconds())
            await redis_db.redis.setex(key, ttl, refresh_token)

        # Сохраняем историю входов
        await AuthService.save_login_history(user.id, request, db)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )

    @staticmethod
    async def save_login_history(user_id: uuid.UUID,
                                 request: Request,
                                 db: AsyncSession) -> None:
        db.add(LoginHistory(
            user_id=user_id,
            ip_address=request.client.host,
            user_agent=request.headers.get('User-Agent')
        ))
        await db.commit()

    @staticmethod
    async def refresh_token(
        refresh_token: str,
        request: Request,
        db: AsyncSession
    ) -> TokenResponse:
        try:
            # Декодируем refresh token
            payload = jwt.decode(
                refresh_token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )

            # Проверяем тип токена
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

            # Проверяем наличие токена в Redis
            if redis_db.redis:
                stored_token = await redis_db.redis.get(f"{user_id}_refresh")
                if not stored_token or stored_token != refresh_token:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token not found or invalid"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Redis connection error"
                )

            # Проверяем существование пользователя в БД
            stmt = select(User).where(User.id == uuid.UUID(user_id))
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            # Удаляем старый refresh token из Redis
            await redis_db.redis.delete(f"{user_id}_refresh")

            # Создаем новую пару токенов
            access_token = AuthService.create_access_token(user.id)
            refresh_token_new, expire = AuthService.create_refresh_token(
                user.id
            )

            # Сохраняем новый refresh token в Redis
            if redis_db.redis:
                ttl = int((expire - datetime.utcnow()).total_seconds())
                await redis_db.redis.setex(
                    f"{user.id}_refresh", ttl, refresh_token_new
                )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token_new
            )

        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token")

    @staticmethod
    async def is_token_blacklisted(access_token: str) -> bool:
        """
        Проверяет, находится ли access token в черном списке (Redis).
        Возвращает True, если токен в черном списке.
        """
        if not redis_db.redis:
            # Если Redis недоступен, считаем, что токен не в черном списке,
            # но логируем предупреждение (пока просто пропускаем)
            return False
        key = f"blacklist_{access_token}"
        exists = await redis_db.redis.exists(key)
        return bool(exists)

    @staticmethod
    async def logout(access_token: str, refresh_token: str) -> None:
        """
        Выполняет выход пользователя, удаляя refresh token из Redis
        и добавляя access token в черный список до его истечения
        """
        if not redis_db.redis:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Redis connection error"
            )

        try:
            # Декодируем refresh token
            payload = jwt.decode(
                refresh_token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )

            # Проверяем тип токена
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

            # Проверяем наличие refresh token в Redis
            stored_token = await redis_db.redis.get(f"{user_id}_refresh")
            if not stored_token or stored_token != refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token not found or invalid"
                )

            # Удаляем refresh token из Redis
            await redis_db.redis.delete(f"{user_id}_refresh")

            # Добавляем access token в черный список до его истечения
            try:
                access_payload = jwt.decode(
                    access_token,
                    settings.secret_key,
                    algorithms=[settings.algorithm],
                    options={"verify_exp": False}
                )
                exp = access_payload.get("exp")
                if exp:
                    ttl = exp - int(datetime.utcnow().timestamp())
                    if ttl > 0:
                        await redis_db.redis.setex(
                            f"blacklist_{access_token}",
                            ttl,
                            "revoked"
                        )
            except Exception:
                # Если не удалось декодировать токен, просто продолжаем
                pass

        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
