import http
import json
import jwt
from enum import Enum

import requests
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class Roles(str, Enum):
    ADMIN = 'ADMIN'
    SUBSCRIBER = 'SUBSCRIBER'


class CustomBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        # 1. Логин для получения токенов
        login_url = settings.AUTH_API_LOGIN_URL
        payload = {'email': username, 'password': password}
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.post(
            login_url, data=json.dumps(payload), headers=headers
        )
        if response.status_code != http.HTTPStatus.OK:
            return None

        tokens = response.json()
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        if not access_token:
            return None

        # 2. Получение данных пользователя через /me
        # Определяем базовый URL: удаляем '/auth/login' из login_url
        base_url = login_url.rsplit('/auth/login', 1)[0]
        me_url = f"{base_url}/users/me"
        headers_with_token = {
            'accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        me_response = requests.get(me_url, headers=headers_with_token)
        if me_response.status_code != http.HTTPStatus.OK:
            return None

        user_data = me_response.json()

        # 3. Создание/обновление пользователя в Django
        try:
            email = user_data.get('email', '')
            # Если email пустой, используем id как email
            if not email:
                email = user_data['id']
            user, created = User.objects.get_or_create(email=email)
            user.first_name = user_data.get('first_name', '')
            user.last_name = user_data.get('last_name', '')
            # is_superuser из auth-service определяет права админа
            is_superuser = user_data.get('is_superuser', False)
            # Если is_superuser не пришёл, попробуем получить из токена
            if not is_superuser:
                try:
                    # Декодируем access_token без верификации подписи
                    payload = jwt.decode(
                        access_token, options={"verify_signature": False}
                    )
                    is_superuser = payload.get('is_superuser', False)
                except jwt.DecodeError:
                    pass
            # Используем поле is_admin для прав администратора
            user.is_admin = is_superuser
            user.is_active = True  # По умолчанию активен
            # Устанавливаем непригодный пароль, чтобы избежать пустого пароля
            user.set_unusable_password()
            user.save()
        except Exception as e:
            # Логирование ошибки (можно добавить logging)
            print(f"Error creating/updating user: {e}")
            return None

        # Сохраняем токены в сессии
        if request is not None:
            request.session['access_token'] = access_token
            request.session['refresh_token'] = refresh_token
            # Устанавливаем время истечения access_token (опционально)
            # Можно сохранить время экспирации, если оно есть в ответe
            # request.session['access_token_expires'] = data.get('expires')

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def refresh_tokens(self, refresh_token):
        """Обновляет access и refresh токены через auth-service."""
        url = settings.AUTH_API_REFRESH_URL
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        payload = {'refresh_token': refresh_token}
        response = requests.post(
            url, data=json.dumps(payload), headers=headers
        )
        if response.status_code != http.HTTPStatus.OK:
            return None
        return response.json()
