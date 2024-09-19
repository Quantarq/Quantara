#!/bin/bash

echo "Starting the server ..."
exec "$@"

uvicorn web_app.api.main:app --host 0.0.0.0 --port 8000 --reload