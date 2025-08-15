"""
Parallel processing capabilities for CFR Document Analyzer.

Provides thread-safe parallel document processing with resource management.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from queue import Queue, Empty
import psutil
import os

from .models import Document, AnalysisResult
from .llm_client import LLMClient
from .progress_tracker import ProgressTracker, ProgressStage


logger = logging.getLogger(__name__)


@dataclass
class ParallelConfig:
    """Configuration for parallel processing."""
    max_workers: int = 4
    chunk_size: int = 10
    timeout_seconds: int = 300
    memory_limit_mb: int = 1024
    enable_monitoring: bool = True
    retry_failed_tasks: bool = True
    max_retries: int = 3


class ResourceMonitor:
    """Monitors system resources during parallel processing."""
    
    def __init__(self, memory_limit_mb: int = 1024):
        """
        Initialize resource monitor.
        
        Args:
            memory_limit_mb: Memory limit in megabytes
        """
        self.memory_limit_mb = memory_limit_mb
        self.monitoring = False
        self.monitor_thread = None
        self.stats = {
            'peak_memory_mb': 0,
            'peak_cpu_percent': 0,
            'memory_warnings': 0,
            'cpu_warnings': 0
        }
        self._lock = threading.Lock()
    
    def start_monitoring(self):
        """Start resource monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self):
        """Resource monitoring loop."""
        while self.monitoring:
            try:
                # Get current process
                process = psutil.Process(os.getpid())
                
                # Memory usage
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                # CPU usage
                cpu_percent = process.cpu_percent()
                
                with self._lock:
                    # Update peak values
                    self.stats['peak_memory_mb'] = max(self.stats['peak_memory_mb'], memory_mb)
                    self.stats['peak_cpu_percent'] = max(self.stats['peak_cpu_percent'], cpu_percent)
                    
                    # Check limits
                    if memory_mb > self.memory_limit_mb:
                        self.stats['memory_warnings'] += 1
                        logger.warning(f"Memory usage ({memory_mb:.1f} MB) exceeds limit ({self.memory_limit_mb} MB)")
                    
                    if cpu_percent > 90:
                        self.stats['cpu_warnings'] += 1
                        logger.warning(f"High CPU usage: {cpu_percent:.1f}%")
                
                time.sleep(1.0)  # Monitor every second
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resource monitoring statistics."""
        with self._lock:
            return self.stats.copy()
    
    def is_memory_available(self, required_mb: int = 100) -> bool:
        """Check if sufficient memory is available."""
        try:
            process = psutil.Process(os.getpid())
            current_mb = process.memory_info().rss / 1024 / 1024
            return (current_mb + required_mb) <= self.memory_limit_mb
        except Exception:
            return True  # Assume available if can't check


class ParallelProcessor:
    """Parallel document processor with resource management."""
    
    def __init__(self, config: Optional[ParallelConfig] = None):
        """
        Initialize parallel processor.
        
        Args:
            config: Parallel processing configuration
        """
        self.config = config or ParallelConfig()
        self.resource_monitor = ResourceMonitor(self.config.memory_limit_mb)
        self.active_futures: Dict[Future, Dict[str, Any]] = {}
        self.results_queue = Queue()
        self.error_queue = Queue()
        self._lock = threading.Lock()
        
        logger.info(f"Parallel processor initialized with {self.config.max_workers} workers")
    
    def process_documents_parallel(self, 
                                 documents: List[Document], 
                                 process_func: Callable[[Document], AnalysisResult],
                                 progress_tracker: Optional[ProgressTracker] = None) -> List[AnalysisResult]:
        """
        Process documents in parallel.
        
        Args:
            documents: List of documents to process
            process_func: Function to process each document
            progress_tracker: Optional progress tracker
            
        Returns:
            List of analysis results
        """
        if not documents:
            return []
        
        logger.info(f"Starting parallel processing of {len(documents)} documents")
        
        # Start resource monitoring
        if self.config.enable_monitoring:
            self.resource_monitor.start_monitoring()
        
        try:
            # Initialize progress tracking
            if progress_tracker:
                progress_tracker.start_stage(
                    ProgressStage.ANALYZING_DOCUMENTS, 
                    len(documents),
                    f"Processing {len(documents)} documents in parallel"
                )
            
            results = []
            failed_documents = []
            
            # Process in chunks to manage memory
            chunk_size = min(self.config.chunk_size, len(documents))
            
            for i in range(0, len(documents), chunk_size):
                chunk = documents[i:i + chunk_size]
                
                logger.info(f"Processing chunk {i//chunk_size + 1}/{(len(documents) + chunk_size - 1)//chunk_size}")
                
                # Process chunk in parallel
                chunk_results, chunk_failures = self._process_chunk(
                    chunk, process_func, progress_tracker, i
                )
                
                results.extend(chunk_results)
                failed_documents.extend(chunk_failures)
                
                # Check memory usage between chunks
                if not self.resource_monitor.is_memory_available(100):
                    logger.warning("Low memory detected, forcing garbage collection")
                    import gc
                    gc.collect()
            
            # Retry failed documents if configured
            if self.config.retry_failed_tasks and failed_documents:
                logger.info(f"Retrying {len(failed_documents)} failed documents")
                retry_results, _ = self._retry_failed_documents(
                    failed_documents, process_func, progress_tracker
                )
                results.extend(retry_results)
            
            # Complete progress tracking
            if progress_tracker:
                progress_tracker.complete_stage(
                    f"Completed processing {len(results)} documents successfully"
                )
            
            logger.info(f"Parallel processing completed: {len(results)} successful, {len(failed_documents)} failed")
            
            return results
            
        except Exception as e:
            logger.error(f"Parallel processing failed: {e}")
            if progress_tracker:
                progress_tracker.fail_stage(f"Parallel processing failed: {e}")
            raise
        
        finally:
            # Stop resource monitoring
            if self.config.enable_monitoring:
                self.resource_monitor.stop_monitoring()
    
    def _process_chunk(self, 
                      chunk: List[Document], 
                      process_func: Callable[[Document], AnalysisResult],
                      progress_tracker: Optional[ProgressTracker],
                      base_index: int) -> Tuple[List[AnalysisResult], List[Document]]:
        """
        Process a chunk of documents in parallel.
        
        Args:
            chunk: Chunk of documents to process
            process_func: Processing function
            progress_tracker: Progress tracker
            base_index: Base index for progress tracking
            
        Returns:
            Tuple of (successful results, failed documents)
        """
        results = []
        failed_documents = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit tasks
            future_to_doc = {}
            for i, document in enumerate(chunk):
                future = executor.submit(self._safe_process_document, document, process_func)
                future_to_doc[future] = (document, base_index + i)
                
                with self._lock:
                    self.active_futures[future] = {
                        'document_id': document.document_number,
                        'start_time': time.time(),
                        'index': base_index + i
                    }
            
            # Collect results
            for future in as_completed(future_to_doc, timeout=self.config.timeout_seconds):
                document, doc_index = future_to_doc[future]
                
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        logger.debug(f"Successfully processed document {document.document_number}")
                    else:
                        failed_documents.append(document)
                        logger.warning(f"Failed to process document {document.document_number}")
                    
                    # Update progress
                    if progress_tracker:
                        progress_tracker.update_progress(
                            doc_index + 1,
                            f"Processed document {document.document_number}",
                            {'document_id': document.document_number, 'success': result is not None}
                        )
                
                except Exception as e:
                    logger.error(f"Error processing document {document.document_number}: {e}")
                    failed_documents.append(document)
                    
                    if progress_tracker:
                        progress_tracker.update_progress(
                            doc_index + 1,
                            f"Failed to process document {document.document_number}",
                            {'document_id': document.document_number, 'error': str(e)}
                        )
                
                finally:
                    # Clean up future tracking
                    with self._lock:
                        if future in self.active_futures:
                            del self.active_futures[future]
        
        return results, failed_documents
    
    def _safe_process_document(self, document: Document, process_func: Callable[[Document], AnalysisResult]) -> Optional[AnalysisResult]:
        """
        Safely process a single document with error handling.
        
        Args:
            document: Document to process
            process_func: Processing function
            
        Returns:
            AnalysisResult or None if failed
        """
        try:
            # Check memory before processing
            if not self.resource_monitor.is_memory_available(50):
                logger.warning(f"Skipping document {document.document_number} due to low memory")
                return None
            
            return process_func(document)
            
        except Exception as e:
            logger.error(f"Error in safe_process_document for {document.document_number}: {e}")
            return None
    
    def _retry_failed_documents(self, 
                               failed_documents: List[Document],
                               process_func: Callable[[Document], AnalysisResult],
                               progress_tracker: Optional[ProgressTracker]) -> Tuple[List[AnalysisResult], List[Document]]:
        """
        Retry processing failed documents.
        
        Args:
            failed_documents: Documents that failed processing
            process_func: Processing function
            progress_tracker: Progress tracker
            
        Returns:
            Tuple of (successful results, still failed documents)
        """
        results = []
        still_failed = []
        
        for attempt in range(self.config.max_retries):
            if not failed_documents:
                break
            
            logger.info(f"Retry attempt {attempt + 1}/{self.config.max_retries} for {len(failed_documents)} documents")
            
            # Wait before retry
            if attempt > 0:
                time.sleep(2 ** attempt)  # Exponential backoff
            
            # Process with single thread for retries
            current_failed = []
            for document in failed_documents:
                try:
                    result = self._safe_process_document(document, process_func)
                    if result:
                        results.append(result)
                        logger.info(f"Successfully retried document {document.document_number}")
                    else:
                        current_failed.append(document)
                except Exception as e:
                    logger.error(f"Retry failed for document {document.document_number}: {e}")
                    current_failed.append(document)
            
            failed_documents = current_failed
        
        still_failed = failed_documents
        return results, still_failed
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get information about currently active tasks.
        
        Returns:
            List of active task information
        """
        with self._lock:
            active_tasks = []
            current_time = time.time()
            
            for future, info in self.active_futures.items():
                active_tasks.append({
                    'document_id': info['document_id'],
                    'index': info['index'],
                    'running_time': current_time - info['start_time'],
                    'done': future.done()
                })
            
            return active_tasks
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance statistics
        """
        resource_stats = self.resource_monitor.get_stats()
        
        return {
            'config': {
                'max_workers': self.config.max_workers,
                'chunk_size': self.config.chunk_size,
                'timeout_seconds': self.config.timeout_seconds,
                'memory_limit_mb': self.config.memory_limit_mb
            },
            'resource_usage': resource_stats,
            'active_tasks': len(self.active_futures),
            'monitoring_enabled': self.config.enable_monitoring
        }
    
    def cancel_all_tasks(self):
        """Cancel all active tasks."""
        with self._lock:
            cancelled_count = 0
            for future in list(self.active_futures.keys()):
                if future.cancel():
                    cancelled_count += 1
            
            logger.info(f"Cancelled {cancelled_count} active tasks")
            self.active_futures.clear()


class ThreadSafeLLMClient:
    """Thread-safe wrapper for LLM client."""
    
    def __init__(self, base_client: LLMClient):
        """
        Initialize thread-safe LLM client.
        
        Args:
            base_client: Base LLM client to wrap
        """
        self.base_client = base_client
        self._lock = threading.Lock()
        self.call_count = 0
        self.last_call_time = 0
    
    def analyze_document_thread_safe(self, content: str, prompt: str, document_id: str = None) -> Tuple[str, bool, Optional[str]]:
        """
        Thread-safe document analysis.
        
        Args:
            content: Document content
            prompt: Analysis prompt
            document_id: Document identifier
            
        Returns:
            Tuple of (response_text, success, error_message)
        """
        with self._lock:
            # Enforce rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_call_time
            min_interval = 1.0 / self.base_client.rate_limit if self.base_client.rate_limit > 0 else 0
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
            
            # Make the call
            result = self.base_client.analyze_document(content, prompt, document_id)
            
            self.call_count += 1
            self.last_call_time = time.time()
            
            return result
    
    def get_call_count(self) -> int:
        """Get number of calls made."""
        with self._lock:
            return self.call_count


def create_parallel_document_processor(documents: List[Document], 
                                     llm_client: LLMClient,
                                     prompt: str,
                                     config: Optional[ParallelConfig] = None) -> Callable[[Document], AnalysisResult]:
    """
    Create a parallel document processor function.
    
    Args:
        documents: List of documents (for context)
        llm_client: LLM client for analysis
        prompt: Analysis prompt
        config: Parallel processing configuration
        
    Returns:
        Document processing function
    """
    thread_safe_client = ThreadSafeLLMClient(llm_client)
    
    def process_document(document: Document) -> Optional[AnalysisResult]:
        """Process a single document."""
        try:
            if not document.content:
                logger.warning(f"Document {document.document_number} has no content")
                return None
            
            # Analyze document
            response_text, success, error = thread_safe_client.analyze_document_thread_safe(
                document.content, prompt, document.document_number
            )
            
            if success:
                # Create analysis result
                result = AnalysisResult(
                    document_id=document.id,
                    prompt_strategy="Parallel Analysis",
                    raw_response=response_text,
                    success=True
                )
                return result
            else:
                logger.error(f"Analysis failed for document {document.document_number}: {error}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing document {document.document_number}: {e}")
            return None
    
    return process_document