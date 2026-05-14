from opentelemetry import trace
from opentelemetry.trace import INVALID_SPAN, Status, StatusCode
from fastapi import Request
from loguru import logger

from core import config


async def tracing_middleware(request: Request, call_next):
    """
    Middleware для трассировки запросов с OpenTelemetry.
    """
    # Если трассировка отключена, пропускаем
    if not config.settings.enable_tracing:
        return await call_next(request)

    # Получаем или генерируем request_id
    request_id = getattr(request.state, 'request_id', None)
    if not request_id:
        request_id = request.headers.get('X-Request-Id')

    # Создаем span для запроса
    tracer = trace.get_tracer(__name__)
    span_name = f"{request.method} {request.url.path}"

    # Начинаем новый span как текущий
    with tracer.start_as_current_span(span_name) as span:
        # Устанавливаем базовые атрибуты
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.path", request.url.path)
        span.set_attribute("http.client_ip", request.client.host if request.client else "unknown")

        # Устанавливаем request_id атрибуты
        if request_id:
            span.set_attribute("http.request_id", request_id)
            span.set_attribute("http.request.header.x-request-id", request_id)
            logger.debug(f"Set request_id attribute on span: {request_id}")

        # Добавляем request_id в request.state для других middleware
        if not hasattr(request.state, 'request_id'):
            request.state.request_id = request_id

        try:
            # Обрабатываем запрос
            response = await call_next(request)

            # Добавляем информацию о response
            span.set_attribute("http.status_code", response.status_code)

            # Устанавливаем статус span на основе response
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
            elif response.status_code >= 400:
                span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
            else:
                span.set_status(Status(StatusCode.OK))

            # Добавляем request_id в response headers если его нет
            if request_id and 'X-Request-Id' not in response.headers:
                response.headers['X-Request-Id'] = request_id

            return response

        except Exception as e:
            # Логируем ошибку в span
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
