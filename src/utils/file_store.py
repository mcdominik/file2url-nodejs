import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from pydantic import BaseModel, Field

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Basic config for logging

class UploadedFile(BaseModel):
    """Data structure for an uploaded file."""
    id: str
    file_path: str # Absolute path to the stored file
    original_name: str
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    mime_type: str

# Module-level dictionary to store file metadata
_file_links: Dict[str, UploadedFile] = {}

def add(id: str, data: UploadedFile) -> None:
    """Adds an entry to the file store."""
    if id in _file_links:
        logger.warning(f"File ID {id} already exists. Overwriting.")
    _file_links[id] = data
    logger.debug(f"Added file link: {id} -> {data.original_name}")

def get(id: str) -> Optional[UploadedFile]:
    """Retrieves an entry from the file store."""
    file_info = _file_links.get(id)
    if file_info:
        logger.debug(f"Retrieved file link: {id}")
    else:
        logger.debug(f"File link not found: {id}")
    return file_info

def delete(id: str) -> bool:
    """Deletes an entry from the file store."""
    if id in _file_links:
        del _file_links[id]
        logger.debug(f"Deleted file link: {id}")
        return True
    logger.debug(f"Attempted to delete non-existent file link: {id}")
    return False

def get_all() -> List[Tuple[str, UploadedFile]]:
    """Returns all entries as a list of (id, UploadedFile) tuples."""
    return list(_file_links.items())

def get_size() -> int:
    """Returns the number of entries in the store."""
    return len(_file_links)

if __name__ == "__main__":
    # Basic test cases
    logging.basicConfig(level=logging.DEBUG) # Enable debug logging for test
    logger.info("--- Testing file_store ---")

    # Test UploadedFile creation
    file1_data = {
        "id": "test001",
        "file_path": "/tmp/uploads/test001.png",
        "original_name": "original_image.png",
        "mime_type": "image/png"
    }
    file1 = UploadedFile(**file1_data)
    print(f"Created UploadedFile: {file1.model_dump_json(indent=2)}")
    assert file1.id == "test001"
    assert file1.timestamp > 0

    # Test add
    add(file1.id, file1)
    assert get_size() == 1
    logger.info(f"Added file1. Store size: {get_size()}")

    # Test get
    retrieved_file1 = get("test001")
    assert retrieved_file1 is not None
    assert retrieved_file1.original_name == "original_image.png"
    logger.info(f"Retrieved file1: {retrieved_file1.original_name}")

    # Test get non-existent
    non_existent_file = get("nonexistent")
    assert non_existent_file is None
    logger.info(f"Retrieved non-existent file: {non_existent_file}")

    # Test add another file
    file2_data = {
        "id": "test002",
        "file_path": "/tmp/uploads/test002.txt",
        "original_name": "document.txt",
        "mime_type": "text/plain"
    }
    file2 = UploadedFile(**file2_data)
    add(file2.id, file2)
    assert get_size() == 2
    logger.info(f"Added file2. Store size: {get_size()}")

    # Test get_all
    all_files = get_all()
    assert len(all_files) == 2
    logger.info(f"All files: {[(item[0], item[1].original_name) for item in all_files]}")

    # Test delete
    assert delete("test001") is True
    assert get_size() == 1
    logger.info(f"Deleted file1. Store size: {get_size()}")
    assert get("test001") is None

    # Test delete non-existent
    assert delete("nonexistent") is False
    assert get_size() == 1
    logger.info(f"Attempted to delete non-existent. Store size: {get_size()}")

    # Test overwriting (should log a warning)
    file2_updated_data = {
        "id": "test002",
        "file_path": "/tmp/uploads/test002_new.txt",
        "original_name": "document_v2.txt",
        "mime_type": "text/plain"
    }
    file2_updated = UploadedFile(**file2_updated_data)
    add(file2_updated.id, file2_updated) # This should log a warning
    assert get_size() == 1
    retrieved_file2_updated = get("test002")
    assert retrieved_file2_updated is not None
    assert retrieved_file2_updated.original_name == "document_v2.txt"
    logger.info(f"Overwrote file2. New original name: {retrieved_file2_updated.original_name}")

    logger.info("--- file_store tests completed ---")
