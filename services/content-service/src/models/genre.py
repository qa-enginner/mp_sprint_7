from uuid import UUID
from pydantic import BaseModel, Field


class Genre(BaseModel):
    uuid: UUID = Field(..., description="Идентификатор жанра")
    name: str = Field(..., description="Название жанра", max_length=255)
