from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from core.settings import settings
from core.firebase import initialize_firebase
from core.middleware import setup_middleware
from core.redis import check_redis_connection
from apps.auth.routes import router as auth_router
from apps.documents.routes import router as documents_router
import logging

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    initialize_firebase()
    
    # Check Redis connection
    if not check_redis_connection():
        logger.warning("Redis connection failed - document upload features may not work")
    else:
        logger.info("Redis connection established")
    
    logger.info("Application started")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG Dashboard API with Firebase Authentication",
    lifespan=lifespan,
)

setup_middleware(app)

app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "manage:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )