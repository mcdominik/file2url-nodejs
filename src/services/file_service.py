import os
import logging
from datetime import datetime
from threading import Timer, Lock
from typing import Optional

from src.utils import file_store
from src.config import settings

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=settings.LOG_LEVEL.upper()) # Use log level from settings

# --- File Cleanup Logic ---
def cleanup_file(file_id: str) -> None:
    """
    Removes a file and its metadata from the store.
    Deletes the physical file and then its entry from the file_store.
    """
    file_data = file_store.get(file_id)
    if file_data:
        try:
            if os.path.exists(file_data.file_path):
                os.unlink(file_data.file_path)
                logger.info(f"Successfully deleted physical file: {file_data.file_path} (ID: {file_id})")
            else:
                logger.warning(f"Physical file not found for deletion: {file_data.file_path} (ID: {file_id})")
        except OSError as e:
            logger.error(f"Error deleting physical file {file_data.file_path} (ID: {file_id}): {e}")
            # Decide if you want to return or still remove from store.
            # For now, we'll still remove it from the store to prevent repeated attempts on a non-deletable file.

        deleted_from_store = file_store.delete(file_id)
        if deleted_from_store:
            logger.info(f"Removed file link entry from store: {file_id}")
        else:
            # This case should ideally not happen if file_data was retrieved successfully
            logger.warning(f"Attempted to remove link for {file_id}, but it was already gone from store.")
    else:
        logger.warning(f"Attempted to cleanup file_id {file_id}, but it was not found in the store.")

def run_periodic_cleanup() -> None:
    """
    Iterates through stored files and removes those older than the link_expiry_ms.
    """
    now_ts = datetime.utcnow().timestamp()
    logger.info(f"Running periodic cleanup at {datetime.fromtimestamp(now_ts).isoformat()}...")
    deleted_count = 0
    
    # Make a copy of items to avoid issues if the store is modified during iteration
    # (though current file_store.get_all() returns a new list, so it's safe)
    all_files = file_store.get_all()

    for file_id, file_data in all_files:
        file_age_seconds = now_ts - file_data.timestamp
        link_expiry_seconds = settings.link_expiry_ms / 1000.0 # Ensure float division

        if file_age_seconds > link_expiry_seconds:
            logger.info(f"Expired link found for file: {file_data.original_name} (ID: {file_id}). Age: {file_age_seconds:.2f}s, Expiry: {link_expiry_seconds}s")
            cleanup_file(file_id)
            deleted_count += 1
    
    if deleted_count > 0:
        logger.info(f"Periodic cleanup finished. Removed {deleted_count} expired file(s).")
    else:
        logger.info("Periodic cleanup finished. No expired files found.")

# --- Periodic Cleanup Task Management ---
_cleanup_timer: Optional[Timer] = None
_timer_lock = Lock()

def _scheduled_cleanup_task() -> None:
    """
    Internal function that runs the cleanup and reschedules itself.
    """
    try:
        run_periodic_cleanup()
    except Exception as e:
        logger.error(f"Error during scheduled periodic cleanup: {e}", exc_info=True)
    finally:
        with _timer_lock:
            # Only reschedule if stop_periodic_cleanup hasn't been called (which sets _cleanup_timer to None)
            if globals().get('_cleanup_timer') is not None: # Check the global _cleanup_timer
                globals()['_cleanup_timer'] = Timer(settings.CLEANUP_INTERVAL_SECONDS, _scheduled_cleanup_task)
                globals()['_cleanup_timer'].start()
                logger.debug(f"Rescheduled cleanup task in {settings.CLEANUP_INTERVAL_SECONDS} seconds.")
            else:
                logger.info("Cleanup timer was stopped. Not rescheduling.")


def start_periodic_cleanup() -> None:
    """
    Starts the periodic cleanup task.
    Runs an initial cleanup and then schedules subsequent runs.
    """
    global _cleanup_timer # Ensure we are modifying the global variable
    with _timer_lock:
        if _cleanup_timer is not None and _cleanup_timer.is_alive():
            logger.warning("Periodic cleanup task is already running.")
            return

        logger.info(f"Starting periodic cleanup. Interval: {settings.CLEANUP_INTERVAL_SECONDS}s, Link Expiry: {settings.LINK_EXPIRY_MINUTES} min.")
        
        # Run once immediately
        try:
            logger.info("Running initial cleanup on startup...")
            run_periodic_cleanup()
        except Exception as e:
            logger.error(f"Error during initial periodic cleanup: {e}", exc_info=True)

        # Schedule the next run
        _cleanup_timer = Timer(settings.CLEANUP_INTERVAL_SECONDS, _scheduled_cleanup_task)
        _cleanup_timer.start()
        logger.info("Periodic cleanup task scheduled.")

def stop_periodic_cleanup() -> None:
    """
    Stops the periodic cleanup task.
    """
    global _cleanup_timer # Ensure we are modifying the global variable
    with _timer_lock:
        if _cleanup_timer is not None and _cleanup_timer.is_alive():
            _cleanup_timer.cancel()
            _cleanup_timer = None # Signal to _scheduled_cleanup_task not to reschedule
            logger.info("Periodic cleanup task has been stopped.")
        else:
            logger.warning("Attempted to stop periodic cleanup, but it was not running or already stopped.")

# --- Main block for testing ---
if __name__ == "__main__":
    import time
    from src.utils.file_store import UploadedFile # For creating test data

    # Configure logger for testing
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Testing file_service.py ---")

    # Override settings for testing
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True) # Ensure upload dir exists
    settings.LINK_EXPIRY_MINUTES = 1/60 # 1 second expiry for testing
    settings.CLEANUP_INTERVAL_SECONDS = 2 # Run cleanup every 2 seconds for testing
    logger.info(f"Test settings: Link Expiry: {settings.link_expiry_ms}ms, Cleanup Interval: {settings.CLEANUP_INTERVAL_SECONDS}s")
    
    # Helper to create dummy files
    def create_dummy_file(file_id: str, original_name: str, age_seconds: int = 0) -> UploadedFile:
        dummy_path = settings.UPLOAD_DIR / f"{file_id}_{original_name}"
        with open(dummy_path, "w") as f:
            f.write("This is a test file.")
        
        file_data = UploadedFile(
            id=file_id,
            file_path=str(dummy_path),
            original_name=original_name,
            mime_type="text/plain",
            timestamp=datetime.utcnow().timestamp() - age_seconds
        )
        file_store.add(file_id, file_data)
        logger.debug(f"Created dummy file: {original_name} (ID: {file_id}), Age: {age_seconds}s, Path: {dummy_path}")
        return file_data

    # 1. Test cleanup_file
    logger.info("\n--- Test 1: cleanup_file ---")
    test_file_id_1 = "testfile001"
    create_dummy_file(test_file_id_1, "cleanup_target.txt")
    assert file_store.get(test_file_id_1) is not None
    assert os.path.exists(file_store.get(test_file_id_1).file_path)
    cleanup_file(test_file_id_1)
    assert file_store.get(test_file_id_1) is None
    # Check if physical file is deleted (small delay might be needed for OS)
    # For now, we trust os.unlink works if no error is logged.
    logger.info("cleanup_file test completed.")

    # 2. Test run_periodic_cleanup
    logger.info("\n--- Test 2: run_periodic_cleanup ---")
    # Files that should be cleaned
    create_dummy_file("expired001", "expired_file_1.txt", age_seconds=5)
    create_dummy_file("expired002", "expired_file_2.txt", age_seconds=10)
    # File that should NOT be cleaned
    create_dummy_file("active001", "active_file.txt", age_seconds=0)
    
    assert file_store.get_size() == 3
    logger.info(f"Store size before run_periodic_cleanup: {file_store.get_size()}")
    run_periodic_cleanup() # LINK_EXPIRY is 1 sec for test
    logger.info(f"Store size after run_periodic_cleanup: {file_store.get_size()}")
    assert file_store.get_size() == 1
    assert file_store.get("active001") is not None
    assert file_store.get("expired001") is None
    assert file_store.get("expired002") is None
    logger.info("run_periodic_cleanup test completed.")
    
    # Cleanup remaining file
    cleanup_file("active001")
    assert file_store.get_size() == 0

    # 3. Test start_periodic_cleanup and stop_periodic_cleanup
    logger.info("\n--- Test 3: Periodic task start/stop ---")
    start_periodic_cleanup() # Includes an initial run
    
    # Create a file that will expire
    create_dummy_file("task_expire001", "task_expire_me.txt", age_seconds=0)
    logger.info(f"Created task_expire001. Store size: {file_store.get_size()}")
    assert file_store.get_size() == 1

    logger.info(f"Waiting for {settings.CLEANUP_INTERVAL_SECONDS + settings.link_expiry_ms/1000 + 1} seconds to see if periodic cleanup runs...")
    time.sleep(settings.CLEANUP_INTERVAL_SECONDS + settings.link_expiry_ms/1000 + 1) # Wait for one interval + expiry + buffer

    logger.info(f"Store size after waiting: {file_store.get_size()}")
    assert file_store.get_size() == 0, f"File 'task_expire001' should have been cleaned. Store size: {file_store.get_size()}"

    stop_periodic_cleanup()
    logger.info("Periodic task stopped. Any further messages about rescheduling should indicate it's from a previous, now-cancelled timer.")
    
    # Test stopping a non-running timer
    logger.info("Attempting to stop again (should warn).")
    stop_periodic_cleanup()

    # Test restarting
    logger.info("Restarting periodic cleanup...")
    start_periodic_cleanup() # Should run initial cleanup (no files to clean) and schedule
    create_dummy_file("task_expire002", "task_expire_me_again.txt", age_seconds=0)
    logger.info(f"Created task_expire002. Store size: {file_store.get_size()}")
    time.sleep(settings.CLEANUP_INTERVAL_SECONDS + settings.link_expiry_ms/1000 + 1)
    assert file_store.get_size() == 0, f"File 'task_expire002' should have been cleaned after restart. Store size: {file_store.get_size()}"
    stop_periodic_cleanup()


    logger.info("\n--- All file_service.py tests completed ---")
    # Clean up dummy files created if any are left (e.g., if tests failed)
    for f_id, f_data in file_store.get_all():
        if os.path.exists(f_data.file_path):
            os.unlink(f_data.file_path)
        file_store.delete(f_id)
    if settings.UPLOAD_DIR.exists() and not os.listdir(settings.UPLOAD_DIR): # only remove if empty
        os.rmdir(settings.UPLOAD_DIR)
    elif settings.UPLOAD_DIR.exists():
        logger.warning(f"Test upload directory {settings.UPLOAD_DIR} not empty. Manual cleanup might be needed.")
