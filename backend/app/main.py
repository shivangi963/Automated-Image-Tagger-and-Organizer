from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, create_indexes
from app.routers import auth, images, albums, search
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    debug=settings.DEBUG
)

# ✅ CORS middleware FIRST (before routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        logger.exception("Request failed: %s %s (%.2fms)", request.method, request.url.path, elapsed_ms)
        raise
    else:
        elapsed_ms = (time.time() - start) * 1000
        logger.info("%s %s completed_in=%.2fms status_code=%s", request.method, request.url.path, elapsed_ms, response.status_code)
        return response

# ✅ Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": "Validation error", "errors": errors, "detail": errors},
    )

@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    detail = exc.detail
    if isinstance(detail, list):
        errors = detail
        message = "; ".join([str(d.get("msg") or d) for d in detail]) if detail else str(detail)
    elif isinstance(detail, dict):
        errors = [detail]
        message = detail.get("msg") or detail.get("detail") or str(detail)
    else:
        errors = []
        message = str(detail)
    logger.warning("HTTP error %s on %s %s: %s", exc.status_code, request.method, request.url.path, message)
    return JSONResponse(status_code=exc.status_code, content={"message": message, "errors": errors, "detail": detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal server error", "errors": [], "detail": "internal_error"},
    )

# ✅ Include routers AFTER middleware
app.include_router(auth.router)
app.include_router(images.router)
app.include_router(albums.router)
app.include_router(search.router)

# ✅ Startup event
@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("Starting Automated Image Tagger & Organizer")
    logger.info("=" * 60)
    try:
        await connect_to_mongo()
        await create_indexes()
        logger.info("✓ Application startup complete")
    except Exception as e:
        logger.exception("Startup error - aborting application: %s", e)
        raise

# ✅ Shutdown event
@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down application...")
    try:
        await close_mongo_connection()
        logger.info("✓ Application shutdown complete")
    except Exception:
        logger.exception("Error during shutdown (continuing exit)")

# ✅ Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.API_VERSION,
    }

# ✅ Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Automated Image Tagger & Organizer",
        "version": settings.API_VERSION,
        "docs": "/docs",
    }