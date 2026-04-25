import pytest
from elasticsearch import Elasticsearch
import json

ES_HOST = "http://localhost:9200"
INDEX_NAME = "movies"


@pytest.fixture(scope="module")
def es_client():
    """Фикстура для подключения к Elasticsearch"""
    client = Elasticsearch(ES_HOST)

    if not client.ping():
        pytest.fail("Не удалось подключиться к Elasticsearch")

    return client


class TestETLProcess:
    """Тесты ETL процесса для индекса movies"""

    def test_total_records_count(self, es_client):
        """Тест 1: Проверка общего количества записей"""
        query = {
            "query": {
                "match_all": {}
            }
        }

        response = es_client.search(index=INDEX_NAME, body=query)

        assert response['hits']['total']['value'] == 999
        assert response['_shards']['failed'] == 0

    def test_na_records_search(self, es_client):
        """Тест 2: Поиск N/A элементов"""
        query = {
            "query": {
                "query_string": {
                    "query": "N//A"
                }
            }
        }

        response = es_client.search(index=INDEX_NAME, body=query)
        response_text = json.dumps(response.body)

        # Проверяем количество найденных записей
        assert response['hits']['total']['value'] == 7

        # Проверяем, что в ответе нет строки "N/A"
        assert "N/A" not in response_text

    def test_camp_word_search(self, es_client):
        """Тест 3: Поиск по слову 'camp'"""
        query = {
            "query": {
                "multi_match": {
                    "query": "camp",
                    "fuzziness": "auto",
                    "fields": [
                        "actors_names",
                        "writers_names",
                        "title",
                        "description",
                        "genres"
                    ]
                }
            }
        }

        response = es_client.search(index=INDEX_NAME, body=query)

        assert response['hits']['total']['value'] == 24
        assert response['hits']['hits'][0]['_id'] == '6764dd98-6546-4ccf-95c5-74a63e980768'

    def test_actor_search(self, es_client):
        """Тест 4: Поиск фильмов по актеру"""
        query = {
            "query": {
                "nested": {
                    "path": "actors",
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "match": {
                                        "actors.name": "Greg Camp"
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }

        response = es_client.search(index=INDEX_NAME, body=query)

        assert response['hits']['total']['value'] == 6

    def test_single_writer_movie(self, es_client):
        """Тест 5: Проверка фильма с одним сценаристом"""
        movie_id = "24eafcd7-1018-4951-9e17-583e2554ef0a"

        query = {
            "query": {
                "term": {
                    "id": {
                        "value": movie_id
                    }
                }
            }
        }

        response = es_client.search(index=INDEX_NAME, body=query)

        assert response['hits']['total']['value'] == 1
        assert response['hits']['hits'][0]['_source']['writers_names'] == ["Craig Hutchinson"]

    def test_movie_without_director(self, es_client):
        """Тест 6: Проверка фильма без режиссера"""
        movie_id = "479f20b0-58d1-4f16-8944-9b82f5b1f22a"

        query = {
            "query": {
                "term": {
                    "id": {
                        "value": movie_id
                    }
                }
            }
        }

        response = es_client.search(index=INDEX_NAME, body=query)

        assert response['hits']['total']['value'] == 1
        assert len(response['hits']['hits'][0]['_source']['directors_names']) == 0

    def test_genres_count(self, es_client):
        """Тест 7: Проверка количества уникальных жанров"""
        query = {
            "size": 0,
            "aggs": {
                "uniq_genres": {
                    "terms": {
                        "field": "genres",
                        "size": 100
                    }
                }
            }
        }

        response = es_client.search(index=INDEX_NAME, body=query)

        buckets = response['aggregations']['uniq_genres']['buckets']
        assert len(buckets) == 26
