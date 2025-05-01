FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /build

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY src/ ./src/

FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    curl \
    git \
    socat \
    lsof \
    lz4 \
    ripgrep \
    psmisc && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    npm install -g corepack@latest && \
    corepack enable && \
    corepack enable pnpm && \
    corepack enable yarn && \
    npm install -g bun --force && \
    npm install -g turbo --force && \
    corepack prepare yarn && \
    corepack prepare pnpm && \
    corepack use pnpm@latest-10 && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /efs/pnpm-store /efs/npm-cache /efs/yarn-cache /efs/bun-cache /tmp/pnpm-local-cache && \
    chmod -R 777 /efs /tmp/pnpm-local-cache && \
    echo "network-concurrency=192\nshamefully-hoist=true\nchild-concurrency=16\nprefer-offline=true\nregistry-timeout=60000\nfetch-timeout=60000\nfetch-retries=5\nstore-dir=/efs/pnpm-store\ncache-dir=/efs/pnpm-store" > /root/.npmrc
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# NVM
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl

RUN mkdir -p /home/user
ENV BASH_ENV /home/user/.bash_env
RUN touch "${BASH_ENV}"
RUN echo '. "${BASH_ENV}"' >> ~/.bashrc

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.2/install.sh | PROFILE="${BASH_ENV}" bash
RUN echo node > .nvmrc
RUN nvm install

WORKDIR /app

COPY --from=builder /build/ /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

VOLUME /efs

EXPOSE 2000-5999 8000-8999

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    NODE_OPTIONS=--max-old-space-size=6144 \
    HOST=0.0.0.0 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1 \
    PNPM_STORE_DIR=/efs/pnpm-store \
    PNPM_CACHE_DIR=/efs/pnpm-store \
    NPM_CACHE_DIR=/efs/npm-cache \
    PNPM_NETWORK_CONCURRENCY=192 \
    PNPM_CHILD_CONCURRENCY=16 \
    PNPM_SHAMEFULLY_HOIST=true \
    PNPM_PREFER_OFFLINE=true \
    PNPM_REGISTRY_TIMEOUT=60000 \
    PNPM_FETCH_TIMEOUT=60000 \
    PNPM_FETCH_RETRIES=5 \
    BUN_CACHE_DIR=/efs/bun-cache \
    BUN_INSTALL_CACHE_DIR=/efs/bun-cache \
    UV_CACHE_DIR=/root/.cache/uv

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]