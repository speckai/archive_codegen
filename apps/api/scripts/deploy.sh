#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Azure CLI is installed
if ! command -v az &>/dev/null; then
	echo -e "${RED}Error: Azure CLI is not installed. Please install it first.${NC}"
	exit 1
fi

# Check if Docker is installed
if ! command -v docker &>/dev/null; then
	echo -e "${RED}Error: Docker is not installed. Please install it first.${NC}"
	exit 1
fi

# Configuration
APP_NAME="speck-api"
RESOURCE_GROUP="speck-main-rg"
IMAGE_NAME="ghcr.io/speckai/speck-api"
TAG=$(git rev-parse --short HEAD)
MONOREPO_ROOT="/Users/raghav/dev/speck/monorepo"

# Change to monorepo root directory
cd "${MONOREPO_ROOT}"

echo -e "${BLUE}Building Docker image from ${PWD}...${NC}"
docker build --platform linux/amd64 -t ${IMAGE_NAME}:${TAG} -t ${IMAGE_NAME}:latest -f apps/api/Dockerfile .

echo -e "${BLUE}Pushing Docker image...${NC}"
docker push ${IMAGE_NAME}:${TAG}
docker push ${IMAGE_NAME}:latest

echo -e "${BLUE}Updating App Service configuration...${NC}"
az webapp config container set \
	--name ${APP_NAME} \
	--resource-group ${RESOURCE_GROUP} \
	--container-image-name ${IMAGE_NAME}:${TAG} \
	--container-registry-url https://ghcr.io \
	--container-registry-user $GITHUB_USERNAME \
	--container-registry-password $GITHUB_TOKEN

echo -e "${BLUE}Restarting App Service...${NC}"
az webapp restart --name ${APP_NAME} --resource-group ${RESOURCE_GROUP}

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Image: ${IMAGE_NAME}:${TAG}${NC}"
echo -e "${GREEN}App URL: https://${APP_NAME}.azurewebsites.net${NC}"
