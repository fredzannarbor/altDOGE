"""Tests for the error handler module."""

import pytest
import time
import logging
from datetime import datetime
from unittest.mock import patch, MagicMock

from cfr_agency_counter.error_handler import (
    CFRCounterError,
    DataLoadError,
    APIError,
    ProcessingError,
    ReportGenerationError,
    ConfigurationError,
    retry_on_failure,
    log_execution_time,
    handle_graceful_degradation,
    ErrorCollector,
    safe_execute,
    ProgressiveErrorHandler
)


class TestCFRCounterError:
    """Test cases for CFRCounterError and subclasses."""
    
    def test_cfr_counter_error_creation(self):
        """Test CFRCounterError creation."""
        error = CFRCounterError("Test error", recoverable=True)
        
        assert error.message == "Test error"
        assert error.recoverable is True
        assert error.cause is None
        assert isinstance(error.timestamp, datetime)
    
    def test_cfr_counter_error_with_cause(self):
        """Test CFRCounterError with cause."""
        original_error = ValueError("Original error")
        error = CFRCounterError("Wrapped error", cause=original_error)
        
        assert error.message == "Wrapped error"
        assert error.cause == original_error
        assert error.recoverable is False
    
    def test_error_subclasses(self):
        """Test error subclasses."""
        data_error = DataLoadError("Data load failed")
        api_error = APIError("API failed")
        processing_error = ProcessingError("Processing failed")
        report_error = ReportGenerationError("Report failed")
        config_error = ConfigurationError("Config failed")
        
        assert isinstance(data_error, CFRCounterError)
        assert isinstance(api_error, CFRCounterError)
        assert isinstance(processing_error, CFRCounterError)
        assert isinstance(report_error, CFRCounterError)
        assert isinstance(config_error, CFRCounterError)


class TestRetryDecorator:
    """Test cases for retry_on_failure decorator."""
    
    def test_retry_success_on_first_attempt(self):
        """Test retry decorator with success on first attempt."""
        call_count = 0
        
        @retry_on_failure(max_retries=3)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        """Test retry decorator with success after failures."""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """Test retry decorator when all attempts fail."""
        call_count = 0
        
        @retry_on_failure(max_retries=2, delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError, match="Persistent failure"):
            test_function()
        
        assert call_count == 3  # Initial + 2 retries
    
    def test_retry_non_recoverable_error(self):
        """Test retry decorator with non-recoverable error."""
        call_count = 0
        
        @retry_on_failure(max_retries=3, recoverable_only=True)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise CFRCounterError("Non-recoverable", recoverable=False)
        
        with pytest.raises(CFRCounterError):
            test_function()
        
        assert call_count == 1  # Should not retry
    
    def test_retry_recoverable_error(self):
        """Test retry decorator with recoverable error."""
        call_count = 0
        
        @retry_on_failure(max_retries=2, delay=0.01, recoverable_only=True)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise CFRCounterError("Recoverable", recoverable=True)
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 3


class TestLogExecutionTime:
    """Test cases for log_execution_time decorator."""
    
    def test_log_execution_time_success(self):
        """Test execution time logging for successful function."""
        @log_execution_time
        def test_function():
            time.sleep(0.01)
            return "success"
        
        with patch('cfr_agency_counter.error_handler.logger') as mock_logger:
            result = test_function()
            
            assert result == "success"
            mock_logger.debug.assert_called()
            mock_logger.info.assert_called()
            
            # Check that execution time was logged
            info_call = mock_logger.info.call_args[0][0]
            assert "Completed" in info_call
            assert "test_function" in info_call
    
    def test_log_execution_time_failure(self):
        """Test execution time logging for failed function."""
        @log_execution_time
        def test_function():
            time.sleep(0.01)
            raise ValueError("Test error")
        
        with patch('cfr_agency_counter.error_handler.logger') as mock_logger:
            with pytest.raises(ValueError):
                test_function()
            
            mock_logger.debug.assert_called()
            mock_logger.error.assert_called()
            
            # Check that failure was logged
            error_call = mock_logger.error.call_args[0][0]
            assert "Failed" in error_call
            assert "test_function" in error_call


class TestGracefulDegradation:
    """Test cases for handle_graceful_degradation decorator."""
    
    def test_graceful_degradation_success(self):
        """Test graceful degradation with successful function."""
        @handle_graceful_degradation(fallback_value="fallback")
        def test_function():
            return "success"
        
        result = test_function()
        
        assert result == "success"
    
    def test_graceful_degradation_failure(self):
        """Test graceful degradation with failed function."""
        @handle_graceful_degradation(fallback_value="fallback")
        def test_function():
            raise ValueError("Test error")
        
        with patch('cfr_agency_counter.error_handler.logger') as mock_logger:
            result = test_function()
            
            assert result == "fallback"
            mock_logger.log.assert_called()
    
    def test_graceful_degradation_custom_log_level(self):
        """Test graceful degradation with custom log level."""
        @handle_graceful_degradation(fallback_value=None, log_level=logging.ERROR)
        def test_function():
            raise ValueError("Test error")
        
        with patch('cfr_agency_counter.error_handler.logger') as mock_logger:
            result = test_function()
            
            assert result is None
            # Check that log was called with ERROR level and a string message
            mock_logger.log.assert_called()
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.ERROR
            assert isinstance(call_args[0][1], str)


class TestErrorCollector:
    """Test cases for ErrorCollector class."""
    
    def test_error_collector_initialization(self):
        """Test ErrorCollector initialization."""
        collector = ErrorCollector()
        
        assert collector.errors == []
        assert collector.warnings == []
        assert isinstance(collector.start_time, datetime)
        assert not collector.has_errors()
        assert not collector.has_warnings()
    
    def test_add_error(self):
        """Test adding errors to collector."""
        collector = ErrorCollector()
        
        # Add CFRCounterError
        cfr_error = CFRCounterError("CFR error", recoverable=True)
        collector.add_error(cfr_error)
        
        # Add regular exception
        regular_error = ValueError("Regular error")
        collector.add_error(regular_error, "test context")
        
        assert len(collector.errors) == 2
        assert collector.has_errors()
        assert collector.errors[0] == cfr_error
        assert isinstance(collector.errors[1], CFRCounterError)
        assert "test context" in collector.errors[1].message
    
    def test_add_warning(self):
        """Test adding warnings to collector."""
        collector = ErrorCollector()
        
        collector.add_warning("Warning message")
        collector.add_warning("Another warning", "test context")
        
        assert len(collector.warnings) == 2
        assert collector.has_warnings()
        assert collector.warnings[0] == "Warning message"
        assert collector.warnings[1] == "test context: Another warning"
    
    def test_get_error_summary(self):
        """Test getting error summary."""
        collector = ErrorCollector()
        
        # Empty collector
        summary = collector.get_error_summary()
        assert "No errors or warnings" in summary
        
        # Add errors and warnings
        collector.add_error(ValueError("Test error"))
        collector.add_warning("Test warning")
        
        summary = collector.get_error_summary()
        assert "Errors (1):" in summary
        assert "Warnings (1):" in summary
        assert "Test error" in summary
        assert "Test warning" in summary
    
    def test_get_recoverable_errors(self):
        """Test getting recoverable errors."""
        collector = ErrorCollector()
        
        recoverable_error = CFRCounterError("Recoverable", recoverable=True)
        fatal_error = CFRCounterError("Fatal", recoverable=False)
        
        collector.add_error(recoverable_error)
        collector.add_error(fatal_error)
        
        recoverable = collector.get_recoverable_errors()
        fatal = collector.get_fatal_errors()
        
        assert len(recoverable) == 1
        assert len(fatal) == 1
        assert recoverable[0] == recoverable_error
        assert fatal[0] == fatal_error
    
    def test_clear(self):
        """Test clearing collector."""
        collector = ErrorCollector()
        
        collector.add_error(ValueError("Error"))
        collector.add_warning("Warning")
        
        assert collector.has_errors()
        assert collector.has_warnings()
        
        collector.clear()
        
        assert not collector.has_errors()
        assert not collector.has_warnings()
        assert len(collector.errors) == 0
        assert len(collector.warnings) == 0


class TestSafeExecute:
    """Test cases for safe_execute function."""
    
    def test_safe_execute_success(self):
        """Test safe_execute with successful function."""
        def test_function(x, y):
            return x + y
        
        result = safe_execute(test_function, 2, 3)
        
        assert result == 5
    
    def test_safe_execute_failure(self):
        """Test safe_execute with failed function."""
        def test_function():
            raise ValueError("Test error")
        
        result = safe_execute(test_function)
        
        assert result is None
    
    def test_safe_execute_with_collector(self):
        """Test safe_execute with error collector."""
        collector = ErrorCollector()
        
        def test_function():
            raise ValueError("Test error")
        
        result = safe_execute(test_function, error_collector=collector, context="test")
        
        assert result is None
        assert collector.has_errors()
        assert len(collector.errors) == 1
        assert "test: Test error" in collector.errors[0].message


class TestProgressiveErrorHandler:
    """Test cases for ProgressiveErrorHandler class."""
    
    def test_progressive_error_handler_initialization(self):
        """Test ProgressiveErrorHandler initialization."""
        handler = ProgressiveErrorHandler(max_errors=5, max_warnings=10)
        
        assert handler.max_errors == 5
        assert handler.max_warnings == 10
        assert handler.error_count == 0
        assert handler.warning_count == 0
        assert handler.should_continue is True
    
    def test_handle_error_within_limit(self):
        """Test handling errors within limit."""
        handler = ProgressiveErrorHandler(max_errors=3)
        
        # Handle errors within limit
        assert handler.handle_error(ValueError("Error 1")) is True
        assert handler.handle_error(ValueError("Error 2")) is True
        assert handler.error_count == 2
        assert handler.should_continue is True
    
    def test_handle_error_exceeds_limit(self):
        """Test handling errors that exceed limit."""
        handler = ProgressiveErrorHandler(max_errors=2)
        
        # Handle errors up to limit
        assert handler.handle_error(ValueError("Error 1")) is True
        assert handler.handle_error(ValueError("Error 2")) is False
        
        assert handler.error_count == 2
        assert handler.should_continue is False
    
    def test_handle_warning_within_limit(self):
        """Test handling warnings within limit."""
        handler = ProgressiveErrorHandler(max_warnings=3)
        
        # Handle warnings within limit
        assert handler.handle_warning("Warning 1") is True
        assert handler.handle_warning("Warning 2") is True
        assert handler.warning_count == 2
        assert handler.should_continue is True
    
    def test_handle_warning_exceeds_limit(self):
        """Test handling warnings that exceed limit."""
        handler = ProgressiveErrorHandler(max_warnings=2)
        
        # Handle warnings up to limit
        assert handler.handle_warning("Warning 1") is True
        assert handler.handle_warning("Warning 2") is False
        
        assert handler.warning_count == 2
        assert handler.should_continue is False
    
    def test_reset(self):
        """Test resetting error handler."""
        handler = ProgressiveErrorHandler(max_errors=5)
        
        # Add some errors
        handler.handle_error(ValueError("Error"))
        handler.handle_warning("Warning")
        
        assert handler.error_count == 1
        assert handler.warning_count == 1
        
        # Reset
        handler.reset()
        
        assert handler.error_count == 0
        assert handler.warning_count == 0
        assert handler.should_continue is True