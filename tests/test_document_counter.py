"""Tests for the document counter module."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from cfr_agency_counter.document_counter import DocumentCounter
from cfr_agency_counter.models import Agency, AgencyDocumentCount, CountingResults
from cfr_agency_counter.api_client import FederalRegisterAPIError


class TestDocumentCounter:
    """Test cases for the DocumentCounter class."""
    
    def create_test_agency(self, name: str, slug: str, cfr_citation: str = "12 CFR 100-199", active: bool = True) -> Agency:
        """Create a test agency for testing."""
        return Agency(
            name=name,
            slug=slug,
            cfr_citation=cfr_citation,
            parent_agency="Test Department",
            active=active,
            description=f"Test agency: {name}"
        )
    
    def test_initialization(self):
        """Test DocumentCounter initialization."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        assert counter.api_client == mock_client
        assert counter.processing_start_time is None
    
    def test_count_documents_successful(self):
        """Test successful document counting for multiple agencies."""
        # Setup mock API client
        mock_client = Mock()
        mock_client.get_agency_document_counts.return_value = {
            'agriculture-department': 1234,
            'treasury-department': 567,
            'defense-department': 0
        }
        mock_client.get_agency_details.return_value = {'name': 'Defense Department'}
        
        # Create test agencies
        agencies = [
            self.create_test_agency("Agriculture Department", "agriculture-department"),
            self.create_test_agency("Treasury Department", "treasury-department"),
            self.create_test_agency("Defense Department", "defense-department")
        ]
        
        counter = DocumentCounter(mock_client)
        results = counter.count_documents_by_agency(agencies)
        
        # Verify results
        assert isinstance(results, CountingResults)
        assert results.total_agencies == 3
        assert results.successful_queries == 3
        assert results.failed_queries == 0
        assert results.agencies_with_documents == 2
        assert results.agencies_without_documents == 1
        assert results.total_documents == 1801  # 1234 + 567 + 0
        assert results.execution_time > 0
        
        # Verify individual results
        assert len(results.results) == 3
        
        # Check agriculture department result
        ag_result = next(r for r in results.results if r.agency.slug == 'agriculture-department')
        assert ag_result.document_count == 1234
        assert ag_result.query_successful is True
        assert ag_result.error_message is None
        
        # Check treasury department result
        treasury_result = next(r for r in results.results if r.agency.slug == 'treasury-department')
        assert treasury_result.document_count == 567
        assert treasury_result.query_successful is True
        
        # Check defense department result (zero documents)
        defense_result = next(r for r in results.results if r.agency.slug == 'defense-department')
        assert defense_result.document_count == 0
        assert defense_result.query_successful is True
    
    def test_count_documents_api_failure(self):
        """Test handling of API failure during document counting."""
        mock_client = Mock()
        mock_client.get_agency_document_counts.side_effect = FederalRegisterAPIError("API connection failed")
        
        agencies = [
            self.create_test_agency("Test Agency", "test-agency")
        ]
        
        counter = DocumentCounter(mock_client)
        results = counter.count_documents_by_agency(agencies)
        
        # Verify all queries failed
        assert results.total_agencies == 1
        assert results.successful_queries == 0
        assert results.failed_queries == 1
        assert results.total_documents == 0
        
        # Verify error message
        assert len(results.results) == 1
        assert results.results[0].query_successful is False
        assert "API connection failed" in results.results[0].error_message
    
    def test_process_single_agency_with_documents(self):
        """Test processing a single agency that has documents."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        agency = self.create_test_agency("Test Agency", "test-agency")
        api_counts = {"test-agency": 100}
        
        result = counter._process_single_agency(agency, api_counts)
        
        assert result.agency == agency
        assert result.document_count == 100
        assert result.query_successful is True
        assert result.error_message is None
    
    def test_process_single_agency_zero_documents(self):
        """Test processing a single agency with zero documents."""
        mock_client = Mock()
        mock_client.get_agency_details.return_value = {'name': 'Test Agency'}
        
        counter = DocumentCounter(mock_client)
        
        agency = self.create_test_agency("Test Agency", "test-agency")
        api_counts = {}  # Agency not in API results
        
        result = counter._process_single_agency(agency, api_counts)
        
        assert result.agency == agency
        assert result.document_count == 0
        assert result.query_successful is True
        assert result.error_message is None
        
        # Verify API was called to check agency existence
        mock_client.get_agency_details.assert_called_once_with("test-agency")
    
    def test_process_single_agency_not_found(self):
        """Test processing a single agency that doesn't exist in API."""
        mock_client = Mock()
        mock_client.get_agency_details.return_value = None  # Agency not found
        
        counter = DocumentCounter(mock_client)
        
        agency = self.create_test_agency("Nonexistent Agency", "nonexistent-agency")
        api_counts = {}
        
        result = counter._process_single_agency(agency, api_counts)
        
        assert result.agency == agency
        assert result.document_count == 0
        assert result.query_successful is False
        assert "not found in Federal Register API" in result.error_message
    
    def test_process_single_agency_api_error(self):
        """Test processing a single agency when API call fails."""
        mock_client = Mock()
        mock_client.get_agency_details.side_effect = FederalRegisterAPIError("Network error")
        
        counter = DocumentCounter(mock_client)
        
        agency = self.create_test_agency("Test Agency", "test-agency")
        api_counts = {}
        
        result = counter._process_single_agency(agency, api_counts)
        
        assert result.agency == agency
        assert result.document_count == 0
        assert result.query_successful is False
        assert "API error: Network error" in result.error_message
    
    def test_handle_missing_agencies(self):
        """Test identification of agencies missing from API results."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        agencies = [
            self.create_test_agency("Agency 1", "agency-1"),
            self.create_test_agency("Agency 2", "agency-2"),
            self.create_test_agency("Agency 3", "agency-3")
        ]
        
        api_results = {
            "agency-1": 100,
            "agency-3": 200
            # agency-2 is missing
        }
        
        missing = counter.handle_missing_agencies(agencies, api_results)
        
        assert missing == ["agency-2"]
    
    def test_get_extra_agencies_in_api(self):
        """Test identification of agencies in API but not in our list."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        agencies = [
            self.create_test_agency("Agency 1", "agency-1"),
            self.create_test_agency("Agency 2", "agency-2")
        ]
        
        api_results = {
            "agency-1": 100,
            "agency-2": 200,
            "agency-3": 300,  # Extra agency
            "agency-4": 400   # Extra agency
        }
        
        extra = counter.get_extra_agencies_in_api(agencies, api_results)
        
        assert set(extra) == {"agency-3", "agency-4"}
    
    def test_create_comprehensive_mapping(self):
        """Test creation of comprehensive agency mapping."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        agencies = [
            self.create_test_agency("Agency 1", "agency-1", "12 CFR 100-199"),
            self.create_test_agency("Agency 2", "agency-2", "13 CFR 200-299"),
            self.create_test_agency("Agency 3", "agency-3", "14 CFR 300-399")
        ]
        
        api_results = {
            "agency-1": 100,
            "agency-3": 300,
            "extra-agency": 500
            # agency-2 is missing
        }
        
        mapping = counter.create_comprehensive_mapping(agencies, api_results)
        
        # Verify mapping structure
        assert mapping['total_agencies_processed'] == 3
        assert mapping['total_agencies_in_api'] == 3
        assert mapping['total_documents'] == 900  # 100 + 300 + 500
        
        # Verify agencies with counts
        assert len(mapping['agencies_with_counts']) == 2
        assert 'agency-1' in mapping['agencies_with_counts']
        assert 'agency-3' in mapping['agencies_with_counts']
        assert mapping['agencies_with_counts']['agency-1']['document_count'] == 100
        assert mapping['agencies_with_counts']['agency-1']['agency_name'] == "Agency 1"
        assert mapping['agencies_with_counts']['agency-1']['cfr_citation'] == "12 CFR 100-199"
        
        # Verify agencies without counts
        assert len(mapping['agencies_without_counts']) == 1
        assert mapping['agencies_without_counts'][0]['slug'] == 'agency-2'
        assert mapping['agencies_without_counts'][0]['agency_name'] == "Agency 2"
        
        # Verify missing and extra agencies
        assert mapping['agencies_missing_from_api'] == ['agency-2']
        assert mapping['extra_agencies_in_api'] == ['extra-agency']
    
    def test_validate_agency_matching_success(self):
        """Test successful agency matching validation."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        agencies = [
            self.create_test_agency("Agency 1", "agency-1"),
            self.create_test_agency("Agency 2", "agency-2")
        ]
        
        api_results = {
            "agency-1": 100,
            "agency-2": 200
        }
        
        is_valid, issues = counter.validate_agency_matching(agencies, api_results)
        
        assert is_valid is True
        assert issues == []
    
    def test_validate_agency_matching_duplicate_slugs(self):
        """Test validation with duplicate agency slugs."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        agencies = [
            self.create_test_agency("Agency 1", "duplicate-slug"),
            self.create_test_agency("Agency 2", "duplicate-slug")
        ]
        
        api_results = {"duplicate-slug": 100}
        
        is_valid, issues = counter.validate_agency_matching(agencies, api_results)
        
        assert is_valid is False
        assert len(issues) == 1
        assert "Duplicate agency slugs" in issues[0]
        assert "duplicate-slug" in issues[0]
    
    def test_validate_agency_matching_invalid_counts(self):
        """Test validation with invalid document counts."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        agencies = [
            self.create_test_agency("Agency 1", "agency-1")
        ]
        
        api_results = {
            "agency-1": -100,  # Invalid negative count
            "agency-2": "invalid"  # Invalid non-integer count
        }
        
        is_valid, issues = counter.validate_agency_matching(agencies, api_results)
        
        assert is_valid is False
        assert len(issues) == 2
        assert any("Invalid document count for agency-1: -100" in issue for issue in issues)
        assert any("Invalid document count for agency-2: invalid" in issue for issue in issues)
    
    def test_validate_agency_matching_empty_slugs(self):
        """Test validation with empty agency slugs."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        
        # Create agency with empty slug by directly setting the attribute
        agency_with_empty_slug = self.create_test_agency("Agency with Empty Slug", "valid-slug")
        agency_with_empty_slug.slug = ""  # Set empty slug after creation
        
        agencies = [agency_with_empty_slug]
        api_results = {}
        
        is_valid, issues = counter.validate_agency_matching(agencies, api_results)
        
        assert is_valid is False
        assert len(issues) == 1
        assert "Agencies with empty slugs" in issues[0]
        assert "Agency with Empty Slug" in issues[0]
    
    def test_count_documents_with_processing_error(self):
        """Test handling of unexpected processing errors."""
        mock_client = Mock()
        mock_client.get_agency_document_counts.return_value = {"agency-1": 100}
        
        counter = DocumentCounter(mock_client)
        
        # Mock _process_single_agency to raise an exception
        with patch.object(counter, '_process_single_agency', side_effect=Exception("Unexpected error")):
            agencies = [self.create_test_agency("Agency 1", "agency-1")]
            results = counter.count_documents_by_agency(agencies)
        
        assert results.total_agencies == 1
        assert results.successful_queries == 0
        assert results.failed_queries == 1
        assert results.results[0].query_successful is False
        assert "Processing error: Unexpected error" in results.results[0].error_message
    
    def test_create_failed_results(self):
        """Test creation of failed results when entire process fails."""
        mock_client = Mock()
        counter = DocumentCounter(mock_client)
        counter.processing_start_time = datetime.now()
        
        agencies = [
            self.create_test_agency("Agency 1", "agency-1"),
            self.create_test_agency("Agency 2", "agency-2")
        ]
        
        error_message = "Complete API failure"
        results = counter._create_failed_results(agencies, error_message)
        
        assert results.total_agencies == 2
        assert results.successful_queries == 0
        assert results.failed_queries == 2
        assert results.agencies_with_documents == 0
        assert results.agencies_without_documents == 0
        assert results.total_documents == 0
        assert results.execution_time > 0
        
        # Verify all results are failed
        for result in results.results:
            assert result.query_successful is False
            assert result.error_message == error_message
            assert result.document_count == 0
    
    def test_empty_agencies_list(self):
        """Test handling of empty agencies list."""
        mock_client = Mock()
        mock_client.get_agency_document_counts.return_value = {}
        
        counter = DocumentCounter(mock_client)
        results = counter.count_documents_by_agency([])
        
        assert results.total_agencies == 0
        assert results.successful_queries == 0
        assert results.failed_queries == 0
        assert results.results == []
    
    def test_empty_api_results(self):
        """Test handling of empty API results."""
        mock_client = Mock()
        mock_client.get_agency_document_counts.return_value = {}
        mock_client.get_agency_details.return_value = None
        
        agencies = [self.create_test_agency("Test Agency", "test-agency")]
        
        counter = DocumentCounter(mock_client)
        results = counter.count_documents_by_agency(agencies)
        
        assert results.total_agencies == 1
        assert results.successful_queries == 0
        assert results.failed_queries == 1
        assert results.results[0].query_successful is False
        assert "not found in Federal Register API" in results.results[0].error_message
    
    @patch('cfr_agency_counter.document_counter.datetime')
    def test_timing_calculation(self, mock_datetime):
        """Test that execution timing is calculated correctly."""
        # Setup mock datetime to control timing
        start_time = datetime(2025, 1, 8, 10, 0, 0)
        end_time = datetime(2025, 1, 8, 10, 0, 5)  # 5 seconds later
        
        # Need more calls for all the datetime.now() calls in the code
        mock_datetime.now.side_effect = [
            start_time,  # processing_start_time
            end_time,    # last_updated in _process_single_agency
            end_time,    # execution_time calculation
            end_time     # timestamp in CountingResults
        ]
        
        mock_client = Mock()
        mock_client.get_agency_document_counts.return_value = {"agency-1": 100}
        
        agencies = [self.create_test_agency("Agency 1", "agency-1")]
        
        counter = DocumentCounter(mock_client)
        results = counter.count_documents_by_agency(agencies)
        
        assert results.execution_time == 5.0