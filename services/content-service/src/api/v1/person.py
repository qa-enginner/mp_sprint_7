from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from loguru import logger
from typing import List

from models.person import Person, PersonFilm
from services.person import PersonService, get_person_service
from core.security import security

router = APIRouter()


@router.get(
    "/search",
    response_model=List[Person],
    summary="Поиск персон",
    description="Поиск персон по имени с полной информацией"
)
async def search_persons(
    query: str = Query(..., min_length=1, description="Поисковый запрос"),
    page_number: int = Query(1, ge=1, alias="page", description="Номер страницы"),
    page_size: int = Query(50, ge=1, le=100, alias="size", description="Количество элементов на странице"),
    person_service: PersonService = Depends(get_person_service),
    token_data: dict = Depends(security)
) -> List[Person]:
    """
    Поиск персон по имени.

    Возвращает полную информацию о каждой персоне, включая фильмы и роли.

    - **query**: Поисковый запрос
    - **page_number**: Номер страницы (начинается с 1)
    - **page_size**: Количество элементов на странице (макс. 100)
    """
    try:
        persons = await person_service.search_persons_with_films(
            query=query,
            page_number=page_number,
            page_size=page_size
        )

        if not persons:
            return []

        return persons

    except Exception as e:
        logger.error(f"Error searching persons: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
        '/{person_id}',
        summary="Получение информации о персоне",
        description="Получение информации о конкретной персоне"
)
async def person_details(
    person_id: UUID,
    person_service: PersonService = Depends(get_person_service),
    token_data: dict = Depends(security)
) -> Person:
    """Получить информацию о персоне по её ID."""
    person = await person_service.get_person_by_id(str(person_id))
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.get(
    "/{person_id}/film",
    response_model=List[PersonFilm],
    summary="Получить фильмы персоны",
    description="Возвращает список фильмов, в которых участвовала персона"
)
async def get_persons_films(
    person_id: UUID,
    person_service: PersonService = Depends(get_person_service),
    token_data: dict = Depends(security)
) -> List[PersonFilm]:
    try:
        films = await person_service.get_persons_films(str(person_id))
        if not films:
            raise HTTPException(
                status_code=404,
                detail="Person not found"
            )
        return films
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting films for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
