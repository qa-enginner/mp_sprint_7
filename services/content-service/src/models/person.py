from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field
from typing import List


class PersonRole(str, Enum):
    ACTOR = "actor"
    DIRECTOR = "director"
    WRITER = "writer"


class PersonFilmRole(BaseModel):
    """Фильм с ролями персоны."""
    uuid: UUID = Field(..., description="Идентификатор фильма")
    roles: List[PersonRole] = Field(
        default_factory=list,
        description="Роли персоны в фильме"
    )


class PersonFilm(BaseModel):
    """
    Модель фильма для отображения в списке фильмов персоны.
    """
    uuid: UUID = Field(..., description="Идентификатор фильма")
    title: str = Field(..., description="Название фильма")
    imdb_rating: float = Field(..., ge=0.0, le=10.0, description="Рейтинг IMDB")


class Person(BaseModel):
    """
    Модель полной информации о персоне.
    """
    uuid: UUID = Field(..., description="Идентификатор персоны")
    full_name: str = Field(..., description="Полное имя персоны")
    films: List[PersonFilmRole] = Field(default_factory=list, description="Фильмы персоны с ролями")


class PersonList(BaseModel):
    """Персона для отображения в списке."""
    uuid: UUID = Field(..., description="Идентификатор персоны")
    full_name: str = Field(..., description="Полное имя персоны")
