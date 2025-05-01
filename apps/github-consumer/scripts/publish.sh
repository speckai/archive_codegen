#!/bin/bash

# Exit on any error
set -e

# Configuration
AWS_REGION="us-west-1"
ECR_REPO="github-consumer"
AWS_ACCOUNT_ID="654654524154"
IMAGE_TAG="latest"
PLATFORM="linux/amd64"

# Full ECR repository URL
ECR_REPO_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

echo "🚀 Starting Docker build and publish process..."

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

echo "📦 Building Docker image..."
docker build --platform ${PLATFORM} -t ${ECR_REPO}:${IMAGE_TAG} .

echo "🔑 Logging into AWS ECR..."
aws ecr get-login-password --region ${AWS_REGION} |
	docker login --username AWS --password-stdin ${ECR_REPO_URL}

echo "🏷️  Tagging image for ECR..."
docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_REPO_URL}:${IMAGE_TAG}

echo "⬆️  Pushing image to ECR..."
docker push ${ECR_REPO_URL}:${IMAGE_TAG}

echo "✅ Successfully built and pushed image to ECR!"
echo "Image: ${ECR_REPO_URL}:${IMAGE_TAG}"
