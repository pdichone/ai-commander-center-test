#!/bin/bash
# Startup script for Streamlit on Render

# Use PORT from Render (defaults to 8501 for local dev)
PORT=${PORT:-8501}

echo "Starting Streamlit UI on port $PORT"
echo "API Backend: $API_BASE_URL"

streamlit run streamlit_app.py \
    --server.port $PORT \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
