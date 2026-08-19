# ---- Stage 1: Build dependencies ----
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install build dependencies for C-extension packages (like psycopg2, cryptography)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    build-base \
    icu-libs \
    icu-data-full \
    openssl-dev \
    python3-dev \
    libwebp-dev

# Resolve and install deps from pyproject.toml/uv.lock (prod group, no dev deps) into
# /app/.venv, without installing this project itself (it's an app, not a distributable package).
COPY pyproject.toml uv.lock .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group prod --no-install-project --no-editable

# ---- Stage 2: Runtime image ----
FROM python:3.12-alpine3.23

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Add runtime deps only (keep lean)
RUN apk add --no-cache \
    libpq \
    libffi \
    icu-libs \
    icu-data-full \
    openssl \
    netcat-openbsd \
    libwebp

# Add non-root user
RUN adduser -D appuser

WORKDIR /app

# Copy the resolved virtualenv from the build stage
COPY --from=builder /app/.venv /app/.venv

# Copy your app code (chown to non-root)
COPY --chown=appuser:appuser . .

# Create staticfiles and media directories with proper ownership
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app/staticfiles /app/media

# Ensure your entrypoint is executable
RUN chmod +x /app/entrypoint.prod.sh

USER appuser

EXPOSE 8000

CMD ["./entrypoint.prod.sh"]
