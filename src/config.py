import os
import re
from pathlib import Path
from typing import Pattern

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment-loaded variables
    DOWNLOAD_DOMAIN: str = Field(default="localhost")
    ENV_TYPE: str = Field(default="dev")
    PORT: int = Field(default=3000)
    UPLOAD_DIR_NAME: str = Field(default="storage")
    MAX_FILE_SIZE_MB: int = Field(default=10)
    LINK_EXPIRY_MINUTES: int = Field(default=60)
    CLEANUP_INTERVAL_SECONDS: int = Field(default=300)
    # Default regex now matches common image MIME types more accurately.
    # It expects the full MIME type string e.g. "image/png"
    ALLOWED_MIME_TYPES_REGEX: str = Field(default=r"image/png|image/jpeg|image/jpg|image/gif|image/webp|image/tiff")
    LOG_LEVEL: str = Field(default="info")

    # Derived properties
    @property
    def UPLOAD_DIR(self) -> Path:
        # project_root/storage
        return Path(__file__).resolve().parent.parent / self.UPLOAD_DIR_NAME

    @property
    def cleanup_interval_ms(self) -> int:
        return self.CLEANUP_INTERVAL_SECONDS * 1000

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def link_expiry_ms(self) -> int:
        return self.LINK_EXPIRY_MINUTES * 60 * 1000

    @property
    def compiled_allowed_mime_types(self) -> Pattern[str]:
        return re.compile(self.ALLOWED_MIME_TYPES_REGEX, re.IGNORECASE)

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Allow extra fields in .env, but don't load them into Settings
        validate_assignment = True # Allow fields to be modified by monkeypatch where appropriate


# Instantiate the settings
settings = Settings()

# Ensure the upload directory exists
if not settings.UPLOAD_DIR.exists():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

if __name__ == "__main__":
    # For testing the configuration loading
    print(f"Python Environment Type: {settings.ENV_TYPE}")
    print(f"Upload Directory: {settings.UPLOAD_DIR}")
    print(f"Max File Size (Bytes): {settings.max_file_size_bytes}")
    print(f"Allowed MIME types: {settings.ALLOWED_MIME_TYPES_REGEX}")
    print(f"Compiled MIME types pattern: {settings.compiled_allowed_mime_types.pattern}")
    print(f"Port: {settings.PORT}")
    # Create a dummy .env to test loading
    with open(".env", "w") as f:
        f.write("DOWNLOAD_DOMAIN=test.example.com\n")
        f.write("PORT=9999\n")
        f.write("MAX_FILE_SIZE_MB=20\n")

    print("\n--- Reloading settings after creating a dummy .env ---")
    settings_reloaded = Settings()
    print(f"Reloaded Download Domain: {settings_reloaded.DOWNLOAD_DOMAIN}")
    print(f"Reloaded Port: {settings_reloaded.PORT}")
    print(f"Reloaded Max File Size (MB): {settings_reloaded.MAX_FILE_SIZE_MB}")
    print(f"Reloaded Max File Size (Bytes): {settings_reloaded.max_file_size_bytes}")

    # Clean up dummy .env
    if os.path.exists(".env"):
        os.remove(".env")

    # Test directory creation
    print(f"\nUpload directory exists: {settings.UPLOAD_DIR.exists()}")
    if settings.UPLOAD_DIR.exists() and settings.UPLOAD_DIR.is_dir() and settings.UPLOAD_DIR.name == settings.UPLOAD_DIR_NAME:
        print(f"Upload directory '{settings.UPLOAD_DIR_NAME}' was correctly created/found at project root.")
    else:
        print(f"Upload directory '{settings.UPLOAD_DIR_NAME}' was NOT correctly created/found.")

    # Example of how other modules would use it:
    # from src.config import settings
    # print(settings.PORT)
