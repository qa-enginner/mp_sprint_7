# core/oauth_client.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
from urllib.parse import urlencode, parse_qs


class OAuthProvider(ABC):
    """Базовый класс для OAuth провайдеров"""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @abstractmethod
    def get_auth_url(self, state: str) -> str:
        """Формирует URL для редиректа на страницу авторизации соцсети"""
        pass

    @abstractmethod
    async def get_token(self, code: str) -> Dict[str, Any]:
        """Обменивает код авторизации на access_token"""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Получает информацию о пользователе из соцсети"""
        pass


class YandexOAuthProvider(OAuthProvider):
    def get_auth_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "login:email login:info"
        }
        return f"https://oauth.yandex.ru/authorize?{urlencode(params)}"

    async def get_token(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth.yandex.ru/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri
                }
            )
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://login.yandex.ru/info",
                headers={"Authorization": f"OAuth {access_token}"}
            )
            return response.json()
