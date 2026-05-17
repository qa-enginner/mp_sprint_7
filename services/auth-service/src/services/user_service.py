import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException, status
from werkzeug.security import generate_password_hash

from models.entity import User, LoginHistory, SocialAccount
from schemas.entity import (
    UserUpdateLogin,
    UserInDB,
    LoginHistoryResponse,
    UserUpdatePassword,
)


class UserService:
    @staticmethod
    async def update_login(
        user_id: uuid.UUID,
        update_data: UserUpdateLogin,
        db: AsyncSession
    ) -> UserInDB:
        """
        Обновляет логин пользователя.
        """
        # Проверяем, существует ли пользователь
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Проверяем, не занят ли новый логин другим пользователем
        existing_login = await db.execute(
            select(User).where(User.login == update_data.new_login)
        )
        if existing_login.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Login already taken"
            )

        # Обновляем логин
        user.login = update_data.new_login
        await db.commit()
        await db.refresh(user)

        return UserInDB.model_validate(user)

    @staticmethod
    async def update_password(
        user_id: uuid.UUID,
        update_data: UserUpdatePassword,
        db: AsyncSession
    ) -> UserInDB:
        """
        Обновляет пароль пользователя после проверки текущего пароля.
        """
        # Проверяем, существует ли пользователь
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Проверяем текущий пароль
        if not user.check_password(update_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        # Хешируем новый пароль и обновляем
        user.password = generate_password_hash(update_data.new_password)
        await db.commit()
        await db.refresh(user)

        return UserInDB.model_validate(user)

    @staticmethod
    async def update_superuser(
        user_id: uuid.UUID,
        is_superuser: bool,
        db: AsyncSession
    ) -> UserInDB:
        """
        Обновляет статус суперпользователя (is_superuser)
        для указанного пользователя.
        """
        # Проверяем, существует ли пользователь
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Обновляем поле is_superuser
        user.is_superuser = is_superuser
        await db.commit()
        await db.refresh(user)

        return UserInDB.model_validate(user)

    @staticmethod
    async def get_user(
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> UserInDB:
        """
        Возвращает информацию о пользователе по ID.
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserInDB.model_validate(user)

    @staticmethod
    async def get_login_history(
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> list[LoginHistoryResponse]:
        """
        Возвращает историю входов пользователя.
        """
        stmt = select(LoginHistory).where(
            LoginHistory.user_id == user_id
        ).order_by(desc(LoginHistory.time))
        result = await db.execute(stmt)
        history = result.scalars().all()
        return [
            LoginHistoryResponse.model_validate(entry) for entry in history
        ]

    @staticmethod
    async def find_or_create_user_by_social(
        provider: str,
        provider_user_id: str,
        email: Optional[str],
        name: Optional[str],
        avatar_url: Optional[str],
        db: AsyncSession
    ) -> User:
        """Находит существующего пользователя по соц-аккаунту
        или создает нового."""
        # Ищем существующую связь
        stmt = select(SocialAccount).where(
            SocialAccount.provider == provider,
            SocialAccount.provider_user_id == provider_user_id
        )
        result = await db.execute(stmt)
        social_account = result.scalar_one_or_none()

        if social_account:
            # Возвращаем существующего пользователя
            stmt_user = select(User).where(User.id == social_account.user_id)
            result_user = await db.execute(stmt_user)
            user = result_user.scalar_one_or_none()
            if user:
                return user

        # Ищем пользователя по email
        user = None
        if email:
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

        if not user:
            # Создаем нового пользователя
            # Генерируем уникальный логин на основе provider_user_id
            login = f"{provider}_{provider_user_id[:8]}"
            # Проверяем, не занят ли логин
            existing = await db.execute(
                select(User).where(User.login == login)
            )
            if existing.scalar_one_or_none():
                # Добавляем суффикс
                import random
                login = f"{login}_{random.randint(1000, 9999)}"

            # Пароль генерируем случайный,
            # т.к. пользователь входит через соцсеть
            password = str(uuid.uuid4())
            user = User(
                login=login,
                email=email or f"{provider_user_id}@{provider}.temp",
                password=password,
                first_name=name or "",
                last_name=""
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Создаем связь пользователя с соцсетью
        social_account = SocialAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email
        )
        db.add(social_account)
        await db.commit()

        return user
