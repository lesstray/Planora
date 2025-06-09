# Используем Python
FROM python:3.10-slim

# Устанавливаем переменные среды
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем зависимости
RUN apt-get update \
  && apt-get install -y libpq-dev gcc \
  && pip install --upgrade pip

# Копируем проект
WORKDIR /app
COPY . /app

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Порт, который Django будет слушать
EXPOSE 8000

# Команда по умолчанию (можно заменить)
CMD ["python", "planora/manage.py", "runserver", "0.0.0.0:8000"]