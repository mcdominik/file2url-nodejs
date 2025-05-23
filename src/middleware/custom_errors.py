from fastapi import HTTPException

class UnsupportedMediaTypeError(HTTPException):
    """Custom exception for 415 Unsupported Media Type errors."""
    def __init__(self, detail: str = "Unsupported file type."):
        super().__init__(status_code=415, detail=detail)

if __name__ == "__main__":
    # Example usage (not part of the module itself, just for testing)
    try:
        raise UnsupportedMediaTypeError()
    except UnsupportedMediaTypeError as e:
        print(f"Caught exception: status_code={e.status_code}, detail='{e.detail}'")

    try:
        raise UnsupportedMediaTypeError(detail="Only JPEG images are allowed.")
    except UnsupportedMediaTypeError as e:
        print(f"Caught exception: status_code={e.status_code}, detail='{e.detail}'")
