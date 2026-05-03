from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_session
from core.security import optional_security, security
from schemas.entity import (
        UserCreate,
        UserInDB,
        UserLogin,
        TokenResponse,
        TokenRefresh,
        TokenData
    )
from services.auth_service import AuthService

router = APIRouter()


@router.post(
    '/register',
    response_model=UserInDB,
    status_code=status.HTTP_201_CREATED
)
async def create_user(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_session)
) -> UserInDB:
    return await AuthService.create_user(user_create, db)


@router.post(
    '/login',
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password"
)
async def login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_session)
):
    """
    Authenticate user by email and password.

    Returns access and refresh tokens upon successful authentication.
    """
    return await AuthService.login(login_data, request, db)


@router.post(
    '/refresh',
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK
)
async def refresh(
    request: Request,
    token_refresh: TokenRefresh,
    db: AsyncSession = Depends(get_session)
):
    return await AuthService.refresh_token(
        token_refresh.refresh_token, request, db
    )


@router.post(
    '/logout',
    status_code=status.HTTP_200_OK,
    summary="Выход из системы",
    responses={
        200: {"description": "Успешный выход"},
        401: {"description": "Не авторизован или неверный токен"}
    }
)
async def logout(
    request: Request,
    token_refresh: TokenRefresh,
    token_data=Depends(optional_security)
    # db: AsyncSession = Depends(get_session)
):
    """
    Выход пользователя из системы.

    Использует optional_security, который не вызывает автоматическую ошибку
    при отсутствии токена, но все равно требует валидный токен для выхода.
    """
    # Если токен не предоставлен или невалиден
    if token_data is None:
        # Проверяем заголовок Authorization вручную
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = auth_header.split(" ")[1].strip()
        # Проверяем черный список для токена из заголовка
        if await AuthService.is_token_blacklisted(access_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        # Токен уже проверен на валидность и черный список
        access_token = token_data.token

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await AuthService.logout(access_token, token_refresh.refresh_token)


@router.get(
    '/validate',
    response_model=TokenData,
    status_code=status.HTTP_200_OK,
    summary="Валидация токена",
    responses={
        200: {"description": "Токен валиден"},
        401: {"description": "Не авторизован или неверный токен"}
    }
)
async def validate_token(
    token_data: TokenData = Depends(security)
) -> TokenData:
    """
    Валидация access токена.
    Возвращает данные токена (user_id и token).
    """
    return token_data
