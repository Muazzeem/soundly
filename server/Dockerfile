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

WORKDIR /app
COPY . /app/  # Copy all files from the build context (./server/) to /app

RUN pip install --no-cache-dir -r requirements/dev.txt

EXPOSE 8000

# The command is defined in docker-compose.yml, but a good default is to run a web server.
# This is a sensible default for the image itself.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
