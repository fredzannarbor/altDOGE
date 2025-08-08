"""Tests for the progress tracker module."""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from cfr_agency_counter.progress_tracker import ProgressTracker


class TestProgressTracker:
    """Test cases for the ProgressTracker class."""
    
    def test_initialization(self):
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker(total_items=100, update_interval=5.0)
        
        assert tracker.total_items == 100
        assert tracker.update_interval == 5.0
        assert tracker.processed_items == 0
        assert tracker.successful_items == 0
        assert tracker.failed_items == 0
        assert tracker.start_time is None
        assert tracker.current_item is None
    
    def test_start_tracking(self):
        """Test starting progress tracking."""
        tracker = ProgressTracker(total_items=50)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            tracker.start()
        
        assert tracker.start_time is not None
        assert tracker.last_update_time is not None
        assert "CFR AGENCY DOCUMENT COUNTER" in mock_stdout.getvalue()
        assert "Processing 50 agencies" in mock_stdout.getvalue()
    
    def test_update_successful_item(self):
        """Test updating progress with successful item."""
        tracker = ProgressTracker(total_items=10, update_interval=20.0)
        tracker.start()
        
        tracker.update("test-agency-1", success=True)
        
        assert tracker.processed_items == 1
        assert tracker.successful_items == 1
        assert tracker.failed_items == 0
        assert tracker.current_item == "test-agency-1"
    
    def test_update_failed_item(self):
        """Test updating progress with failed item."""
        tracker = ProgressTracker(total_items=10, update_interval=20.0)
        tracker.start()
        
        tracker.update("test-agency-1", success=False)
        
        assert tracker.processed_items == 1
        assert tracker.successful_items == 0
        assert tracker.failed_items == 1
        assert tracker.current_item == "test-agency-1"
    
    def test_progress_display_at_interval(self):
        """Test that progress is displayed at specified intervals."""
        tracker = ProgressTracker(total_items=10, update_interval=10.0)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            tracker.start()
            
            # First update should not trigger display (0% -> 10%)
            tracker.update("agency-1", success=True)
            first_output = mock_stdout.getvalue()
            
            # Second update should trigger display (10% -> 20%)
            tracker.update("agency-2", success=True)
            second_output = mock_stdout.getvalue()
        
        # Check that progress bar appeared after second update
        assert "█" in second_output and "█" not in first_output.split('\n')[-10:]
    
    def test_set_current_item(self):
        """Test setting current item without updating counts."""
        tracker = ProgressTracker(total_items=10)
        
        tracker.set_current_item("processing-agency")
        
        assert tracker.current_item == "processing-agency"
        assert tracker.processed_items == 0
        assert tracker.successful_items == 0
        assert tracker.failed_items == 0
    
    def test_get_progress_stats_before_start(self):
        """Test getting progress stats before starting."""
        tracker = ProgressTracker(total_items=10)
        
        stats = tracker.get_progress_stats()
        
        assert stats == {}
    
    def test_get_progress_stats_after_start(self):
        """Test getting progress stats after starting."""
        tracker = ProgressTracker(total_items=20)
        tracker.start()
        
        # Process some items
        tracker.update("agency-1", success=True)
        tracker.update("agency-2", success=False)
        tracker.update("agency-3", success=True)
        
        stats = tracker.get_progress_stats()
        
        assert stats['total_items'] == 20
        assert stats['processed_items'] == 3
        assert stats['successful_items'] == 2
        assert stats['failed_items'] == 1
        assert stats['percentage_complete'] == 15.0  # 3/20 * 100
        assert stats['success_rate'] == pytest.approx(66.67, rel=1e-2)  # 2/3 * 100
        assert isinstance(stats['elapsed_time'], timedelta)
        assert isinstance(stats['estimated_remaining'], timedelta)
        assert stats['current_item'] == "agency-3"
        assert stats['items_per_second'] >= 0
    
    def test_get_progress_stats_no_items_processed(self):
        """Test getting progress stats when no items have been processed."""
        tracker = ProgressTracker(total_items=10)
        tracker.start()
        
        stats = tracker.get_progress_stats()
        
        assert stats['processed_items'] == 0
        assert stats['success_rate'] == 0
        assert stats['estimated_remaining'] == timedelta(0)
    
    def test_finish_tracking(self):
        """Test finishing progress tracking."""
        tracker = ProgressTracker(total_items=5)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            tracker.start()
            
            # Process all items
            for i in range(5):
                tracker.update(f"agency-{i+1}", success=i < 4)  # Last one fails
            
            tracker.finish()
            output = mock_stdout.getvalue()
        
        assert "PROCESSING COMPLETE" in output
        assert "Total items processed: 5/5" in output
        assert "Successful: 4" in output
        assert "Failed: 1" in output
        assert "Success rate: 80.0%" in output
        assert "Total time:" in output
        assert "Average time per item:" in output
    
    def test_finish_without_start(self):
        """Test finishing tracking without starting."""
        tracker = ProgressTracker(total_items=10)
        
        with patch('sys.stdout', new_callable=StringIO):
            tracker.finish()  # Should not crash
    
    def test_format_duration_hours(self):
        """Test duration formatting with hours."""
        tracker = ProgressTracker(total_items=10)
        
        duration = timedelta(hours=2, minutes=30, seconds=45)
        formatted = tracker._format_duration(duration)
        
        assert formatted == "2h 30m 45s"
    
    def test_format_duration_minutes(self):
        """Test duration formatting with minutes only."""
        tracker = ProgressTracker(total_items=10)
        
        duration = timedelta(minutes=5, seconds=30)
        formatted = tracker._format_duration(duration)
        
        assert formatted == "5m 30s"
    
    def test_format_duration_seconds(self):
        """Test duration formatting with seconds only."""
        tracker = ProgressTracker(total_items=10)
        
        duration = timedelta(seconds=45)
        formatted = tracker._format_duration(duration)
        
        assert formatted == "45s"
    
    def test_get_eta_string_before_start(self):
        """Test getting ETA string before starting."""
        tracker = ProgressTracker(total_items=10)
        
        eta = tracker.get_eta_string()
        
        assert eta == "Calculating..."
    
    def test_get_eta_string_no_items_processed(self):
        """Test getting ETA string when no items processed."""
        tracker = ProgressTracker(total_items=10)
        tracker.start()
        
        eta = tracker.get_eta_string()
        
        assert eta == "Calculating..."
    
    def test_get_eta_string_with_progress(self):
        """Test getting ETA string with some progress."""
        tracker = ProgressTracker(total_items=10)
        tracker.start()
        tracker.update("agency-1", success=True)
        
        eta = tracker.get_eta_string()
        
        # Should be a time string in HH:MM:SS format
        assert len(eta) == 8  # HH:MM:SS
        assert eta.count(':') == 2
    
    def test_is_complete_false(self):
        """Test is_complete when not all items processed."""
        tracker = ProgressTracker(total_items=10)
        tracker.start()
        tracker.update("agency-1", success=True)
        
        assert not tracker.is_complete()
    
    def test_is_complete_true(self):
        """Test is_complete when all items processed."""
        tracker = ProgressTracker(total_items=2)
        tracker.start()
        tracker.update("agency-1", success=True)
        tracker.update("agency-2", success=True)
        
        assert tracker.is_complete()
    
    def test_get_summary_line_before_start(self):
        """Test getting summary line before starting."""
        tracker = ProgressTracker(total_items=10)
        
        summary = tracker.get_summary_line()
        
        assert summary == "Progress tracking not started"
    
    def test_get_summary_line_with_progress(self):
        """Test getting summary line with progress."""
        tracker = ProgressTracker(total_items=10)
        tracker.start()
        tracker.update("agency-1", success=True)
        tracker.update("agency-2", success=False)
        
        summary = tracker.get_summary_line()
        
        assert "Progress: 20.0%" in summary
        assert "(2/10)" in summary
        assert "Success: 50.0%" in summary
        assert "ETA:" in summary
    
    def test_progress_bar_display(self):
        """Test that progress bar is displayed correctly."""
        tracker = ProgressTracker(total_items=10, update_interval=10.0)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            tracker.start()
            tracker.update("agency-1", success=True)  # 10%
            output = mock_stdout.getvalue()
        
        # Should contain progress bar elements
        assert "█" in output  # Filled portion
        assert "░" in output  # Empty portion
        assert "10.0%" in output
        assert "Processed: 1/10" in output
        assert "Success: 1 | Failed: 0" in output
    
    def test_multiple_updates_with_display(self):
        """Test multiple updates with progress display."""
        tracker = ProgressTracker(total_items=5, update_interval=20.0)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            tracker.start()
            
            # First update: 20% - should trigger display
            tracker.update("agency-1", success=True)
            first_display = "20.0%" in mock_stdout.getvalue()
            
            # Second update: 40% - should trigger display
            tracker.update("agency-2", success=True)
            second_display = "40.0%" in mock_stdout.getvalue()
            
            # Third update: 60% - should trigger display
            tracker.update("agency-3", success=False)
            third_display = "60.0%" in mock_stdout.getvalue()
        
        assert first_display
        assert second_display
        assert third_display
    
    def test_final_update_always_displays(self):
        """Test that final update always displays progress."""
        tracker = ProgressTracker(total_items=3, update_interval=50.0)  # High interval
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            tracker.start()
            
            # These updates shouldn't trigger display due to high interval
            tracker.update("agency-1", success=True)  # 33.3%
            tracker.update("agency-2", success=True)  # 66.7%
            
            # Final update should always display
            tracker.update("agency-3", success=True)  # 100%
            output = mock_stdout.getvalue()
        
        assert "100.0%" in output  # Final progress should be shown