# Python FastAPI File Upload Service

<p align="center">
  A temporary file hosting service built with Python, FastAPI, and Uvicorn.
  <br />
  Inspired by and ported from a <a href="https://github.com/mcdominik/file2url-nodejs">Node.js version</a>.
</p>

## Description

This service allows users to upload files, which are then stored temporarily. A unique download link is generated for each uploaded file. These links, and the files themselves, will expire and be automatically cleaned up after a configurable period. This is useful for sharing files that don't need permanent storage.

## Features

*   **FastAPI Backend:** Modern, fast (high-performance) web framework for building APIs.
*   **Pydantic Settings Management:** Type-annotated configuration loaded from environment variables and `.env` files.
*   **Periodic File Cleanup:** A background service automatically deletes expired files.
*   **Docker Support:** Containerize the application for easy deployment and scaling. Includes a non-root user for better security.
*   **Pytest Tests:** A suite of tests to ensure functionality and reliability.
*   **Async Operations:** Utilizes `async/await` for non-blocking I/O operations.

## Tech Stack

*   **Python 3.10+**
*   **FastAPI:** Web framework.
*   **Uvicorn:** ASGI server.
*   **Pydantic & Pydantic-Settings:** Data validation and settings management.
*   **Python-Multipart:** For handling file uploads.
*   **Pytest & HTTPX:** For testing.

## Prerequisites

*   Python 3.10 or newer
*   Pip (Python package installer)
*   Docker (optional, for containerized deployment)
*   A virtual environment manager (e.g., `venv`, `virtualenv`) is recommended.

## Setup and Running Locally

1.  **Clone the repository:**
    ```bash
    git clone <your_repository_url>
    cd <repository_directory_name>
    ```

2.  **Create and activate a virtual environment:**
    (Replace `venv` with your preferred virtual environment name if desired)
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Settings are managed via a `.env` file. Copy the example file and customize it:
    ```bash
    cp .env.example .env
    ```
    Open `.env` and adjust the variables as needed. Key variables include:
    *   `PORT`: Port for the application (default: `8000`).
    *   `DOWNLOAD_DOMAIN`: The public base URL for download links (e.g., `http://localhost:8000`).
    *   `MAX_FILE_SIZE_MB`: Maximum allowed file size in megabytes.
    *   `LINK_EXPIRY_MINUTES`: How long files are kept before cleanup.
    *   `CLEANUP_INTERVAL_SECONDS`: How often the cleanup service runs.
    *   `ALLOWED_MIME_TYPES_REGEX`: Regex to validate allowed file MIME types.
    *   `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`).
    *   `UPLOAD_DIR_NAME`: Name of the directory to store uploaded files (default: `storage`).

5.  **Run the application:**
    The application will start, and Uvicorn will typically show the address it's running on (e.g., `http://0.0.0.0:8000`).
    ```bash
    uvicorn src.main:app --reload --port ${PORT:-8000}
    ```
    (The `${PORT:-8000}` part will use the PORT from your `.env` or default to 8000 if not set in the shell environment. Uvicorn also respects the PORT from `.env` if `src.main:app` is configured to use it via `settings.PORT` for its `uvicorn.run` call, which it is.)

## Running with Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t python-file-upload .
    ```

2.  **Ensure your `.env` file is configured** as described in the "Setup and Running Locally" section. This file will be passed to the Docker container.

3.  **Create a host directory for persistent storage (optional but recommended):**
    If you want uploaded files to persist across container restarts, create a directory on your host machine that will be mounted into the container.
    ```bash
    mkdir storage 
    ```
    (Ensure this matches the `UPLOAD_DIR_NAME` in your `.env` file if you changed it from the default "storage").

4.  **Run the Docker container:**
    This command runs the container in detached mode (`-d`), maps a host port to the container's port, mounts the `storage` directory, and passes the `.env` file.
    ```bash
    docker run -d \
      -p 8000:${PORT:-8000} \
      -v $(pwd)/storage:/app/storage \
      --env-file .env \
      python-file-upload
    ```
    *   Replace `8000` in `-p 8000:...` with your desired host port if different.
    *   The `${PORT:-8000}` should match the `PORT` defined in your `.env` file or the application's default (which is 8000).
    *   The volume mount `-v $(pwd)/storage:/app/storage` ensures that files uploaded to `/app/storage` inside the container are saved in the `storage` directory on your host.

## API Endpoints

*   **`GET /`**: Serves the HTML home page with an upload form.
*   **`POST /upload`**: Handles file uploads.
    *   **Form Data Field:** `imageFile` (the file to upload).
    *   **Response:** HTML page with the download link for the uploaded file.
*   **`GET /file/{file_id}`**: Downloads the file associated with the given `file_id`.
*   **`GET /health`**: Health check endpoint. Returns `{"status": "ok"}`.

## Running Tests

1.  **Ensure development dependencies are installed:**
    Make sure your virtual environment is active and you've run:
    ```bash
    pip install -r requirements.txt 
    ```
    (This installs `pytest` and `httpx` which are included in `requirements.txt`).

2.  **Run tests:**
    From the project root directory:
    ```bash
    pytest -v
    ```

## Configuration

*   Application settings are managed by Pydantic models in `src/config.py`.
*   Environment variables are loaded from a `.env` file (see `.env.example` for all options) and override default values.
*   Key configurations include port, upload directory, file size limits, link expiry times, and allowed MIME types.

## Project Structure

```
.
├── .env.example        # Example environment variables
├── .gitignore          # Git ignore rules
├── Dockerfile          # Docker configuration
├── README.md           # This file
├── pytest.ini          # Pytest configuration
├── requirements.txt    # Python dependencies
├── src                 # Source code
│   ├── __init__.py
│   ├── config.py       # Application configuration (Pydantic settings)
│   ├── main.py         # FastAPI application entry point
│   ├── middleware      # Custom middleware
│   │   ├── __init__.py
│   │   ├── custom_errors.py
│   │   └── logging_middleware.py
│   ├── routers         # API routers
│   │   └── file_router.py
│   ├── services        # Business logic (e.g., file cleanup)
│   │   └── file_service.py
│   └── utils           # Utility modules
│       ├── __init__.py
│       ├── file_store.py   # In-memory link/file metadata storage
│       └── misc_utils.py   # Miscellaneous helper functions
└── tests               # Test files
    └── test_main.py    # Main integration tests
```

## Cleanup Service

The application includes an automated background service (`src/services/file_service.py`) that periodically checks for and deletes expired files from the storage and their associated metadata. The frequency of this cleanup and the expiry time for links are configurable via environment variables (`CLEANUP_INTERVAL_SECONDS` and `LINK_EXPIRY_MINUTES`).

---

<p align="right">(<a href="#python-fastapi-file-upload-service">back to top</a>)</p>
