import http
from typing import Optional, Union, TypedDict, Literal
import httpx
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings


class AuthUnavailable(TypedDict):
    auth_unavailable: Literal[True]


async def validate_token_via_auth_service(token: str) -> Union[dict, AuthUnavailable, None]:
    """
    Отправляет токен в сервис авторизации для валидации.
    Возвращает payload токена в виде словаря или None, если токен невалиден.
    При недоступности сервиса возвращает словарь с флагом auth_unavailable.
    """
    url = f"{settings.auth_service_url}/api/v1/auth/validate"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                return None  # Invalid token
            else:
                # Log unexpected status codes
                return None
    except httpx.TimeoutException:
        # Specific timeout handling
        return {"auth_unavailable": True}
    except httpx.ConnectError:
        # Service unreachable
        return {"auth_unavailable": True}
    except Exception as e:
        # Log unexpected errors
        return None


class JWTBearer(HTTPBearer):
    """
    Класс - наследник fastapi.security.HTTPBearer.
    Метод `__call__` класса HTTPBearer возвращает объект HTTPAuthorizationCredentials из заголовка `Authorization`

    class HTTPAuthorizationCredentials(BaseModel):
        scheme: str #  'Bearer'
        credentials: str #  сам токен в кодировке Base64

    FastAPI при использовании класса HTTPBearer добавит всё необходимое для авторизации в Swagger документацию.
    """
    def __init__(self, auto_error: bool = True, graceful: bool = False):
        super().__init__(auto_error=auto_error)
        self.graceful = graceful

    async def __call__(self, request: Request) -> Optional[dict]:
        """
        Переопределение метода родительского класса HTTPBearer.
        """
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)
        if not credentials:
            if self.auto_error:
                raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Invalid authorization code.')
            else:
                return None
        if not credentials.scheme == 'Bearer':
            raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail='Only Bearer token might be accepted')
        decoded_token = await self.parse_token(credentials.credentials)
        if not decoded_token:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Invalid or expired token.')
        # Если сервис авторизации недоступен
        if isinstance(decoded_token, dict) and decoded_token.get("auth_unavailable"):
            if self.graceful:
                # В режиме изящной деградации возвращаем флаг
                return decoded_token
            else:
                # В строгом режиме считаем это ошибкой авторизации
                raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Authentication service unavailable.')
        return decoded_token

    async def parse_token(self, jwt_token: str) -> Optional[dict]:
        return await validate_token_via_auth_service(jwt_token)


security = JWTBearer()
optional_security = JWTBearer(auto_error=False)
graceful_security = JWTBearer(graceful=True)
