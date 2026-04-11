FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml README.md ./
COPY ccp ./ccp

RUN uv pip install --system --no-cache ".[django-app]"

EXPOSE 8000

WORKDIR /app/ccp/app/django-app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
