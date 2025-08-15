"""
Session management for CFR Document Analyzer.

Handles analysis session lifecycle, state persistence, and resumption capabilities.
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from .database import Database
from .models import AnalysisSession, SessionStatus
from .utils import safe_json_dumps, safe_json_loads, format_timestamp


logger = logging.getLogger(__name__)


class SessionManager:
    """Manages analysis session lifecycle and persistence."""
    
    def __init__(self, database: Database):
        """
        Initialize session manager.
        
        Args:
            database: Database instance
        """
        self.database = database
        logger.info("Session manager initialized")
    
    def create_session(self, agency_slugs: List[str], prompt_strategy: str, 
                      document_limit: Optional[int] = None, 
                      session_config: Optional[Dict[str, Any]] = None) -> AnalysisSession:
        """
        Create a new analysis session.
        
        Args:
            agency_slugs: List of agency identifiers
            prompt_strategy: Analysis strategy name
            document_limit: Maximum documents to analyze
            session_config: Additional session configuration
            
        Returns:
            AnalysisSession object
        """
        try:
            # Generate session ID
            timestamp = format_timestamp()
            session_id = f"session_{timestamp}_{uuid.uuid4().hex[:8]}"
            
            # Create session data
            session_data = {
                'session_id': session_id,
                'agency_slugs': safe_json_dumps(agency_slugs),
                'prompt_strategy': prompt_strategy,
                'document_limit': document_limit,
                'status': SessionStatus.CREATED.value,
                'documents_processed': 0,
                'total_documents': 0,
                'config': safe_json_dumps(session_config or {}),
                'created_at': datetime.now().isoformat()
            }
            
            # Store in database
            query = """
                INSERT INTO sessions 
                (session_id, agency_slugs, prompt_strategy, document_limit, status, 
                 documents_processed, total_documents, config, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                session_data['session_id'],
                session_data['agency_slugs'],
                session_data['prompt_strategy'],
                session_data['document_limit'],
                session_data['status'],
                session_data['documents_processed'],
                session_data['total_documents'],
                session_data['config'],
                session_data['created_at']
            )
            
            self.database.execute_query(query, params)
            
            # Create AnalysisSession object
            session = AnalysisSession(
                session_id=session_id,
                agency_slugs=agency_slugs,
                prompt_strategy=prompt_strategy,
                document_limit=document_limit,
                status=SessionStatus.CREATED,
                documents_processed=0,
                total_documents=0,
                created_at=datetime.now()
            )
            
            logger.info(f"Created session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            AnalysisSession object or None if not found
        """
        try:
            query = "SELECT * FROM sessions WHERE session_id = ?"
            results = self.database.execute_query(query, (session_id,))
            
            if not results:
                return None
            
            session_data = dict(results[0])
            
            # Parse session data
            agency_slugs = safe_json_loads(session_data.get('agency_slugs', '[]'), [])
            status = SessionStatus(session_data.get('status', 'created'))
            
            session = AnalysisSession(
                session_id=session_data['session_id'],
                agency_slugs=agency_slugs,
                prompt_strategy=session_data['prompt_strategy'],
                document_limit=session_data.get('document_limit'),
                status=status,
                documents_processed=session_data.get('documents_processed', 0),
                total_documents=session_data.get('total_documents', 0),
                created_at=datetime.fromisoformat(session_data['created_at']) if session_data.get('created_at') else None,
                completed_at=datetime.fromisoformat(session_data['completed_at']) if session_data.get('completed_at') else None
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def update_session_status(self, session_id: str, status: SessionStatus, 
                             documents_processed: Optional[int] = None,
                             total_documents: Optional[int] = None) -> bool:
        """
        Update session status and progress.
        
        Args:
            session_id: Session identifier
            status: New session status
            documents_processed: Number of documents processed
            total_documents: Total number of documents
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build update query dynamically
            updates = ["status = ?"]
            params = [status.value]
            
            if documents_processed is not None:
                updates.append("documents_processed = ?")
                params.append(documents_processed)
            
            if total_documents is not None:
                updates.append("total_documents = ?")
                params.append(total_documents)
            
            if status == SessionStatus.COMPLETED:
                updates.append("completed_at = CURRENT_TIMESTAMP")
            
            query = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?"
            params.append(session_id)
            
            self.database.execute_query(query, tuple(params))
            
            logger.debug(f"Updated session {session_id} status to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    def list_sessions(self, limit: Optional[int] = None, 
                     status_filter: Optional[SessionStatus] = None) -> List[AnalysisSession]:
        """
        List analysis sessions.
        
        Args:
            limit: Maximum number of sessions to return
            status_filter: Filter by session status
            
        Returns:
            List of AnalysisSession objects
        """
        try:
            query = "SELECT * FROM sessions"
            params = []
            
            if status_filter:
                query += " WHERE status = ?"
                params.append(status_filter.value)
            
            query += " ORDER BY created_at DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            results = self.database.execute_query(query, tuple(params))
            
            sessions = []
            for row in results:
                session_data = dict(row)
                agency_slugs = safe_json_loads(session_data.get('agency_slugs', '[]'), [])
                status = SessionStatus(session_data.get('status', 'created'))
                
                session = AnalysisSession(
                    session_id=session_data['session_id'],
                    agency_slugs=agency_slugs,
                    prompt_strategy=session_data['prompt_strategy'],
                    document_limit=session_data.get('document_limit'),
                    status=status,
                    documents_processed=session_data.get('documents_processed', 0),
                    total_documents=session_data.get('total_documents', 0),
                    created_at=datetime.fromisoformat(session_data['created_at']) if session_data.get('created_at') else None,
                    completed_at=datetime.fromisoformat(session_data['completed_at']) if session_data.get('completed_at') else None
                )
                
                sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    def resume_session(self, session_id: str) -> Optional[AnalysisSession]:
        """
        Resume an interrupted session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            AnalysisSession object or None if cannot resume
        """
        try:
            session = self.get_session(session_id)
            
            if not session:
                logger.error(f"Session not found: {session_id}")
                return None
            
            if session.status == SessionStatus.COMPLETED:
                logger.warning(f"Session {session_id} is already completed")
                return session
            
            if session.status == SessionStatus.FAILED:
                logger.info(f"Resuming failed session: {session_id}")
                # Reset status to running for resumption
                self.update_session_status(session_id, SessionStatus.RUNNING)
                session.status = SessionStatus.RUNNING
            
            logger.info(f"Resumed session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to resume session {session_id}: {e}")
            return None
    
    def cancel_session(self, session_id: str) -> bool:
        """
        Cancel a running session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session(session_id)
            
            if not session:
                logger.error(f"Session not found: {session_id}")
                return False
            
            if session.status in [SessionStatus.COMPLETED, SessionStatus.CANCELLED]:
                logger.warning(f"Session {session_id} is already {session.status.value}")
                return True
            
            # Update status to cancelled
            success = self.update_session_status(session_id, SessionStatus.CANCELLED)
            
            if success:
                logger.info(f"Cancelled session: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cancel session {session_id}: {e}")
            return False
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """
        Clean up old completed sessions.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            query = """
                DELETE FROM sessions 
                WHERE status IN ('completed', 'cancelled', 'failed') 
                AND datetime(created_at) < datetime('now', '-{} days')
            """.format(days_old)
            
            # Get count before deletion
            count_query = """
                SELECT COUNT(*) FROM sessions 
                WHERE status IN ('completed', 'cancelled', 'failed') 
                AND datetime(created_at) < datetime('now', '-{} days')
            """.format(days_old)
            
            count_results = self.database.execute_query(count_query)
            count = count_results[0][0] if count_results else 0
            
            if count > 0:
                self.database.execute_query(query)
                logger.info(f"Cleaned up {count} old sessions")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Dictionary with session statistics
        """
        try:
            stats = {}
            
            # Total sessions
            total_query = "SELECT COUNT(*) FROM sessions"
            total_results = self.database.execute_query(total_query)
            stats['total_sessions'] = total_results[0][0] if total_results else 0
            
            # Sessions by status
            status_query = "SELECT status, COUNT(*) FROM sessions GROUP BY status"
            status_results = self.database.execute_query(status_query)
            stats['by_status'] = {row[0]: row[1] for row in status_results}
            
            # Recent sessions (last 7 days)
            recent_query = """
                SELECT COUNT(*) FROM sessions 
                WHERE datetime(created_at) > datetime('now', '-7 days')
            """
            recent_results = self.database.execute_query(recent_query)
            stats['recent_sessions'] = recent_results[0][0] if recent_results else 0
            
            # Average processing time for completed sessions
            avg_query = """
                SELECT AVG(
                    (julianday(completed_at) - julianday(created_at)) * 24 * 60
                ) as avg_minutes
                FROM sessions 
                WHERE status = 'completed' AND completed_at IS NOT NULL
            """
            avg_results = self.database.execute_query(avg_query)
            avg_minutes = avg_results[0][0] if avg_results and avg_results[0][0] else 0
            stats['avg_processing_minutes'] = round(avg_minutes, 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return {}
    
    def archive_session(self, session_id: str, archive_path: Optional[str] = None) -> bool:
        """
        Archive a session to file system.
        
        Args:
            session_id: Session identifier
            archive_path: Custom archive path (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session(session_id)
            
            if not session:
                logger.error(f"Session not found: {session_id}")
                return False
            
            # Get session analyses
            analyses_query = """
                SELECT a.*, d.document_number, d.title, d.agency_slug
                FROM analyses a
                JOIN documents d ON a.document_id = d.id
                WHERE d.agency_slug IN ({})
                AND a.prompt_strategy = ?
            """.format(','.join(['?' for _ in session.agency_slugs]))
            
            params = session.agency_slugs + [session.prompt_strategy]
            analyses_results = self.database.execute_query(analyses_query, tuple(params))
            
            # Prepare archive data
            archive_data = {
                'session': {
                    'session_id': session.session_id,
                    'agency_slugs': session.agency_slugs,
                    'prompt_strategy': session.prompt_strategy,
                    'document_limit': session.document_limit,
                    'status': session.status.value,
                    'documents_processed': session.documents_processed,
                    'total_documents': session.total_documents,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'completed_at': session.completed_at.isoformat() if session.completed_at else None
                },
                'analyses': [dict(row) for row in analyses_results],
                'archived_at': datetime.now().isoformat()
            }
            
            # Determine archive path
            if not archive_path:
                archive_dir = Path("archives")
                archive_dir.mkdir(exist_ok=True)
                archive_path = archive_dir / f"{session_id}_archive.json"
            else:
                archive_path = Path(archive_path)
                archive_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write archive file
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Archived session {session_id} to {archive_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive session {session_id}: {e}")
            return False