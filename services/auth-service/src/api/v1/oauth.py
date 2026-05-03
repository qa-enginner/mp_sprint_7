from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from core.oauth_factory import OAuthProviderFactory
from db import redis_db
from db.postgres import get_session
from services.auth_service import AuthService
from services.user_service import UserService
import secrets
from datetime import datetime
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

    # Сохраняем токен обновления в Redis
    if redis_db.redis:
        key = f"{user.id}_refresh"
        # Вычисляем TTL в секундах
        ttl = int((expire - datetime.utcnow()).total_seconds())
        await redis_db.redis.setex(key, ttl, refresh_token)

    await AuthService.save_login_history(user.id, request, db)

    # 6. Возвращаем JSON с токенами
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


@router.get("/{provider}/callback")
async def oauth_callback_with_provider(
    provider: str,
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_session)
):
    """
    Callback URL с указанием провайдера в пути.
    Обрабатывает код авторизации и создает/авторизует пользователя.
    """
    return await _process_oauth_callback(provider, code, state, request, db)
