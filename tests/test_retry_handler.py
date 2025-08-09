"""
Tests for RetryHandler class.
"""

import pytest
import time
from unittest.mock import Mock, patch
import requests

from cfr_document_analyzer.retry_handler import RetryHandler, RetryConfig


class TestRetryHandler:
    """Test cases for RetryHandler class."""
    
    @pytest.fixture
    def retry_handler(self):
        """Create RetryHandler with test configuration."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,  # Short delay for tests
            max_delay=1.0,
            backoff_factor=2.0,
            jitter=False  # Disable jitter for predictable tests
        )
        return RetryHandler(config)
    
    def test_execute_with_retry_success_first_attempt(self, retry_handler):
        """Test successful execution on first attempt."""
        mock_func = Mock(return_value="success")
        
        result, success, error = retry_handler.execute_with_retry(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        assert success is True
        assert error is None
        assert mock_func.call_count == 1
    
    def test_execute_with_retry_success_after_retries(self, retry_handler):
        """Test successful execution after retries."""
        mock_func = Mock()
        mock_func.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            requests.exceptions.Timeout("Timeout"),
            "success"
        ]
        
        start_time = time.time()
        result, success, error = retry_handler.execute_with_retry(mock_func)
        end_time = time.time()
        
        assert result == "success"
        assert success is True
        assert error is None
        assert mock_func.call_count == 3
        # Should have delays between attempts
        assert end_time - start_time >= 0.3  # 0.1 + 0.2 seconds delay
    
    def test_execute_with_retry_permanent_error(self, retry_handler):
        """Test handling of permanent errors (no retry)."""
        mock_response = Mock()
        mock_response.status_code = 404
        error = requests.exceptions.HTTPError("404 Not Found")
        error.response = mock_response
        
        mock_func = Mock(side_effect=error)
        
        result, success, error_msg = retry_handler.execute_with_retry(mock_func)
        
        assert result is None
        assert success is False
        assert "404 Not Found" in error_msg
        assert mock_func.call_count == 1  # No retries for permanent errors
    
    def test_execute_with_retry_max_attempts_exceeded(self, retry_handler):
        """Test behavior when max attempts are exceeded."""
        mock_func = Mock(side_effect=requests.exceptions.Timeout("Timeout"))
        
        result, success, error = retry_handler.execute_with_retry(mock_func)
        
        assert result is None
        assert success is False
        assert "Timeout" in error
        assert mock_func.call_count == 3  # max_attempts
    
    def test_classify_error_temporary_errors(self, retry_handler):
        """Test classification of temporary errors."""
        # Timeout errors
        timeout_error = requests.exceptions.Timeout("Timeout")
        assert retry_handler._classify_error(timeout_error) == 'temporary'
        
        # Connection errors
        conn_error = requests.exceptions.ConnectionError("Connection failed")
        assert retry_handler._classify_error(conn_error) == 'temporary'
        
        # HTTP 5xx errors
        mock_response = Mock()
        mock_response.status_code = 500
        http_error = requests.exceptions.HTTPError("500 Server Error")
        http_error.response = mock_response
        assert retry_handler._classify_error(http_error) == 'temporary'
        
        # Rate limit errors
        mock_response.status_code = 429
        rate_limit_error = requests.exceptions.HTTPError("429 Too Many Requests")
        rate_limit_error.response = mock_response
        assert retry_handler._classify_error(rate_limit_error) == 'temporary'
    
    def test_classify_error_permanent_errors(self, retry_handler):
        """Test classification of permanent errors."""
        # HTTP 4xx errors (except 429)
        for status_code in [400, 401, 403, 404, 410]:
            mock_response = Mock()
            mock_response.status_code = status_code
            http_error = requests.exceptions.HTTPError(f"{status_code} Error")
            http_error.response = mock_response
            assert retry_handler._classify_error(http_error) == 'permanent'
    
    def test_calculate_delay_exponential_backoff(self, retry_handler):
        """Test exponential backoff delay calculation."""
        # First retry (attempt 1)
        delay1 = retry_handler._calculate_delay(1, Exception("test"))
        assert delay1 == 0.1  # base_delay
        
        # Second retry (attempt 2)
        delay2 = retry_handler._calculate_delay(2, Exception("test"))
        assert delay2 == 0.2  # base_delay * backoff_factor
        
        # Third retry (attempt 3)
        delay3 = retry_handler._calculate_delay(3, Exception("test"))
        assert delay3 == 0.4  # base_delay * backoff_factor^2
    
    def test_calculate_delay_max_delay_cap(self, retry_handler):
        """Test that delay is capped at max_delay."""
        # Large attempt number should be capped
        delay = retry_handler._calculate_delay(10, Exception("test"))
        assert delay == 1.0  # max_delay
    
    def test_handle_rate_limit_with_retry_after_header(self, retry_handler):
        """Test rate limit handling with Retry-After header."""
        mock_response = Mock()
        mock_response.headers = {'Retry-After': '5'}
        mock_response.status_code = 429
        
        error = requests.exceptions.HTTPError("429 Too Many Requests")
        error.response = mock_response
        
        delay = retry_handler._handle_rate_limit(error)
        assert delay == 5.0
    
    def test_handle_rate_limit_without_retry_after_header(self, retry_handler):
        """Test rate limit handling without Retry-After header."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 429
        
        error = requests.exceptions.HTTPError("429 Too Many Requests")
        error.response = mock_response
        
        delay = retry_handler._handle_rate_limit(error)
        assert delay == 30.0  # Default rate limit delay
    
    def test_is_rate_limit_error(self, retry_handler):
        """Test rate limit error detection."""
        # Rate limit error
        mock_response = Mock()
        mock_response.status_code = 429
        rate_limit_error = requests.exceptions.HTTPError("429 Too Many Requests")
        rate_limit_error.response = mock_response
        
        assert retry_handler._is_rate_limit_error(rate_limit_error) is True
        
        # Non-rate limit error
        mock_response.status_code = 404
        other_error = requests.exceptions.HTTPError("404 Not Found")
        other_error.response = mock_response
        
        assert retry_handler._is_rate_limit_error(other_error) is False
        
        # Non-HTTP error
        other_error = Exception("Some other error")
        assert retry_handler._is_rate_limit_error(other_error) is False
    
    @patch('time.sleep')
    def test_rate_limit_delay_calculation(self, mock_sleep, retry_handler):
        """Test that rate limit errors use special delay calculation."""
        mock_response = Mock()
        mock_response.headers = {'Retry-After': '10'}
        mock_response.status_code = 429
        
        rate_limit_error = requests.exceptions.HTTPError("429 Too Many Requests")
        rate_limit_error.response = mock_response
        
        mock_func = Mock()
        mock_func.side_effect = [rate_limit_error, "success"]
        
        result, success, error = retry_handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert success is True
        # Should have used the Retry-After delay
        mock_sleep.assert_called_once_with(10.0)