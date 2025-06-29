# ---- Stage 1: Build dependencies ----
FROM python:3.13.5-alpine3.22 AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
    python3-dev

# Copy requirements
COPY requirements.txt .

# Upgrade pip and install Python deps with prefer-binary
RUN pip install --upgrade --no-cache-dir --root-user-action=ignore pip setuptools wheel && \
    pip install --no-cache-dir --root-user-action=ignore --prefer-binary -r requirements.txt

# ---- Stage 2: Runtime image ----
FROM python:3.13.5-alpine3.22

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Add runtime deps only (keep lean)
RUN apk add --no-cache \
    libpq \
    libffi \
    icu-libs \
    icu-data-full \
    openssl

# Add non-root user
RUN adduser -D appuser

WORKDIR /app

# Copy installed Python packages and binaries from build stage
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy your app code (chown to non-root)
COPY --chown=appuser:appuser . .

# Ensure your entrypoint is executable
RUN chmod +x /app/entrypoint.prod.sh

USER appuser

EXPOSE 8000

CMD ["./entrypoint.prod.sh"]
