import datetime
from typing import Callable, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from core.config import settings
from core.security import decode_token
from db.redis_db import get_redis


async def rate_limit_middleware(
    request: Request, call_next: Callable
) -> Response:
    """
    Middleware для ограничения количества запросов (rate limiting)
    на основе Redis.
    Использует идентификатор пользователя (если аутентифицирован) или IP-адрес.
    Лимит: REQUEST_LIMIT_PER_MINUTE запросов в минуту.
    """
    # Получаем подключение к Redis
    redis: Optional[Redis] = await get_redis()
    if redis is None:
        # Если Redis недоступен, пропускаем ограничение
        return await call_next(request)

    # Определяем идентификатор для ограничения
    identifier = await _get_identifier(request)
    # Ключ с точностью до минуты в формате ГГГГММДДЧЧММ
    now = datetime.datetime.now()
    key = f'{identifier}:{now.strftime("%Y%m%d%H%M")}'

    # Создаем pipeline для атомарности
    pipe = redis.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, 120)  # TTL 120 секунд для автоматической очистки старых ключей
    result = await pipe.execute()

    # Результат incr находится по индексу 0
    request_count = result[0]

    # Лимит из настроек (по умолчанию 20)
    limit = getattr(settings, 'request_limit_per_minute', 20)
    if request_count > limit:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={'detail': 'Too many requests'}
        )

    # Продолжаем обработку запроса
    return await call_next(request)


async def _get_identifier(request: Request) -> str:
    """
    Возвращает идентификатор для rate limiting.
    Составной ключ: user_id из токена и IP-адрес.
    Всегда включает оба компонента.
    Если пользователь аутентифицирован, использует user_id из токена,
    иначе 'unknown'.
    """
    client_ip = request.client.host if request.client else 'unknown'

    # Пытаемся получить токен из заголовка Authorization
    user_id = 'unknown'
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
        decoded = decode_token(token)
        if decoded and "sub" in decoded:
            user_id = decoded["sub"]

    return f'user:{user_id}:ip:{client_ip}'
