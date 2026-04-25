from typing import List, Dict
from loguru import logger


class DataTransformer():
    """Класс для трансформации данных."""

    @staticmethod
    def transform_film(film: Dict) -> Dict:
        """Трансформировать данные фильма для Elasticsearch."""
        try:
            return {
                "id": str(film["id"]),
                "imdb_rating": film.get("imdb_rating"),
                "genres": film.get("genres", []),
                "title": film.get("title", ""),
                "description": film.get("description", ""),
                "directors_names": [
                    d["name"] for d in film.get("directors", [])
                ],
                "actors_names": [
                    a["name"] for a in film.get("actors", [])
                ],
                "writers_names": [
                    w["name"] for w in film.get("writers", [])
                ],
                "directors": film.get("directors", []),
                "actors": film.get("actors", []),
                "writers": film.get("writers", [])
            }
        except Exception as e:
            logger.error(f"Error transforming film {film.get('id')}: {e}")
            raise

    @staticmethod
    def transform_person(person: Dict) -> Dict:
        """Трансформировать данные персоны."""
        try:
            return {
                "id": str(person["id"]),
                "full_name": person["full_name"]
            }
        except Exception as e:
            logger.error(f"Error transforming person {person.get('id')}: {e}")
            raise

    @staticmethod
    def transform_genre(genre: Dict) -> Dict:
        """Трансформировать данные жанра."""
        try:
            return {
                "id": str(genre["id"]),
                "name": genre["name"],
                "description": genre.get("description")
            }
        except Exception as e:
            logger.error(f"Error transforming genre {genre.get('id')}: {e}")
            raise

    def transform_batch(self, data: List[Dict], data_type: str) -> List[Dict]:
        """Трансформировать пакет данных."""
        transformer_map = {
            "film_work": self.transform_film,
            "person": self.transform_person,
            "genre": self.transform_genre
        }

        if data_type not in transformer_map:
            raise ValueError(f"Unknown data type: {data_type}")

        return [transformer_map[data_type](item) for item in data]
