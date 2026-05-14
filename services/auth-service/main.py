import uvicorn
from loguru import logger
from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.asyncio import Redis

from api.v1 import auth, users, oauth
from core import config
from core.middleware import logging_middleware
from core.rate_limit_middleware import rate_limit_middleware
from core.request_id_middleware import request_id_middleware
from core.tracing import instrument_app
from core.tracing_middleware import tracing_middleware
from core.cors import setup_cors
from db import redis_db
from db.postgres import create_database, wait_for_postgres


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager для управления жизненным циклом приложения.
    """
    # Подключаемся к Redis
    redis_db.redis = Redis(
        host=config.settings.redis_host,
        port=config.settings.redis_port,
        db=0,
        decode_responses=True
    )

    # Проверяем подключения к базам данных
    try:
        # Проверяем подключение к Redis
        await redis_db.redis.ping()
        logger.info("✓ Successfully connected to Redis")
    except Exception as e:
        logger.error(f"✗ Failed to connect to Redis: {e}")

    # Ожидаем доступности PostgreSQL
    if not await wait_for_postgres():
        logger.error("✗ PostgreSQL is not available. Exiting.")
        raise Exception("PostgreSQL is not available")

    # Создаем таблицы в базе данных
    try:
        await create_database()
        logger.info("✓ Database tables created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create database tables: {e}")

    # Настраиваем логирование
    logger.add(
        "logs/async_api.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO"
    )
    logger.info("Starting ASYNC_API Service")

    # Передаем управление приложению
    yield

    logger.info("Server shutdown")

    # Закрываем подключения к базам данных
    try:
        await redis_db.redis.close()
        logger.info("✓ Redis connection closed")
    except Exception as e:
        logger.error(f"✗ Error closing Redis connection: {e}")


app = FastAPI(
    title=config.settings.project_name,
    description=config.settings.project_description,
    version=config.settings.project_version,
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    lifespan=lifespan,
)

# Instrument application for tracing
logger.debug(f"enable_tracing = {config.settings.enable_tracing}")
instrument_app(app)

# Setup CORS middleware
setup_cors(app)

app.middleware('http')(tracing_middleware)
app.middleware('http')(request_id_middleware)
app.middleware('http')(rate_limit_middleware)
app.middleware('http')(logging_middleware)


app.include_router(auth.router, prefix='/api/v1/auth', tags=['Auth'])
app.include_router(users.router, prefix='/api/v1/users', tags=['Users'])
app.include_router(oauth.router, prefix='/api/v1/oauth', tags=['OAuth'])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
