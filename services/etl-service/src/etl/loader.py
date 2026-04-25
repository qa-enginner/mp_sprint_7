import backoff
from elasticsearch import Elasticsearch, helpers
from typing import List, Dict
from loguru import logger
from config.settings import config
from config.elastic_settings import ELASTIC_SETTINGS, ELASTIC_INDICES


class ElasticsearchLoader:
    """Класс для загрузки данных в Elasticsearch."""

    def __init__(self):
        self.config = config.elastic
        self.es = None

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=config.etl.max_retries
    )
    def connect(self):
        """Установить соединение с Elasticsearch."""
        if not self.es:
            self.es = Elasticsearch(
                hosts=[self.config.url],
                verify_certs=False,
                request_timeout=30
            )
            if not self.es.ping():
                raise ConnectionError("Cannot connect to Elasticsearch")
        return self.es

    def create_index(self, index_name: str):
        """Создать индекс с настройками."""

        es = self.connect()
        if not es.indices.exists(index=index_name):
            body = {
                    'settings': ELASTIC_SETTINGS,
                    'mappings': {
                        'dynamic': 'strict',
                        'properties': ELASTIC_INDICES[index_name],
                    },
                }
            es.indices.create(index=index_name, body=body)
            logger.info(f"Index {index_name} created")

    def bulk_load(self, index_name: str, data: List[Dict]):
        """Массовая загрузка данных в Elasticsearch."""
        es = self.connect()

        actions = [
            {
                "_index": index_name,
                "_id": doc["id"],
                "_source": doc
            }
            for doc in data
        ]

        try:
            success, failed = helpers.bulk(
                es,
                actions,
                stats_only=True
            )
            logger.info(f"Loaded {success} documents to {index_name}")
            if failed:
                logger.error(f"Failed to load {failed} documents")
            return success, failed
        except Exception as e:
            logger.error(f"Bulk load failed: {e}")
            raise
