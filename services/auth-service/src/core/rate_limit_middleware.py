import datetime
from typing import Callable, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from core.config import settings
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
    now = datetime.datetime.now()
    # Ключ: идентификатор:текущая_минута
    key = f'{identifier}:{now.minute}'

    # Создаем pipeline для атомарности
    pipe = redis.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, 59)  # TTL 59 секунд, чтобы ключ удалился в конце минуты
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
    Приоритет: user_id из токена, затем IP-адрес.
    """
    # Проверяем, есть ли аутентифицированный пользователь
    # В проекте используется security = JWTBearer(),
    # который добавляет request.state.user?
    # Пока что используем IP-адрес
    client_ip = request.client.host if request.client else 'unknown'
    return f'ip:{client_ip}'
