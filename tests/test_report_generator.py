"""Tests for the report generator module."""

import pytest
import json
import csv
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open

from cfr_agency_counter.report_generator import ReportGenerator
from cfr_agency_counter.models import Agency, AgencyDocumentCount, CountingResults


class TestReportGenerator:
    """Test cases for the ReportGenerator class."""
    
    def create_test_agency(self, name: str, slug: str, cfr_citation: str = "12 CFR 100-199") -> Agency:
        """Create a test agency for testing."""
        return Agency(
            name=name,
            slug=slug,
            cfr_citation=cfr_citation,
            parent_agency="Test Department",
            active=True,
            description=f"Test agency: {name}"
        )
    
    def create_test_results(self) -> CountingResults:
        """Create test counting results."""
        agencies = [
            self.create_test_agency("Agriculture Department", "agriculture-department"),
            self.create_test_agency("Treasury Department", "treasury-department"),
            self.create_test_agency("Defense Department", "defense-department")
        ]
        
        results = [
            AgencyDocumentCount(
                agency=agencies[0],
                document_count=1234,
                last_updated=datetime.now(),
                query_successful=True
            ),
            AgencyDocumentCount(
                agency=agencies[1],
                document_count=567,
                last_updated=datetime.now(),
                query_successful=True
            ),
            AgencyDocumentCount(
                agency=agencies[2],
                document_count=0,
                last_updated=datetime.now(),
                query_successful=False,
                error_message="Agency not found in API"
            )
        ]
        
        return CountingResults(
            total_agencies=3,
            successful_queries=2,
            failed_queries=1,
            agencies_with_documents=2,
            agencies_without_documents=0,
            total_documents=1801,
            execution_time=5.5,
            timestamp=datetime.now(),
            results=results
        )
    
    def test_initialization(self):
        """Test ReportGenerator initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            
            assert generator.output_directory == Path(temp_dir)
            assert generator.output_directory.exists()
    
    def test_initialization_creates_directory(self):
        """Test that initialization creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "new_reports"
            generator = ReportGenerator(str(output_dir))
            
            assert generator.output_directory.exists()
    
    def test_generate_csv_report(self):
        """Test CSV report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            filepath = generator.generate_csv_report(results, "test_report.csv")
            
            assert Path(filepath).exists()
            assert filepath.endswith("test_report.csv")
            
            # Verify CSV content
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                assert len(rows) == 3
                assert rows[0]['agency_name'] == 'Agriculture Department'
                assert rows[0]['document_count'] == '1234'
                assert rows[0]['query_successful'] == 'True'
                assert rows[2]['error_message'] == 'Agency not found in API'
    
    def test_generate_csv_report_auto_filename(self):
        """Test CSV report generation with auto-generated filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            filepath = generator.generate_csv_report(results)
            
            assert Path(filepath).exists()
            assert "cfr_agency_document_counts_" in filepath
            assert filepath.endswith(".csv")
    
    def test_generate_json_report(self):
        """Test JSON report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            filepath = generator.generate_json_report(results, "test_report.json")
            
            assert Path(filepath).exists()
            assert filepath.endswith("test_report.json")
            
            # Verify JSON content
            with open(filepath, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                assert 'metadata' in data
                assert 'agencies' in data
                assert len(data['agencies']) == 3
                assert data['metadata']['total_agencies'] == 3
                assert data['agencies'][0]['agency']['name'] == 'Agriculture Department'
                assert data['agencies'][0]['document_count'] == 1234
    
    def test_generate_json_report_without_metadata(self):
        """Test JSON report generation without metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            filepath = generator.generate_json_report(results, "test_report.json", include_metadata=False)
            
            with open(filepath, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                assert 'metadata' not in data
                assert 'summary' not in data
                assert 'agencies' in data
                assert len(data['agencies']) == 3
    
    def test_generate_summary_report(self):
        """Test summary report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            filepath = generator.generate_summary_report(results, "test_summary.txt")
            
            assert Path(filepath).exists()
            assert filepath.endswith("test_summary.txt")
            
            # Verify summary content
            with open(filepath, 'r', encoding='utf-8') as summaryfile:
                content = summaryfile.read()
                
                assert "CFR AGENCY DOCUMENT COUNTER - SUMMARY REPORT" in content
                assert "Total agencies processed: 3" in content
                assert "Successful queries: 2" in content
                assert "Failed queries: 1" in content
                assert "Total documents found: 1,801" in content
                assert "TOP 10 AGENCIES BY DOCUMENT COUNT" in content
                assert "Agriculture Department: 1,234 documents" in content
    
    def test_generate_all_reports(self):
        """Test generating all report formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            reports = generator.generate_all_reports(results, "test_all")
            
            assert len(reports) == 3
            assert 'csv' in reports
            assert 'json' in reports
            assert 'summary' in reports
            
            # Verify all files exist
            for report_type, filepath in reports.items():
                assert Path(filepath).exists()
                assert "test_all" in filepath
    
    def test_escape_csv_value(self):
        """Test CSV value escaping."""
        generator = ReportGenerator()
        
        # Test normal string
        assert generator._escape_csv_value("Normal text") == "Normal text"
        
        # Test string with line breaks
        assert generator._escape_csv_value("Line 1\nLine 2\rLine 3") == "Line 1 Line 2 Line 3"
        
        # Test string with multiple spaces
        assert generator._escape_csv_value("Multiple   spaces   here") == "Multiple spaces here"
        
        # Test string with null bytes
        assert generator._escape_csv_value("Text\x00with\x00nulls") == "Textwithnulls"
        
        # Test empty string
        assert generator._escape_csv_value("") == ""
        
        # Test None value
        assert generator._escape_csv_value(None) == ""
    
    def test_build_json_report_data_with_metadata(self):
        """Test building JSON report data with metadata."""
        generator = ReportGenerator()
        results = self.create_test_results()
        
        data = generator._build_json_report_data(results, include_metadata=True)
        
        assert 'metadata' in data
        assert 'summary' in data
        assert 'agencies' in data
        assert data['metadata']['total_agencies'] == 3
        assert data['metadata']['successful_queries'] == 2
        assert len(data['agencies']) == 3
    
    def test_build_json_report_data_without_metadata(self):
        """Test building JSON report data without metadata."""
        generator = ReportGenerator()
        results = self.create_test_results()
        
        data = generator._build_json_report_data(results, include_metadata=False)
        
        assert 'metadata' not in data
        assert 'summary' not in data
        assert 'agencies' in data
        assert len(data['agencies']) == 3
    
    def test_build_summary_content(self):
        """Test building summary content."""
        generator = ReportGenerator()
        results = self.create_test_results()
        
        content = generator._build_summary_content(results)
        
        assert "CFR AGENCY DOCUMENT COUNTER - SUMMARY REPORT" in content
        assert "OVERALL STATISTICS" in content
        assert "DOCUMENT STATISTICS" in content
        assert "TOP 10 AGENCIES BY DOCUMENT COUNT" in content
        assert "FAILED QUERIES" in content
        assert "Total agencies processed: 3" in content
        assert "Success rate: 66.7%" in content
    
    def test_validate_output_format(self):
        """Test output format validation."""
        generator = ReportGenerator()
        
        assert generator.validate_output_format("csv") is True
        assert generator.validate_output_format("CSV") is True
        assert generator.validate_output_format("json") is True
        assert generator.validate_output_format("summary") is True
        assert generator.validate_output_format("txt") is True
        assert generator.validate_output_format("invalid") is False
        assert generator.validate_output_format("xml") is False
    
    def test_get_supported_formats(self):
        """Test getting supported formats."""
        generator = ReportGenerator()
        
        formats = generator.get_supported_formats()
        
        assert isinstance(formats, list)
        assert 'csv' in formats
        assert 'json' in formats
        assert 'summary' in formats
        assert len(formats) == 3
    
    def test_cleanup_old_reports(self):
        """Test cleaning up old report files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            
            # Test with empty directory
            removed_count = generator.cleanup_old_reports(days_old=30)
            assert removed_count == 0
            
            # Create a test file and verify cleanup doesn't crash
            test_file = Path(temp_dir) / "cfr_agency_test_report.csv"
            test_file.touch()
            
            # Should not remove recent files
            removed_count = generator.cleanup_old_reports(days_old=30)
            assert removed_count == 0
            assert test_file.exists()
    
    def test_csv_report_io_error(self):
        """Test CSV report generation with IO error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            # Mock open to raise IOError
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with pytest.raises(IOError, match="Failed to write CSV report"):
                    generator.generate_csv_report(results, "test.csv")
    
    def test_json_report_io_error(self):
        """Test JSON report generation with IO error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            # Mock open to raise IOError
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with pytest.raises(IOError, match="Failed to write JSON report"):
                    generator.generate_json_report(results, "test.json")
    
    def test_summary_report_io_error(self):
        """Test summary report generation with IO error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            # Mock open to raise IOError
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with pytest.raises(IOError, match="Failed to write summary report"):
                    generator.generate_summary_report(results, "test.txt")
    
    def test_csv_special_characters(self):
        """Test CSV generation with special characters in data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            
            # Create agency with special characters
            agency = Agency(
                name="Agency with \"quotes\" and, commas",
                slug="special-agency",
                cfr_citation="12 CFR 100-199",
                parent_agency="Department with\nnewlines",
                active=True,
                description="Description with\ttabs and\rcarriage returns"
            )
            
            result = AgencyDocumentCount(
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
                execution_time=1.0,
                timestamp=datetime.now(),
                results=[result]
            )
            
            filepath = generator.generate_csv_report(results, "special_chars.csv")
            
            # Verify file was created and can be read
            assert Path(filepath).exists()
            
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                assert len(rows) == 1
                assert "quotes" in rows[0]['agency_name']
                assert "commas" in rows[0]['agency_name']
                # Newlines should be converted to spaces
                assert "\n" not in rows[0]['parent_agency']
    
    def test_summary_with_zero_document_agencies(self):
        """Test summary report with agencies that have zero documents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            
            # Create results with zero-document agencies
            agency1 = self.create_test_agency("Agency 1", "agency-1")
            agency2 = self.create_test_agency("Agency 2", "agency-2")
            
            results_list = [
                AgencyDocumentCount(
                    agency=agency1,
                    document_count=100,
                    last_updated=datetime.now(),
                    query_successful=True
                ),
                AgencyDocumentCount(
                    agency=agency2,
                    document_count=0,
                    last_updated=datetime.now(),
                    query_successful=True
                )
            ]
            
            results = CountingResults(
                total_agencies=2,
                successful_queries=2,
                failed_queries=0,
                agencies_with_documents=1,
                agencies_without_documents=1,
                total_documents=100,
                execution_time=1.0,
                timestamp=datetime.now(),
                results=results_list
            )
            
            content = generator._build_summary_content(results)
            
            assert "AGENCIES WITH ZERO DOCUMENTS" in content
            assert "Agency 2" in content
    
    def test_json_datetime_serialization(self):
        """Test that datetime objects are properly serialized in JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            results = self.create_test_results()
            
            filepath = generator.generate_json_report(results, "datetime_test.json")
            
            # Verify JSON can be loaded and contains ISO format dates
            with open(filepath, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                # Check that timestamps are in ISO format
                assert 'T' in data['metadata']['generated_at']
                assert 'T' in data['agencies'][0]['last_updated']