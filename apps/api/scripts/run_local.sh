#!/bin/bash
uv run uvicorn src.api:app --reload --lifespan on --host api.dev.local --port 8080
