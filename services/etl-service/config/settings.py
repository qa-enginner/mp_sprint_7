import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class PostgresConfig:
    host: str = os.getenv('POSTGRES_HOST')
    port: int = int(os.getenv('POSTGRES_PORT'))
    dbname: str = os.getenv('POSTGRES_DB')
    user: str = os.getenv('POSTGRES_USER')
    password: str = os.getenv('POSTGRES_PASSWORD')

    @property
    def dsn(self):
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.dbname}"
        )


@dataclass
class ElasticsearchConfig:
    host: str = os.getenv('ELASTIC_HOST')
    port: int = int(os.getenv('ELASTIC_PORT'))

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"


@dataclass
class RedisConfig:
    host: str = os.getenv('REDIS_HOST')
    port: int = int(os.getenv('REDIS_PORT'))
    db: int = int(os.getenv('REDIS_DB'))

    @property
    def dsn(self):
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class ETLConfig:
    batch_size: int = int(os.getenv('BATCH_SIZE'))
    sleep_interval: int = int(os.getenv('SLEEP_INTERVAL'))
    max_retries: int = int(os.getenv('MAX_RETRIES'))
    state_key: str = os.getenv('STATE_KEY')


@dataclass
class Config:
    postgres: PostgresConfig = PostgresConfig()
    elastic: ElasticsearchConfig = ElasticsearchConfig()
    redis: RedisConfig = RedisConfig()
    etl: ETLConfig = ETLConfig()


config = Config()
