from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource, ResourceAttributes
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from loguru import logger

from core import config


def configure_tracer() -> None:
    """Настраивает трассировку OpenTelemetry с экспортом в Jaeger."""
    logger.debug(
        "configure_tracer called, enable_tracing="
        f"{config.settings.enable_tracing}"
    )
    if not config.settings.enable_tracing:
        logger.info("Tracing is disabled via ENABLE_TRACING")
        return

    # Создаем ресурс с именем сервиса
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: config.settings.project_name,
    })
    trace.set_tracer_provider(TracerProvider(resource=resource))
    logger.debug("TracerProvider set")

    # Определяем, использовать ли коллектор или агент
    collector_endpoint = config.settings.jaeger_collector_endpoint
    if collector_endpoint and collector_endpoint.startswith("http"):
        # Используем HTTP коллектор
        jaeger_exporter = JaegerExporter(
            collector_endpoint=collector_endpoint,
        )
        logger.info(
            f"Jaeger tracing configured via collector endpoint: "
            f"{collector_endpoint}"
        )
    else:
        # Используем UDP агент
        jaeger_exporter = JaegerExporter(
            agent_host_name=config.settings.jaeger_agent_host,
            agent_port=config.settings.jaeger_agent_port,
        )
        logger.info(
            f"Jaeger tracing configured to agent "
            f"{config.settings.jaeger_agent_host}:"
            f"{config.settings.jaeger_agent_port}"
        )

    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

    # Чтобы видеть трейсы в консоли (для отладки)
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(ConsoleSpanExporter())
    )


def instrument_app(app: FastAPI) -> None:
    """Инструментирует приложение FastAPI для трейсинга."""
    logger.debug(
        "instrument_app called, enable_tracing="
        f"{config.settings.enable_tracing}"
    )
    if not config.settings.enable_tracing:
        logger.info("Skipping FastAPI instrumentation (tracing disabled)")
        return

    configure_tracer()
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI application instrumented for tracing")
