FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=soundly.settings.dev

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libproj-dev \
    gdal-bin \
    libpq-dev \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/server/

COPY ./server /app/server/

RUN pip install --no-cache-dir -r requirements/dev.txt
