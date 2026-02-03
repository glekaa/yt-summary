FROM python:3.13.5-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Копируем shared library
COPY libs/db /libs/db

# Копируем зависимости сервиса
COPY gateway/pyproject.toml gateway/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Копируем код сервиса
COPY gateway/ .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
