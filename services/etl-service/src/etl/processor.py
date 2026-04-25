import time
from datetime import datetime
from loguru import logger

from src.state import RedisStorage, State
from src.etl.extractor import PostgresExtractor
from src.etl.loader import ElasticsearchLoader
from src.etl.transformer import DataTransformer
from config.settings import config


class ETLProcessor:
    """Основной процессор ETL."""

    def __init__(self):
        self.state = None
        self.extractor = PostgresExtractor()
        self.transformer = DataTransformer()
        self.loader = ElasticsearchLoader()
        self.config = config.etl

    def initialize_state(self, redis_client):
        """Инициализировать состояние."""
        storage = RedisStorage(redis_client)
        self.state = State(storage)
        for table in ['film_work', 'person', 'genre']:
            if not self.state.get_state(f"{table}_modified"):
                self.state.set_state(
                    f"{table}_modified",  datetime.min.isoformat()
                )
                logger.info(f"Initialized state for {table}")

    def process_table(self, table: str, index_name: str):
        """Обработать изменения в таблице."""
        logger.info(f"Processing {table}")

        # Получить время последней модификации
        last_modified = self.state.get_state(f"{table}_modified")

        # Извлечь данные из Postgres
        extract_method = getattr(self.extractor, f"extract_{table}")
        raw_data = extract_method(last_modified)

        if not raw_data:
            logger.info(f"No new data for {table}")
            return

        # Трансформировать данные
        transformed_data = self.transformer.transform_batch(raw_data, f"{table}")
        logger.info(f"Transformed {len(transformed_data)} {table} records")

        # Загрузить данные в Elasticsearch
        self.loader.bulk_load(index_name, transformed_data)

        # Обновить состояние Redis
        if raw_data:
            latest_modified = max(
                item["modified"] for item in raw_data if item.get("modified")
            )
            self.state.set_state(
                f"{table}_modified", latest_modified.isoformat()
            )

        logger.info(f"Processed {len(raw_data)} {table} records")

    def process_all(self):
        """Обработать все таблицы."""
        logger.info("Starting ETL process")

        # Обработка фильмов (table, index)
        self.process_table('film_work', 'movies')

        # Обработка жанров (table, index)
        self.process_table('genre', 'genre')

        # Обработка персон (table, index)
        self.process_table('person', 'persons')

        logger.info("ETL process completed")

    def run(self, redis_client):
        """Запустить основной цикл ETL."""
        self.initialize_state(redis_client)

        # Создать индексы
        self.loader.create_index('movies')
        self.loader.create_index('persons')
        self.loader.create_index('genres')

        while True:
            try:
                self.process_all()
                logger.info(
                    f"Sleeping for {self.config.sleep_interval} sec..."
                )
                time.sleep(self.config.sleep_interval)
            except KeyboardInterrupt:
                logger.info("ETL process stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in ETL process: {e}")
                logger.info(f"Retry in {self.config.sleep_interval} sec...")
                time.sleep(self.config.sleep_interval)
