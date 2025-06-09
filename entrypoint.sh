#!/bin/bash
set -e

# Ожидаем доступность БД
echo "Waiting for PostgreSQL..."

until PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - running migrations"

# Миграции и запуск
python planora/manage.py makemigrations
python planora/manage.py migrate
python planora/manage.py runserver 0.0.0.0:8000
