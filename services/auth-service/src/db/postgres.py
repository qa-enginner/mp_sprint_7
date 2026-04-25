from typing import AsyncGenerator
import asyncio
from core.config import settings
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from loguru import logger


Base = declarative_base()


def get_postgres_dsn() -> str:
    """Возвращает DSN строку подключения к PostgreSQL."""
    return (
        f'postgresql+asyncpg://'
        f'{settings.postgres_user}:'
        f'{settings.postgres_password}@'
        f'{settings.postgres_host}:'
        f'{settings.postgres_port}/'
        f'{settings.postgres_db}'
    )


async def wait_for_postgres(retries: int = 5, delay: int = 2) -> bool:
    """
    Ожидает доступности PostgreSQL сервера.

    Args:
        retries: Количество попыток подключения
        delay: Задержка между попытками в секундах

    Returns:
        bool: True если подключение успешно, False в противном случае
    """
    dsn = get_postgres_dsn()

    for attempt in range(retries):
        try:
            from sqlalchemy import text
            engine = create_async_engine(dsn, echo=False, future=True)
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            logger.info("✓ Successfully connected to PostgreSQL")
            return True
        except Exception as e:
            logger.warning(f"✗ Attempt {attempt + 1}/{retries} failed: "
                           f"{str(e)}")
            # Дополнительная информация об ошибке
            logger.debug(f"Error details: {type(e).__name__}: {str(e)}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)

    logger.error("✗ Failed to connect to PostgreSQL after all attempts")
    return False


def get_engine():
    """Создаёт и возвращает движок SQLAlchemy."""
    dsn = get_postgres_dsn()
    return create_async_engine(dsn, echo=True, future=True)


engine = get_engine()
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def create_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def purge_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Функция понадобится при внедрении зависимостей
# Dependency
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
