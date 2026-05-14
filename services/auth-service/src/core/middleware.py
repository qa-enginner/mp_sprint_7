import time
from typing import Callable, Dict
from fastapi import Request, Response
from loguru import logger


def filter_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Фильтрует чувствительные заголовки, заменяя их значения на '***'.
    """
    sensitive_headers = {
        'authorization',
        'cookie',
        'set-cookie',
        'proxy-authorization',
        'x-api-key',
        'x-auth-token',
        'access-token',
        'refresh-token',
    }
    
    filtered = {}
    for key, value in headers.items():
        lower_key = key.lower()
        if lower_key in sensitive_headers:
            filtered[key] = '***'
        else:
            filtered[key] = value
    return filtered


def get_headers_dict(request: Request) -> Dict[str, str]:
    """
    Преобразует заголовки запроса в словарь.
    """
    headers = {}
    for key, value in request.headers.items():
        headers[key] = value
    return headers


async def logging_middleware(
    request: Request, call_next: Callable
) -> Response:
    """
    Middleware для логирования HTTP-запросов и ответов.
    """
    start_time = time.time()

    # Получаем и фильтруем заголовки
    request_headers = get_headers_dict(request)
    filtered_headers = filter_sensitive_headers(request_headers)

    # Логируем входящий запрос с заголовками
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"query={dict(request.query_params)} "
        f"client={request.client.host if request.client else 'unknown'} "
        f"headers={filtered_headers}"
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
