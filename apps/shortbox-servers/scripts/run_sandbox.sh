#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX_DIR="$(dirname "${SCRIPT_DIR}")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if docker-compose is installed
if ! command -v docker-compose &>/dev/null; then
	echo -e "${RED}Error: docker-compose is not installed${NC}"
	exit 1
fi

# Build the images first if they don't exist
if ! docker images | grep -q "speckai/sandbox-container" || ! docker images | grep -q "speckai/sandbox-manager"; then
	echo -e "${YELLOW}Building sandbox images first...${NC}"
	"${SCRIPT_DIR}/build_sandbox.sh"
fi

echo -e "${GREEN}Starting sandbox environment...${NC}"
cd "${SANDBOX_DIR}"

# Run docker-compose
docker-compose up "$@"
