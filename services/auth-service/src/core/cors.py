"""
CORS configuration for the auth service.
"""
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI


def setup_cors(app: FastAPI):
    """
    Configure CORS middleware for the FastAPI application.
    """
    # Allow all origins in development if CORS_ALLOW_ALL_ORIGINS is set
    if os.getenv("CORS_ALLOW_ALL_ORIGINS", "false").lower() == "true":
        origins = ["*"]
    else:
        # List of allowed origins (can be extended via environment variable)
        origins = [
            "http://localhost",
            "http://localhost:80",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://localhost:8002",
            "http://127.0.0.1",
            "http://127.0.0.1:80",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
            "http://127.0.0.1:8002",
            # Add any other frontend URLs
        ]

    # Allow all origins for development (can be restricted in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )