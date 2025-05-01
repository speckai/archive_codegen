#!/bin/sh

docker info >/dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "ERROR: Cannot connect to the Docker daemon. Check if docker is running."
	exit 1
fi

IMAGE_NAME="github-consumer"

docker build -f Dockerfile . -t "${IMAGE_NAME}"

echo "Image ${IMAGE_NAME} built successfully!"
