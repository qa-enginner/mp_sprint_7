import jwt
import time
import json
import uuid
import requests
import http
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect


class TokenRefreshMiddleware:
    """
    Middleware для автоматического обновления access_token при его истечении.
    Проверяет наличие access_token в сессии, декодирует его и при необходимости
    обновляет с помощью refresh_token.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Пропускаем обновление для страниц входа и выхода
        if request.path in ['/admin/login/', '/admin/logout/', '/login/', '/logout/']:
            return self.get_response(request)

        access_token = request.session.get('access_token')
        refresh_token = request.session.get('refresh_token')

        # Если нет access_token, пропускаем
        if not access_token:
            return self.get_response(request)

        # Проверяем срок действия access_token
        try:
            # Декодируем без верификации подписи (только для получения payload)
            # В реальном приложении следует верифицировать подпись, но для проверки exp достаточно
            payload = jwt.decode(access_token, options={"verify_signature": False})
            exp = payload.get('exp')
            if exp and exp < time.time() + 60:  # Если истекает в течение минуты
                # Токен скоро истечет, пытаемся обновить
                if refresh_token:
                    new_tokens = self.refresh_tokens(refresh_token, request)
                    if new_tokens:
                        request.session['access_token'] = new_tokens.get('access_token')
                        request.session['refresh_token'] = new_tokens.get('refresh_token')
                    else:
                        # Не удалось обновить, разлогиниваем пользователя
                        logout(request)
                        return redirect('/admin/login/')
        except jwt.DecodeError:
            # Токен невалиден, удаляем из сессии
            if 'access_token' in request.session:
                del request.session['access_token']
            if 'refresh_token' in request.session:
                del request.session['refresh_token']
            logout(request)
            return redirect('/admin/login/')
        except Exception:
            # Любая другая ошибка - пропускаем
            pass

        return self.get_response(request)

    def refresh_tokens(self, refresh_token, request=None):
        """Вызывает эндпоинт обновления токенов."""
        url = settings.AUTH_API_REFRESH_URL
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        # Добавляем X-Request-Id, если он есть в request
        if request and hasattr(request, 'request_id') and request.request_id:
            headers['X-Request-Id'] = request.request_id
        payload = {'refresh_token': refresh_token}
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            if response.status_code == http.HTTPStatus.OK:
                return response.json()
        except requests.RequestException:
            pass
        return None


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Получаем request_id из заголовка Nginx
        request_id = request.headers.get('X-Request-Id')

        if not request_id:
            # Генерируем новый request_id, если заголовок отсутствует
            request_id = str(uuid.uuid4())

        # Сохраняем в request для использования в views и других middleware
        request.request_id = request_id

        response = self.get_response(request)

        # Передаем request_id дальше в FastAPI (в заголовке ответа)
        response['X-Request-Id'] = request_id

        return response
