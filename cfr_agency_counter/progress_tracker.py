"""
Progress Tracker for providing user feedback during document counting operations.

This module provides real-time progress updates, time estimation, and status
information during the document counting process.
"""

import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and displays progress during document counting operations."""
    
    def __init__(self, total_items: int, update_interval: float = 10.0):
        """
        Initialize the progress tracker.
        
        Args:
            total_items: Total number of items to process
            update_interval: Progress update interval as percentage (default: 10%)
        """
        self.total_items = total_items
        self.update_interval = update_interval
        self.processed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.start_time: Optional[datetime] = None
        self.last_update_time: Optional[datetime] = None
        self.last_update_percentage = 0.0
        self.current_item: Optional[str] = None
        
        logger.info(f"Progress tracker initialized for {total_items} items")
    
    def start(self) -> None:
        """Start tracking progress."""
        self.start_time = datetime.now()
        self.last_update_time = self.start_time
        logger.info("Progress tracking started")
        self._print_progress_header()
    
    def update(self, item_name: str, success: bool = True) -> None:
        """
        Update progress with a completed item.
        
        Args:
            item_name: Name of the item being processed
            success: Whether the item was processed successfully
        """
        self.current_item = item_name
        self.processed_items += 1
        
        if success:
            self.successful_items += 1
        else:
            self.failed_items += 1
        
        # Check if we should display a progress update
        current_percentage = (self.processed_items / self.total_items) * 100
        
        if (current_percentage - self.last_update_percentage >= self.update_interval or 
            self.processed_items == self.total_items):
            self._display_progress_update(current_percentage)
            self.last_update_percentage = current_percentage
            self.last_update_time = datetime.now()
    
    def set_current_item(self, item_name: str) -> None:
        """
        Set the current item being processed without updating counts.
        
        Args:
            item_name: Name of the item currently being processed
        """
        self.current_item = item_name
    
    def get_progress_stats(self) -> Dict[str, Any]:
        """
        Get current progress statistics.
        
        Returns:
            Dictionary with progress statistics
        """
        if not self.start_time:
            return {}
        
        elapsed_time = datetime.now() - self.start_time
        percentage_complete = (self.processed_items / self.total_items) * 100
        
        # Calculate estimated time remaining
        if self.processed_items > 0:
            avg_time_per_item = elapsed_time.total_seconds() / self.processed_items
            remaining_items = self.total_items - self.processed_items
            estimated_remaining = timedelta(seconds=avg_time_per_item * remaining_items)
        else:
            estimated_remaining = timedelta(0)
        
        # Calculate success rate
        success_rate = (self.successful_items / self.processed_items * 100) if self.processed_items > 0 else 0
        
        return {
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'successful_items': self.successful_items,
            'failed_items': self.failed_items,
            'percentage_complete': percentage_complete,
            'success_rate': success_rate,
            'elapsed_time': elapsed_time,
            'estimated_remaining': estimated_remaining,
            'current_item': self.current_item,
            'items_per_second': self.processed_items / elapsed_time.total_seconds() if elapsed_time.total_seconds() > 0 else 0
        }
    
    def finish(self) -> None:
        """Finish progress tracking and display final summary."""
        if not self.start_time:
            logger.warning("Progress tracking was never started")
            return
        
        end_time = datetime.now()
        total_time = end_time - self.start_time
        
        print("\n" + "="*80)
        print("PROCESSING COMPLETE")
        print("="*80)
        print(f"Total items processed: {self.processed_items}/{self.total_items}")
        print(f"Successful: {self.successful_items}")
        print(f"Failed: {self.failed_items}")
        success_rate = (self.successful_items/self.processed_items*100) if self.processed_items > 0 else 0.0
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Total time: {self._format_duration(total_time)}")
        avg_time = total_time.total_seconds()/self.processed_items if self.processed_items > 0 else 0.0
        print(f"Average time per item: {avg_time:.2f}s")
        print("="*80)
        
        logger.info(f"Progress tracking completed: {self.successful_items}/{self.processed_items} successful")
    
    def _print_progress_header(self) -> None:
        """Print the progress tracking header."""
        print("\n" + "="*80)
        print("CFR AGENCY DOCUMENT COUNTER - PROGRESS TRACKING")
        print("="*80)
        print(f"Processing {self.total_items} agencies...")
        print(f"Progress updates every {self.update_interval}%")
        print("-"*80)
    
    def _display_progress_update(self, percentage: float) -> None:
        """
        Display a progress update.
        
        Args:
            percentage: Current completion percentage
        """
        stats = self.get_progress_stats()
        
        # Create progress bar
        bar_width = 40
        filled_width = int(bar_width * percentage / 100)
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        print(f"\n[{bar}] {percentage:.1f}%")
        print(f"Processed: {stats['processed_items']}/{stats['total_items']} agencies")
        print(f"Success: {stats['successful_items']} | Failed: {stats['failed_items']} | Rate: {stats['success_rate']:.1f}%")
        print(f"Elapsed: {self._format_duration(stats['elapsed_time'])} | "
              f"Remaining: {self._format_duration(stats['estimated_remaining'])}")
        print(f"Speed: {stats['items_per_second']:.2f} agencies/sec")
        
        if stats['current_item']:
            print(f"Current: {stats['current_item']}")
        
        print("-"*80)
    
    def _format_duration(self, duration: timedelta) -> str:
        """
        Format a duration for display.
        
        Args:
            duration: Duration to format
            
        Returns:
            Formatted duration string
        """
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def get_eta_string(self) -> str:
        """
        Get estimated time of arrival as a formatted string.
        
        Returns:
            ETA string or empty if not available
        """
        if not self.start_time or self.processed_items == 0:
            return "Calculating..."
        
        stats = self.get_progress_stats()
        eta = datetime.now() + stats['estimated_remaining']
        return eta.strftime("%H:%M:%S")
    
    def is_complete(self) -> bool:
        """
        Check if processing is complete.
        
        Returns:
            True if all items have been processed
        """
        return self.processed_items >= self.total_items
    
    def get_summary_line(self) -> str:
        """
        Get a one-line summary of current progress.
        
        Returns:
            Summary string
        """
        if not self.start_time:
            return "Progress tracking not started"
        
        stats = self.get_progress_stats()
        return (f"Progress: {stats['percentage_complete']:.1f}% "
                f"({stats['processed_items']}/{stats['total_items']}) | "
                f"Success: {stats['success_rate']:.1f}% | "
                f"ETA: {self.get_eta_string()}")