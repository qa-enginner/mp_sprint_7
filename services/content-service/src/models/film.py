from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional


class UUIDMixin(BaseModel):
    """Миксин для хранения первичных ключей."""
    uuid: UUID


class PersonShort(UUIDMixin):
    full_name: str


class GenreShort(UUIDMixin):
    name: str


class Film(UUIDMixin):
    """Модель фильма."""
    imdb_rating: float
    genres: List[GenreShort] = Field(default_factory=list)
    title: str
    description: Optional[str] = None
    actors: List[PersonShort] = Field(default_factory=list)
    writers: List[PersonShort] = Field(default_factory=list)
    directors: List[PersonShort] = Field(default_factory=list)


class FilmList(UUIDMixin):
    """Модель списка фильмов."""
    title: str
    imdb_rating: float
