from http import HTTPStatus
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from services.film import FilmService, get_film_service
from models.film import Film, FilmList
from core.security import security, graceful_security
from enum import Enum
from uuid import UUID

router = APIRouter()


class FilmSortField(str, Enum):
    IMDB_RATING_ASC = "imdb_rating"
    IMDB_RATING_DESC = "-imdb_rating"


@router.get(
        '/',
        response_model=list[FilmList],
        summary='Главная страница',
        description="Получение списка фильмов с пагинацией и сортировкой"
)
async def film_list(
    genre: Optional[UUID] = None,
    film_service: FilmService = Depends(get_film_service),
    token_data: dict = Depends(graceful_security),
    sort: Optional[FilmSortField] = Query(
        FilmSortField.IMDB_RATING_DESC
    ),
    page_size: int = Query(50, ge=1, le=100),
    page_number: int = Query(1, ge=1),
) -> list[FilmList]:
    """
    Достуна сортировка по:
    - imdb_rating (ascending)
    - -imdb_rating (descending)
    """

    # Изящная деградация: если сервис авторизации недоступен, возвращаем пустой список
    if isinstance(token_data, dict) and token_data.get("auth_unavailable"):
        return []

    # Parse sort enum value
    sort_str = sort.value
    sort_field = sort_str.lstrip('-')
    sort_descending = sort_str.startswith('-')

    available_films = await film_service.get_all(
        sort_by=sort_field,
        sort_descending=sort_descending,
        page_number=page_number,
        page_size=page_size,
        genre_id=genre
    )

    return available_films


@router.get(
    '/search',
    response_model=list[FilmList],
    summary="Поиск фильмов",
    description="Полнотекстовый поиск фильмов по названию с пагинацией",
)
async def search_films(
    query: str = Query(..., min_length=1, description="Поисковый запрос"),
    page_number: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(50, ge=1, le=100, description="Количество элементов на странице"),
    film_service: FilmService = Depends(get_film_service),
    token_data: dict = Depends(security)
) -> list[FilmList]:
    """
    Поиск фильмов по названию.

    Args:
        query: Поисковый запрос
        page_number: Номер страницы (начинается с 1)
        page_size: Количество фильмов на странице (1-100)

    Returns:
        Список фильмов с пагинацией
    """

    searched_films = await film_service.search_films(query, page_number, page_size)
    return searched_films


@router.get(
        '/{film_id}',
        response_model=Film,
        summary="Страница фильма",
        description="Полная информация по фильму."
)
async def film_details(
    film_id: UUID,
    film_service: FilmService = Depends(get_film_service),
    token_data: dict = Depends(security)
) -> Film:
    """Получение информации о фильме по ID."""

    film = await film_service.get_by_id(str(film_id))
    if not film:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Film not found'
        )

    return film
