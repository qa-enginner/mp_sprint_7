import http
import logging
from typing import Optional
from jose import jwt
from jose.exceptions import (
    JWTError,
    ExpiredSignatureError,
    JWTClaimsError,
    JWSSignatureError,
    JWSError
)
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from schemas.entity import TokenData


def decode_token(token: str) -> Optional[dict]:
    """
    Функция декодирует токен, используя секретный ключ, сохранённый в объекте settings в поле secret_key.
    Возвращает содержимое токена в виде словаря или None, если токен невалиден или при декодировании
    было выброшено исключение.
    """
    try:
        logging.debug(f"Algorithm: {settings.algorithm}")
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    except ExpiredSignatureError as e:
        logging.error(f"Token expired: {e}")
        logging.error(f"Token length: {len(token)}")
        return None

    except JWTClaimsError as e:
        logging.error(f"Invalid JWT claims (e.g., audience, issuer validation failed): {e}")
        logging.error(f"Token length: {len(token)}")
        logging.error(f"Token repr: {repr(token)}")
        return None

    except JWSSignatureError as e:
        logging.error(f"Invalid token signature: {e}")
        logging.error(f"Token length: {len(token)}")
        logging.error(f"Token repr: {repr(token)}")
        return None

    except JWSError as e:
        logging.error(f"JWS error (invalid format or structure): {e}")
        logging.error(f"Token length: {len(token)}")
        logging.error(f"Token repr: {repr(token)}")
        return None

    except JWTError as e:
        # Базовое исключение для всех остальных ошибок JWT
        logging.error(f"JWT decode error: {e}")
        logging.error(f"Token length: {len(token)}")
        logging.error(f"Token repr: {repr(token)}")
        return None


class JWTBearer(HTTPBearer):
    """
    Класс - наследник fastapi.security.HTTPBearer. Рекомендуем исследовать этот класс.
    Метод `__call__` класса HTTPBearer возвращает объект HTTPAuthorizationCredentials из заголовка `Authorization`

    class HTTPAuthorizationCredentials(BaseModel):
        scheme: str #  'Bearer'
        credentials: str #  сам токен в кодировке Base64

    FastAPI при использовании класса HTTPBearer добавит всё необходимое для авторизации в Swagger документацию.
    """
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> TokenData:
        """
        Переопределение метода родительского класса HTTPBearer.
        Логика проста: достаём токен из заголовка и декодируем его.
        В результате возвращаем TokenData или выбрасываем исключение.
        Так как далее объект этого класса будет использоваться как зависимость Depends(...),
        то при этом будет вызван метод `__call__`.
        """
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Invalid authorization code.')
        if not credentials.scheme == 'Bearer':
            raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail='Only Bearer token might be accepted')
        decoded_token = self.parse_token(credentials.credentials)
        if not decoded_token:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Invalid or expired token.')
        # Создаем TokenData из decoded_token
        user_id = decoded_token.get('sub')
        if not user_id:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Invalid token payload.')
        return TokenData(user_id=user_id, token=credentials.credentials)

    @staticmethod
    def parse_token(jwt_token: str) -> Optional[dict]:
        return decode_token(jwt_token)


security = JWTBearer()
optional_security = JWTBearer(auto_error=False)
