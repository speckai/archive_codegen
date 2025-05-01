#!/bin/bash

cleanup() {
	export USING_NGINX="false"
	echo "Stopping all processes..."

	pkill -P $(pgrep -f "supervisord -c supervisord.conf") 2>/dev/null
	pkill -f "supervisord -c supervisord.conf" 2>/dev/null

	pkill -f "uvicorn src.api:app" 2>/dev/null

	sudo nginx -s stop 2>/dev/null || true
	pkill -f "nginx" 2>/dev/null
	exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

echo "Stopping any existing nginx processes..."
sudo nginx -s stop 2>/dev/null || true

export USING_NGINX="true"
export UVICORN_RELOAD="--reload"
supervisord -c supervisord.conf

# Wait for supervisor exit
wait

# Cleanup on exit
cleanup
