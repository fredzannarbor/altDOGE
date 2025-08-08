"""
Configuration settings for the CFR Agency Document Counter.

This module handles configuration from environment variables and provides
default values for the application.
"""

import os
import logging
from typing import Optional


class Config:
    """Configuration class for the CFR Agency Document Counter."""
    
    # Federal Register API settings
    FR_API_BASE_URL: str = os.getenv(
        'FR_API_BASE_URL', 
        'https://www.ecfr.gov/api/v1'
    )
    
    FR_API_RATE_LIMIT: float = float(os.getenv('FR_API_RATE_LIMIT', '1.0'))
    
    # Request settings
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_BACKOFF_FACTOR: float = float(os.getenv('RETRY_BACKOFF_FACTOR', '2.0'))
    
    # Output settings
    OUTPUT_DIRECTORY: str = os.getenv('OUTPUT_DIRECTORY', './results')
    DEFAULT_OUTPUT_FORMATS: list = ['csv', 'json']
    
    # Logging settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def setup_logging(cls, verbose: bool = False) -> None:
        """Set up logging configuration."""
        level = logging.DEBUG if verbose else getattr(logging, cls.LOG_LEVEL.upper())
        
        logging.basicConfig(
            level=level,
            format=cls.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('cfr_agency_counter.log')
            ]
        )
        
        # Reduce noise from urllib3
        logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    @classmethod
    def validate(cls) -> None:
        """Validate configuration settings."""
        if cls.FR_API_RATE_LIMIT <= 0:
            raise ValueError("API rate limit must be positive")
        
        if cls.REQUEST_TIMEOUT <= 0:
            raise ValueError("Request timeout must be positive")
        
        if cls.MAX_RETRIES < 0:
            raise ValueError("Max retries cannot be negative")
        
        if not cls.FR_API_BASE_URL.startswith(('http://', 'https://')):
            raise ValueError("API base URL must be a valid HTTP/HTTPS URL")