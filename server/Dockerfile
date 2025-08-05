FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# This ENV will be set by docker-compose, but it's good practice to have it here too.
ENV DJANGO_SETTINGS_MODULE=soundly.settings.dev

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y \
    libproj-dev \
    gdal-bin \
    libpq-dev \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./server/ /app/

RUN pip install --no-cache-dir -r requirements/dev.txt

EXPOSE 8000

# The command is defined in docker-compose.yml
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]