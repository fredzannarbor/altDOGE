"""
Integration tests for full analysis workflow.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from cfr_document_analyzer.database import Database
from cfr_document_analyzer.analysis_engine import AnalysisEngine
from cfr_document_analyzer.session_manager import SessionManager
from cfr_document_analyzer.statistics_engine import StatisticsEngine
from cfr_document_analyzer.export_manager import ExportManager
from cfr_document_analyzer.models import Document, SessionStatus


class TestFullWorkflowIntegration:
    """Integration tests for complete analysis workflow."""
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_database(self, temp_dir):
        """Test database instance."""
        db_path = temp_dir / "test.db"
        return Database(str(db_path))
    
    @pytest.fixture
    def sample_documents(self):
        """Sample documents for testing."""
        return [
            Document(
                document_number="2024-12345",
                title="Test Regulation on Data Collection",
                agency_slug="test-agency",
                publication_date="2024-01-15",
                content="This regulation establishes requirements for data collection and reporting by federal agencies. The regulation is required under 42 U.S.C. 1234 to ensure proper oversight of agency activities.",
                content_length=200
            ),
            Document(
                document_number="2024-12346",
                title="Administrative Procedures Update",
                agency_slug="test-agency",
                publication_date="2024-01-20",
                content="This document updates administrative procedures for processing applications. While not explicitly required by statute, these procedures are necessary for efficient agency operations.",
                content_length=180
            )
        ]
    
    @pytest.mark.integration
    def test_complete_analysis_workflow(self, test_database, temp_dir, sample_documents):
        """Test complete analysis workflow from start to finish."""
        # Initialize components
        session_manager = SessionManager(test_database)
        export_manager = ExportManager(str(temp_dir))
        
        # Mock LLM responses for consistent testing
        with patch('cfr_document_analyzer.llm_client.LLMClient') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            
            # Mock DOGE analysis responses
            mock_llm.analyze_document_with_doge_prompts.side_effect = [
                Mock(
                    category=Mock(value='SR'),
                    statutory_references=['42 U.S.C. 1234'],
                    reform_recommendations=['Simplify reporting requirements'],
                    justification='This regulation is statutorily required under 42 U.S.C. 1234.'
                ),
                Mock(
                    category=Mock(value='NRAN'),
                    statutory_references=[],
                    reform_recommendations=['Modernize application process'],
                    justification='This procedure is needed for agency operations but not statutorily required.'
                )
            ]
            
            # Mock meta-analysis response
            mock_llm.perform_meta_analysis.return_value = Mock(
                success=True,
                key_patterns=['Pattern 1: Regulatory burden', 'Pattern 2: Modernization needs'],
                priority_actions=['Action 1: Review requirements', 'Action 2: Streamline processes'],
                executive_summary='Analysis shows opportunities for regulatory reform.',
                processing_time=30.0
            )
            
            # Mock document retrieval
            with patch('cfr_document_analyzer.document_retriever.DocumentRetriever') as mock_retriever_class:
                mock_retriever = Mock()
                mock_retriever_class.return_value = mock_retriever
                mock_retriever.get_agency_documents.return_value = sample_documents
                
                # Initialize analysis engine
                analysis_engine = AnalysisEngine(test_database)
                
                # Step 1: Create analysis session
                session = session_manager.create_session(
                    agency_slugs=['test-agency'],
                    prompt_strategy='DOGE Criteria',
                    document_limit=10
                )
                
                assert session.session_id is not None
                assert session.status == SessionStatus.CREATED
                
                # Step 2: Store sample documents in database
                for doc in sample_documents:
                    doc_data = {
                        'document_number': doc.document_number,
                        'title': doc.title,
                        'agency_slug': doc.agency_slug,
                        'publication_date': doc.publication_date,
                        'content': doc.content,
                        'content_length': doc.content_length
                    }
                    doc.id = test_database.store_document(doc_data)
                
                # Step 3: Run analysis
                completed_session = analysis_engine.analyze_agency_documents(
                    agency_slug='test-agency',
                    prompt_strategy='DOGE Criteria',
                    document_limit=10
                )
                
                assert completed_session.status == SessionStatus.COMPLETED
                assert completed_session.documents_processed > 0
                
                # Step 4: Get analysis results
                results = analysis_engine.get_analysis_results(completed_session.session_id)
                
                assert len(results) == 2
                assert all(result['analysis']['success'] for result in results)
                
                # Step 5: Perform meta-analysis
                meta_analysis = analysis_engine.perform_meta_analysis(completed_session.session_id)
                
                assert meta_analysis is not None
                assert meta_analysis.success is True
                assert len(meta_analysis.key_patterns) > 0
                
                # Step 6: Generate statistics
                stats_engine = StatisticsEngine(test_database)
                overall_stats = stats_engine.get_overall_statistics()
                
                assert overall_stats.total_documents >= 2
                assert overall_stats.success_rate > 0
                
                # Step 7: Export results
                exported_files = export_manager.export_session_results(
                    results, completed_session.session_id, ['json', 'csv', 'html']
                )
                
                assert 'json' in exported_files
                assert 'csv' in exported_files
                assert 'html' in exported_files
                
                # Verify exported files exist
                for file_path in exported_files.values():
                    assert Path(file_path).exists()
                
                # Step 8: Create agency presentation
                presentation_path = export_manager.create_agency_presentation_summary(
                    results, completed_session.session_id
                )
                
                assert presentation_path
                assert Path(presentation_path).exists()
    
    @pytest.mark.integration
    def test_session_lifecycle_management(self, test_database):
        """Test complete session lifecycle management."""
        session_manager = SessionManager(test_database)
        
        # Create session
        session = session_manager.create_session(
            agency_slugs=['test-agency-1', 'test-agency-2'],
            prompt_strategy='DOGE Criteria',
            document_limit=5
        )
        
        original_session_id = session.session_id
        
        # Update session status
        success = session_manager.update_session_status(
            original_session_id,
            SessionStatus.RUNNING,
            documents_processed=3,
            total_documents=5
        )
        assert success is True
        
        # Retrieve updated session
        updated_session = session_manager.get_session(original_session_id)
        assert updated_session.status == SessionStatus.RUNNING
        assert updated_session.documents_processed == 3
        assert updated_session.total_documents == 5
        
        # Complete session
        success = session_manager.update_session_status(
            original_session_id,
            SessionStatus.COMPLETED,
            documents_processed=5
        )
        assert success is True
        
        # List sessions
        sessions = session_manager.list_sessions(limit=10)
        assert len(sessions) >= 1
        assert any(s.session_id == original_session_id for s in sessions)
        
        # Archive session
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "test_archive.json"
            success = session_manager.archive_session(original_session_id, str(archive_path))
            assert success is True
            assert archive_path.exists()
    
    @pytest.mark.integration
    def test_error_recovery_and_resilience(self, test_database, sample_documents):
        """Test error recovery and system resilience."""
        # Test database recovery
        session_manager = SessionManager(test_database)
        
        # Create session
        session = session_manager.create_session(
            agency_slugs=['test-agency'],
            prompt_strategy='DOGE Criteria'
        )
        
        # Simulate interruption by marking as failed
        session_manager.update_session_status(session.session_id, SessionStatus.FAILED)
        
        # Resume session
        resumed_session = session_manager.resume_session(session.session_id)
        assert resumed_session is not None
        assert resumed_session.session_id == session.session_id
        
        # Test graceful handling of missing data
        non_existent_session = session_manager.get_session('non_existent_session_123')
        assert non_existent_session is None
        
        # Test statistics with empty database
        stats_engine = StatisticsEngine(test_database)
        empty_stats = stats_engine.get_overall_statistics()
        assert empty_stats.total_documents == 0
        assert empty_stats.success_rate == 0.0
    
    @pytest.mark.integration
    def test_export_format_compatibility(self, test_database, temp_dir):
        """Test compatibility of different export formats."""
        export_manager = ExportManager(str(temp_dir))
        
        # Sample analysis results
        sample_results = [
            {
                'document_number': '2024-12345',
                'title': 'Test Document',
                'agency_slug': 'test-agency',
                'publication_date': '2024-01-15',
                'content_length': 200,
                'analysis': {
                    'category': 'SR',
                    'statutory_references': ['42 U.S.C. 1234'],
                    'reform_recommendations': ['Simplify requirements'],
                    'justification': 'Test justification',
                    'success': True,
                    'processing_time': 15.5
                }
            }
        ]
        
        # Test all export formats
        exported_files = export_manager.export_session_results(
            sample_results, 'test_session_123', ['json', 'csv', 'html']
        )
        
        # Verify all formats were exported
        assert len(exported_files) == 3
        
        # Verify file contents
        json_path = Path(exported_files['json'])
        assert json_path.exists()
        
        csv_path = Path(exported_files['csv'])
        assert csv_path.exists()
        
        html_path = Path(exported_files['html'])
        assert html_path.exists()
        
        # Verify JSON structure
        import json as json_module
        with open(json_path, 'r') as f:
            json_data = json_module.load(f)
        
        assert 'metadata' in json_data
        assert 'results' in json_data
        assert len(json_data['results']) == 1
        
        # Verify CSV structure
        import csv
        with open(csv_path, 'r') as f:
            csv_reader = csv.reader(f)
            headers = next(csv_reader)
            data_row = next(csv_reader)
        
        assert 'Document Number' in headers
        assert '2024-12345' in data_row
        
        # Verify HTML structure
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        assert '<!DOCTYPE html>' in html_content
        assert 'Test Document' in html_content
    
    @pytest.mark.integration
    def test_performance_under_load(self, test_database):
        """Test system performance under load."""
        import time
        
        session_manager = SessionManager(test_database)
        
        # Create multiple sessions rapidly
        start_time = time.time()
        session_ids = []
        
        for i in range(10):
            session = session_manager.create_session(
                agency_slugs=[f'test-agency-{i}'],
                prompt_strategy='DOGE Criteria',
                document_limit=5
            )
            session_ids.append(session.session_id)
        
        creation_time = time.time() - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert creation_time < 5.0  # 5 seconds for 10 sessions
        
        # Verify all sessions were created
        assert len(session_ids) == 10
        assert len(set(session_ids)) == 10  # All unique
        
        # Test concurrent session updates
        start_time = time.time()
        
        for session_id in session_ids:
            session_manager.update_session_status(
                session_id, SessionStatus.COMPLETED, documents_processed=5, total_documents=5
            )
        
        update_time = time.time() - start_time
        assert update_time < 3.0  # 3 seconds for 10 updates
        
        # Verify all sessions were updated
        sessions = session_manager.list_sessions(limit=20)
        completed_sessions = [s for s in sessions if s.status == SessionStatus.COMPLETED]
        assert len(completed_sessions) >= 10
    
    @pytest.mark.integration
    def test_data_consistency_and_integrity(self, test_database, sample_documents):
        """Test data consistency and integrity across operations."""
        session_manager = SessionManager(test_database)
        stats_engine = StatisticsEngine(test_database)
        
        # Store documents
        document_ids = []
        for doc in sample_documents:
            doc_data = {
                'document_number': doc.document_number,
                'title': doc.title,
                'agency_slug': doc.agency_slug,
                'publication_date': doc.publication_date,
                'content': doc.content
            }
            doc_id = test_database.store_document(doc_data)
            document_ids.append(doc_id)
        
        # Create analysis results
        for doc_id in document_ids:
            analysis_data = {
                'document_id': doc_id,
                'prompt_strategy': 'DOGE Criteria',
                'category': 'SR',
                'statutory_references': '["42 U.S.C. 1234"]',
                'reform_recommendations': '["Simplify requirements"]',
                'justification': 'Test justification',
                'success': True,
                'processing_time': 15.0
            }
            test_database.store_analysis(analysis_data)
        
        # Verify data consistency
        overall_stats = stats_engine.get_overall_statistics()
        
        assert overall_stats.total_documents >= len(sample_documents)
        assert overall_stats.success_rate > 0
        
        # Verify referential integrity
        for doc_id in document_ids:
            analyses = test_database.get_analyses_by_document(doc_id)
            assert len(analyses) >= 1
            
            for analysis in analyses:
                assert analysis['document_id'] == doc_id
                assert analysis['success'] == 1  # SQLite boolean as integer