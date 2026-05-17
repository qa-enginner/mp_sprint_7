from fastapi import APIRouter, Depends, Request, status, HTTPException

from core.security import optional_security
from core.dependencies import RequestContext, get_db_context
from schemas.entity import (
        UserCreate,
        UserInDB,
        UserLogin,
        TokenResponse,
        TokenRefresh,
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
    context: RequestContext = Depends(get_db_context)
) -> UserInDB:
    return await AuthService.create_user(user_create, context.db)


@router.post(
    '/login',
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password"
)
async def login(
    request: Request,
    login_data: UserLogin,
    context: RequestContext = Depends(get_db_context)
):
    """
    Authenticate user by email and password.

    Returns access and refresh tokens upon successful authentication.
    """
    return await AuthService.login(login_data, request, context.db)


@router.post(
    '/refresh',
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK
)
async def refresh(
    request: Request,
    token_refresh: TokenRefresh,
    context: RequestContext = Depends(get_db_context)
):
    return await AuthService.refresh_token(
        token_refresh.refresh_token, request, context.db
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
                detail="Token is blacklisted",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Проверяем refresh token
        if await AuthService.is_token_blacklisted(token_refresh.refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is blacklisted",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Добавляем оба токена в черный список
        await AuthService.blacklist_token(access_token)
        await AuthService.blacklist_token(token_refresh.refresh_token)
        return {"message": "Logged out successfully"}

    # Если токен предоставлен и валиден
    # Проверяем черный список для access token из token_data
    if await AuthService.is_token_blacklisted(token_data.token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is blacklisted",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Проверяем refresh token
    if await AuthService.is_token_blacklisted(token_refresh.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is blacklisted",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Добавляем оба токена в черный список
    await AuthService.blacklist_token(token_data.token)
    await AuthService.blacklist_token(token_refresh.refresh_token)
    return {"message": "Logged out successfully"}
