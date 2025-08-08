"""
Error handling utilities for the CFR Agency Document Counter.

This module provides comprehensive error handling, recovery mechanisms,
and logging utilities for robust operation.
"""

import logging
import time
import functools
from typing import Any, Callable, Optional, Type, Union, List
from datetime import datetime


logger = logging.getLogger(__name__)


class CFRCounterError(Exception):
    """Base exception for CFR Agency Document Counter errors."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None, 
                 recoverable: bool = False):
        """
        Initialize CFR Counter error.
        
        Args:
            message: Error message
            cause: Original exception that caused this error
            recoverable: Whether this error is recoverable
        """
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.recoverable = recoverable
        self.timestamp = datetime.now()


class DataLoadError(CFRCounterError):
    """Error loading or parsing agency data."""
    pass


class APIError(CFRCounterError):
    """Error communicating with the Federal Register API."""
    pass


class ProcessingError(CFRCounterError):
    """Error during document counting or processing."""
    pass


class ReportGenerationError(CFRCounterError):
    """Error generating reports."""
    pass


class ConfigurationError(CFRCounterError):
    """Error in configuration or setup."""
    pass


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, 
                    backoff_factor: float = 2.0, 
                    exceptions: tuple = (Exception,),
                    recoverable_only: bool = True):
    """
    Decorator to retry function calls on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        recoverable_only: Only retry if error is marked as recoverable
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Check if error is recoverable (for CFRCounterError)
                    if (recoverable_only and 
                        isinstance(e, CFRCounterError) and 
                        not e.recoverable):
                        logger.error(f"Non-recoverable error in {func.__name__}: {e}")
                        raise
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def log_execution_time(func: Callable) -> Callable:
    """
    Decorator to log function execution time.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with execution time logging
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        func_name = f"{func.__module__}.{func.__name__}"
        
        try:
            logger.debug(f"Starting {func_name}")
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Completed {func_name} in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed {func_name} after {execution_time:.2f}s: {e}")
            raise
    
    return wrapper


def handle_graceful_degradation(fallback_value: Any = None, 
                               log_level: int = logging.WARNING):
    """
    Decorator for graceful degradation on errors.
    
    Args:
        fallback_value: Value to return on error
        log_level: Logging level for the error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.log(
                    log_level,
                    f"Graceful degradation in {func.__name__}: {e}. "
                    f"Returning fallback value: {fallback_value}"
                )
                return fallback_value
        
        return wrapper
    return decorator


class ErrorCollector:
    """Collects and manages errors during processing."""
    
    def __init__(self):
        """Initialize error collector."""
        self.errors: List[CFRCounterError] = []
        self.warnings: List[str] = []
        self.start_time = datetime.now()
    
    def add_error(self, error: Union[CFRCounterError, Exception], 
                  context: str = "") -> None:
        """
        Add an error to the collection.
        
        Args:
            error: Error to add
            context: Additional context information
        """
        if isinstance(error, CFRCounterError):
            cfr_error = error
        else:
            cfr_error = CFRCounterError(
                message=f"{context}: {str(error)}" if context else str(error),
                cause=error,
                recoverable=False
            )
        
        self.errors.append(cfr_error)
        logger.error(f"Error collected: {cfr_error.message}")
    
    def add_warning(self, message: str, context: str = "") -> None:
        """
        Add a warning to the collection.
        
        Args:
            message: Warning message
            context: Additional context information
        """
        warning_msg = f"{context}: {message}" if context else message
        self.warnings.append(warning_msg)
        logger.warning(f"Warning collected: {warning_msg}")
    
    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings have been collected."""
        return len(self.warnings) > 0
    
    def get_error_summary(self) -> str:
        """
        Get a summary of collected errors and warnings.
        
        Returns:
            Formatted summary string
        """
        lines = []
        
        if self.has_errors():
            lines.append(f"Errors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"  {i}. {error.message}")
                if error.cause:
                    lines.append(f"     Caused by: {error.cause}")
        
        if self.has_warnings():
            lines.append(f"Warnings ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"  {i}. {warning}")
        
        if not lines:
            lines.append("No errors or warnings collected")
        
        return "\n".join(lines)
    
    def get_recoverable_errors(self) -> List[CFRCounterError]:
        """Get list of recoverable errors."""
        return [error for error in self.errors if error.recoverable]
    
    def get_fatal_errors(self) -> List[CFRCounterError]:
        """Get list of fatal (non-recoverable) errors."""
        return [error for error in self.errors if not error.recoverable]
    
    def clear(self) -> None:
        """Clear all collected errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
        logger.debug("Error collector cleared")


def setup_error_logging(log_file: str = "errors.log") -> None:
    """
    Set up dedicated error logging.
    
    Args:
        log_file: Path to error log file
    """
    error_logger = logging.getLogger('cfr_agency_counter.errors')
    error_logger.setLevel(logging.ERROR)
    
    # Create error file handler
    error_handler = logging.FileHandler(log_file)
    error_handler.setLevel(logging.ERROR)
    
    # Create formatter for error logs
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
        'Exception: %(exc_info)s\n'
        '---'
    )
    error_handler.setFormatter(error_formatter)
    
    error_logger.addHandler(error_handler)
    logger.info(f"Error logging configured: {log_file}")


def log_system_info() -> None:
    """Log system information for debugging."""
    import sys
    import platform
    import os
    
    logger.info("System Information:")
    logger.info(f"  Python version: {sys.version}")
    logger.info(f"  Platform: {platform.platform()}")
    logger.info(f"  Architecture: {platform.architecture()}")
    logger.info(f"  Processor: {platform.processor()}")
    logger.info(f"  Working directory: {os.getcwd()}")
    logger.info(f"  Process ID: {os.getpid()}")


def create_error_context(operation: str, **kwargs) -> dict:
    """
    Create error context information.
    
    Args:
        operation: Name of the operation being performed
        **kwargs: Additional context information
        
    Returns:
        Dictionary with context information
    """
    context = {
        'operation': operation,
        'timestamp': datetime.now().isoformat(),
        'process_id': os.getpid() if 'os' in globals() else None
    }
    context.update(kwargs)
    return context


def safe_execute(func: Callable, *args, error_collector: Optional[ErrorCollector] = None, 
                context: str = "", **kwargs) -> Any:
    """
    Safely execute a function with error collection.
    
    Args:
        func: Function to execute
        *args: Positional arguments for function
        error_collector: ErrorCollector to add errors to
        context: Context information for errors
        **kwargs: Keyword arguments for function
        
    Returns:
        Function result or None if error occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_collector:
            error_collector.add_error(e, context)
        else:
            logger.error(f"Error in {context or func.__name__}: {e}")
        return None


class ProgressiveErrorHandler:
    """Handles errors with progressive severity levels."""
    
    def __init__(self, max_errors: int = 10, max_warnings: int = 50):
        """
        Initialize progressive error handler.
        
        Args:
            max_errors: Maximum errors before stopping
            max_warnings: Maximum warnings before stopping
        """
        self.max_errors = max_errors
        self.max_warnings = max_warnings
        self.error_count = 0
        self.warning_count = 0
        self.should_continue = True
    
    def handle_error(self, error: Exception, context: str = "") -> bool:
        """
        Handle an error and determine if processing should continue.
        
        Args:
            error: Error that occurred
            context: Context information
            
        Returns:
            True if processing should continue, False otherwise
        """
        self.error_count += 1
        
        logger.error(f"Error {self.error_count}/{self.max_errors} in {context}: {error}")
        
        if self.error_count >= self.max_errors:
            logger.critical(f"Maximum error threshold reached ({self.max_errors}). Stopping.")
            self.should_continue = False
        
        return self.should_continue
    
    def handle_warning(self, message: str, context: str = "") -> bool:
        """
        Handle a warning and determine if processing should continue.
        
        Args:
            message: Warning message
            context: Context information
            
        Returns:
            True if processing should continue, False otherwise
        """
        self.warning_count += 1
        
        logger.warning(f"Warning {self.warning_count}/{self.max_warnings} in {context}: {message}")
        
        if self.warning_count >= self.max_warnings:
            logger.error(f"Maximum warning threshold reached ({self.max_warnings}). Stopping.")
            self.should_continue = False
        
        return self.should_continue
    
    def reset(self) -> None:
        """Reset error and warning counts."""
        self.error_count = 0
        self.warning_count = 0
        self.should_continue = True