#!/bin/sh

# Check if Docker is running
docker info >/dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "ERROR: Cannot connect to the Docker daemon. Check if docker is running."
	exit 1
fi

# Image and Container names
IMAGE_NAME="speck-server"
CONTAINER_NAME="speck-server-container"

# Check if a container with the same name is already running
if docker ps -a | grep -q "${CONTAINER_NAME}"; then
	echo "Container with name ${CONTAINER_NAME} already exists. Stopping and removing..."
	docker stop "${CONTAINER_NAME}"
	docker rm "${CONTAINER_NAME}"
fi

# Run the container (without -d to show output in the terminal)
docker run -p 8080:8080 --env-file .env --name "${CONTAINER_NAME}" "${IMAGE_NAME}"

# Check if the container exited with any error
if [ $? -eq 0 ]; then
	echo "Container ${CONTAINER_NAME} exited gracefully!"
else
	echo "Container ${CONTAINER_NAME} encountered an error and exited."
	exit 2
fi
