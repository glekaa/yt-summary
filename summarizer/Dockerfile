FROM python:3.13.5-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Копируем shared library
COPY libs/db /libs/db

# Копируем зависимости сервиса
COPY summarizer/pyproject.toml summarizer/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Копируем код сервиса
COPY summarizer/ .

CMD ["uv", "run", "python", "main.py"]
