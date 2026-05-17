from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from core.oauth_factory import OAuthProviderFactory
from db import redis_db
from core.dependencies import get_db_context
from services.auth_service import AuthService
from services.user_service import UserService
import secrets
from loguru import logger

router = APIRouter()


@router.get("/auth-url")
async def get_auth_url(request: Request, provider: str = "yandex"):
    """
    Возвращает URL для редиректа на страницу авторизации соцсети.
    Используется фронтендом для перенаправления пользователя.
    По умолчанию используется провайдер yandex.
    """
    try:
        oauth_provider = OAuthProviderFactory.get_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Генерируем state для защиты от CSRF
    state = secrets.token_urlsafe(32)

    # Сохраняем state в Redis или сессии
    if redis_db.redis:
        await redis_db.redis.setex(f"oauth_state:{state}", 600, provider)
    else:
        logger.warning("Redis not available, state will not be validated")

    auth_url = oauth_provider.get_auth_url(state)
    return {"auth_url": auth_url, "state": state}


async def _process_oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    db: AsyncSession
):
    """
    Общая логика обработки OAuth callback.
    """
    # 1. Проверяем state (защита от CSRF)
    saved_state = None
    if redis_db.redis:
        saved_state = await redis_db.redis.get(f"oauth_state:{state}")
        logger.debug(f"State from Redis: {saved_state}, provider: {provider}")
    else:
        logger.warning("Redis connection not available")
    if not saved_state or saved_state != provider:
        logger.warning(
            f"Invalid state: saved={saved_state}, expected={provider}"
        )
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # 2. Получаем access_token
    oauth_provider = OAuthProviderFactory.get_provider(provider)
    token_data = await oauth_provider.get_token(code)

    if "access_token" not in token_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to get access token"
        )

    # 3. Получаем информацию о пользователе
    user_info = await oauth_provider.get_user_info(token_data["access_token"])
    logger.debug(f"User info from provider: {user_info}")

    # Проверяем наличие обязательного поля id
    if not user_info.get("id"):
        logger.error(
            f"Provider {provider} returned user info without id: {user_info}"
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid user info from provider"
        )

    # 4. Ищем или создаем пользователя в БД
    user = await UserService.find_or_create_user_by_social(
        provider=provider,
        provider_user_id=user_info.get("id"),
        email=user_info.get("email"),
        name=user_info.get("name") or user_info.get("login"),
        avatar_url=user_info.get("avatar_url") or user_info.get("picture"),
        db=db
    )
    logger.info(f"User {user.id} authenticated via {provider}")

    # 5. Генерируем токены для нашего auth-сервиса
    access_token = AuthService.create_access_token(user.id)
    refresh_token, expire = AuthService.create_refresh_token(user.id)

    # 6. Сохраняем refresh token в БД
    await AuthService.save_refresh_token(
        user_id=user.id,
        refresh_token=refresh_token,
        user_agent=request.headers.get("User-Agent", ""),
        ip_address=request.client.host if request.client else None,
        db=db
    )

    # 7. Удаляем использованный state из Redis
    if redis_db.redis:
        await redis_db.redis.delete(f"oauth_state:{state}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expire,
        "user": user
    }


@router.get("/callback")
async def oauth_callback(
    request: Request,
    provider: str,
    code: str,
    state: str,
    context=Depends(get_db_context)
):
    """
    Callback endpoint для OAuth провайдеров.
    """
    return await _process_oauth_callback(
        provider=provider,
        code=code,
        state=state,
        request=request,
        db=context.db
    )
