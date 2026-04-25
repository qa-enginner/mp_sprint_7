from functools import lru_cache
from typing import Optional, List, Dict, Any

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.genre import Genre
from loguru import logger


class GenreService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_all_genres(self) -> List[Genre]:

        # Получаем из Elasticsearch
        genres = await self._get_genres_from_elastic()

        return genres

    async def get_genre_by_id(self, genre_id: str) -> Optional[Genre]:
        """
        Получить жанр по ID.
        """
        genre = await self._get_genre_from_elastic(genre_id)
        if not genre:
            return None

        return genre

    async def _get_genres_from_elastic(self) -> List[Genre]:
        """
        Получить список жанров из Elasticsearch.
        """

        search_result = await self.elastic.search(
                index='genre',
                body={
                    "query": {"match_all": {}},
                    "_source": ["name"]
                }
            )

        return self._parse_genres_list(search_result)

    def _parse_genres_list(self, search_result: Dict[str, Any]) -> List[Genre]:
        """
        Парсинг списка жанров из результата поиска.
        """
        genres = []
        for doc in search_result['hits']['hits']:
            try:
                source = doc['_source']
                genre = Genre(
                    uuid=doc['_id'],
                    name=source.get('name', '')
                )
                genres.append(genre)
            except Exception as e:
                logger.error(f"Error parsing genre data: {e}")
                continue

        return genres

    async def _get_genre_from_elastic(self, genre_id: str) -> Optional[Genre]:
        """
        Получить жанр из Elasticsearch.
        """
        try:
            doc = await self.elastic.get(
                index='genre',
                id=genre_id,
                _source_includes='name'
            )
        except NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error getting genre {genre_id}: {e}")
            return None

        return self._parse_genre_document(doc)

    def _parse_genre_document(self, doc: Dict[str, Any]) -> Genre:
        """
        Парсинг документа жанра из Elasticsearch.
        """
        source = doc['_source']

        genre_data = {
            'uuid': doc['_id'],
            'name': source.get('name', '')
        }

        return Genre(**genre_data)


@lru_cache()
def get_genre_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    return GenreService(redis, elastic)
