FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc postgresql-client \
    curl procps unzip git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /project/apps/api/

COPY ./apps/api/pyproject.toml ./apps/api/uv.lock* ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY ./apps/api/src/ ./src/

FROM python:3.13-slim

WORKDIR /project/apps/api/

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev postgresql-client \
    curl procps unzip git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    nginx supervisor \
    ffmpeg \
    ripgrep \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY --from=builder /project/apps/api/ ./

COPY ./apps/api/nginx.conf /etc/supervisor/conf.d/nginx.conf
COPY ./apps/api/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN uv run -m playwright install --with-deps chromium

EXPOSE 80

ENV PYTHONPATH=/project/apps/api \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/root/.cache/uv \
    UVICORN_RELOAD="" \
    IS_DOCKER="true" \
    USING_NGINX="true"

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
