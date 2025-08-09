"""
Configuration settings for CFR Document Analyzer.

Extends the existing CFR counter configuration with document analysis settings.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for CFR Document Analyzer."""
    
    # Database settings
    DATABASE_PATH: str = os.getenv('CDA_DATABASE_PATH', './cfr_document_analyzer.db')
    
    # Federal Register API settings (inherited from cfr_agency_counter)
    FR_API_BASE_URL: str = os.getenv('FR_API_BASE_URL', 'https://www.federalregister.gov/api/v1')
    FR_API_RATE_LIMIT: float = float(os.getenv('FR_API_RATE_LIMIT', '1.0'))
    
    # Request settings
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_BACKOFF_FACTOR: float = float(os.getenv('RETRY_BACKOFF_FACTOR', '2.0'))
    
    # LLM settings
    DEFAULT_MODEL: str = os.getenv('CDA_DEFAULT_MODEL', 'gemini/gemini-2.5-flash')
    LLM_RATE_LIMIT: float = float(os.getenv('CDA_LLM_RATE_LIMIT', '1.0'))
    MAX_TOKENS: int = int(os.getenv('CDA_MAX_TOKENS', '16384'))
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    
    # Document processing settings
    MAX_DOCUMENT_LENGTH: int = int(os.getenv('CDA_MAX_DOC_LENGTH', '1000000'))
    DOCUMENT_CACHE_SIZE: int = int(os.getenv('CDA_CACHE_SIZE', '100'))
    
    # Document retrieval settings
    DEFAULT_PAGE_SIZE: int = int(os.getenv('CDA_DEFAULT_PAGE_SIZE', '100'))
    MAX_PAGE_SIZE: int = int(os.getenv('CDA_MAX_PAGE_SIZE', '1000'))
    ENABLE_HTML_FALLBACK: bool = os.getenv('CDA_ENABLE_HTML_FALLBACK', 'true').lower() == 'true'
    CONTENT_EXTRACTION_TIMEOUT: int = int(os.getenv('CDA_CONTENT_EXTRACTION_TIMEOUT', '30'))
    
    # Retry settings
    MAX_RETRY_ATTEMPTS: int = int(os.getenv('CDA_MAX_RETRY_ATTEMPTS', '3'))
    RETRY_BASE_DELAY: float = float(os.getenv('CDA_RETRY_BASE_DELAY', '1.0'))
    RETRY_MAX_DELAY: float = float(os.getenv('CDA_RETRY_MAX_DELAY', '60.0'))
    RETRY_BACKOFF_FACTOR: float = float(os.getenv('CDA_RETRY_BACKOFF_FACTOR', '2.0'))
    
    # Analysis settings
    DEFAULT_PROMPT_STRATEGY: str = os.getenv('CDA_DEFAULT_STRATEGY', 'DOGE Criteria')
    DEFAULT_DOCUMENT_LIMIT: int = int(os.getenv('CDA_DEFAULT_DOC_LIMIT', '10'))
    
    # Output settings
    OUTPUT_DIRECTORY: str = os.getenv('CDA_OUTPUT_DIR', './results')
    DEFAULT_OUTPUT_FORMATS: list = ['json', 'csv']
    
    # Logging settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE: str = os.getenv('CDA_LOG_FILE', 'cfr_document_analyzer.log')
    
    # Test agencies with small rule bodies for proof of concept
    TEST_AGENCIES: list = [
        'national-credit-union-administration',  # NCUA - smaller agency
        'farm-credit-administration',            # FCA - smaller agency  
        'federal-housing-finance-agency'         # FHFA - smaller agency
    ]
    
    @classmethod
    def setup_logging(cls, verbose: bool = False) -> None:
        """Set up logging configuration."""
        level = logging.DEBUG if verbose else getattr(logging, cls.LOG_LEVEL.upper())
        
        # Create logs directory if it doesn't exist
        log_path = Path(cls.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=level,
            format=cls.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(cls.LOG_FILE)
            ]
        )
        
        # Reduce noise from external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
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
        
        if cls.MAX_DOCUMENT_LENGTH <= 0:
            raise ValueError("Max document length must be positive")
        
        if cls.DEFAULT_DOCUMENT_LIMIT <= 0:
            raise ValueError("Default document limit must be positive")
    
    @classmethod
    def get_output_dir(cls) -> Path:
        """Get output directory as Path object, creating if necessary."""
        output_dir = Path(cls.OUTPUT_DIRECTORY)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir