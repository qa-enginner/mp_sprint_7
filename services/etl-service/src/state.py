import json
import abc
from typing import Any, Dict
from json import JSONDecodeError
from redis import Redis, RedisError
from loguru import logger
from config.settings import config


class BaseStorage(abc.ABC):
    """Абстрактное хранилище состояния.

    Позволяет сохранять и получать состояние.
    Способ хранения состояния может варьироваться в зависимости
    от итоговой реализации. Например, можно хранить информацию
    в базе данных или в распределённом файловом хранилище.
    """

    @abc.abstractmethod
    def save_state(self, state: Dict[str, Any]) -> None:
        """Сохранить состояние в хранилище."""

    @abc.abstractmethod
    def retrieve_state(self) -> Dict[str, Any]:
        """Получить состояние из хранилища."""


class RedisStorage(BaseStorage):
    """Хранилище состояния в Redis."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.state_key = config.etl.state_key

    def save_state(self, state: Dict[str, Any]) -> None:
        """Сохранить состояние в Redis."""
        try:
            self.redis.set(self.state_key, json.dumps(state))
        except RedisError as e:
            logger.error(f"Failed to save state to Redis: {e}")
            raise

    def retrieve_state(self) -> Dict[str, Any]:
        """Получить состояние из Redis."""
        try:
            data = self.redis.get(self.state_key)
            if data:
                return json.loads(data)
            return {}
        except (JSONDecodeError, RedisError) as e:
            logger.error(f"Failed to retrieve state from Redis: {e}")
            return {}


class State:
    """Класс для работы с состояниями."""

    def __init__(self, storage: BaseStorage) -> None:
        self.storage = storage

    def set_state(self, key: str, value: Any) -> None:
        """Установить состояние для определённого ключа."""
        state = self.storage.retrieve_state()
        state[key] = value
        self.storage.save_state(state)

    def get_state(self, key: str) -> Any:
        """Получить состояние по определённому ключу."""
        state = self.storage.retrieve_state()
        return state.get(key)
