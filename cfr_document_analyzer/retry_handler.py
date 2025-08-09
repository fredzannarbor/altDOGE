"""
Retry handler for Federal Register API calls.

Implements exponential backoff and error classification for robust API interactions.
"""

import time
import random
import logging
from typing import Callable, Any, Optional, Tuple
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True


class RetryHandler:
    """Handles retries with exponential backoff and error classification."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry handler.
        
        Args:
            config: Retry configuration, uses defaults if None
        """
        self.config = config or RetryConfig()
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Tuple[Any, bool, Optional[str]]:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Tuple of (result, success, error_message)
        """
        last_error = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"Function succeeded on attempt {attempt}")
                return result, True, None
                
            except Exception as e:
                last_error = str(e)
                error_type = self._classify_error(e)
                
                logger.debug(f"Attempt {attempt} failed with {error_type} error: {e}")
                
                # Don't retry permanent errors
                if error_type == 'permanent':
                    logger.debug(f"Permanent error, not retrying: {e}")
                    return None, False, last_error
                
                # Don't retry on last attempt
                if attempt == self.config.max_attempts:
                    logger.warning(f"All {self.config.max_attempts} attempts failed, last error: {e}")
                    return None, False, last_error
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, e)
                logger.debug(f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{self.config.max_attempts})")
                time.sleep(delay)
        
        return None, False, last_error
    
    def _classify_error(self, error: Exception) -> str:
        """
        Classify error as temporary or permanent.
        
        Args:
            error: Exception to classify
            
        Returns:
            'temporary', 'permanent', or 'critical'
        """
        if isinstance(error, requests.exceptions.RequestException):
            if isinstance(error, requests.exceptions.Timeout):
                return 'temporary'
            elif isinstance(error, requests.exceptions.ConnectionError):
                return 'temporary'
            elif hasattr(error, 'response') and error.response is not None:
                status_code = error.response.status_code
                
                # Temporary errors (should retry)
                if status_code in [429, 500, 502, 503, 504]:
                    return 'temporary'
                
                # Permanent errors (don't retry)
                elif status_code in [400, 401, 403, 404, 410]:
                    return 'permanent'
                
                # Other HTTP errors - treat as temporary
                else:
                    return 'temporary'
            else:
                # Network-level errors - treat as temporary
                return 'temporary'
        
        # Non-HTTP errors - treat as temporary by default
        return 'temporary'
    
    def _calculate_delay(self, attempt: int, error: Exception) -> float:
        """
        Calculate delay for next retry attempt.
        
        Args:
            attempt: Current attempt number (1-based)
            error: Exception that caused the retry
            
        Returns:
            Delay in seconds
        """
        # Handle rate limiting specially
        if self._is_rate_limit_error(error):
            return self._handle_rate_limit(error)
        
        # Standard exponential backoff
        delay = self.config.base_delay * (self.config.backoff_factor ** (attempt - 1))
        
        # Cap at maximum delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.config.jitter:
            jitter = random.uniform(0, delay * 0.1)  # Up to 10% jitter
            delay += jitter
        
        return delay
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if error is a rate limit error.
        
        Args:
            error: Exception to check
            
        Returns:
            True if rate limit error
        """
        if isinstance(error, requests.exceptions.HTTPError):
            if hasattr(error, 'response') and error.response is not None:
                return error.response.status_code == 429
        return False
    
    def _handle_rate_limit(self, error: Exception) -> float:
        """
        Handle rate limit error with appropriate delay.
        
        Args:
            error: Rate limit exception
            
        Returns:
            Delay in seconds
        """
        # Check for Retry-After header
        if hasattr(error, 'response') and error.response is not None:
            retry_after = error.response.headers.get('Retry-After')
            if retry_after:
                try:
                    delay = float(retry_after)
                    logger.info(f"Rate limited, waiting {delay} seconds as specified by Retry-After header")
                    return min(delay, self.config.max_delay)
                except ValueError:
                    pass
        
        # Default rate limit delay
        delay = 30.0  # 30 seconds default for rate limits
        logger.info(f"Rate limited, waiting {delay} seconds")
        return delay