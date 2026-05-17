from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from db.postgres import get_session
from core.security import security
from schemas.entity import (
    UserUpdateLogin,
    UserInDB,
    LoginHistoryResponse,
    UserUpdatePassword,
    UserUpdateSuperuser,
    TokenData,
)
from services.user_service import UserService

router = APIRouter()


async def get_current_user_id(
    token_data: TokenData = Depends(security)
) -> str:
    """
    Извлекает user_id из access token.
    Использует кастомный HTTPBearer для проверки токена.
    """
    return token_data.user_id


@router.get(
    "/me",
    response_model=UserInDB,
    status_code=status.HTTP_200_OK,
    summary="Получить информацию о текущем пользователе",
    responses={
        200: {"description": "Информация о пользователе получена"},
        401: {"description": "Не авторизован"},
        404: {"description": "Пользователь не найден"},
    }
)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
) -> UserInDB:
    """
    Возвращает информацию о текущем пользователе.
    """
    return await UserService.get_user(
        user_id=uuid.UUID(user_id),
        db=db
    )


@router.patch(
    "/me",
    response_model=UserInDB,
    status_code=status.HTTP_200_OK,
    summary="Обновление логина текущего пользователя",
    responses={
        200: {"description": "Логин успешно обновлен"},
        400: {"description": "Некорректные данные"},
        401: {"description": "Не авторизован"},
        404: {"description": "Пользователь не найден"},
        409: {"description": "Логин уже занят"},
    }
)
async def update_login(
    update_data: UserUpdateLogin,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
) -> UserInDB:
    """
    Обновляет логин текущего пользователя.
    """
    return await UserService.update_login(
        user_id=user_id,
        update_data=update_data,
        db=db
    )


@router.patch(
    "/me/password",
    response_model=UserInDB,
    status_code=status.HTTP_200_OK,
    summary="Изменение пароля текущего пользователя",
    responses={
        200: {"description": "Пароль успешно изменен"},
        400: {"description": "Некорректные данные"},
        401: {"description": "Неверный текущий пароль или не авторизован"},
        404: {"description": "Пользователь не найден"},
    }
)
async def update_password(
    update_data: UserUpdatePassword,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
) -> UserInDB:
    """
    Изменяет пароль текущего пользователя после проверки текущего пароля.
    """
    return await UserService.update_password(
        user_id=uuid.UUID(user_id),
        update_data=update_data,
        db=db
    )


@router.get(
    "/me/login-history",
    response_model=list[LoginHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Получить историю входов текущего пользователя",
    responses={
        200: {"description": "История входов получена"},
        401: {"description": "Не авторизован"},
        404: {"description": "Пользователь не найден"},
    }
)
async def get_login_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
) -> list[LoginHistoryResponse]:
    """
    Возвращает историю входов текущего пользователя.
    """
    return await UserService.get_login_history(
        user_id=uuid.UUID(user_id),
        db=db
    )


@router.patch(
    "/{user_id}/superuser",
    response_model=UserInDB,
    status_code=status.HTTP_200_OK,
    summary="Обновить статус суперпользователя",
    responses={
        200: {"description": "Статус суперпользователя обновлен"},
        400: {"description": "Некорректные данные"},
        401: {"description": "Не авторизован"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Пользователь не найден"},
    }
)
async def update_superuser(
    user_id: str,
    update_data: UserUpdateSuperuser,
    token_data: TokenData = Depends(security),
    db: AsyncSession = Depends(get_session)
) -> UserInDB:
    """
    Обновляет статус суперпользователя для указанного пользователя.
    Требуются права суперпользователя.
    """
    # Получаем текущего пользователя (того, кто делает запрос)
    current_user = await UserService.get_user(
        user_id=uuid.UUID(token_data.user_id),
        db=db
    )
    # Проверяем, что текущий пользователь - суперпользователь
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для изменения статуса суперпользователя"
        )
    return await UserService.update_superuser(
        user_id=uuid.UUID(user_id),
        is_superuser=update_data.is_superuser,
        db=db
    )
