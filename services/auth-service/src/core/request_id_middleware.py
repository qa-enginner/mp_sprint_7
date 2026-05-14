import uuid
from typing import Callable
from fastapi import Request, Response
from loguru import logger
from opentelemetry import trace
from opentelemetry.trace import INVALID_SPAN


async def request_id_middleware(
    request: Request, call_next: Callable
) -> Response:
    """
    Middleware для добавления уникального идентификатора запроса
    (X-Request-Id). Если заголовок X-Request-Id отсутствует,
    генерирует новый UUID. Добавляет request_id в состояние запроса
    (request.state) и в заголовок ответа.
    """
    # Получаем request_id из заголовка
    request_id = request.headers.get('X-Request-Id')

    if not request_id:
        request_id = str(uuid.uuid4())
        logger.debug(
            f"Generated new Request-ID for {request.method} "
            f"{request.url.path}: {request_id}"
        )
    else:
        logger.debug(f"Using existing Request-ID: {request_id}")

    # Сохраняем request_id в состоянии запроса для использования
    # в других middleware и обработчиках
    request.state.request_id = request_id

    # Пытаемся добавить request_id в атрибуты текущего спана OpenTelemetry
    current_span = trace.get_current_span()
    if current_span is not None and current_span != INVALID_SPAN:
        current_span.set_attribute('http.request_id', request_id)
        current_span.set_attribute(
            'http.request.header.x-request-id', request_id
        )
        logger.debug(
            f"Set request_id attribute on span: {request_id}"
        )
    else:
        logger.debug(
            f"Request ID {request_id} but no active span in "
            "request_id_middleware"
        )

    # Продолжаем обработку запроса
    response = await call_next(request)

    # Добавляем request_id в заголовок ответа
    response.headers['X-Request-Id'] = request_id

    return response
