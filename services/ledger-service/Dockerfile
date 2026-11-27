# --- Build stage: resolve and install locked production dependencies ----------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# --- Runtime stage: no build tools, non-root user -----------------------------
FROM python:3.12-slim AS runtime

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
# Files stay owned by root, so the application user cannot modify them.
COPY --from=builder /app/.venv ./.venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src

USER app
EXPOSE 8000

# Access logs are disabled: the middleware already logs each request as JSON.
CMD ["uvicorn", "--factory", "src.api.main:create_app", \
     "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
