import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Название проекта
    project_name: str = os.getenv("PROJECT_NAME", "Auth Service")

    # Описание проекта
    project_description: str = os.getenv(
        "PROJECT_DESCRIPTION",
        "Сервис аутентификации и авторизации"
    )

    # Версия проекта
    project_version: str = os.getenv("PROJECT_VERSION", "1.0.0")

    # Настройки PostgreSQL
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "auth_db")

    # Настройки Redis
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    # Настройки JWT
    secret_key: str = os.getenv("SECRET_KEY", "a-string-secret-at-least-256-bits-long")
    algorithm: str = os.getenv("ALGORITHM", "HS256")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаем экземпляр настроек
settings = Settings()
