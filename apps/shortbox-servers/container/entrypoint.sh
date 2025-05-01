#!/bin/bash

# Initialize nvm
export NVM_DIR="${HOME}/.nvm"
[[ -s "${NVM_DIR}/nvm.sh" ]] && \. "${NVM_DIR}/nvm.sh"
[[ -s "${NVM_DIR}/bash_completion" ]] && \. "${NVM_DIR}/bash_completion"

# Create cache directories if they do not exist
mkdir -p "${PNPM_STORE_DIR:-/efs/pnpm-store}"
mkdir -p "${NPM_CACHE_DIR:-/efs/npm-cache}"
mkdir -p "${YARN_CACHE_FOLDER:-/efs/yarn-cache}"
mkdir -p "${BUN_CACHE_DIR:-/efs/bun-cache}"

# Set permissions on main directories only, not recursively
chmod 777 /efs || echo "Warning: Could not set permissions on /efs"
chmod 777 "${PNPM_STORE_DIR:-/efs/pnpm-store}" || echo "Warning: Could not set permissions on pnpm store"
chmod 777 "${NPM_CACHE_DIR:-/efs/npm-cache}" || echo "Warning: Could not set permissions on npm cache"
chmod 777 "${YARN_CACHE_FOLDER:-/efs/yarn-cache}" || echo "Warning: Could not set permissions on yarn cache"
chmod 777 "${BUN_CACHE_DIR:-/efs/bun-cache}" || echo "Warning: Could not set permissions on bun cache"

# Configure package managers to use the shared cache
pnpm config set store-dir "${PNPM_STORE_DIR:-/efs/pnpm-store}"
npm config set cache "${NPM_CACHE_DIR:-/efs/npm-cache}"
yarn config set globalFolder "${YARN_CACHE_FOLDER:-/efs/yarn-cache}"
yarn config set enableGlobalCache true
# Bun uses environment variables for cache configuration
export BUN_INSTALL_CACHE_DIR=${BUN_CACHE_DIR:-/efs/bun-cache}

# Log configuration
echo "Package manager caches configured:"
echo "PNPM: $(pnpm config get store-dir)"
echo "NPM: $(npm config get cache)"
echo "YARN: $(yarn config get cache-folder)"
echo "BUN: ${BUN_INSTALL_CACHE_DIR}"
echo "Node.js version: $(node -v)"
echo "npm version: $(npm -v)"
echo "Yarn version: $(yarn -v)"
echo "Git version: $(git --version)"

# Execute the command passed to docker
exec "$@"
