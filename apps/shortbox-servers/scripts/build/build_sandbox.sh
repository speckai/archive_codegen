#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHORTBOX_DIR="$(dirname "$(dirname "${SCRIPT_DIR}")")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Building sandbox containers...${NC}"

# Build the container service
echo -e "${GREEN}Building shortbox container...${NC}"
docker build --platform linux/amd64 -t shortbox/container:latest -f "${SHORTBOX_DIR}/container/Dockerfile" "${SHORTBOX_DIR}/container"

# Build the manager service
echo -e "${GREEN}Building shortbox manager...${NC}"
docker build --platform linux/amd64 -t shortbox/manager:latest -f "${SHORTBOX_DIR}/manager/Dockerfile" "${SHORTBOX_DIR}/manager"

echo -e "${GREEN}Successfully built both containers!${NC}"

# Show the built images
echo -e "\n${YELLOW}Built images:${NC}"
docker images | grep shortbox
