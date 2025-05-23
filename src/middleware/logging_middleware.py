import logging
from typing import Callable, Awaitable

from fastapi import Request, Response

# Initialize logger
logger = logging.getLogger(__name__)
# Basic configuration for the logger if not configured elsewhere
# logging.basicConfig(level=logging.INFO) # Will be configured in main.py

async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Logs the method and URL of each incoming request.
    """
    logger.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response: {response.status_code} for {request.method} {request.url}")
    except Exception as e:
        logger.error(f"Error processing request {request.method} {request.url}: {e}", exc_info=True)
        # Re-raise the exception to be handled by FastAPI's default error handling
        # or other registered exception handlers.
        raise
    return response

if __name__ == "__main__":
    # This block is for demonstration or direct testing if needed,
    # but this middleware is typically tested within a FastAPI application.
    import asyncio
    from unittest.mock import Mock

    # Configure logger for the test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    async def mock_call_next(request: Request) -> Response:
        # Simulate a successful response
        # In a real scenario, this would be the next middleware or the route handler
        logger.info(f"mock_call_next called for {request.url}")
        return Response(content="Mock response", status_code=200)

    async def mock_call_next_with_error(request: Request) -> Response:
        logger.info(f"mock_call_next_with_error called for {request.url}, will raise error")
        raise ValueError("Simulated processing error")

    async def run_test():
        # Test 1: Successful request
        mock_request_success = Mock(spec=Request)
        mock_request_success.method = "GET"
        mock_request_success.url = "/test/success"
        
        logger.info("\n--- Testing successful request logging ---")
        response_success = await request_logging_middleware(mock_request_success, mock_call_next)
        assert response_success.status_code == 200
        # Check logs for "Request: GET /test/success" and "Response: 200 for GET /test/success"

        # Test 2: Request that causes an error in `call_next`
        mock_request_error = Mock(spec=Request)
        mock_request_error.method = "POST"
        mock_request_error.url = "/test/error"

        logger.info("\n--- Testing error request logging ---")
        try:
            await request_logging_middleware(mock_request_error, mock_call_next_with_error)
        except ValueError as e:
            assert str(e) == "Simulated processing error"
            # Check logs for "Request: POST /test/error" and "Error processing request POST /test/error: Simulated processing error"
        else:
            assert False, "ValueError was not raised by middleware"
        
        logger.info("\n--- Logging middleware tests completed ---")

    # Python 3.7+
    asyncio.run(run_test())
