from typing import List
from fastapi import APIRouter, Depends, HTTPException

from services.genre import GenreService, get_genre_service
from models.genre import Genre
from core.security import security
from loguru import logger

from uuid import UUID

router = APIRouter()


@router.get(
        '/',
        response_model=List[Genre],
        summary="Получение списка жанров",
        description="Возвращает список жанров"
)
async def get_genres_list(
    genre_service: GenreService = Depends(get_genre_service),
    token_data: dict = Depends(security)
) -> List[Genre]:

    genres = await genre_service.get_all_genres()
    return genres


@router.get(
    "/{genre_id}",
    response_model=Genre,
    summary="Получить жанр по ID",
    description="Возвращает информацию о жанре по его идентификатору",
)
async def get_genre_details(
    genre_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
    token_data: dict = Depends(security)
) -> Genre:

    genre = await genre_service.get_genre_by_id(str(genre_id))
    if not genre:
        raise HTTPException(
                    status_code=404,
                    detail="Genre not found"
                )
    return genre
