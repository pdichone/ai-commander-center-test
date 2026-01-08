"""
Main entry point for Render deployment.
Re-exports the FastAPI app from api.main
"""

from api.main import app

# This allows Render to use: uvicorn app:app
__all__ = ["app"]
