import logging
import os
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Request
)
from fastapi.responses import FileResponse, HTMLResponse

from src.config import settings
from src.utils import file_store
from src.utils.misc_utils import generate_home_html, get_cool_random_name
from src.middleware.custom_errors import UnsupportedMediaTypeError
from src.services import file_service # For one-time download cleanup
from src.utils.file_store import UploadedFile # Pydantic model

# Initialize logger and router
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_home(request: Request) -> HTMLResponse:
    """
    Serves the main HTML page.
    """
    logger.info(f"Serving home page. Client: {request.client.host if request.client else 'Unknown'}")
    html_content = generate_home_html(settings.link_expiry_ms)
    return HTMLResponse(content=html_content)

@router.post("/upload", response_class=HTMLResponse)
async def upload_file(
    background_tasks: BackgroundTasks, # Added for potential future use (e.g. one-time downloads)
    imageFile: UploadFile = File(...)
) -> HTMLResponse:
    """
    Handles file uploads, stores the file, and returns a download link.
    """
    logger.info(f"Upload attempt for file: {imageFile.filename}, content_type: {imageFile.content_type}, size: {imageFile.size}")

    # File Validation (Type)
    if not imageFile.content_type:
        logger.warning(f"Upload rejected: File '{imageFile.filename}' has no content type.")
        raise UnsupportedMediaTypeError(detail="File has no content type specified.")
    
    if not settings.compiled_allowed_mime_types.match(imageFile.content_type):
        logger.warning(f"Upload rejected: File '{imageFile.filename}' with MIME type '{imageFile.content_type}' is not allowed.")
        raise UnsupportedMediaTypeError(
            detail=f"Invalid file type: {imageFile.content_type}. Only files matching regex '{settings.ALLOWED_MIME_TYPES_REGEX}' are allowed."
        )

    # File Validation (Size)
    # FastAPI's UploadFile.size should be reliable as it's derived from Content-Length
    # or by spooling to disk for larger files.
    if imageFile.size is None or imageFile.size <= 0 : # Check for invalid size
        logger.warning(f"Upload rejected: File '{imageFile.filename}' has invalid size: {imageFile.size}.")
        raise HTTPException(status_code=400, detail="File size is invalid or zero.")

    if imageFile.size > settings.max_file_size_bytes:
        logger.warning(f"Upload rejected: File '{imageFile.filename}' (size: {imageFile.size}B) exceeds maximum size of {settings.max_file_size_bytes}B.")
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {settings.MAX_FILE_SIZE_MB}MB. Your file size: {imageFile.size // (1024*1024):.2f}MB"
        )

    # Generate File ID (ensure uniqueness)
    file_id = get_cool_random_name()
    while file_store.get(file_id):
        logger.warning(f"Generated file ID {file_id} already exists. Regenerating.")
        file_id = str(uuid.uuid4()) # Use a more robust UUID if collisions are frequent

    # Ensure UPLOAD_DIR exists (config.py should create it, this is a fallback/check)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Construct file path
    # Using a UUID for the filename on disk to prevent conflicts and path traversal issues with original filename
    file_extension = os.path.splitext(imageFile.filename)[1] if imageFile.filename else ".dat"
    # Sanitize file_extension further if necessary, e.g. limit length, check for odd chars.
    # For now, os.path.splitext should be okay.
    disk_filename = f"{str(uuid.uuid4())}{file_extension}"
    file_path = settings.UPLOAD_DIR / disk_filename

    try:
        # Save File
        # await imageFile.seek(0) # Reset cursor if read previously, not needed if using .size and then .read() once.
        contents = await imageFile.read() # Read the entire file into memory
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        logger.info(f"File '{imageFile.filename}' saved to '{file_path}' with ID '{file_id}'.")

        # Store Metadata
        file_data = UploadedFile(
            id=file_id,
            file_path=str(file_path), # Store as string
            original_name=imageFile.filename or "untitled",
            timestamp=datetime.utcnow().timestamp(),
            mime_type=imageFile.content_type
        )
        file_store.add(file_id, file_data)
        logger.info(f"Metadata for file ID '{file_id}' ({imageFile.filename}) added to store.")

        # Generate Response
        # Ensure DOWNLOAD_DOMAIN is correctly formatted (e.g., http://localhost:8000)
        # Settings should provide this full URL.
        download_url = f"{settings.DOWNLOAD_DOMAIN}/file/{file_id}"
        
        logger.info(f"Successfully processed upload for '{imageFile.filename}'. Download URL: {download_url}")
        return HTMLResponse(
            content=f"<h1>Your link: <a href='{download_url}' target='_blank'>{download_url}</a></h1>"
                    f"<p>Original filename: {imageFile.filename}</p>"
                    f"<p>Link will expire in {settings.LINK_EXPIRY_MINUTES} minutes.</p>",
            status_code=201
        )

    except Exception as e:
        logger.error(f"Error during file upload process for '{imageFile.filename}': {e}", exc_info=True)
        # Attempt to delete partially saved file if it exists
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
                logger.info(f"Cleaned up partially saved file: {file_path}")
            except OSError as unlink_e:
                logger.error(f"Failed to clean up partially saved file {file_path}: {unlink_e}")
        
        # Re-raise a generic server error or the specific error if it's an HTTPException
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while uploading the file: {str(e)}")
    finally:
        await imageFile.close()


@router.get("/file/{file_id_param}")
async def download_file(
    file_id_param: str,
    request: Request, # Added to log client IP
    background_tasks: BackgroundTasks # For one-time download
):
    """
    Serves a file for download if it exists and the link hasn't expired.
    Optionally implements one-time download.
    """
    logger.debug(f"Download attempt for file_id: {file_id_param}. Client: {request.client.host if request.client else 'Unknown'}")
    file_data = file_store.get(file_id_param)

    if not file_data:
        logger.warning(f"File not found or link expired for file_id: {file_id_param}.")
        raise HTTPException(status_code=404, detail="File not found or link expired.")

    # Check if file physically exists (it should, but good for robustness)
    if not os.path.exists(file_data.file_path):
        logger.error(f"File metadata found for ID '{file_id_param}', but physical file '{file_data.file_path}' is missing.")
        # Clean up stale store entry
        file_store.delete(file_id_param)
        raise HTTPException(status_code=404, detail="File not found (missing on disk).")

    # Optional: One-time download implementation
    # If you want this, uncomment the following line and ensure file_service is correctly set up.
    # background_tasks.add_task(file_service.cleanup_file, file_id_param)
    # logger.info(f"Scheduled cleanup for file_id: {file_id_param} after download.")
    # Note: If cleanup_file is slow, it might be better to handle it fully in the background.
    # For now, let's keep it simple and not enable one-time download by default.
    # If one-time download is enabled, the message about link expiry might be confusing.

    logger.info(f"Serving file: {file_data.original_name} (ID: {file_id_param}) from path: {file_data.file_path}")
    return FileResponse(
        path=file_data.file_path,
        filename=file_data.original_name,
        media_type=file_data.mime_type
    )

if __name__ == "__main__":
    # This section is for illustration or very basic standalone testing of the router.
    # However, FastAPI routers are best tested with a running Uvicorn server and an HTTP client.
    print("Router defined. To test, include it in a FastAPI app and run with Uvicorn.")
    print(f"Example endpoints:")
    print(f"  GET /")
    print(f"  POST /upload  (expects 'imageFile' as form data)")
    print(f"  GET /file/{{file_id}}")

    # You could add mock objects and call functions directly for unit tests,
    # but that wouldn't test the full FastAPI request/response flow.
    # Example:
    # async def test_home_route():
    #    req_mock = Mock(spec=Request)
    #    req_mock.client = None
    #    response = await get_home(req_mock)
    #    assert response.status_code == 200
    #    assert "FastAPI File Upload Service" in response.body.decode()
    # asyncio.run(test_home_route())
