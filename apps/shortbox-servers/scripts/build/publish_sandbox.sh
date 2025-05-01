#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# AWS Account and region
AWS_ACCOUNT="654654524154"
AWS_REGION="us-west-1"
ECR_URL="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_URL}"

# Push manager
echo -e "${GREEN}Pushing manager to ECR...${NC}"
docker tag shortbox/manager:latest "${ECR_URL}"/shortbox/manager:latest
docker push "${ECR_URL}"/shortbox/manager:latest

# Push container
echo -e "${GREEN}Pushing container to ECR...${NC}"
docker tag shortbox/container:latest "${ECR_URL}"/shortbox/container:latest
docker push "${ECR_URL}"/shortbox/container:latest

echo -e "${GREEN}Successfully pushed images to ECR!${NC}"
