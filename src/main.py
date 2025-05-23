import uvicorn
from fastapi import FastAPI, HTTPException, Request # Removed File, UploadFile
from fastapi.responses import JSONResponse # Removed HTMLResponse, RedirectResponse
# from fastapi.staticfiles import StaticFiles # Removed, as files are served via router
# import os # Keep for os.path.abspath if still used, but UPLOAD_DIRECTORY direct use is gone
# import shutil # Removed
# from typing import List # Removed
import logging

# Import settings and new middleware/errors
from src.config import settings
from src.middleware.logging_middleware import request_logging_middleware
from src.middleware.custom_errors import UnsupportedMediaTypeError
from src.routers.file_router import router as file_router # Import the new router
from src.services.file_service import start_periodic_cleanup, stop_periodic_cleanup # For startup/shutdown

# Configure logging using settings from src.config
logging.basicConfig(level=settings.LOG_LEVEL.upper(),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# UPLOAD_DIRECTORY and MAX_FILE_SIZE are no longer directly used in main.py
# They are used within settings and the file_router.

app = FastAPI(title="Python File Upload Service")

# Add startup and shutdown event handlers
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: Starting periodic cleanup task...")
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True) # Ensure upload dir exists
    start_periodic_cleanup()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown: Stopping periodic cleanup task...")
    stop_periodic_cleanup()

# Add middleware
app.middleware("http")(request_logging_middleware)

# Add custom exception handler
@app.exception_handler(UnsupportedMediaTypeError)
async def unsupported_media_type_handler(request: Request, exc: UnsupportedMediaTypeError) -> JSONResponse:
    logger.warning(f"UnsupportedMediaTypeError caught: {exc.detail} for request {request.method} {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Remove static file mounting, as files are served by the router
# app.mount("/uploads", StaticFiles(directory=UPLOAD_DIRECTORY), name="uploads")

# Include the file router
# The router handles '/', '/upload', and '/file/{file_id_param}'
app.include_router(file_router, tags=["File Operations"])


# Placeholder routes (GET / and POST /upload) are now removed as they are in file_router.py

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Simple health check endpoint."""
    logger.debug("Health check endpoint called.")
    return {"status": "ok", "message": "Service is healthy"}

if __name__ == "__main__":
    logger.info(f"Starting server on host 0.0.0.0, port {settings.PORT}")
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"Max file size: {settings.MAX_FILE_SIZE_MB} MB")
    logger.info(f"Allowed MIME types regex: {settings.ALLOWED_MIME_TYPES_REGEX}")
    logger.info(f"Link expiry: {settings.LINK_EXPIRY_MINUTES} minutes")
    logger.info(f"Cleanup interval: {settings.CLEANUP_INTERVAL_SECONDS} seconds")
    
    reload_flag = settings.ENV_TYPE.lower() == "dev"
    logger.info(f"Server reload mode: {'Enabled' if reload_flag else 'Disabled'} (based on ENV_TYPE='{settings.ENV_TYPE}')")
    
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=reload_flag)
