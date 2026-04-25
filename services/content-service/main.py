import uvicorn
from loguru import logger
from contextlib import asynccontextmanager
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis

from api.v1 import film, genre, person
from core import config
from db import elastic, redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager для управления жизненным циклом приложения.
    """
    # Подключаемся к Redis
    redis.redis = Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        decode_responses=True  # Рекомендуется для удобства работы
    )

    # Подключаемся к Elasticsearch
    elastic.es = AsyncElasticsearch(
        hosts=[f'{config.ELASTIC_SCHEMA}{config.ELASTIC_HOST}:{config.ELASTIC_PORT}'],
        verify_certs=False  # Отключаем проверку SSL для локального использования
    )

    # Проверяем подключения к базам данных
    try:
        # Проверяем подключение к Redis
        await redis.redis.ping()
        logger.info("✓ Successfully connected to Redis")

        # Проверяем подключение к Elasticsearch
        info = await elastic.es.info()
        logger.info(f"✓ Successfully connected to Elasticsearch v{info['version']['number']}")
    except Exception as e:
        logger.info(f"✗ Failed to connect to database: {e}")

    # Передаем управление приложению
    yield

    logger.info("Server shutdown")

    # Закрываем подключения к базам данных
    try:
        await redis.redis.close()
        logger.info("✓ Redis connection closed")
    except Exception as e:
        logger.info(f"✗ Error closing Redis connection: {e}")

    try:
        await elastic.es.close()
        logger.info("✓ Elasticsearch connection closed")
    except Exception as e:
        logger.info(f"✗ Error closing Elasticsearch connection: {e}")

app = FastAPI(
    title=config.PROJECT_NAME,
    description=config.PROJECT_DESCRIPTION,
    version=config.PROJECT_VERSION,
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)


app.include_router(film.router, prefix='/api/v1/film', tags=['Films'])
app.include_router(genre.router, prefix='/api/v1/genre', tags=['Genres'])
app.include_router(person.router, prefix='/api/v1/person', tags=['Persons'])


if __name__ == "__main__":
    logger.add(
        "logs/async_api.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO"
    )

    logger.info("Starting ASYNC_API Service")
    uvicorn.run(app, host="0.0.0.0", port=8000)
