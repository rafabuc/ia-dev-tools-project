"""
Main FastAPI application for DevOps Copilot.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.utils.logging import get_logger

# Import routers
try:
    #from backend.api.v1.endpoints.workflows import router as workflows_router
    from backend.api.routes.workflows import router as workflows_router
    workflows_available = True
except ImportError as e:
    print(f"Warning: Could not import workflows router: {e}")
    workflows_available = False

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DevOps Copilot API",
    description="AI-powered DevOps automation platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers if available
if workflows_available:
    app.include_router(workflows_router)
else:
    @app.get("/api/workflows/health")
    async def workflows_unavailable():
        return {"status": "workflows_module_not_loaded"}

# Health and root endpoints
@app.get("/")
async def root():
    return {
        "message": "DevOps Copilot API",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "openapi": "/openapi.json",
            "workflows": "/api/workflows" if workflows_available else "module_not_loaded"
        }
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    from backend.celery_app import app as celery_app
    
    health_status = {
        "api": "healthy",
        "service": "devops-copilot",
        "timestamp": "2025-12-30T02:30:00Z",
        "dependencies": {}
    }
    
    # Check Redis (Celery broker)
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, db=0, socket_timeout=1)
        r.ping()
        health_status["dependencies"]["redis"] = "healthy"
    except Exception as e:
        health_status["dependencies"]["redis"] = f"unhealthy: {str(e)}"
    
    # Check database
    try:
        from backend.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        health_status["dependencies"]["database"] = f"unhealthy: {str(e)}"
    
    return health_status

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("DevOps Copilot starting up")
    
    # Initialize database if needed
    try:
        from backend.database import engine
        from backend.models.workflow import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning(f"Could not initialize database: {e}")
    
    logger.info("Startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down DevOps Copilot")


@app.get("/debug/routes")
async def debug_routes():
    """Endpoint para depurar rutas registradas."""
    routes = []
    for route in app.routes:
        route_info = {
            "path": route.path,
            "methods": getattr(route, "methods", []),
            "name": getattr(route, "name", ""),
            "endpoint": str(getattr(route, "endpoint", "")),
        }
        routes.append(route_info)
    
    # Filtrar solo las rutas de workflows
    workflow_routes = [r for r in routes if "/workflows" in r["path"]]
    
    return {
        "all_routes": routes,
        "workflow_routes": workflow_routes
    }
    
# Development server
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )