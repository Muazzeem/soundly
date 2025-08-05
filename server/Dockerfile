FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=soundly.settings.dev
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    build-essential \ 
    python3-dev \
    libpq-dev
WORKDIR /app/server/
COPY . /app/server/
RUN pip --timeout 600 install --upgrade pip setuptools wheel
RUN pip install -r requirements/dev.txt


