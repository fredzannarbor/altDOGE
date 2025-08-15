"""
Progress tracking for CFR Document Analyzer.

Provides real-time progress tracking with callbacks and persistence.
"""

import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .database import Database
from .utils import safe_json_dumps, safe_json_loads


logger = logging.getLogger(__name__)


class ProgressStage(Enum):
    """Progress tracking stages."""
    INITIALIZING = "initializing"
    RETRIEVING_DOCUMENTS = "retrieving_documents"
    ANALYZING_DOCUMENTS = "analyzing_documents"
    PERFORMING_META_ANALYSIS = "performing_meta_analysis"
    EXPORTING_RESULTS = "exporting_results"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressUpdate:
    """Progress update information."""
    session_id: str
    stage: ProgressStage
    current_step: int
    total_steps: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_steps == 0:
            return 0.0
        return min(100.0, (self.current_step / self.total_steps) * 100.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'stage': self.stage.value,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'percentage': self.percentage,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }


class ProgressTracker:
    """Advanced progress tracking with callbacks and persistence."""
    
    def __init__(self, database: Database, session_id: str):
        """
        Initialize progress tracker.
        
        Args:
            database: Database instance
            session_id: Session identifier
        """
        self.database = database
        self.session_id = session_id
        self.callbacks: List[Callable[[ProgressUpdate], None]] = []
        self.current_stage = ProgressStage.INITIALIZING
        self.current_step = 0
        self.total_steps = 0
        self.start_time = time.time()
        self.stage_start_times: Dict[ProgressStage, float] = {}
        self.progress_history: List[ProgressUpdate] = []
        
        # Initialize progress table if needed
        self._initialize_progress_table()
        
        logger.info(f"Progress tracker initialized for session: {session_id}")
    
    def _initialize_progress_table(self):
        """Initialize progress tracking table."""
        try:
            query = """
                CREATE TABLE IF NOT EXISTS progress_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    current_step INTEGER NOT NULL,
                    total_steps INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    message TEXT,
                    details TEXT,  -- JSON
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """
            
            self.database.execute_query(query)
            
            # Create index for better performance
            index_query = "CREATE INDEX IF NOT EXISTS idx_progress_session ON progress_tracking(session_id)"
            self.database.execute_query(index_query)
            
        except Exception as e:
            logger.error(f"Failed to initialize progress table: {e}")
    
    def add_callback(self, callback: Callable[[ProgressUpdate], None]):
        """
        Add progress callback.
        
        Args:
            callback: Function to call on progress updates
        """
        self.callbacks.append(callback)
        logger.debug(f"Added progress callback for session {self.session_id}")
    
    def remove_callback(self, callback: Callable[[ProgressUpdate], None]):
        """
        Remove progress callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.debug(f"Removed progress callback for session {self.session_id}")
    
    def start_stage(self, stage: ProgressStage, total_steps: int, message: str = ""):
        """
        Start a new progress stage.
        
        Args:
            stage: Progress stage
            total_steps: Total number of steps in this stage
            message: Stage description message
        """
        self.current_stage = stage
        self.current_step = 0
        self.total_steps = total_steps
        self.stage_start_times[stage] = time.time()
        
        update = ProgressUpdate(
            session_id=self.session_id,
            stage=stage,
            current_step=0,
            total_steps=total_steps,
            message=message or f"Starting {stage.value.replace('_', ' ').title()}"
        )
        
        self._notify_progress(update)
        logger.info(f"Started stage {stage.value} with {total_steps} steps")
    
    def update_progress(self, current_step: int, message: str = "", details: Optional[Dict[str, Any]] = None):
        """
        Update progress within current stage.
        
        Args:
            current_step: Current step number
            message: Progress message
            details: Additional progress details
        """
        self.current_step = current_step
        
        update = ProgressUpdate(
            session_id=self.session_id,
            stage=self.current_stage,
            current_step=current_step,
            total_steps=self.total_steps,
            message=message,
            details=details or {}
        )
        
        self._notify_progress(update)
        
        # Log progress at intervals
        if current_step % max(1, self.total_steps // 10) == 0 or current_step == self.total_steps:
            logger.debug(f"Progress: {current_step}/{self.total_steps} ({update.percentage:.1f}%) - {message}")
    
    def increment_progress(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        """
        Increment progress by one step.
        
        Args:
            message: Progress message
            details: Additional progress details
        """
        self.update_progress(self.current_step + 1, message, details)
    
    def complete_stage(self, message: str = ""):
        """
        Complete the current stage.
        
        Args:
            message: Completion message
        """
        if self.current_stage in self.stage_start_times:
            stage_duration = time.time() - self.stage_start_times[self.current_stage]
            logger.info(f"Completed stage {self.current_stage.value} in {stage_duration:.2f}s")
        
        self.update_progress(
            self.total_steps, 
            message or f"Completed {self.current_stage.value.replace('_', ' ').title()}",
            {'stage_completed': True}
        )
    
    def fail_stage(self, error_message: str, details: Optional[Dict[str, Any]] = None):
        """
        Mark current stage as failed.
        
        Args:
            error_message: Error description
            details: Additional error details
        """
        self.current_stage = ProgressStage.FAILED
        
        update = ProgressUpdate(
            session_id=self.session_id,
            stage=ProgressStage.FAILED,
            current_step=self.current_step,
            total_steps=self.total_steps,
            message=error_message,
            details=details or {}
        )
        
        self._notify_progress(update)
        logger.error(f"Stage failed: {error_message}")
    
    def complete_analysis(self, message: str = "Analysis completed successfully"):
        """
        Mark entire analysis as completed.
        
        Args:
            message: Completion message
        """
        total_duration = time.time() - self.start_time
        
        self.current_stage = ProgressStage.COMPLETED
        
        update = ProgressUpdate(
            session_id=self.session_id,
            stage=ProgressStage.COMPLETED,
            current_step=self.total_steps,
            total_steps=self.total_steps,
            message=message,
            details={
                'total_duration_seconds': total_duration,
                'completed_at': datetime.now().isoformat()
            }
        )
        
        self._notify_progress(update)
        logger.info(f"Analysis completed in {total_duration:.2f}s")
    
    def _notify_progress(self, update: ProgressUpdate):
        """
        Notify all callbacks and persist progress.
        
        Args:
            update: Progress update to notify
        """
        # Add to history
        self.progress_history.append(update)
        
        # Persist to database
        self._persist_progress(update)
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def _persist_progress(self, update: ProgressUpdate):
        """
        Persist progress update to database.
        
        Args:
            update: Progress update to persist
        """
        try:
            query = """
                INSERT INTO progress_tracking 
                (session_id, stage, current_step, total_steps, percentage, message, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                update.session_id,
                update.stage.value,
                update.current_step,
                update.total_steps,
                update.percentage,
                update.message,
                safe_json_dumps(update.details),
                update.timestamp.isoformat()
            )
            
            self.database.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Failed to persist progress: {e}")
    
    def get_current_progress(self) -> Optional[ProgressUpdate]:
        """
        Get current progress state.
        
        Returns:
            Current ProgressUpdate or None
        """
        if self.progress_history:
            return self.progress_history[-1]
        return None
    
    def get_progress_history(self) -> List[ProgressUpdate]:
        """
        Get complete progress history.
        
        Returns:
            List of ProgressUpdate objects
        """
        return self.progress_history.copy()
    
    def get_stage_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stage performance.
        
        Returns:
            Dictionary with stage statistics
        """
        stats = {
            'total_duration': time.time() - self.start_time,
            'stages': {},
            'current_stage': self.current_stage.value,
            'overall_progress': 0.0
        }
        
        # Calculate stage durations
        for stage, start_time in self.stage_start_times.items():
            if stage == self.current_stage:
                duration = time.time() - start_time
            else:
                # Find when this stage ended
                stage_end = None
                for update in self.progress_history:
                    if update.stage == stage and update.current_step == update.total_steps:
                        stage_end = update.timestamp.timestamp()
                        break
                
                duration = stage_end - start_time if stage_end else 0
            
            stats['stages'][stage.value] = {
                'duration_seconds': duration,
                'start_time': datetime.fromtimestamp(start_time).isoformat()
            }
        
        # Calculate overall progress
        if self.progress_history:
            latest = self.progress_history[-1]
            if latest.stage == ProgressStage.COMPLETED:
                stats['overall_progress'] = 100.0
            else:
                # Estimate based on stage progression
                stage_weights = {
                    ProgressStage.INITIALIZING: 5,
                    ProgressStage.RETRIEVING_DOCUMENTS: 15,
                    ProgressStage.ANALYZING_DOCUMENTS: 70,
                    ProgressStage.PERFORMING_META_ANALYSIS: 8,
                    ProgressStage.EXPORTING_RESULTS: 2
                }
                
                completed_weight = 0
                current_weight = stage_weights.get(latest.stage, 0)
                
                for stage in ProgressStage:
                    if stage.value in stats['stages'] and stage != latest.stage:
                        completed_weight += stage_weights.get(stage, 0)
                
                stage_progress = (latest.percentage / 100.0) * current_weight
                stats['overall_progress'] = completed_weight + stage_progress
        
        return stats
    
    @classmethod
    def load_progress_from_database(cls, database: Database, session_id: str) -> Optional['ProgressTracker']:
        """
        Load progress tracker from database.
        
        Args:
            database: Database instance
            session_id: Session identifier
            
        Returns:
            ProgressTracker instance or None if not found
        """
        try:
            query = """
                SELECT * FROM progress_tracking 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """
            
            results = database.execute_query(query, (session_id,))
            
            if not results:
                return None
            
            # Create tracker
            tracker = cls(database, session_id)
            
            # Restore progress history
            for row in results:
                row_dict = dict(row)
                
                update = ProgressUpdate(
                    session_id=row_dict['session_id'],
                    stage=ProgressStage(row_dict['stage']),
                    current_step=row_dict['current_step'],
                    total_steps=row_dict['total_steps'],
                    message=row_dict['message'] or "",
                    timestamp=datetime.fromisoformat(row_dict['timestamp']),
                    details=safe_json_loads(row_dict.get('details', '{}'), {})
                )
                
                tracker.progress_history.append(update)
            
            # Set current state from last update
            if tracker.progress_history:
                last_update = tracker.progress_history[-1]
                tracker.current_stage = last_update.stage
                tracker.current_step = last_update.current_step
                tracker.total_steps = last_update.total_steps
            
            logger.info(f"Loaded progress tracker for session {session_id} with {len(tracker.progress_history)} updates")
            return tracker
            
        except Exception as e:
            logger.error(f"Failed to load progress tracker for session {session_id}: {e}")
            return None
    
    def cleanup_old_progress(self, days_old: int = 7) -> int:
        """
        Clean up old progress tracking data.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of records cleaned up
        """
        try:
            # Count records to be deleted
            count_query = """
                SELECT COUNT(*) FROM progress_tracking 
                WHERE datetime(timestamp) < datetime('now', '-{} days')
            """.format(days_old)
            
            count_results = self.database.execute_query(count_query)
            count = count_results[0][0] if count_results else 0
            
            if count > 0:
                # Delete old records
                delete_query = """
                    DELETE FROM progress_tracking 
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                """.format(days_old)
                
                self.database.execute_query(delete_query)
                logger.info(f"Cleaned up {count} old progress records")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old progress data: {e}")
            return 0


class ConsoleProgressCallback:
    """Console-based progress callback for CLI usage."""
    
    def __init__(self, show_details: bool = False):
        """
        Initialize console progress callback.
        
        Args:
            show_details: Whether to show detailed progress information
        """
        self.show_details = show_details
        self.last_percentage = -1
    
    def __call__(self, update: ProgressUpdate):
        """
        Handle progress update.
        
        Args:
            update: Progress update to display
        """
        # Only show progress at 5% intervals to reduce noise
        percentage = int(update.percentage)
        if percentage != self.last_percentage and percentage % 5 == 0:
            stage_name = update.stage.value.replace('_', ' ').title()
            print(f"[{percentage:3d}%] {stage_name}: {update.message}")
            self.last_percentage = percentage
        
        # Show details if requested
        if self.show_details and update.details:
            for key, value in update.details.items():
                print(f"  {key}: {value}")
        
        # Always show completion and errors
        if update.stage in [ProgressStage.COMPLETED, ProgressStage.FAILED]:
            stage_name = update.stage.value.replace('_', ' ').title()
            print(f"[{update.percentage:3.0f}%] {stage_name}: {update.message}")


class WebProgressCallback:
    """Web-based progress callback for Streamlit or web interfaces."""
    
    def __init__(self, progress_container=None):
        """
        Initialize web progress callback.
        
        Args:
            progress_container: Web framework progress container (e.g., Streamlit)
        """
        self.progress_container = progress_container
        self.updates = []
    
    def __call__(self, update: ProgressUpdate):
        """
        Handle progress update.
        
        Args:
            update: Progress update to store
        """
        self.updates.append(update)
        
        # Update web container if available
        if self.progress_container:
            try:
                # This would be framework-specific implementation
                # For Streamlit: self.progress_container.progress(update.percentage / 100.0)
                pass
            except Exception as e:
                logger.error(f"Web progress callback failed: {e}")
    
    def get_latest_updates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get latest progress updates for web display.
        
        Args:
            limit: Maximum number of updates to return
            
        Returns:
            List of progress update dictionaries
        """
        return [update.to_dict() for update in self.updates[-limit:]]