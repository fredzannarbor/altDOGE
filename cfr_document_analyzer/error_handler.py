"""
Error handling for CFR Document Analyzer.

Provides centralized error handling and validation.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum


logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Error codes for different types of failures."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    API_ERROR = "API_ERROR"
    LLM_ERROR = "LLM_ERROR"
    DOCUMENT_ERROR = "DOCUMENT_ERROR"
    EXPORT_ERROR = "EXPORT_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class AnalysisError(Exception):
    """Base exception for analysis errors."""
    
    def __init__(self, message: str, error_code: ErrorCode, recoverable: bool = True, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.recoverable = recoverable
        self.context = context or {}
        super().__init__(message)


class ErrorHandler:
    """Centralized error handling and recovery."""
    
    @staticmethod
    def handle_validation_error(message: str, context: Optional[Dict] = None) -> AnalysisError:
        """Handle validation errors."""
        error = AnalysisError(message, ErrorCode.VALIDATION_ERROR, recoverable=False, context=context)
        logger.error(f"Validation error: {message}")
        return error
    
    @staticmethod
    def handle_database_error(message: str, context: Optional[Dict] = None) -> AnalysisError:
        """Handle database errors."""
        error = AnalysisError(message, ErrorCode.DATABASE_ERROR, recoverable=True, context=context)
        logger.error(f"Database error: {message}")
        return error
    
    @staticmethod
    def handle_api_error(message: str, context: Optional[Dict] = None) -> AnalysisError:
        """Handle API errors."""
        error = AnalysisError(message, ErrorCode.API_ERROR, recoverable=True, context=context)
        logger.error(f"API error: {message}")
        return error
    
    @staticmethod
    def handle_llm_error(message: str, context: Optional[Dict] = None) -> AnalysisError:
        """Handle LLM errors."""
        error = AnalysisError(message, ErrorCode.LLM_ERROR, recoverable=True, context=context)
        logger.error(f"LLM error: {message}")
        return error
    
    @staticmethod
    def handle_document_error(message: str, context: Optional[Dict] = None) -> AnalysisError:
        """Handle document processing errors."""
        error = AnalysisError(message, ErrorCode.DOCUMENT_ERROR, recoverable=True, context=context)
        logger.error(f"Document error: {message}")
        return error
    
    @staticmethod
    def handle_export_error(message: str, context: Optional[Dict] = None) -> AnalysisError:
        """Handle export errors."""
        error = AnalysisError(message, ErrorCode.EXPORT_ERROR, recoverable=True, context=context)
        logger.error(f"Export error: {message}")
        return error
    
    @staticmethod
    def validate_agency_slug(agency_slug: str) -> None:
        """Validate agency slug format."""
        if not agency_slug:
            raise ErrorHandler.handle_validation_error("Agency slug cannot be empty")
        
        if not isinstance(agency_slug, str):
            raise ErrorHandler.handle_validation_error("Agency slug must be a string")
        
        if len(agency_slug) < 3:
            raise ErrorHandler.handle_validation_error("Agency slug too short")
        
        # Check for valid characters (letters, numbers, hyphens)
        if not all(c.isalnum() or c == '-' for c in agency_slug):
            raise ErrorHandler.handle_validation_error("Agency slug contains invalid characters")
    
    @staticmethod
    def validate_document_limit(limit: Optional[int]) -> None:
        """Validate document limit parameter."""
        if limit is not None:
            if not isinstance(limit, int):
                raise ErrorHandler.handle_validation_error("Document limit must be an integer")
            
            if limit <= 0:
                raise ErrorHandler.handle_validation_error("Document limit must be positive")
            
            if limit > 1000:
                raise ErrorHandler.handle_validation_error("Document limit too large (max: 1000)")
    
    @staticmethod
    def validate_prompt_strategy(strategy: str, available_strategies: list) -> None:
        """Validate prompt strategy."""
        if not strategy:
            raise ErrorHandler.handle_validation_error("Prompt strategy cannot be empty")
        
        if strategy not in available_strategies:
            raise ErrorHandler.handle_validation_error(
                f"Unknown prompt strategy: {strategy}. Available: {', '.join(available_strategies)}"
            )
    
    @staticmethod
    def should_retry(error: AnalysisError) -> bool:
        """Determine if an error should trigger a retry."""
        if not error.recoverable:
            return False
        
        # Don't retry validation errors
        if error.error_code == ErrorCode.VALIDATION_ERROR:
            return False
        
        # Don't retry configuration errors
        if error.error_code == ErrorCode.CONFIGURATION_ERROR:
            return False
        
        return True
    
    @staticmethod
    def get_user_friendly_message(error: AnalysisError) -> str:
        """Get user-friendly error message."""
        error_messages = {
            ErrorCode.VALIDATION_ERROR: "Invalid input provided",
            ErrorCode.DATABASE_ERROR: "Database operation failed",
            ErrorCode.API_ERROR: "External service unavailable",
            ErrorCode.LLM_ERROR: "Analysis service unavailable",
            ErrorCode.DOCUMENT_ERROR: "Document processing failed",
            ErrorCode.EXPORT_ERROR: "Export operation failed",
            ErrorCode.CONFIGURATION_ERROR: "Configuration error"
        }
        
        base_message = error_messages.get(error.error_code, "Unknown error occurred")
        
        if error.recoverable:
            return f"{base_message}. Please try again."
        else:
            return f"{base_message}. Please check your input and try again."