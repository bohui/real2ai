"""
Real2.AI FastAPI Backend - Refactored
Australian Real Estate AI Assistant
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
import logging
from typing import Dict, Optional, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.config import get_settings
from app.core.logging_config import configure_logging

# Configure logging to respect LOG_LEVEL from environment or settings
settings = get_settings()

level_name = os.getenv("LOG_LEVEL", settings.log_level or "INFO").upper()
log_level = getattr(logging, level_name, logging.INFO)

# Configure logging formatter via env/setting: LOG_FORMAT in {json, console}
log_format_name = os.getenv(
    "LOG_FORMAT", getattr(settings, "log_format", "json")
).lower()
use_json = log_format_name == "json"
configure_logging(level=log_level, use_json=use_json)

# Ensure key loggers follow the configured level even if basicConfig was a no-op
for logger_name in (
    "app",
    "app.router.websockets",
    "uvicorn",
    "uvicorn.access",
):
    logging.getLogger(logger_name).setLevel(log_level)

logger = logging.getLogger(__name__)

# Import application modules
from app.services.communication.websocket_singleton import websocket_manager
from app.core.langsmith_init import initialize_langsmith, get_langsmith_status

# Import routers
from app.router.auth import router as auth_router
from app.router.documents import router as documents_router
from app.router.contracts import router as contracts_router
from app.router.users import router as users_router
from app.router.onboarding import router as onboarding_router
from app.router.ocr import router as ocr_router
from app.router.health import router as health_router
from app.router.websockets import router as websockets_router
from app.router.property_profile import router as property_profile_router
from app.router.property_intelligence import router as property_intelligence_router
from app.router.cache import router as cache_router
from app.router.evaluation import router as evaluation_router
from app.middleware.auth_middleware import setup_auth_middleware
from app.clients.factory import get_supabase_client

# Simple rate limiting middleware (IP + path windowed)
import time
from starlette.requests import Request
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._buckets: Dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        now = time.time()
        window_start = now - 60.0
        bucket = self._buckets.setdefault(key, [])
        # prune old
        while bucket and bucket[0] < window_start:
            bucket.pop(0)
        if len(bucket) >= self.requests_per_minute:
            return Response("Rate limit exceeded", status_code=429)
        bucket.append(now)
        return await call_next(request)


# Initialize services (no global service instances required)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Real2.AI API...")

    # Run startup diagnostics including time sync checks
    try:
        from app.startup_diagnostics import run_startup_diagnostics

        await run_startup_diagnostics()
    except Exception as e:
        logger.error(f"Startup diagnostics failed: {e}")
        # Continue startup even if diagnostics fail

    # Initialize LangSmith tracing
    langsmith_enabled = initialize_langsmith()
    if langsmith_enabled:
        status = get_langsmith_status()
        logger.info(f"LangSmith tracing enabled for project: {status['project_name']}")
    else:
        logger.info("LangSmith tracing disabled")

    # Validate production security configuration
    if settings.environment == "production":
        logger.info("Validating production security configuration...")

        # Validate CORS origins in production
        allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
        if not allowed_origins_env or "localhost" in allowed_origins_env:
            logger.critical(
                "CRITICAL: ALLOWED_ORIGINS must be configured for production"
            )
            logger.critical("Current origins include localhost or are empty")
            logger.critical(
                "Set ALLOWED_ORIGINS environment variable with production domains only"
            )
            raise RuntimeError("Invalid ALLOWED_ORIGINS configuration for production")

        logger.info("Production security configuration validated successfully")

    # Validate JWT configuration on startup
    logger.info("Validating JWT configuration...")
    try:
        from app.core.auth import validate_jwt_configuration

        jwt_validation = validate_jwt_configuration()

        if jwt_validation["status"] == "critical":
            logger.critical("CRITICAL JWT CONFIGURATION ISSUES FOUND:")
            for issue in jwt_validation["issues"]:
                logger.critical(f"  - {issue}")
            logger.critical("Recommendations:")
            for rec in jwt_validation["recommendations"]:
                logger.critical(f"  - {rec}")
            logger.critical(
                "Application startup FAILED due to critical JWT security issues"
            )
            raise RuntimeError("Critical JWT configuration issues prevent startup")

        elif jwt_validation["status"] == "warning":
            logger.warning("JWT configuration warnings:")
            for warning in jwt_validation["warnings"]:
                logger.warning(f"  - {warning}")
            logger.warning("Recommendations:")
            for rec in jwt_validation["recommendations"]:
                logger.warning(f"  - {rec}")

        logger.info("JWT configuration validation completed successfully")

    except Exception as e:
        if "Critical JWT configuration issues" in str(e):
            # Re-raise critical issues
            raise
        logger.error(f"JWT validation failed with error: {e}")
        logger.error("Continuing startup but JWT security may be compromised")

    # No global service initializations required

    # Initialize task recovery system
    logger.info("Initializing task recovery system...")
    try:
        from app.core.recovery_orchestrator import recovery_orchestrator
        from app.services.recovery_monitor import recovery_monitor

        # Run startup recovery sequence
        recovery_results = await recovery_orchestrator.startup_recovery_sequence()
        logger.info(f"Task recovery completed: {recovery_results.summary}")

        # Start recovery monitoring
        await recovery_monitor.start_monitoring()
        logger.info("Recovery monitoring started")

    except Exception as e:
        logger.error(f"Task recovery initialization failed: {e}")
        # Continue startup even if recovery fails
        pass

    logger.info("Real2.AI API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Real2.AI API...")

    # Stop recovery monitoring
    try:
        from app.services.recovery_monitor import recovery_monitor

        await recovery_monitor.stop_monitoring()
        logger.info("Recovery monitoring stopped")
    except Exception as e:
        logger.error(f"Failed to stop recovery monitoring: {e}")

    # Close websocket connections
    await websocket_manager.disconnect_all()

    logger.info("Real2.AI API shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="Real2.AI API",
    description="Australian Real Estate AI Assistant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
# Get allowed origins from environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

# Add production origins if configured
if os.getenv("ENVIRONMENT") == "production":
    production_origins = [
        "https://real2.ai",
        "https://www.real2.ai",
        "https://app.real2.ai",
    ]
    allowed_origins.extend(production_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Mx-ReqToken",
        "Keep-Alive",
        "X-Requested-With",
        "If-Modified-Since",
        "X-Refresh-Token",
    ],
    expose_headers=["Content-Length", "Content-Type", "Authorization"],
    max_age=3600,  # Cache preflight responses for 1 hour
)


# Add basic security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Only set headers if not already set by upstream
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload"
        )
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware, requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "120"))
)

# Add authentication middleware
setup_auth_middleware(app, validate_token=True)

# Expose a module-level database client placeholder for tests to patch
# Tests expect `app.main.db_client` to exist and be patchable
db_client = None

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(contracts_router)
app.include_router(onboarding_router)  # More specific route first
app.include_router(users_router)
app.include_router(ocr_router)
app.include_router(websockets_router)
app.include_router(property_profile_router)
app.include_router(property_intelligence_router)
app.include_router(cache_router)
app.include_router(evaluation_router)


# Import background tasks
from app.tasks.background_tasks import (
    # process_document_background,
    # analyze_contract_background,
    enhanced_reprocess_document_with_ocr_background,
    batch_ocr_processing_background,
    generate_pdf_report,
)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
    )
