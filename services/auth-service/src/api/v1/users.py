from fastapi import APIRouter, Depends, status
import uuid

from core.security import security
from core.dependencies import (
    RequestContext, PaginationParams, require_superuser
)
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

    Примечание: Оставлено для обратной совместимости.
    В новых эндпоинтах используйте RequestContext.
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
    context: RequestContext = Depends(RequestContext.from_depends)
) -> UserInDB:
    """
    Возвращает информацию о текущем пользователе.
    """
    return await UserService.get_user(
        user_id=uuid.UUID(context.user_id),
        db=context.db
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
    context: RequestContext = Depends(RequestContext.from_depends)
) -> UserInDB:
    """
    Обновляет логин текущего пользователя.
    """
    return await UserService.update_login(
        user_id=context.user_id,
        update_data=update_data,
        db=context.db
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
    context: RequestContext = Depends(RequestContext.from_depends)
) -> UserInDB:
    """
    Изменяет пароль текущего пользователя после проверки текущего пароля.
    """
    return await UserService.update_password(
        user_id=uuid.UUID(context.user_id),
        update_data=update_data,
        db=context.db
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
    pagination: PaginationParams = Depends(),
    context: RequestContext = Depends(RequestContext.from_depends)
) -> list[LoginHistoryResponse]:
    """
    Возвращает историю входов текущего пользователя с пагинацией.
    """
    return await UserService.get_login_history(
        user_id=uuid.UUID(context.user_id),
        db=context.db,
        page=pagination.page,
        size=pagination.size
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
    context: RequestContext = Depends(require_superuser)
) -> UserInDB:
    """
    Обновляет статус суперпользователя для указанного пользователя.
    Требуются права суперпользователя.
    """
    return await UserService.update_superuser(
        user_id=uuid.UUID(user_id),
        is_superuser=update_data.is_superuser,
        db=context.db
    )
