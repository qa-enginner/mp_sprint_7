#!/usr/bin/env bash

set -e

echo "=== Настройка баз данных ==="

# 1. Создаем миграции для всех приложений
echo "Создание миграций..."
python manage.py makemigrations

# 2. Применяем миграции для БД default (авторизация)
echo "Миграции для БД default (авторизация)..."
python manage.py migrate --database=default

# 3. Применяем миграции только для приложения movies в БД movies
echo "Миграции для БД movies (контент)..."
python manage.py migrate --fake movies --database=movies

# 4. Создаем суперпользователя в БД default
echo "Создание суперпользователя..."
python manage.py createsuperuser --noinput --database=default || true

# 5. Собираем статику
echo "Сбор статики..."
python manage.py collectstatic --no-input

# 6. Настройка прав
echo "Настройка прав..."
chown www-data:www-data /var/log || true

echo "=== Запуск uWSGI ==="
# Запускаем uWSGI
uwsgi --strict --ini uwsgi.ini




# set -e

# # Убедимся, что у users есть миграция
# python manage.py makemigrations users

# # Применяем миграции в правильном порядке
# python manage.py migrate contenttypes
# python manage.py migrate auth
# python manage.py migrate users  # Реально создаём таблицу
# python manage.py migrate admin
# python manage.py migrate --fake movies 0001_initial
# python manage.py migrate

# python manage.py collectstatic --no-input
# python manage.py createsuperuser --noinput || true 

# chown www-data:www-data /var/log

# uwsgi --strict --ini uwsgi.ini
