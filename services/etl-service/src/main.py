import redis
from loguru import logger
from config.settings import config
from src.etl.processor import ETLProcessor


def main():
    """Точка входа в приложение."""
    # Настройка логгера
    logger.add(
        "logs/etl.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO"
    )

    logger.info("Starting ETL Service")

    # Подключение к Redis
    try:
        redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            decode_responses=False
        )
        redis_client.ping()
        logger.info("Connected to Redis")
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return

    # Запуск ETL процессора
    processor = ETLProcessor()
    processor.run(redis_client)


if __name__ == "__main__":
    main()
