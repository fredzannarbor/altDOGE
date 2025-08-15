"""
Tests for session management functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from cfr_document_analyzer.session_manager import SessionManager
from cfr_document_analyzer.models import AnalysisSession, SessionStatus
from cfr_document_analyzer.database import Database


class TestSessionManager:
    """Test session management functionality."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock database for testing."""
        db = Mock(spec=Database)
        db.execute_query.return_value = []
        return db
    
    @pytest.fixture
    def session_manager(self, mock_database):
        """Session manager instance for testing."""
        return SessionManager(mock_database)
    
    def test_create_session(self, session_manager, mock_database):
        """Test session creation."""
        # Test session creation
        session = session_manager.create_session(
            agency_slugs=['test-agency'],
            prompt_strategy='DOGE Criteria',
            document_limit=10
        )
        
        # Verify session properties
        assert session.agency_slugs == ['test-agency']
        assert session.prompt_strategy == 'DOGE Criteria'
        assert session.document_limit == 10
        assert session.status == SessionStatus.CREATED
        assert session.session_id.startswith('session_')
        
        # Verify database was called
        mock_database.execute_query.assert_called()
    
    def test_get_session(self, session_manager, mock_database):
        """Test session retrieval."""
        # Mock database response
        mock_database.execute_query.return_value = [
            {
                'session_id': 'test_session_123',
                'agency_slugs': '["test-agency"]',
                'prompt_strategy': 'DOGE Criteria',
                'document_limit': 10,
                'status': 'created',
                'documents_processed': 0,
                'total_documents': 0,
                'created_at': '2024-01-01T12:00:00'
            }
        ]
        
        # Test session retrieval
        session = session_manager.get_session('test_session_123')
        
        # Verify session properties
        assert session is not None
        assert session.session_id == 'test_session_123'
        assert session.agency_slugs == ['test-agency']
        assert session.status == SessionStatus.CREATED
    
    def test_get_nonexistent_session(self, session_manager, mock_database):
        """Test retrieval of non-existent session."""
        # Mock empty database response
        mock_database.execute_query.return_value = []
        
        # Test session retrieval
        session = session_manager.get_session('nonexistent_session')
        
        # Should return None
        assert session is None
    
    def test_update_session_status(self, session_manager, mock_database):
        """Test session status update."""
        # Test status update
        success = session_manager.update_session_status(
            'test_session_123',
            SessionStatus.RUNNING,
            documents_processed=5,
            total_documents=10
        )
        
        # Verify success
        assert success is True
        
        # Verify database was called
        mock_database.execute_query.assert_called()
    
    def test_list_sessions(self, session_manager, mock_database):
        """Test session listing."""
        # Mock database response
        mock_database.execute_query.return_value = [
            {
                'session_id': 'session_1',
                'agency_slugs': '["agency-1"]',
                'prompt_strategy': 'DOGE Criteria',
                'document_limit': 10,
                'status': 'completed',
                'documents_processed': 10,
                'total_documents': 10,
                'created_at': '2024-01-01T12:00:00'
            },
            {
                'session_id': 'session_2',
                'agency_slugs': '["agency-2"]',
                'prompt_strategy': 'DOGE Criteria',
                'document_limit': 5,
                'status': 'running',
                'documents_processed': 3,
                'total_documents': 5,
                'created_at': '2024-01-02T12:00:00'
            }
        ]
        
        # Test session listing
        sessions = session_manager.list_sessions(limit=10)
        
        # Verify results
        assert len(sessions) == 2
        assert sessions[0].session_id == 'session_1'
        assert sessions[1].session_id == 'session_2'
    
    def test_resume_session(self, session_manager, mock_database):
        """Test session resumption."""
        # Mock database response for get_session
        mock_database.execute_query.return_value = [
            {
                'session_id': 'test_session_123',
                'agency_slugs': '["test-agency"]',
                'prompt_strategy': 'DOGE Criteria',
                'document_limit': 10,
                'status': 'failed',
                'documents_processed': 5,
                'total_documents': 10,
                'created_at': '2024-01-01T12:00:00'
            }
        ]
        
        # Test session resumption
        session = session_manager.resume_session('test_session_123')
        
        # Verify session was resumed
        assert session is not None
        assert session.session_id == 'test_session_123'
    
    def test_cancel_session(self, session_manager, mock_database):
        """Test session cancellation."""
        # Mock database response for get_session
        mock_database.execute_query.return_value = [
            {
                'session_id': 'test_session_123',
                'agency_slugs': '["test-agency"]',
                'prompt_strategy': 'DOGE Criteria',
                'document_limit': 10,
                'status': 'running',
                'documents_processed': 5,
                'total_documents': 10,
                'created_at': '2024-01-01T12:00:00'
            }
        ]
        
        # Test session cancellation
        success = session_manager.cancel_session('test_session_123')
        
        # Verify success
        assert success is True
    
    def test_cleanup_old_sessions(self, session_manager, mock_database):
        """Test cleanup of old sessions."""
        # Mock database responses
        mock_database.execute_query.side_effect = [
            [(5,)],  # Count query result
            []       # Delete query result
        ]
        
        # Test cleanup
        cleaned_count = session_manager.cleanup_old_sessions(days_old=30)
        
        # Verify cleanup count
        assert cleaned_count == 5
    
    def test_get_session_statistics(self, session_manager, mock_database):
        """Test session statistics retrieval."""
        # Mock database responses
        mock_database.execute_query.side_effect = [
            [(10,)],  # Total sessions
            [('completed', 7), ('running', 2), ('failed', 1)],  # By status
            [(3,)],   # Recent sessions
            [(15.5,)] # Average processing time
        ]
        
        # Test statistics retrieval
        stats = session_manager.get_session_statistics()
        
        # Verify statistics
        assert stats['total_sessions'] == 10
        assert stats['by_status']['completed'] == 7
        assert stats['recent_sessions'] == 3
        assert stats['avg_processing_minutes'] == 15.5
    
    def test_archive_session(self, session_manager, mock_database):
        """Test session archival."""
        # Mock database responses
        mock_database.execute_query.side_effect = [
            # get_session response
            [{
                'session_id': 'test_session_123',
                'agency_slugs': '["test-agency"]',
                'prompt_strategy': 'DOGE Criteria',
                'document_limit': 10,
                'status': 'completed',
                'documents_processed': 10,
                'total_documents': 10,
                'created_at': '2024-01-01T12:00:00'
            }],
            # analyses query response
            []
        ]
        
        # Test session archival
        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_json_dump:
                success = session_manager.archive_session('test_session_123')
        
        # Verify success
        assert success is True
    
    def test_session_validation(self):
        """Test session data validation."""
        # Test valid session
        session = AnalysisSession(
            session_id='test_123',
            agency_slugs=['test-agency'],
            prompt_strategy='DOGE Criteria'
        )
        
        # Should not raise exception
        assert session.session_id == 'test_123'
        
        # Test invalid session (empty agency slugs)
        with pytest.raises(ValueError):
            AnalysisSession(
                session_id='test_123',
                agency_slugs=[],
                prompt_strategy='DOGE Criteria'
            )
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        session = AnalysisSession(
            session_id='test_123',
            agency_slugs=['test-agency'],
            prompt_strategy='DOGE Criteria',
            documents_processed=7,
            total_documents=10
        )
        
        assert session.progress_percentage == 70.0
        
        # Test edge case: no total documents
        session.total_documents = 0
        assert session.progress_percentage == 0.0