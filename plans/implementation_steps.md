# Детальный план реализации структуры проекта

## Текущее состояние
- Существует базовый Auth Service на FastAPI
- Нет структурированной организации кода
- Отсутствует Admin Panel
- Нет четкого разделения на сервисы

## Шаг 1: Создание базовой структуры директорий

### 1.1. Создать корневую структуру
```bash
mkdir -p packages/shared/{models,utils,clients}
mkdir -p packages/database/migrations
mkdir -p services/auth-service/src/{auth,oauth,users,middleware,api,core,tests}
mkdir -p services/admin-panel/admin_panel/apps/{users,content,auth_integration}
mkdir -p docker/{auth-service,admin-panel}
mkdir -p infrastructure/{terraform,kubernetes}
mkdir -p docs/{api,architecture,deployment}
mkdir -p scripts
```

### 1.2. Создать основные конфигурационные файлы
- `.gitignore` - игнорирование временных файлов
- `.env.example` - шаблон переменных окружения
- `docker-compose.yml` - общая конфигурация для разработки
- `Makefile` - утилиты для разработки
- `README.md` - документация проекта

## Шаг 2: Настройка Docker окружения

### 2.1. Создать Dockerfile для Auth Service
```dockerfile
# services/auth-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2. Создать Dockerfile для Admin Panel
```dockerfile
# services/admin-panel/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### 2.3. Создать общий docker-compose.yml
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: auth_db
      POSTGRES_USER: auth_user
      POSTGRES_PASSWORD: auth_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  auth-service:
    build: ./services/auth-service
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://auth_user:auth_pass@postgres:5432/auth_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./services/auth-service:/app
      - ./packages/shared:/app/shared

  admin-panel:
    build: ./services/admin-panel
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://auth_user:auth_pass@postgres:5432/auth_db
      - AUTH_SERVICE_URL=http://auth-service:8000
    depends_on:
      - postgres
      - auth-service
    volumes:
      - ./services/admin-panel:/app
      - ./packages/shared:/app/shared

volumes:
  postgres_data:
```

## Шаг 3: Реорганизация Auth Service

### 3.1. Структура Clean Architecture для Auth Service
```
services/auth-service/
├── src/
│   ├── auth/                    # Доменный слой аутентификации
│   │   ├── entities/           # User, Token, Permission
│   │   ├── use_cases/          # RegisterUser, LoginUser, ValidateToken
│   │   └── repositories/       # UserRepository, TokenRepository
│   ├── oauth/                  # OAuth провайдеры
│   │   ├── providers/          # Google, Yandex, VK
│   │   └── use_cases/          # OAuthLogin, OAuthCallback
│   ├── users/                  # Управление пользователями
│   │   ├── entities/           # UserProfile, SocialAccount
│   │   └── use_cases/          # UpdateProfile, UnlinkSocial
│   ├── middleware/             # Общие middleware
│   │   ├── rate_limiter.py
│   │   ├── circuit_breaker.py
│   │   └── auth_middleware.py
│   ├── api/                    # REST API эндпоинты
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── oauth.py
│   │   │   └── users.py
│   │   └── dependencies.py     # FastAPI dependencies
│   ├── core/                   # Конфигурация и зависимости
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── redis.py
│   │   └── di.py              # Dependency Injection
│   └── tests/                  # Тесты
│       ├── unit/
│       └── integration/
├── alembic/                    # Миграции БД
│   ├── versions/
│   └── alembic.ini
├── requirements.txt
└── main.py
```

### 3.2. Ключевые изменения в коде
1. Вынести модели в `packages/shared/models/`
2. Реализовать репозитории с паттерном Unit of Work
3. Добавить dependency injection для тестируемости
4. Реализовать недостающие эндпоинты:
   - `POST /auth/introspect` - валидация токенов
   - `GET /auth/oauth/{provider}` - инициация OAuth
   - `GET /auth/oauth/callback/{provider}` - обработка коллбэка
   - `DELETE /user/social/{provider}/unlink` - открепление соцсети

## Шаг 4: Создание Admin Panel

### 4.1. Инициализация Django проекта
```bash
cd services/admin-panel
django-admin startproject admin_panel .
python manage.py startapp users
python manage.py startapp content
python manage.py startapp auth_integration
```

### 4.2. Структура Django приложения
```
services/admin-panel/
├── admin_panel/
│   ├── apps/
│   │   ├── users/              # Управление пользователями
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── admin.py
│   │   │   └── urls.py
│   │   ├── content/            # Управление контентом
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   └── admin.py
│   │   └── auth_integration/   # Интеграция с Auth Service
│   │       ├── middleware.py   # Auth middleware
│   │       ├── clients.py      # HTTP клиент к Auth Service
│   │       └── decorators.py   # Декораторы для проверки прав
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
└── requirements.txt
```

### 4.3. Интеграция с Auth Service
1. Создать HTTP клиент с Circuit Breaker
2. Реализовать middleware для проверки JWT токенов
3. Настроить кэширование результатов валидации в Redis
4. Реализовать fallback механизм при недоступности Auth Service

## Шаг 5: Создание общих библиотек

### 5.1. Общие модели (Pydantic + SQLAlchemy)
```python
# packages/shared/models/user.py
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserBase(BaseModel):
    email: str
    username: str
    is_active: bool = True

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

### 5.2. Общие утилиты
```python
# packages/shared/utils/jwt.py
import jwt
from datetime import datetime, timedelta

def create_jwt_token(user_id: str, secret: str, expires_delta: timedelta) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_jwt_token(token: str, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
```

### 5.3. HTTP клиент с Circuit Breaker
```python
# packages/shared/clients/auth_client.py
import httpx
from circuitbreaker import circuit

class AuthServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
    
    @circuit(failure_threshold=5, expected_exception=httpx.HTTPError)
    async def validate_token(self, token: str) -> dict:
        response = await self.client.post(
            f"{self.base_url}/auth/introspect",
            json={"token": token}
        )
        response.raise_for_status()
        return response.json()
```

## Шаг 6: Настройка CI/CD

### 6.1. GitHub Actions workflow
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test-auth-service:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test Auth Service
        run: |
          cd services/auth-service
          pip install -r requirements.txt
          pytest

  test-admin-panel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test Admin Panel
        run: |
          cd services/admin-panel
          pip install -r requirements.txt
          python manage.py test

  build-docker:
    runs-on: ubuntu-latest
    needs: [test-auth-service, test-admin-panel]
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker images
        run: |
          docker build -t auth-service ./services/auth-service
          docker build -t admin-panel ./services/admin-panel
```

## Шаг 7: Документация

### 7.1. API документация
- Swagger UI для Auth Service (автоматически генерируется FastAPI)
- Django REST Framework Browsable API для Admin Panel
- Postman коллекция для тестирования

### 7.2. Архитектурная документация
- Диаграммы последовательности для ключевых сценариев
- ER-диаграмма базы данных
- Схема развертывания в production

## График выполнения

| Этап | Длительность | Приоритет |
|------|--------------|-----------|
| Шаг 1: Базовая структура | 1-2 дня | Высокий |
| Шаг 2: Docker окружение | 1 день | Высокий |
| Шаг 3: Реорганизация Auth Service | 3-5 дней | Высокий |
| Шаг 4: Создание Admin Panel | 4-6 дней | Средний |
| Шаг 5: Общие библиотеки | 2-3 дня | Средний |
| Шаг 6: CI/CD | 1-2 дня | Низкий |
| Шаг 7: Документация | 1-2 дня | Низкий |

## Критерии успеха

1. **Работоспособность**:
   - Auth Service отвечает на все эндпоинты
   - Admin Panel позволяет управлять пользователями
   - Сервисы работают в Docker окружении

2. **Качество кода**:
   - Покрытие тестами > 80%
   - Соответствие Clean Architecture
   - Отсутствие циклических зависимостей

3. **Производительность**:
   - Response time < 100ms для критичных эндпоинтов
   - Правильно работающий rate limiting
   - Устойчивость к отказам (circuit breaker)

4. **Поддерживаемость**:
   - Четкая документация
   - Автоматизированные тесты
   - Легкость развертывания