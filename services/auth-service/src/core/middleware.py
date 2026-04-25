import time
from typing import Callable
from fastapi import Request, Response
from loguru import logger


async def logging_middleware(
    request: Request, call_next: Callable
) -> Response:
    """
    Middleware для логирования HTTP-запросов и ответов.
    """
    start_time = time.time()
    
    # Логируем входящий запрос
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"query={dict(request.query_params)} "
        f"client={request.client.host if request.client else 'unknown'}"
    )
    
    # Обрабатываем запрос
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request error: {e}")
        raise
    
    # Логируем ответ
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"status={response.status_code} "
        f"duration={process_time:.2f}ms"
    )
    
    return response