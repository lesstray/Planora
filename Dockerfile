FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем зависимости, включая psql
RUN apt-get update \
  && apt-get install -y libpq-dev gcc postgresql-client \
  && pip install --upgrade pip

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
