"""
Django settings for example project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'secret_key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', False) == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(', ')

# Application definition

INSTALLED_APPS = [
    'users',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'movies',
    'corsheaders',
]

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'users.auth.CustomBackend',
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = ["http://127.0.0.1:8080",]

ROOT_URLCONF = 'example.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'example.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('SQL_HOST', '127.0.0.1'),
        'PORT': os.getenv('SQL_PORT', 5432),
        'OPTIONS': {
            'options': os.getenv('SQL_OPTIONS'),
        },
    },
    'movies': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('ADMIN_POSTGRES_DB', 'movies'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('SQL_HOST', '127.0.0.1'),
        'PORT': os.getenv('SQL_PORT', 5432),
        'OPTIONS': {
            'options': os.getenv('SQL_OPTIONS'),
        },
    }
}


class AuthAndMoviesRouter:
    """
    Роутер для маршрутизации между БД:
    - default: для авторизации (пользователи, сессии, права доступа, admin)
    - movies: только для контента (фильмы, жанры, персоны и т.д.)
    """
    
    # Приложения, которые должны быть ТОЛЬКО в default
    DEFAULT_APPS = {
        'auth',        # django.contrib.auth
        'contenttypes',# django.contrib.contenttypes
        'sessions',    # django.contrib.sessions
        'admin',       # django.contrib.admin
        'users',       # если у вас есть свое приложение users
    }
    
    # Приложения, которые должны быть ТОЛЬКО в movies
    MOVIES_APPS = {
        'movies',      # ваше приложение с фильмами
        # добавьте другие приложения, связанные с контентом
    }
    
    def db_for_read(self, model, **hints):
        app_label = model._meta.app_label
        
        if app_label in self.DEFAULT_APPS:
            return 'default'
        elif app_label in self.MOVIES_APPS:
            return 'movies'
        
        # По умолчанию default
        return 'default'
    
    def db_for_write(self, model, **hints):
        app_label = model._meta.app_label
        
        if app_label in self.DEFAULT_APPS:
            return 'default'
        elif app_label in self.MOVIES_APPS:
            return 'movies'
        
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Разрешаем связи только между объектами в одной БД
        """
        return obj1._state.db == obj2._state.db
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Критически важно для миграций!
        """
        # Приложения default идут только в default
        if app_label in self.DEFAULT_APPS:
            return db == 'default'
        
        # Приложения movies идут только в movies
        if app_label in self.MOVIES_APPS:
            return db == 'movies'
        
        # Все остальные приложения по умолчанию идут в default
        return db == 'default'


DATABASE_ROUTERS = ['example.settings.AuthAndMoviesRouter']

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

AUTH_API_LOGIN_URL = os.getenv(
    'AUTH_API_LOGIN_URL', 'http://127.0.0.1:8002/api/v1/auth/login'
)
AUTH_API_REFRESH_URL = os.getenv(
    'AUTH_API_REFRESH_URL', 'http://127.0.0.1:8002/api/v1/auth/refresh'
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        }
    },
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
        },
    },
    'handlers': {
        'debug-console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'filters': ['require_debug_true'],
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['debug-console'],
            'propagate': False,
        }
    },
}
