#!/bin/bash

PORT=5000
echo "Checking and killing processes on port $PORT..."
sudo lsof -t -i:${PORT} | xargs -r sudo kill -9
echo "Starting server..."
exec python3 app.py
