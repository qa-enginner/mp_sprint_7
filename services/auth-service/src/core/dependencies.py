"""
Зависимости для auth-service.

Содержит классы-зависимости для объединения общих зависимостей,
пагинации и проверки прав суперпользователя.
"""

from typing import Optional, Dict
from fastapi import Depends, Query, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from db.postgres import get_session
from core.security import security, optional_security
from schemas.entity import TokenData, UserInDB
from services.user_service import UserService


class RequestContext:
    """
    Контекст запроса, объединяющий общие зависимости.

    Содержит информацию о текущем пользователе, сессии БД и токене.
    Позволяет уменьшить дублирование зависимостей в эндпоинтах.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        token_data: Optional[TokenData] = None,
        request: Optional[Request] = None
    ):
        self.user_id = user_id
        self.db = db
        self.token_data = token_data
        self.request = request

    async def get_current_user(self) -> UserInDB:
        """
        Получить объект текущего пользователя из БД.

        Returns:
            UserInDB: Объект пользователя

        Raises:
            HTTPException: Если контекст неполный или пользователь не найден
        """
        if not self.user_id or not self.db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недостаточно данных в контексте запроса"
            )

        return await UserService.get_user(
            user_id=uuid.UUID(self.user_id),
            db=self.db
        )

    async def is_superuser(self) -> bool:
        """
        Проверить, является ли текущий пользователь суперпользователем.

        Returns:
            bool: True если пользователь суперпользователь, иначе False
        """
        try:
            user = await self.get_current_user()
            return user.is_superuser
        except Exception:
            return False

    @classmethod
    async def from_depends(
        cls,
        token_data: TokenData = Depends(security),
        db: AsyncSession = Depends(get_session),
        request: Request = None
    ) -> "RequestContext":
        """
        Фабричный метод для использования в Depends.

        Args:
            token_data: Данные токена (из security зависимости)
            db: Сессия БД
            request: Объект запроса FastAPI

        Returns:
            RequestContext: Инициализированный контекст запроса
        """
        return cls(
            user_id=token_data.user_id if token_data else None,
            db=db,
            token_data=token_data,
            request=request
        )

    @classmethod
    async def optional_from_depends(
        cls,
        token_data: TokenData = Depends(optional_security),
        db: AsyncSession = Depends(get_session),
        request: Request = None
    ) -> "RequestContext":
        """
        Фабричный метод для опциональной аутентификации.

        Используется в эндпоинтах, где аутентификация не обязательна.

        Args:
            token_data: Данные токена (может быть None)
            db: Сессия БД
            request: Объект запроса FastAPI

        Returns:
            RequestContext: Инициализированный контекст запроса
        """
        return cls(
            user_id=token_data.user_id if token_data else None,
            db=db,
            token_data=token_data,
            request=request
        )


class PaginationParams:
    """
    Параметры пагинации для стандартизации.

    Обеспечивает единый интерфейс для работы с пагинацией
    во всех эндпоинтах, требующих разбивки на страницы.
    """

    def __init__(
        self,
        page: int = Query(
            1, ge=1, description="Номер страницы (начинается с 1)"
        ),
        size: int = Query(
            50, ge=1, le=100,
            description="Количество элементов на странице (1-100)"
        )
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size

    def to_dict(self) -> Dict[str, int]:
        """
        Преобразовать параметры пагинации в словарь.

        Returns:
            Dict[str, int]: Словарь с параметрами пагинации
        """
        return {
            "page": self.page,
            "size": self.size,
            "offset": self.offset
        }

    def __repr__(self) -> str:
        return (
            f"PaginationParams(page={self.page}, "
            f"size={self.size}, offset={self.offset})"
        )


async def require_superuser(
    context: RequestContext = Depends(RequestContext.from_depends)
) -> RequestContext:
    """
    Зависимость, требующая прав суперпользователя.

    Проверяет, является ли текущий пользователь суперпользователем.
    Если нет - возвращает HTTP 403.

    Args:
        context: Контекст запроса с информацией о пользователе

    Returns:
        RequestContext: Тот же контекст, если проверка пройдена

    Raises:
        HTTPException: 403 если пользователь не суперпользователь
    """
    if not await context.is_superuser():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуются права суперпользователя."
        )
    return context


async def get_db_context(
    db: AsyncSession = Depends(get_session)
) -> RequestContext:
    """
    Упрощенный контекст только с сессией БД.

    Используется в эндпоинтах, где не требуется аутентификация,
    но нужен доступ к базе данных.

    Args:
        db: Сессия БД

    Returns:
        RequestContext: Контекст только с сессией БД
    """
    return RequestContext(db=db)
