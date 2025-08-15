"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from cfr_document_analyzer.database import Database
from cfr_document_analyzer.models import Document


@pytest.fixture(scope="session")
def temp_test_dir():
    """Session-scoped temporary directory for test files."""
    temp_dir = tempfile.mkdtemp(prefix="cfr_analyzer_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_database(temp_test_dir):
    """Test database instance with temporary file."""
    db_path = temp_test_dir / "test.db"
    return Database(str(db_path))


@pytest.fixture
def sample_document():
    """Single sample document for testing."""
    return Document(
        document_number="2024-12345",
        title="Test Regulation Document",
        agency_slug="test-agency",
        publication_date="2024-01-15",
        content="This is a test regulation document content for analysis.",
        content_length=55,
        id=1
    )


@pytest.fixture
def sample_documents():
    """Multiple sample documents for testing."""
    return [
        Document(
            document_number="2024-12345",
            title="Test Regulation on Data Collection",
            agency_slug="test-agency",
            publication_date="2024-01-15",
            content="This regulation establishes requirements for data collection.",
            content_length=60,
            id=1
        ),
        Document(
            document_number="2024-12346",
            title="Administrative Procedures Update",
            agency_slug="test-agency",
            publication_date="2024-01-20",
            content="This document updates administrative procedures.",
            content_length=45,
            id=2
        ),
        Document(
            document_number="2024-12347",
            title="Reporting Requirements Modification",
            agency_slug="another-agency",
            publication_date="2024-01-25",
            content="This modifies existing reporting requirements.",
            content_length=42,
            id=3
        )
    ]


@pytest.fixture
def sample_analysis_results():
    """Sample analysis results for testing."""
    return [
        {
            'document_number': '2024-12345',
            'title': 'Test Regulation on Data Collection',
            'agency_slug': 'test-agency',
            'publication_date': '2024-01-15',
            'content_length': 60,
            'analysis': {
                'category': 'SR',
                'statutory_references': ['42 U.S.C. 1234', '15 U.S.C. 5678'],
                'reform_recommendations': ['Simplify reporting requirements', 'Modernize data collection'],
                'justification': 'This regulation is statutorily required under 42 U.S.C. 1234.',
                'success': True,
                'processing_time': 15.5,
                'created_at': '2024-01-15T12:00:00'
            }
        },
        {
            'document_number': '2024-12346',
            'title': 'Administrative Procedures Update',
            'agency_slug': 'test-agency',
            'publication_date': '2024-01-20',
            'content_length': 45,
            'analysis': {
                'category': 'NRAN',
                'statutory_references': [],
                'reform_recommendations': ['Streamline approval process'],
                'justification': 'This procedure is needed for agency operations but not statutorily required.',
                'success': True,
                'processing_time': 12.3,
                'created_at': '2024-01-20T12:00:00'
            }
        }
    ]


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    mock_client = Mock()
    mock_client.analyze_document.return_value = ("Mock analysis response", True, None)
    mock_client.get_usage_stats.return_value = Mock(
        total_calls=10,
        successful_calls=9,
        failed_calls=1,
        total_tokens=5000,
        total_cost=0.10,
        total_time=150.0
    )
    return mock_client


@pytest.fixture
def mock_document_retriever():
    """Mock document retriever for testing."""
    mock_retriever = Mock()
    mock_retriever.get_agency_documents.return_value = []
    return mock_retriever


@pytest.fixture
def mock_progress_tracker():
    """Mock progress tracker for testing."""
    mock_tracker = Mock()
    mock_tracker.start_stage.return_value = None
    mock_tracker.update_progress.return_value = None
    mock_tracker.complete_stage.return_value = None
    mock_tracker.fail_stage.return_value = None
    return mock_tracker


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring external API"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark slow tests
        if "performance" in item.nodeid.lower() or "load" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)
        
        # Mark tests requiring API
        if "api" in item.nodeid.lower() or "llm" in item.nodeid.lower():
            item.add_marker(pytest.mark.requires_api)


# Custom assertions
def assert_valid_session_id(session_id):
    """Assert that a session ID is valid."""
    assert session_id is not None
    assert isinstance(session_id, str)
    assert session_id.startswith('session_')
    assert len(session_id) > 20  # Should have timestamp and UUID


def assert_valid_analysis_result(result):
    """Assert that an analysis result is valid."""
    assert result is not None
    assert 'document_number' in result
    assert 'analysis' in result
    assert isinstance(result['analysis'], dict)
    assert 'success' in result['analysis']


def assert_valid_export_files(exported_files, expected_formats):
    """Assert that exported files are valid."""
    assert isinstance(exported_files, dict)
    
    for format_name in expected_formats:
        assert format_name in exported_files
        file_path = Path(exported_files[format_name])
        assert file_path.exists()
        assert file_path.stat().st_size > 0  # File is not empty


# Add custom assertions to pytest namespace
pytest.assert_valid_session_id = assert_valid_session_id
pytest.assert_valid_analysis_result = assert_valid_analysis_result
pytest.assert_valid_export_files = assert_valid_export_files