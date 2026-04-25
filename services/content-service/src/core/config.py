import os
# from logging import config as logging_config

# from core.logger import LOGGING

# # Применяем настройки логирования
# logging_config.dictConfig(LOGGING)
# LOG_FILE = os.getenv('LOG_FILE', 'log.log')

# Название проекта. Используется в Swagger-документации
PROJECT_NAME = os.getenv('PROJECT_NAME', 'Read-only API для онлайн-кинотеатра')
PROJECT_DESCRIPTION = os.getenv('PROJECT_DESCRIPTION', 'Информация о фильмах, жанрах и людях, участвовавших в создании произведения')
PROJECT_VERSION = os.getenv('PROJECT_VERSION', '1.0.0')

# Настройки Redis
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Настройки Elasticsearch
ELASTIC_SCHEMA = os.getenv('ELASTIC_SCHEMA', 'http://')
ELASTIC_HOST = os.getenv('ELASTIC_HOST', '127.0.0.1')
ELASTIC_PORT = int(os.getenv('ELASTIC_PORT', 9200))

# Корень проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Настройки JWT
JWT_SECRET_KEY = os.getenv('SECRET_KEY', 'secret_key')
JWT_ALGORITHM = os.getenv('ALGORITHM', 'HS256')

# URL сервиса авторизации
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth-service:8000')

# Для совместимости с security.py (ожидает объект settings с атрибутами jwt_secret_key и jwt_algorithm)
class Settings:
    jwt_secret_key = JWT_SECRET_KEY
    jwt_algorithm = JWT_ALGORITHM
    auth_service_url = AUTH_SERVICE_URL

settings = Settings()
