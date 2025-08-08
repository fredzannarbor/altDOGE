"""Integration tests for the CFR Agency Document Counter."""

import pytest
import tempfile
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from cfr_agency_counter.main import main
from cfr_agency_counter.data_loader import AgencyDataLoader
from cfr_agency_counter.api_client import FederalRegisterClient
from cfr_agency_counter.document_counter import DocumentCounter
from cfr_agency_counter.progress_tracker import ProgressTracker
from cfr_agency_counter.report_generator import ReportGenerator
from cfr_agency_counter.models import Agency, AgencyDocumentCount, CountingResults


class TestEndToEndIntegration:
    """Test cases for end-to-end integration."""
    
    def create_test_agencies_csv(self, temp_dir: str) -> str:
        """Create a test agencies CSV file."""
        csv_path = Path(temp_dir) / "test_agencies.csv"
        
        test_data = [
            {
                'active': '1',
                'cfr_citation': '12 CFR 100-199',
                'parent_agency_name': 'Treasury Department',
                'agency_name': 'Test Agency 1',
                'description': 'First test agency'
            },
            {
                'active': '1',
                'cfr_citation': '13 CFR 200-299',
                'parent_agency_name': 'Commerce Department',
                'agency_name': 'Test Agency 2',
                'description': 'Second test agency'
            },
            {
                'active': '0',
                'cfr_citation': '14 CFR 300-399',
                'parent_agency_name': 'Transportation Department',
                'agency_name': 'Inactive Agency',
                'description': 'Inactive test agency'
            }
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['active', 'cfr_citation', 'parent_agency_name', 'agency_name', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(test_data)
        
        return str(csv_path)
    
    def test_complete_pipeline_integration(self):
        """Test complete pipeline from CSV to reports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test CSV file
            csv_path = self.create_test_agencies_csv(temp_dir)
            
            # Mock API responses
            mock_api_counts = {
                'test-agency-1': 100,
                'test-agency-2': 50
                # inactive-agency not in results (simulating zero documents)
            }
            
            with patch('cfr_agency_counter.api_client.FederalRegisterClient') as mock_client_class:
                # Setup mock client
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.get_agency_document_counts.return_value = mock_api_counts
                mock_client.get_agency_details.return_value = {'name': 'Test Agency'}
                
                # Run the complete pipeline
                loader = AgencyDataLoader()
                agencies = loader.get_cfr_active_agencies(csv_path)
                
                counter = DocumentCounter(mock_client)
                results = counter.count_documents_by_agency(agencies)
                
                generator = ReportGenerator(temp_dir)
                reports = generator.generate_all_reports(results)
                
                # Verify results
                assert len(agencies) == 2  # Only active CFR agencies
                assert results.total_agencies == 2
                assert results.successful_queries == 2
                assert results.total_documents == 150  # 100 + 50
                
                # Verify reports were generated
                assert 'csv' in reports
                assert 'json' in reports
                assert 'summary' in reports
                
                # Verify files exist
                for report_path in reports.values():
                    assert Path(report_path).exists()
    
    def test_data_loader_integration(self):
        """Test data loader integration with various data scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = self.create_test_agencies_csv(temp_dir)
            
            loader = AgencyDataLoader()
            
            # Test loading all agencies
            all_agencies = loader.load_agencies(csv_path)
            assert len(all_agencies) == 3
            
            # Test CFR filtering
            cfr_agencies = loader.filter_cfr_agencies(all_agencies)
            assert len(cfr_agencies) == 3  # All have CFR citations
            
            # Test active filtering
            active_agencies = loader.get_active_agencies(all_agencies)
            assert len(active_agencies) == 2
            
            # Test combined filtering
            active_cfr_agencies = loader.get_cfr_active_agencies(csv_path)
            assert len(active_cfr_agencies) == 2
            
            # Verify agency properties
            for agency in active_cfr_agencies:
                assert agency.active is True
                assert agency.cfr_citation
                assert agency.name
                assert agency.slug
    
    def test_api_client_integration(self):
        """Test API client integration with mocked responses."""
        with patch('requests.Session') as mock_session_class:
            # Setup mock session
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'facets': {
                    'agency': {
                        'test-agency': 100,
                        'another-agency': 50
                    }
                }
            }
            mock_session.get.return_value = mock_response
            
            # Test API client
            client = FederalRegisterClient(rate_limit=10.0)  # High rate for testing
            counts = client.get_agency_document_counts()
            
            assert counts == {'test-agency': 100, 'another-agency': 50}
            
            # Verify rate limiting was configured
            assert client.rate_limit == 10.0
            
            # Test individual agency lookup
            mock_response.json.return_value = {'name': 'Test Agency', 'slug': 'test-agency'}
            details = client.get_agency_details('test-agency')
            
            assert details['name'] == 'Test Agency'
            assert details['slug'] == 'test-agency'
    
    def test_document_counter_integration(self):
        """Test document counter integration with various scenarios."""
        # Create test agencies
        agencies = [
            Agency(
                name="Agency with Documents",
                slug="agency-with-docs",
                cfr_citation="12 CFR 100-199",
                parent_agency="Test Dept",
                active=True,
                description="Test agency"
            ),
            Agency(
                name="Agency without Documents",
                slug="agency-without-docs",
                cfr_citation="13 CFR 200-299",
                parent_agency="Test Dept",
                active=True,
                description="Test agency"
            ),
            Agency(
                name="Missing Agency",
                slug="missing-agency",
                cfr_citation="14 CFR 300-399",
                parent_agency="Test Dept",
                active=True,
                description="Test agency"
            )
        ]
        
        # Mock API client
        mock_client = MagicMock()
        mock_client.get_agency_document_counts.return_value = {
            'agency-with-docs': 100
            # Other agencies not in results
        }
        
        # Mock agency details calls
        def mock_get_agency_details(slug):
            if slug == 'agency-without-docs':
                return {'name': 'Agency without Documents'}  # Exists but no docs
            elif slug == 'missing-agency':
                return None  # Doesn't exist
            return {'name': 'Unknown'}
        
        mock_client.get_agency_details.side_effect = mock_get_agency_details
        
        # Test document counter
        counter = DocumentCounter(mock_client)
        results = counter.count_documents_by_agency(agencies)
        
        # Verify results
        assert results.total_agencies == 3
        assert results.successful_queries == 2  # agency-with-docs and agency-without-docs
        assert results.failed_queries == 1  # missing-agency
        assert results.agencies_with_documents == 1
        assert results.agencies_without_documents == 1
        assert results.total_documents == 100
        
        # Verify individual results
        results_by_slug = {r.agency.slug: r for r in results.results}
        
        # Agency with documents
        with_docs = results_by_slug['agency-with-docs']
        assert with_docs.query_successful is True
        assert with_docs.document_count == 100
        
        # Agency without documents
        without_docs = results_by_slug['agency-without-docs']
        assert without_docs.query_successful is True
        assert without_docs.document_count == 0
        
        # Missing agency
        missing = results_by_slug['missing-agency']
        assert missing.query_successful is False
        assert "not found" in missing.error_message.lower()
    
    def test_progress_tracker_integration(self):
        """Test progress tracker integration."""
        tracker = ProgressTracker(total_items=5, update_interval=20.0)
        
        # Test progress tracking
        tracker.start()
        
        # Simulate processing items
        items = ['item1', 'item2', 'item3', 'item4', 'item5']
        for i, item in enumerate(items):
            success = i < 4  # Last item fails
            tracker.update(item, success)
            
            stats = tracker.get_progress_stats()
            assert stats['processed_items'] == i + 1
            assert stats['total_items'] == 5
        
        # Verify final stats
        final_stats = tracker.get_progress_stats()
        assert final_stats['processed_items'] == 5
        assert final_stats['successful_items'] == 4
        assert final_stats['failed_items'] == 1
        assert final_stats['percentage_complete'] == 100.0
        assert final_stats['success_rate'] == 80.0
        
        tracker.finish()
        assert tracker.is_complete()
    
    def test_report_generator_integration(self):
        """Test report generator integration with real data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test results
            agencies = [
                Agency(
                    name="Test Agency 1",
                    slug="test-agency-1",
                    cfr_citation="12 CFR 100-199",
                    parent_agency="Treasury",
                    active=True,
                    description="First test agency"
                ),
                Agency(
                    name="Test Agency 2",
                    slug="test-agency-2",
                    cfr_citation="13 CFR 200-299",
                    parent_agency="Commerce",
                    active=True,
                    description="Second test agency"
                )
            ]
            
            results_list = [
                AgencyDocumentCount(
                    agency=agencies[0],
                    document_count=100,
                    last_updated=datetime.now(),
                    query_successful=True
                ),
                AgencyDocumentCount(
                    agency=agencies[1],
                    document_count=50,
                    last_updated=datetime.now(),
                    query_successful=True
                )
            ]
            
            results = CountingResults(
                total_agencies=2,
                successful_queries=2,
                failed_queries=0,
                agencies_with_documents=2,
                agencies_without_documents=0,
                total_documents=150,
                execution_time=5.0,
                timestamp=datetime.now(),
                results=results_list
            )
            
            # Test report generation
            generator = ReportGenerator(temp_dir)
            reports = generator.generate_all_reports(results)
            
            # Verify all reports were generated
            assert len(reports) == 3
            assert 'csv' in reports
            assert 'json' in reports
            assert 'summary' in reports
            
            # Verify CSV content
            csv_path = reports['csv']
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                assert len(rows) == 2
                assert rows[0]['agency_name'] == 'Test Agency 1'
                assert rows[0]['document_count'] == '100'
                assert rows[1]['agency_name'] == 'Test Agency 2'
                assert rows[1]['document_count'] == '50'
            
            # Verify JSON content
            import json
            json_path = reports['json']
            with open(json_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                assert 'metadata' in data
                assert 'agencies' in data
                assert len(data['agencies']) == 2
                assert data['metadata']['total_documents'] == 150
            
            # Verify summary content
            summary_path = reports['summary']
            with open(summary_path, 'r', encoding='utf-8') as summaryfile:
                content = summaryfile.read()
                
                assert "Total agencies processed: 2" in content
                assert "Total documents found: 150" in content
                assert "Test Agency 1: 100 documents" in content
    
    def test_error_handling_integration(self):
        """Test error handling integration across components."""
        from cfr_agency_counter.error_handler import ErrorCollector, safe_execute
        
        collector = ErrorCollector()
        
        # Test safe execution with data loader
        def failing_load():
            raise ValueError("CSV parsing failed")
        
        result = safe_execute(failing_load, error_collector=collector, context="data_loading")
        
        assert result is None
        assert collector.has_errors()
        assert len(collector.errors) == 1
        assert "data_loading" in collector.errors[0].message
        
        # Test safe execution with API client
        def failing_api_call():
            raise ConnectionError("API connection failed")
        
        result = safe_execute(failing_api_call, error_collector=collector, context="api_call")
        
        assert result is None
        assert len(collector.errors) == 2
        
        # Get error summary
        summary = collector.get_error_summary()
        assert "Errors (2):" in summary
        assert "CSV parsing failed" in summary
        assert "API connection failed" in summary


class TestPerformanceIntegration:
    """Test cases for performance and scalability."""
    
    def test_memory_usage_monitoring(self):
        """Test memory usage during processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create a larger dataset
        agencies = []
        for i in range(100):
            agency = Agency(
                name=f"Test Agency {i}",
                slug=f"test-agency-{i}",
                cfr_citation=f"{12 + i} CFR {100 + i*10}-{199 + i*10}",
                parent_agency="Test Department",
                active=True,
                description=f"Test agency number {i}"
            )
            agencies.append(agency)
        
        # Mock API client for performance testing
        mock_client = MagicMock()
        mock_client.get_agency_document_counts.return_value = {
            f"test-agency-{i}": i * 10 for i in range(100)
        }
        
        # Process agencies
        counter = DocumentCounter(mock_client)
        results = counter.count_documents_by_agency(agencies)
        
        # Check memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for 100 agencies)
        assert memory_increase < 100 * 1024 * 1024  # 100MB
        
        # Verify results
        assert results.total_agencies == 100
        assert results.successful_queries == 100
        assert results.total_documents == sum(i * 10 for i in range(100))
    
    def test_rate_limiting_compliance(self):
        """Test API rate limiting compliance."""
        import time
        
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            
            # Mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'facets': {'agency': {}}}
            mock_session.get.return_value = mock_response
            
            # Test rate limiting
            client = FederalRegisterClient(rate_limit=2.0)  # 2 requests per second
            
            start_time = time.time()
            
            # Make multiple requests
            for _ in range(3):
                client.get_agency_document_counts()
            
            elapsed_time = time.time() - start_time
            
            # Should take at least 1 second due to rate limiting (3 requests at 2/sec)
            assert elapsed_time >= 1.0
            
            # Verify requests were made
            assert mock_session.get.call_count == 3
    
    def test_large_dataset_processing(self):
        """Test processing of large agency datasets."""
        import time
        
        # Create a large number of agencies
        agencies = []
        for i in range(500):  # Simulate processing many agencies
            agency = Agency(
                name=f"Agency {i:03d}",
                slug=f"agency-{i:03d}",
                cfr_citation=f"{12 + (i % 50)} CFR {100 + i}-{199 + i}",
                parent_agency=f"Department {i % 10}",
                active=i % 4 != 0,  # 75% active
                description=f"Test agency {i}"
            )
            agencies.append(agency)
        
        # Mock API responses
        mock_client = MagicMock()
        mock_api_counts = {f"agency-{i:03d}": i for i in range(500)}
        mock_client.get_agency_document_counts.return_value = mock_api_counts
        
        counter = DocumentCounter(mock_client)
        
        # Time the processing
        start_time = time.time()
        results = counter.count_documents_by_agency(agencies)
        processing_time = time.time() - start_time
        
        # Verify results
        assert results.total_agencies == 500
        assert results.successful_queries == 500
        assert results.total_documents == sum(range(500))
        
        # Performance should be reasonable (less than 10 seconds for 500 agencies)
        assert processing_time < 10.0
        
        # Verify processing was efficient
        assert processing_time > 0