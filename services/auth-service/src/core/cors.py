"""
CORS configuration for the auth service.
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from .config import settings


def setup_cors(app: FastAPI):
    """
    Configure CORS middleware for the FastAPI application with separate
    settings for development and production environments.
    """
    # Parse allowed origins from environment variable
    if settings.cors_allowed_origins:
        # Split by comma and strip whitespace
        origins = [
            origin.strip()
            for origin in settings.cors_allowed_origins.split(",")
            if origin.strip()
        ]
    else:
        origins = []

    # Determine if we're in development mode
    is_development = settings.environment.lower() in (
        "development", "dev", "local"
    )

    # Development defaults: allow localhost origins
    if is_development and not origins:
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
        ]

    # Handle CORS_ALLOW_ALL_ORIGINS flag
    if settings.cors_allow_all_origins:
        # When allowing all origins, credentials cannot be True per CORS spec
        # So we set origins to ["*"] and disable allow_credentials
        origins = ["*"]
        allow_credentials = False
    else:
        allow_credentials = True

    # Parse allowed methods
    if settings.cors_allow_methods:
        allow_methods = [
            method.strip()
            for method in settings.cors_allow_methods.split(",")
            if method.strip()
        ]
    else:
        # Safe default methods for production
        allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]

    # Parse allowed headers
    if settings.cors_allow_headers:
        allow_headers = [
            header.strip()
            for header in settings.cors_allow_headers.split(",")
            if header.strip()
        ]
    else:
        # Safe default headers
        allow_headers = ["Content-Type", "Authorization", "Accept"]

    # Parse expose headers
    if settings.cors_expose_headers:
        expose_headers = [
            header.strip()
            for header in settings.cors_expose_headers.split(",")
            if header.strip()
        ]
    else:
        expose_headers = []

    # In development, we can be more permissive if needed
    if is_development:
        # Optionally allow all methods and headers in dev
        # But keep it secure by default - uncomment if needed
        # allow_methods = ["*"]
        # allow_headers = ["*"]
        # expose_headers = ["*"]
        pass

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        expose_headers=expose_headers,
    )
