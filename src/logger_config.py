
import logging
import sys
from pathlib import Path


def setup_logging():
    """
    Sets up a centralized logger for the application.
    Logs are sent to both the console (INFO level) and a file (DEBUG level).
    """
    # Define the log file path relative to the project root
    project_root = Path(__file__).parent.parent.resolve()
    log_file_path = project_root / "altdoge.log"

    # Get the root logger
    root_logger = logging.getLogger()

    # Avoid adding duplicate handlers if this function is called multiple times
    if root_logger.hasHandlers():
        # Clear existing handlers to ensure a clean setup
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    root_logger.setLevel(logging.DEBUG)  # Set the lowest level to capture all messages

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a file handler to write logs to a file
    # Use 'a' for append mode
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Log all levels to the file
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Create a stream handler to write logs to the console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)  # Log INFO and above to the console
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    logging.info("Logging configured to write to console and altdoge.log")
