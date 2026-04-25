import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException, status
from werkzeug.security import generate_password_hash

from models.entity import User, LoginHistory
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

        return UserInDB.from_orm(user)

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

        return UserInDB.from_orm(user)

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
        return UserInDB.from_orm(user)

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
        return [LoginHistoryResponse.from_orm(entry) for entry in history]
