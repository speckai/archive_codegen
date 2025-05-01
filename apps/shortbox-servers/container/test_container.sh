#!/bin/bash
set -e

echo "Building container image..."
docker build -t shortbox-container-test .

echo "Running container with bash to diagnose uvicorn..."
docker run --rm -it shortbox-container-test bash -c "which uvicorn || echo 'uvicorn not found'; pip list | grep uvicorn || echo 'uvicorn not installed'; which uv; uv --version; echo 'Testing uv run...'; uv run -c 'import sys; print(sys.executable)'; echo 'PATH:'; echo \$PATH"
