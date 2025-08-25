"""Test app configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
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


# Simplified middleware for testing
class TestSecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response


class TestRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)


class TestAuthContextMiddleware(BaseHTTPMiddleware):
    """Simplified auth middleware for testing."""
    
    async def dispatch(self, request, call_next):
        # Skip auth processing in tests - handled by dependency overrides
        return await call_next(request)


def create_test_app() -> FastAPI:
    """Create a test FastAPI app without lifespan events."""
    test_app = FastAPI(
        title="Real2.AI API - Test",
        description="Test version without lifespan events",
        version="1.0.0-test",
    )
    
    # Add simplified CORS
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add simplified middleware
    test_app.add_middleware(TestSecurityHeadersMiddleware)
    test_app.add_middleware(TestRateLimitMiddleware)
    test_app.add_middleware(TestAuthContextMiddleware)
    
    # Include routers
    test_app.include_router(health_router)
    test_app.include_router(auth_router)
    test_app.include_router(documents_router)
    test_app.include_router(contracts_router)
    test_app.include_router(onboarding_router)
    test_app.include_router(users_router)
    test_app.include_router(ocr_router)
    test_app.include_router(websockets_router)
    test_app.include_router(property_profile_router)
    test_app.include_router(property_intelligence_router)
    test_app.include_router(cache_router)
    
    return test_app