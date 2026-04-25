from functools import lru_cache
from typing import List, Optional, Dict, Any
import json
from loguru import logger
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.person import Person, PersonFilm, PersonFilmRole, PersonRole


FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5


class PersonService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_persons_films(self, person_id: str) -> List[PersonFilm]:
        """
        Получить все фильмы, в которых участвовала персона.
        """
        # Ключ кэша для фильмов персоны
        cache_key = f"person_films:{person_id}"

        # Пытаемся получить из кэша
        films = await self._get_persons_films_from_cache(cache_key)
        if films:
            return films

        # Получаем из Elasticsearch
        films = await self._get_person_films_from_elastic(person_id)

        # Сохраняем в кэш
        await self._put_persons_films_to_cache(cache_key, films)
        return films

    async def get_person_by_id(self, person_id: str) -> Optional[Person]:
        """
        Получить персону по ID.
        """

        try:
            person_info = await self._get_person_info(person_id)
            if not person_info:
                logger.warning(f"Person {person_id} not found")
                return None

            films_with_roles = await self._get_person_films_with_roles(person_id, person_info['name'])

            person = Person(
                uuid=UUID(person_id),
                full_name=person_info['name'],
                films=films_with_roles
            )

            return person

        except Exception as e:
            logger.error(f"Error getting person {person_id}: {str(e)}")
            return None

    async def search_persons_with_films(
        self,
        query: str,
        page_number: int = 1,
        page_size: int = 50
    ) -> List[Person]:
        """
        Поиск персон по имени с загрузкой фильмов для каждого результата.
        """
        try:
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["full_name^3", "name^2"],
                        "fuzziness": "AUTO"
                    }
                },
                "from": (page_number - 1) * page_size,
                "size": page_size,
                "_source": ["id", "full_name", "name"]
            }

            search_result = await self.elastic.search(
                index='persons',
                body=search_body
            )

            logger.info(f"Search result: {search_result}")

            persons = []
            for hit in search_result['hits']['hits']:
                try:
                    person_id = hit['_id']
                    logger.info(f"Person ID: {person_id}")

                    if person_id:
                        person = await self.get_person_by_id(str(person_id))
                        logger.debug(person)
                        if person:
                            persons.append(person)
                except Exception as e:
                    logger.error(f"Error parsing person from search: {e}")
                    continue

            return persons

        except Exception as e:
            logger.error(f"Error searching persons: {e}")
        return []

    async def _get_person_films_from_elastic(
        self, person_id: str
    ) -> List[PersonFilm]:
        """
        Получить фильмы персоны из Elasticsearch.
        Используем агрегацию по всем индексам фильмов.
        """
        try:
            # Получаем информацию о персоне
            person_doc = await self.elastic.get(
                index='persons',
                id=person_id,
                _source_includes=['full_name']
            )
            person_name = person_doc['_source']['full_name']
        except Exception as e:
            logger.error(f"Error getting person name {person_id}: {e}")
            return []

        try:
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "nested": {
                                    "path": "actors",
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {"term": {"actors.id": person_id}},
                                                {"match_phrase": {"actors.name": person_name}}
                                            ]
                                        }
                                    }
                                }
                            },
                            {
                                "nested": {
                                    "path": "writers",
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {"term": {"writers.id": person_id}},
                                                {"match_phrase": {"writers.name": person_name}}
                                            ]
                                        }
                                    }
                                }
                            },
                            {
                                "nested": {
                                    "path": "directors",
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {"term": {"directors.id": person_id}},
                                                {"match_phrase": {"directors.name": person_name}}
                                            ]
                                        }
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "sort": [
                    {"imdb_rating": {"order": "desc"}}
                ],
                "size": 1000,
                "_source": ["id", "title", "imdb_rating", "actors", "writers", "directors"]
            }

            search_result = await self.elastic.search(
                index='movies',
                body=search_body
            )

        except Exception as e:
            logger.error(f"Error searching films for person {person_id}: {e}")
            return []

        films = []
        for doc in search_result['hits']['hits']:
            try:
                source = doc['_source']
                film_id = source.get('id', str(doc['_id']))

                film = PersonFilm(
                    uuid=UUID(film_id),
                    title=source.get('title', ''),
                    imdb_rating=source.get('imdb_rating', 0.0)
                )
                films.append(film)
            except Exception as e:
                logger.error(f"Error parsing film for person {person_id}: {e}")
                continue

        return films

    async def _get_person_films_with_roles(self, person_id: str, person_name: str) -> List[PersonFilmRole]:
        """
        Получает фильмы персоны с определением всех ролей.
        """
        try:
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "nested": {
                                    "path": "actors",
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {"term": {"actors.id": person_id}},
                                                {"match_phrase": {"actors.name": person_name}}
                                            ]
                                        }
                                    }
                                }
                            },
                            {
                                "nested": {
                                    "path": "writers",
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {"term": {"writers.id": person_id}},
                                                {"match_phrase": {"writers.name": person_name}}
                                            ]
                                        }
                                    }
                                }
                            },
                            {
                                "nested": {
                                    "path": "directors",
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {"term": {"directors.id": person_id}},
                                                {"match_phrase": {"directors.name": person_name}}
                                            ]
                                        }
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": 1000,
                "_source": ["id", "actors", "writers", "directors"]
            }

            search_result = await self.elastic.search(
                index='movies',
                body=search_body
            )

            films_with_roles = []
            films_seen = set()  # Для дедупликации

            for hit in search_result['hits']['hits']:
                try:
                    film_id = hit['_source'].get('id', hit['_id'])

                    # Пропускаем дубликаты
                    if film_id in films_seen:
                        continue
                    films_seen.add(film_id)

                    roles = self._determine_roles_for_film(
                        hit['_source'],
                        person_id,
                        person_name
                    )

                    if roles:
                        film_role = PersonFilmRole(
                            uuid=UUID(film_id),
                            roles=roles
                        )
                        films_with_roles.append(film_role)

                        logger.debug(f"Found film {film_id} with roles: {[r.value for r in roles]}")

                except Exception as e:
                    logger.error(f"Error processing film hit: {str(e)}")
                    continue

            logger.info(f"Found {len(films_with_roles)} films for person {person_id}")
            return films_with_roles

        except Exception as e:
            logger.error(f"Error getting films with roles for {person_id}: {str(e)}")
            return []

    async def _search_persons_simple(
        self,
        query: str,
        page_number: int = 1,
        page_size: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Простой поиск персон (только ID и имя).
        """
        try:
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["full_name^3", "name^2"],
                        "fuzziness": "AUTO",
                        "operator": "and"
                    }
                },
                "from": (page_number - 1) * page_size,
                "size": page_size,
                "_source": ["full_name", "name"]
            }

            search_result = await self.elastic.search(
                index='persons',
                body=search_body
            )

            persons = []
            for hit in search_result['hits']['hits']:
                try:
                    source = hit['_source']
                    name = source.get('full_name') or source.get('name')

                    if name:
                        persons.append({
                            'id': hit['_id'],
                            'name': name,
                            'score': hit.get('_score', 0)
                        })
                except Exception as e:
                    logger.error(f"Error parsing person from search: {str(e)}")
                    continue

            logger.info(f"Found {len(persons)} persons for query '{query}'")
            return persons

        except Exception as e:
            logger.error(f"Error in simple person search: {str(e)}")
            return []

    async def _get_person_info(self, person_id: str):
        """
        Получает основную информацию о персонаже.
        """
        try:
            person_doc = await self.elastic.get(
                index='persons',
                id=person_id,
                _source_includes=['name', 'full_name']
            )

            source = person_doc['_source']

            name = source.get('full_name') or source.get('name')

            if not name:
                logger.warning(f"Person {person_id} has no name in: {source}")
                return None

            return {
                'id': person_id,
                'name': name,
                'source': source
            }

        except NotFoundError:
            logger.debug(f"Person {person_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting person info for {person_id}: {str(e)}")
            return None

    def _determine_roles_for_film(self,
                                  film_source: Dict[str, Any],
                                  person_id: str,
                                  person_name: str
                                  ) -> List[PersonRole]:
        """
        Определяет все роли персоны в конкретном фильме.
        """
        roles = []

        actors = film_source.get('actors', [])
        if self._is_person_in_list(actors, person_id, person_name):
            roles.append(PersonRole.ACTOR)

        writers = film_source.get('writers', [])
        if self._is_person_in_list(writers, person_id, person_name):
            roles.append(PersonRole.WRITER)

        directors = film_source.get('directors', [])
        if self._is_person_in_list(directors, person_id, person_name):
            roles.append(PersonRole.DIRECTOR)

        return roles

    def _is_person_in_list(self, items: List, person_id: str, person_name: str) -> bool:
        """
        Проверяет, находится ли персона в списке.
        """
        if not isinstance(items, list):
            return False

        for item in items:
            if isinstance(item, dict):
                item_id = item.get('id', '')
                item_name = item.get('name', '')

                if item_id == person_id or item_name == person_name:
                    return True

        return False

    async def _get_persons_films_from_cache(self, cache_key: str) -> Optional[List[PersonFilm]]:
        """Получает список фильмов из кэша Redis."""
        try:
            data = await self.redis.get(cache_key)
            if data:
                return [PersonFilm.parse_raw(item) for item in json.loads(data)]
        except Exception as e:
            logger.warning(f"Error getting films from cache {cache_key}: {e}")
        return None

    async def _put_persons_films_to_cache(self, cache_key: str, films: List[PersonFilm]):
        """Сохраняет список фильмов в кэш Redis."""
        if not films:
            return

        try:
            films_json = json.dumps([film.json() for film in films])
            await self.redis.setex(
                cache_key,
                FILM_CACHE_EXPIRE_IN_SECONDS,
                films_json
            )
            logger.debug(f"Cached {len(films)} films with key {cache_key}")
        except Exception as e:
            logger.warning(f"Error caching films {cache_key}: {e}")


@lru_cache()
def get_person_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> PersonService:
    return PersonService(redis, elastic)
