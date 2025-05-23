import pytest
import httpx # Not strictly needed for TestClient, but good for general knowledge
import os
from pathlib import Path
import shutil # For cleaning up directories

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Application imports
from src.main import app # Your FastAPI application instance
from src.config import settings
from src.utils import file_store
from src.utils.file_store import UploadedFile # For type hinting if needed
from src.services import file_service # For cleanup logic if desired

# Ensure the upload directory exists before tests run, and clear it.
# This is important if previous test runs failed and left files behind.
if settings.UPLOAD_DIR.exists():
    # Delete all contents of UPLOAD_DIR
    for item in settings.UPLOAD_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
else:
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Clear the in-memory file store before tests run
file_store._file_links.clear()


@pytest.fixture(scope="module")
def client() -> TestClient:
    """
    Provides a TestClient instance for the FastAPI application.
    This client allows sending requests to the application in tests.
    """
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def cleanup_after_each_test():
    """
    Cleans up the file store and UPLOAD_DIR after each test.
    `autouse=True` ensures this fixture runs for every test.
    """
    yield # Test runs here
    # Cleanup: Clear the in-memory file store
    file_store._file_links.clear()
    # Cleanup: Clear the UPLOAD_DIR
    if settings.UPLOAD_DIR.exists():
        for item in settings.UPLOAD_DIR.iterdir():
            # Ensure we only delete files created by tests (e.g. check name or type)
            # For simplicity here, we clear all if tests are expected to manage their files.
            # Or, more robustly, tests should register their created files and this fixture cleans them.
            if item.is_file(): # Only delete files, not potential subdirectories unless intended
                item.unlink()
            # If subdirectories are created by tests and need cleanup:
            # elif item.is_dir():
            #     shutil.rmtree(item)
    # print(f"Cleaned up after test. Store size: {file_store.get_size()}, Upload dir items: {len(list(settings.UPLOAD_DIR.iterdir())) if settings.UPLOAD_DIR.exists() else 0}")


# --- Test Cases ---

def test_get_home(client: TestClient):
    """Test the home page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html; charset=utf-8" == response.headers["content-type"]
    content = response.text
    assert "Welcome to the FastAPI File Upload Service!" in content
    assert f"Links to uploaded files are valid for {settings.LINK_EXPIRY_MINUTES} minutes." in content

def test_upload_file_success(client: TestClient):
    """Test successful file upload."""
    dummy_file_name = "test_image.png"
    dummy_file_content = b"fake image data"
    dummy_mime_type = "image/png"

    # Ensure the MIME type is allowed
    assert settings.compiled_allowed_mime_types.match(dummy_mime_type), \
        f"Test setup error: MIME type {dummy_mime_type} is not allowed by current settings."

    files = {"imageFile": (dummy_file_name, dummy_file_content, dummy_mime_type)}
    response = client.post("/upload", files=files)

    assert response.status_code == 201
    assert "text/html; charset=utf-8" == response.headers["content-type"]
    
    content = response.text
    assert "Your link:" in content
    assert f"Original filename: {dummy_file_name}" in content

    # Extract file ID from the link
    # Example link: <h1>Your link: <a href='http://localhost:8000/file/some_id_123' target='_blank'>...</a></h1>
    import re
    match = re.search(r"/file/([a-zA-Z0-9_-]+)", content)
    assert match, "Could not find file ID in the response link."
    file_id = match.group(1)

    # Assert file exists in file_store
    stored_file_data = file_store.get(file_id)
    assert stored_file_data is not None
    assert stored_file_data.original_name == dummy_file_name
    assert stored_file_data.mime_type == dummy_mime_type

    # Assert physical file exists
    # The router saves with a UUID name, so we need to check the path from stored_file_data
    physical_file_path = Path(stored_file_data.file_path)
    assert physical_file_path.exists()
    assert physical_file_path.is_file()
    with open(physical_file_path, "rb") as f:
        assert f.read() == dummy_file_content
    
    # Cleanup is handled by the cleanup_after_each_test fixture

def test_upload_file_invalid_type(client: TestClient):
    """Test file upload with a non-allowed MIME type."""
    dummy_file_name = "test_document.txt"
    dummy_file_content = b"some text data"
    dummy_mime_type = "text/plain" # Assuming this is not in ALLOWED_MIME_TYPES_REGEX

    # Ensure the MIME type is NOT allowed (important for test validity)
    assert not settings.compiled_allowed_mime_types.match(dummy_mime_type), \
        f"Test setup warning: MIME type {dummy_mime_type} IS allowed by current settings. Test might not be effective."

    files = {"imageFile": (dummy_file_name, dummy_file_content, dummy_mime_type)}
    response = client.post("/upload", files=files)

    assert response.status_code == 415 # Unsupported Media Type
    assert "application/json" == response.headers["content-type"]
    json_response = response.json()
    assert "detail" in json_response
    assert f"Invalid file type: {dummy_mime_type}" in json_response["detail"]
    assert settings.ALLOWED_MIME_TYPES_REGEX in json_response["detail"]

def test_upload_file_too_large(client: TestClient, monkeypatch):
    """Test file upload that exceeds the maximum file size."""
        
        # Store original to ensure monkeypatch reverts correctly if needed, though pytest handles it.
        # original_max_mb = settings.MAX_FILE_SIZE_MB # This line had unexpected indent

        # Set MAX_FILE_SIZE_MB to 0 for this test. This makes max_file_size_bytes = 0.
    monkeypatch.setattr(settings, 'MAX_FILE_SIZE_MB', 0)
        
        # The settings.max_file_size_bytes property will now be 0.
    effective_max_bytes = settings.max_file_size_bytes
    assert effective_max_bytes == 0 # Confirm our understanding

    dummy_file_name = "large_file.png"
        # Create content larger than 0 bytes.
    dummy_file_content = b"This content is definitely larger than zero bytes."
    assert len(dummy_file_content) > effective_max_bytes
    dummy_mime_type = "image/png" # An allowed type

    files = {"imageFile": (dummy_file_name, dummy_file_content, dummy_mime_type)}
    response = client.post("/upload", files=files)

    assert response.status_code == 413 # Payload Too Large
    assert "application/json" == response.headers["content-type"]
    json_response = response.json()
    assert "detail" in json_response
        # The error message in the router uses settings.MAX_FILE_SIZE_MB.
        # We patched settings.MAX_FILE_SIZE_MB to 0.
    # The router formats MAX_FILE_SIZE_MB as an int if it's a whole number, or float otherwise in its message.
    # When MAX_FILE_SIZE_MB is 0, the message is "Max size is 0MB"
    assert "File too large. Max size is 0MB" in json_response["detail"]
    # Optionally, also check for the part about the actual file size if it's consistent
    assert "Your file size:" in json_response["detail"]

    # monkeypatch will automatically restore the original value of settings.MAX_FILE_SIZE_MB
    # No explicit restore needed due to monkeypatch's fixture scope.

def test_download_file_success(client: TestClient):
    """Test successful file download."""
    # 1. Upload a file first
    dummy_file_name = "download_me.png"
    dummy_file_content = b"data for download test"
    dummy_mime_type = "image/png"

    assert settings.compiled_allowed_mime_types.match(dummy_mime_type)

    files = {"imageFile": (dummy_file_name, dummy_file_content, dummy_mime_type)}
    upload_response = client.post("/upload", files=files)
    assert upload_response.status_code == 201
    
    import re
    match = re.search(r"/file/([a-zA-Z0-9_-]+)", upload_response.text)
    assert match, "Could not find file ID in the upload response."
    file_id = match.group(1)

    # 2. Download the file
    download_response = client.get(f"/file/{file_id}")

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == dummy_mime_type
    # Check for filename in content-disposition. Browser typically uses this.
    # Example: 'attachment; filename="download_me.png"' or 'inline; filename="download_me.png"'
    assert f'filename="{dummy_file_name}"' in download_response.headers["content-disposition"]
    assert download_response.content == dummy_file_content

    # Cleanup is handled by the cleanup_after_each_test fixture

def test_download_file_not_found(client: TestClient):
    """Test downloading a file that does not exist."""
    non_existent_id = "this_id_does_not_exist_12345"
    response = client.get(f"/file/{non_existent_id}")

    assert response.status_code == 404
    assert "application/json" == response.headers["content-type"]
    json_response = response.json()
    assert "detail" in json_response
    assert "File not found" in json_response["detail"] # Router might say "File not found or link expired."

# TODO: Add tests for link expiry if possible (requires manipulating time or file timestamps)
# TODO: Add tests for one-time download if that feature is enabled and implemented.
# TODO: Test for files with no content type if the router handles it specifically.
#       The router currently raises UnsupportedMediaTypeError for no content type.
# TODO: Test for files with zero or invalid size if router handles it (currently 400 error from router).

def test_upload_file_no_content_type(client: TestClient):
    """Test file upload with no content type provided."""
    dummy_file_name = "no_type_file.dat"
    dummy_file_content = b"some data"
    # When not providing a MIME type, TestClient might default or omit.
    # The key is how the server interprets a missing Content-Type for the part.
    # FastAPI/Starlette might provide a default like 'application/octet-stream'
    # or it might be None. The router code checks for `imageFile.content_type` being None.
    
    # To simulate a missing content type for a file part in multipart/form-data with TestClient,
    # you might need to construct the multipart request more manually, or rely on
    # the default behavior when the third item in the tuple (mime_type) is omitted.
    # TestClient's default for `files` items without a content type is often `application/octet-stream`.
    # Our router checks `if not imageFile.content_type:`, which means an empty string or None.
    # Starlette's UploadFile usually has a content_type. If it's empty, it would trigger.
    # For this test, we'll assume a scenario where it *could* be None or empty.
    # The router code specifically raises "File has no content type specified."
    
    # Simulating a file part without a Content-Type header is tricky with high-level clients.
    # The most direct way to test the `if not imageFile.content_type:` branch
    # might be to mock `imageFile.content_type` to be None or empty within the endpoint,
    # which is more of a unit test for the endpoint's internal logic.
    # For an integration test, we assume Starlette provides *some* content_type.
    # If Starlette provides 'application/octet-stream' and it's not allowed,
    # it will be caught by the *invalid type* check instead.
    
    # Let's try omitting the content type and see what TestClient sends
    # and how our server responds. It will likely be treated as 'application/octet-stream'.
    # If 'application/octet-stream' is *not* in ALLOWED_MIME_TYPES_REGEX, this will behave like test_upload_file_invalid_type.
    # If it *is* allowed, it would be a successful upload.
    
    # Given the router logic: `if not imageFile.content_type: raise UnsupportedMediaTypeError(...)`
    # This specific branch is hard to hit if Starlette always provides a default content_type.
    # We will assume for now that if a browser or client somehow sends a file part
    # without a Content-Type sub-header, Starlette's UploadFile.content_type might be None or empty.
    
    # If 'application/octet-stream' is disallowed (common):
    if not settings.compiled_allowed_mime_types.match("application/octet-stream"):
        files = {"imageFile": (dummy_file_name, dummy_file_content)} # Omitting mime_type
        response = client.post("/upload", files=files)
        assert response.status_code == 415
        assert "Invalid file type: application/octet-stream" in response.json()["detail"]
    else:
        # If 'application/octet-stream' IS allowed, this test isn't testing the 'no content type' branch.
        pytest.skip("Skipping test_upload_file_no_content_type because application/octet-stream is allowed by settings.")

def test_upload_file_zero_size(client: TestClient):
    """Test uploading a file with zero size."""
    dummy_file_name = "empty_file.dat"
    dummy_file_content = b""
    dummy_mime_type = "application/octet-stream" # Or any allowed type

    # Ensure the MIME type is allowed for this test to focus on size
    if not settings.compiled_allowed_mime_types.match(dummy_mime_type):
         pytest.skip(f"Skipping test_upload_file_zero_size because MIME type {dummy_mime_type} is not allowed.")

    files = {"imageFile": (dummy_file_name, dummy_file_content, dummy_mime_type)}
    response = client.post("/upload", files=files)

    # The router has: `if imageFile.size is None or imageFile.size <= 0:`
    assert response.status_code == 400 # Bad Request
    assert "application/json" == response.headers["content-type"]
    json_response = response.json()
    assert "detail" in json_response
    assert "File size is invalid or zero" in json_response["detail"]

# Health check test
def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Service is healthy"}

# TODO: If your application creates the UPLOAD_DIR on startup via an event handler,
# that event handler might not run for TestClient if not configured.
# However, our file_router.py ensures UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
# before saving, and config.py also does this, so it should be fine.
# The fixture `cleanup_after_each_test` also helps manage this directory.

# Final check: ensure UPLOAD_DIR is clean after all tests in this module if module-scoped cleanup is added
def M_final_cleanup(): # Not a pytest fixture, but called by one if needed
    if settings.UPLOAD_DIR.exists():
        for item in settings.UPLOAD_DIR.iterdir():
            if item.is_dir(): shutil.rmtree(item)
            else: item.unlink()
    if file_store.get_size() > 0:
        file_store._file_links.clear()
    print("M_Final cleanup: Cleared UPLOAD_DIR and file_store for the module.")

@pytest.fixture(scope="module", autouse=True)
def module_scoped_cleanup_trigger():
    yield # All tests in module run
    M_final_cleanup()
    # Optional: remove UPLOAD_DIR itself if it was created by tests and should not persist
    # if settings.UPLOAD_DIR.exists() and settings.UPLOAD_DIR.name == "storage_test": # Be careful
    #     shutil.rmtree(settings.UPLOAD_DIR)


# Note on monkeypatching settings for 'test_upload_file_too_large':
# If settings were a simple dict or module-level variables, monkeypatch.setattr would be straightforward.
# Since `settings` is a Pydantic BaseSettings instance, `monkeypatch.setattr(settings, 'max_file_size_bytes', new_value)`
# works because Pydantic models allow attribute assignment if `validate_assignment=True` (default is False for performance).
# If it were False, the change might not be reflected or might error.
# For Pydantic V2, `model_config['validate_assignment'] = True` would enable this.
# For V1, `Config.validate_assignment = True`.
# Alternatively, one could mock the `settings` object imported by the router module:
# `monkeypatch.setattr('src.routers.file_router.settings', mocked_settings_object)`
# The current approach of monkeypatching the imported `settings` instance in `test_main.py`
# should work if that same instance is used by the router. Python's module import system
# typically ensures that `from src.config import settings` yields the same instance.

# Ensure test files are not picked up by .gitignore if they are created outside UPLOAD_DIR
# (e.g. if tests created files in `tests/` dir itself for upload).
# Current tests create file content in-memory.
