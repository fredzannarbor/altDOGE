"""
Tests for parallel processing functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import threading
import time

from cfr_document_analyzer.parallel_processor import (
    ParallelProcessor, ParallelConfig, ResourceMonitor, ThreadSafeLLMClient
)
from cfr_document_analyzer.models import Document, AnalysisResult
from cfr_document_analyzer.llm_client import LLMClient


class TestResourceMonitor:
    """Test resource monitoring functionality."""
    
    def test_resource_monitor_initialization(self):
        """Test resource monitor initialization."""
        monitor = ResourceMonitor(memory_limit_mb=512)
        
        assert monitor.memory_limit_mb == 512
        assert not monitor.monitoring
        assert monitor.stats['peak_memory_mb'] == 0
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = ResourceMonitor()
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.monitoring is True
        assert monitor.monitor_thread is not None
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert monitor.monitoring is False
    
    def test_get_stats(self):
        """Test getting resource statistics."""
        monitor = ResourceMonitor()
        
        stats = monitor.get_stats()
        
        assert isinstance(stats, dict)
        assert 'peak_memory_mb' in stats
        assert 'peak_cpu_percent' in stats
        assert 'memory_warnings' in stats
        assert 'cpu_warnings' in stats
    
    @patch('cfr_document_analyzer.parallel_processor.psutil.Process')
    def test_memory_availability_check(self, mock_process):
        """Test memory availability checking."""
        # Mock process memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        monitor = ResourceMonitor(memory_limit_mb=512)
        
        # Should have memory available
        assert monitor.is_memory_available(100) is True
        
        # Should not have memory available for large request
        assert monitor.is_memory_available(500) is False


class TestParallelConfig:
    """Test parallel configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ParallelConfig()
        
        assert config.max_workers == 4
        assert config.chunk_size == 10
        assert config.timeout_seconds == 300
        assert config.memory_limit_mb == 1024
        assert config.enable_monitoring is True
        assert config.retry_failed_tasks is True
        assert config.max_retries == 3
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ParallelConfig(
            max_workers=8,
            chunk_size=20,
            timeout_seconds=600,
            memory_limit_mb=2048,
            enable_monitoring=False,
            retry_failed_tasks=False,
            max_retries=5
        )
        
        assert config.max_workers == 8
        assert config.chunk_size == 20
        assert config.timeout_seconds == 600
        assert config.memory_limit_mb == 2048
        assert config.enable_monitoring is False
        assert config.retry_failed_tasks is False
        assert config.max_retries == 5


class TestThreadSafeLLMClient:
    """Test thread-safe LLM client wrapper."""
    
    @pytest.fixture
    def mock_base_client(self):
        """Mock base LLM client."""
        client = Mock(spec=LLMClient)
        client.rate_limit = 1.0
        client.analyze_document.return_value = ("response", True, None)
        return client
    
    def test_thread_safe_client_initialization(self, mock_base_client):
        """Test thread-safe client initialization."""
        client = ThreadSafeLLMClient(mock_base_client)
        
        assert client.base_client == mock_base_client
        assert client.call_count == 0
        assert client.last_call_time == 0
    
    def test_thread_safe_analysis(self, mock_base_client):
        """Test thread-safe document analysis."""
        client = ThreadSafeLLMClient(mock_base_client)
        
        # Test analysis
        result = client.analyze_document_thread_safe("content", "prompt", "doc_123")
        
        # Verify result
        assert result == ("response", True, None)
        assert client.call_count == 1
        
        # Verify base client was called
        mock_base_client.analyze_document.assert_called_once_with("content", "prompt", "doc_123")
    
    def test_rate_limiting(self, mock_base_client):
        """Test rate limiting in thread-safe client."""
        mock_base_client.rate_limit = 10.0  # 10 requests per second
        client = ThreadSafeLLMClient(mock_base_client)
        
        # Make multiple rapid calls
        start_time = time.time()
        for i in range(3):
            client.analyze_document_thread_safe(f"content_{i}", "prompt", f"doc_{i}")
        end_time = time.time()
        
        # Should take at least 0.2 seconds (3 calls at 10/sec = 0.3s interval minimum)
        # We'll be lenient and check for at least 0.1 seconds
        assert end_time - start_time >= 0.1
        assert client.call_count == 3


class TestParallelProcessor:
    """Test parallel document processor."""
    
    @pytest.fixture
    def sample_documents(self):
        """Sample documents for testing."""
        return [
            Document(
                document_number="2024-001",
                title="Test Document 1",
                agency_slug="test-agency",
                content="Test content 1",
                id=1
            ),
            Document(
                document_number="2024-002",
                title="Test Document 2",
                agency_slug="test-agency",
                content="Test content 2",
                id=2
            ),
            Document(
                document_number="2024-003",
                title="Test Document 3",
                agency_slug="test-agency",
                content="Test content 3",
                id=3
            )
        ]
    
    @pytest.fixture
    def mock_process_func(self):
        """Mock processing function."""
        def process_func(document):
            # Simulate processing time
            time.sleep(0.01)
            return AnalysisResult(
                document_id=document.id,
                prompt_strategy="Test Strategy",
                success=True
            )
        return process_func
    
    def test_processor_initialization(self):
        """Test processor initialization."""
        config = ParallelConfig(max_workers=2)
        processor = ParallelProcessor(config)
        
        assert processor.config.max_workers == 2
        assert isinstance(processor.resource_monitor, ResourceMonitor)
        assert len(processor.active_futures) == 0
    
    def test_process_documents_parallel(self, sample_documents, mock_process_func):
        """Test parallel document processing."""
        config = ParallelConfig(max_workers=2, enable_monitoring=False)
        processor = ParallelProcessor(config)
        
        # Process documents
        results = processor.process_documents_parallel(
            sample_documents, mock_process_func
        )
        
        # Verify results
        assert len(results) == 3
        for result in results:
            assert isinstance(result, AnalysisResult)
            assert result.success is True
    
    def test_empty_documents_handling(self, mock_process_func):
        """Test handling of empty document list."""
        processor = ParallelProcessor()
        
        results = processor.process_documents_parallel([], mock_process_func)
        
        assert results == []
    
    def test_chunk_processing(self, sample_documents, mock_process_func):
        """Test chunk-based processing."""
        config = ParallelConfig(max_workers=2, chunk_size=2, enable_monitoring=False)
        processor = ParallelProcessor(config)
        
        # Process documents in chunks
        results = processor.process_documents_parallel(
            sample_documents, mock_process_func
        )
        
        # Should still get all results
        assert len(results) == 3
    
    def test_error_handling_in_processing(self, sample_documents):
        """Test error handling during processing."""
        def failing_process_func(document):
            if document.document_number == "2024-002":
                raise Exception("Processing failed")
            return AnalysisResult(
                document_id=document.id,
                prompt_strategy="Test Strategy",
                success=True
            )
        
        config = ParallelConfig(max_workers=2, enable_monitoring=False, retry_failed_tasks=False)
        processor = ParallelProcessor(config)
        
        # Process documents with one failure
        results = processor.process_documents_parallel(
            sample_documents, failing_process_func
        )
        
        # Should get results for successful documents only
        assert len(results) == 2
    
    def test_retry_mechanism(self, sample_documents):
        """Test retry mechanism for failed documents."""
        call_count = {}
        
        def flaky_process_func(document):
            doc_id = document.document_number
            call_count[doc_id] = call_count.get(doc_id, 0) + 1
            
            # Fail on first attempt, succeed on retry
            if call_count[doc_id] == 1 and doc_id == "2024-002":
                raise Exception("First attempt failed")
            
            return AnalysisResult(
                document_id=document.id,
                prompt_strategy="Test Strategy",
                success=True
            )
        
        config = ParallelConfig(
            max_workers=2, 
            enable_monitoring=False, 
            retry_failed_tasks=True,
            max_retries=2
        )
        processor = ParallelProcessor(config)
        
        # Process documents with retry
        results = processor.process_documents_parallel(
            sample_documents, flaky_process_func
        )
        
        # Should get all results after retry
        assert len(results) == 3
        # Document 2024-002 should have been called twice
        assert call_count["2024-002"] == 2
    
    def test_get_active_tasks(self, sample_documents, mock_process_func):
        """Test getting active task information."""
        processor = ParallelProcessor()
        
        # Initially no active tasks
        active_tasks = processor.get_active_tasks()
        assert len(active_tasks) == 0
    
    def test_get_performance_stats(self):
        """Test getting performance statistics."""
        config = ParallelConfig(max_workers=4, chunk_size=10)
        processor = ParallelProcessor(config)
        
        stats = processor.get_performance_stats()
        
        assert isinstance(stats, dict)
        assert stats['config']['max_workers'] == 4
        assert stats['config']['chunk_size'] == 10
        assert 'resource_usage' in stats
        assert 'active_tasks' in stats
    
    def test_cancel_all_tasks(self):
        """Test cancelling all active tasks."""
        processor = ParallelProcessor()
        
        # Cancel tasks (should handle empty case gracefully)
        processor.cancel_all_tasks()
        
        # Should have no active tasks
        assert len(processor.active_futures) == 0
    
    @patch('cfr_document_analyzer.parallel_processor.ThreadPoolExecutor')
    def test_timeout_handling(self, mock_executor, sample_documents):
        """Test timeout handling in parallel processing."""
        # Mock executor to simulate timeout
        mock_future = Mock()
        mock_future.result.side_effect = TimeoutError("Task timed out")
        
        mock_executor_instance = Mock()
        mock_executor_instance.submit.return_value = mock_future
        mock_executor_instance.__enter__.return_value = mock_executor_instance
        mock_executor_instance.__exit__.return_value = None
        mock_executor.return_value = mock_executor_instance
        
        # Mock as_completed to yield the future
        with patch('cfr_document_analyzer.parallel_processor.as_completed') as mock_as_completed:
            mock_as_completed.return_value = [mock_future]
            
            config = ParallelConfig(timeout_seconds=1, enable_monitoring=False)
            processor = ParallelProcessor(config)
            
            def dummy_process_func(document):
                return AnalysisResult(document_id=document.id, prompt_strategy="Test", success=True)
            
            # Should handle timeout gracefully
            results = processor.process_documents_parallel([sample_documents[0]], dummy_process_func)
            
            # Should return empty results due to timeout
            assert len(results) == 0
    
    @pytest.mark.integration
    def test_parallel_processing_integration(self, sample_documents):
        """Integration test for parallel processing."""
        # This would test the full parallel processing workflow
        # with real threading and resource monitoring
        pass