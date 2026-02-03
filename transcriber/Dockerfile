FROM python:3.13.5-slim-bookworm

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Копируем shared library
COPY libs/db /libs/db

# Копируем зависимости сервиса
COPY transcriber/pyproject.toml transcriber/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Копируем код сервиса
COPY transcriber/ .

CMD ["uv", "run", "python", "main.py"]
