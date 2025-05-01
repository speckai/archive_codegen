#!/bin/bash
uv run uvicorn src.main:app --reload --lifespan on --host 0.0.0.0 --port 8040 --workers 1
