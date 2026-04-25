from functools import lru_cache
import json
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film, FilmList
from loguru import logger
from uuid import UUID

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


class FilmService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, film_id: str) -> Optional[Film]:
        film = await self._film_from_cache(film_id)
        if not film:
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await self._put_film_to_cache(film)

        return film

    async def get_all(
        self,
        sort_by: str = 'imdb_rating',
        sort_descending: bool = True,
        page_number: int = 1,
        page_size: int = 50,
        genre_id: Optional[UUID] = None
    ) -> list[FilmList]:

        sort_order = "desc" if sort_descending else "asc"

        films = await self._get_films_from_elastic(
            sort_by=sort_by,
            sort_order=sort_order,
            page=page_number,
            size=page_size,
            genre_id=genre_id
        )
        return films

    async def search_films(
        self,
        query: str,
        page_number: int = 1,
        page_size: int = 50
    ) -> list[FilmList]:
        # Генерируем ключ для кэша на основе параметров поиска
        cache_key = f"search_films:{query}:page_{page_number}:size_{page_size}"

        # Пытаемся получить результаты из кэша
        cached_films = await self._get_search_films_from_cache(cache_key)
        if cached_films is not None:
            return cached_films

        # Если в кэше нет, получаем из Elasticsearch
        search_result = await self._search_films_in_elasticsearch(
            query=query,
            page_number=page_number,
            page_size=page_size
        )

        # Сохраняем результаты в кэш
        await self._put_search_films_to_cache(cache_key, search_result)

        return search_result

    async def _get_film_from_elastic(self, film_id: str) -> Optional[Film]:
        try:
            doc = await self.elastic.get(index='movies', id=film_id)
        except NotFoundError:
            return None

        source = doc['_source']

        # Получаем UUID жанров из индекса genre по названиям
        genre_objects = await self._get_genre_objects(source.get('genres', []))

        # Преобразуем актеров
        actors = self._convert_persons(source.get('actors', []))

        # Преобразуем сценаристов
        writers = self._convert_persons(source.get('writers', []))

        # Преобразуем режиссеров
        directors = self._convert_persons(source.get('directors', []))

        film_data = {
            'uuid': doc['_id'],
            'title': source.get('title', ''),
            'imdb_rating': source.get('imdb_rating', 0.0),
            'description': source.get('description') or '',
            'genres': genre_objects,
            'actors': actors,
            'writers': writers,
            'directors': directors
        }

        return Film(**film_data)

    def _convert_persons(self, persons_list):
        """Преобразует список персон из формата Elasticsearch
        в нужный формат"""
        converted_persons = []
        for person in persons_list:
            converted_persons.append({
                'uuid': person.get('id', ''),
                'full_name': person.get('name', '')
            })
        return converted_persons

    async def _get_genre_objects(self, genre_names):
        """Преобразует названия жанров в объекты с UUID и name"""
        if not genre_names:
            return []

        genre_objects = []

        # Ищем жанры по названию в индексе genre
        for genre_name in genre_names:
            try:
                # Поиск жанра по названию
                search_result = await self.elastic.search(
                    index='genre',
                    body={
                        "query": {
                            "term": {
                                "name.keyword": genre_name
                            }
                        },
                        "size": 1
                    }
                )

                genre_doc = search_result['hits']['hits'][0]
                genre_objects.append({
                        'uuid': genre_doc['_id'],
                        'name': genre_doc['_source']['name']
                    })

            except Exception as e:
                logger.error(f"Error searching for genre '{genre_name}': {e}")
                continue

        return genre_objects

    async def _get_films_from_elastic(
            self,
            sort_by: str,
            sort_order: str,
            page: int,
            size: int,
            genre_id: Optional[UUID] = None
    ) -> list[FilmList]:
        """
        Получить фильмы из Elasticsearch с пагинацией и сортировкой.
        """
        # Если указан genre_id, получаем название жанра
        if genre_id:
            try:
                doc = await self.elastic.get(index='genre', id=str(genre_id))
                genre_name = doc['_source'].get('name')
            except Exception as e:
                logger.error(f"Error getting genre {genre_id}: {e}")
                genre_name = None
        else:
            genre_name = None

        # Формируем запрос в зависимости от наличия жанра
        if genre_name:
            query = {
                "terms": {
                    "genres": [genre_name]
                }
            }
        else:
            query = {"match_all": {}}

        body = {
            "sort": [
                {sort_by: {"order": sort_order}}
            ],
            "from": (page - 1) * size,
            "size": size,
            "query": query,
            "_source": ["id", "title", "imdb_rating"]
        }

        try:
            docs = await self.elastic.search(index="movies", body=body)
        except Exception as e:
            logger.error(f"Error searching films in Elasticsearch: {e}")
            return []

        films = []
        for doc in docs['hits']['hits']:
            try:
                # Преобразуем данные для FilmList
                source = doc['_source']
                film = FilmList(
                    uuid=source.get('id', str(doc['_id'])),
                    title=source.get('title', ''),
                    imdb_rating=source.get('imdb_rating', 0.0)
                )
                films.append(film)
            except Exception as e:
                logger.error(f"Error parsing film data: {e}")
                continue

        return films

    async def _search_films_in_elasticsearch(
        self,
        query: str,
        page_number: int = 1,
        page_size: int = 50
    ) -> list[FilmList]:
        search_result = await self.elastic.search(
            index="movies",
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title", "description"]
                    }
                },
                "from": (page_number - 1) * page_size,
                "size": page_size
            }
        )

        films = []
        for doc in search_result['hits']['hits']:
            source = doc['_source']
            film = FilmList(
                uuid=doc['_id'],  # Используем ID из Elasticsearch
                title=source.get('title', ''),
                imdb_rating=source.get('imdb_rating', 0.0)
            )
            films.append(film)

        return films

    async def _film_from_cache(self, film_id: str) -> Optional[Film]:
        data = await self.redis.get(film_id)
        if not data:
            return None
        film = Film.parse_raw(data)
        return film

    async def _put_film_to_cache(self, film: Film):
        logger.info(f"Put film {film.uuid} to cache")
        await self.redis.set(
            str(film.uuid),
            film.json(),
            FILM_CACHE_EXPIRE_IN_SECONDS
        )

    async def _get_search_films_from_cache(
        self,
        cache_key: str
    ) -> Optional[list[FilmList]]:
        """Получает список фильмов из кэша Redis по ключу поиска."""
        try:
            data = await self.redis.get(cache_key)
            if data:
                # Десериализуем JSON строку в список словарей
                films_data = json.loads(data)
                # Создаем список объектов FilmList из данных
                films = [FilmList(**film_data) for film_data in films_data]
                return films
        except Exception as e:
            logger.warning(
                f"Error getting search films from cache {cache_key}: {e}"
            )
        return None

    async def _put_search_films_to_cache(
        self,
        cache_key: str,
        films: list[FilmList]
    ):
        """Сохраняет список фильмов в кэш Redis по ключу поиска."""
        try:
            # Сериализуем список объектов FilmList в JSON строку
            films_json = json.dumps([film.dict() for film in films], cls=UUIDEncoder)
            await self.redis.setex(
                cache_key,
                FILM_CACHE_EXPIRE_IN_SECONDS,
                films_json
            )
            logger.info(
                f"Cached {len(films)} search films with key {cache_key}"
            )
        except Exception as e:
            logger.warning(f"Error caching search films {cache_key}: {e}")


@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(redis, elastic)
