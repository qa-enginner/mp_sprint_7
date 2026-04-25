import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection
from typing import Dict, List, Optional
from datetime import datetime
import backoff
from config.settings import config


class PostgresExtractor:
    """Класс для извлечения данных из PostgreSQL."""

    def __init__(self):
        self.config = config.postgres

    @backoff.on_exception(
        backoff.expo,
        psycopg2.OperationalError,
        max_tries=config.etl.max_retries
    )
    def get_connection(self) -> connection:
        """Получить соединение с PostgreSQL."""
        return psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.dbname,
            user=self.config.user,
            password=self.config.password,
            cursor_factory=psycopg2.extras.DictCursor
        )

    def extract_film_work(self, modified_since: Optional[datetime] = None) -> List[Dict]:
        """Извлечь фильмы, измененные после указанной даты."""
        query = """
            SELECT
                fw.id,
                fw.title,
                fw.description,
                fw.rating as imdb_rating,
                fw.type,
                fw.created,
                fw.modified,
                COALESCE(
                    json_agg(
                        DISTINCT jsonb_build_object(
                            'id', p.id,
                            'name', p.full_name
                        )
                    ) FILTER (WHERE p.id IS NOT NULL AND pfw.role = 'director'),
                    '[]'
                ) as directors,
                COALESCE(
                    json_agg(
                        DISTINCT jsonb_build_object(
                            'id', p.id,
                            'name', p.full_name
                        )
                    ) FILTER (WHERE p.id IS NOT NULL AND pfw.role = 'actor'),
                    '[]'
                ) as actors,
                COALESCE(
                    json_agg(
                        DISTINCT jsonb_build_object(
                            'id', p.id,
                            'name', p.full_name
                        )
                    ) FILTER (WHERE p.id IS NOT NULL AND pfw.role = 'writer'),
                    '[]'
                ) as writers,
                COALESCE(
                    array_agg(DISTINCT g.name) FILTER (WHERE g.name IS NOT NULL),
                    '{}'
                ) as genres
            FROM content.film_work fw
            LEFT JOIN content.person_film_work pfw ON pfw.film_work_id = fw.id
            LEFT JOIN content.person p ON p.id = pfw.person_id
            LEFT JOIN content.genre_film_work gfw ON gfw.film_work_id = fw.id
            LEFT JOIN content.genre g ON g.id = gfw.genre_id
            WHERE (%s IS NULL OR fw.modified > %s)
            GROUP BY fw.id
            ORDER BY fw.modified;
        """

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (modified_since, modified_since))
                return [dict(row) for row in cursor.fetchall()]

    def extract_person(self, modified_since: Optional[datetime] = None) -> List[Dict]:
        """Извлечь персоны, измененные после указанной даты."""
        query = """
            SELECT
                p.id,
                p.full_name,
                p.created,
                p.modified
            FROM content.person p
            WHERE (%s IS NULL OR p.modified > %s)
            GROUP BY p.id
            ORDER BY p.modified;
        """

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (modified_since, modified_since))
                return [dict(row) for row in cursor.fetchall()]

    def extract_genre(self, modified_since: Optional[datetime] = None) -> List[Dict]:
        """Извлечь жанры, измененные после указанной даты."""
        query = """
            SELECT
                g.id,
                g.name,
                g.description,
                g.created,
                g.modified
            FROM content.genre g
            WHERE (%s IS NULL OR g.modified > %s)
            GROUP BY g.id
            ORDER BY g.modified;
        """

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (modified_since, modified_since))
                return [dict(row) for row in cursor.fetchall()]

    def get_max_modified_time(self, table: str) -> Optional[datetime]:
        """Получить максимальное время модификации для таблицы."""
        query = f"SELECT MAX(modified) FROM content.{table};"

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return result[0] if result else None
