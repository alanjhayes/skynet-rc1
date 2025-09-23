#!/bin/bash

# Ollama initialization script
# This script ensures the required model is downloaded

MODEL_NAME="${OLLAMA_MODEL}"
OLLAMA_BASE_URL="${OLLAMA_HOST:-http://ollama:11434}"

if [ -z "$MODEL_NAME" ]; then
    echo "ERROR: OLLAMA_MODEL environment variable not set"
    exit 1
fi

echo "Checking if Ollama model $MODEL_NAME is available..."

# Wait for Ollama to be ready
echo "Waiting for Ollama at $OLLAMA_BASE_URL to be ready..."
until curl -f "$OLLAMA_BASE_URL/api/tags" >/dev/null 2>&1; do
    echo "Waiting for Ollama to start..."
    sleep 5
done

# Set OLLAMA_HOST for the ollama CLI
export OLLAMA_HOST="$OLLAMA_BASE_URL"

# Check if model exists
echo "Checking if model $MODEL_NAME exists..."
if ! ollama list | grep -q "$MODEL_NAME"; then
    echo "Model $MODEL_NAME not found. Downloading..."
    ollama pull "$MODEL_NAME"
    if [ $? -eq 0 ]; then
        echo "Model $MODEL_NAME downloaded successfully."
    else
        echo "ERROR: Failed to download model $MODEL_NAME"
        exit 1
    fi
else
    echo "Model $MODEL_NAME is already available."
fi

echo "Ollama initialization complete."