"""Tests for the data models module."""

import pytest
from datetime import datetime
from cfr_agency_counter.models import Agency, AgencyDocumentCount, CountingResults


class TestAgency:
    """Test cases for the Agency data class."""
    
    def test_valid_agency_creation(self):
        """Test creating a valid agency."""
        agency = Agency(
            name="Test Agency",
            slug="test-agency",
            cfr_citation="12 CFR 100-199",
            parent_agency="Parent Department",
            active=True,
            description="A test agency"
        )
        
        assert agency.name == "Test Agency"
        assert agency.slug == "test-agency"
        assert agency.active is True
    
    def test_agency_validation_empty_name(self):
        """Test agency validation with empty name."""
        with pytest.raises(ValueError, match="Agency name and slug are required"):
            Agency(
                name="",
                slug="test-agency",
                cfr_citation="12 CFR 100-199",
                parent_agency="",
                active=True,
                description="Test"
            )
    
    def test_agency_validation_empty_slug(self):
        """Test agency validation with empty slug."""
        with pytest.raises(ValueError, match="Agency name and slug are required"):
            Agency(
                name="Test Agency",
                slug="",
                cfr_citation="12 CFR 100-199",
                parent_agency="",
                active=True,
                description="Test"
            )


class TestAgencyDocumentCount:
    """Test cases for the AgencyDocumentCount data class."""
    
    def test_valid_document_count_creation(self):
        """Test creating a valid document count."""
        agency = Agency(
            name="Test Agency",
            slug="test-agency",
            cfr_citation="12 CFR 100-199",
            parent_agency="",
            active=True,
            description="Test"
        )
        
        doc_count = AgencyDocumentCount(
            agency=agency,
            document_count=100,
            last_updated=datetime.now(),
            query_successful=True
        )
        
        assert doc_count.document_count == 100
        assert doc_count.query_successful is True
        assert doc_count.error_message is None
    
    def test_negative_document_count(self):
        """Test validation with negative document count."""
        agency = Agency(
            name="Test Agency",
            slug="test-agency",
            cfr_citation="12 CFR 100-199",
            parent_agency="",
            active=True,
            description="Test"
        )
        
        with pytest.raises(ValueError, match="Document count cannot be negative"):
            AgencyDocumentCount(
                agency=agency,
                document_count=-1,
                last_updated=datetime.now(),
                query_successful=True
            )
    
    def test_failed_query_without_error_message(self):
        """Test validation for failed query without error message."""
        agency = Agency(
            name="Test Agency",
            slug="test-agency",
            cfr_citation="12 CFR 100-199",
            parent_agency="",
            active=True,
            description="Test"
        )
        
        with pytest.raises(ValueError, match="Error message required when query unsuccessful"):
            AgencyDocumentCount(
                agency=agency,
                document_count=0,
                last_updated=datetime.now(),
                query_successful=False
            )


class TestCountingResults:
    """Test cases for the CountingResults data class."""
    
    def test_valid_counting_results(self):
        """Test creating valid counting results."""
        agency = Agency(
            name="Test Agency",
            slug="test-agency",
            cfr_citation="12 CFR 100-199",
            parent_agency="",
            active=True,
            description="Test"
        )
        
        doc_count = AgencyDocumentCount(
            agency=agency,
            document_count=100,
            last_updated=datetime.now(),
            query_successful=True
        )
        
        results = CountingResults(
            total_agencies=1,
            successful_queries=1,
            failed_queries=0,
            agencies_with_documents=1,
            agencies_without_documents=0,
            total_documents=100,
            execution_time=5.0,
            timestamp=datetime.now(),
            results=[doc_count]
        )
        
        assert results.total_agencies == 1
        assert results.success_rate == 100.0
        assert "Processed 1 agencies" in results.get_summary()
    
    def test_mismatched_totals(self):
        """Test validation with mismatched totals."""
        with pytest.raises(ValueError, match="Total agencies must match results length"):
            CountingResults(
                total_agencies=2,
                successful_queries=1,
                failed_queries=0,
                agencies_with_documents=1,
                agencies_without_documents=0,
                total_documents=100,
                execution_time=5.0,
                timestamp=datetime.now(),
                results=[]
            )