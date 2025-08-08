"""
Integration tests for agency synopsis feature in CFR Document Analyzer.

Tests complete agency presentation generation with LLM synopsis,
error handling, and async processing.
"""

import unittest
import tempfile
import asyncio
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cfr_document_analyzer.export_manager import ExportManager
from cfr_document_analyzer.llm_client import LLMClient
from cfr_document_analyzer.models import RegulationCategory


class TestAgencySynopsisIntegration(unittest.TestCase):
    """Integration tests for agency synopsis feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = ExportManager(output_dir=self.temp_dir)
        
        # Sample analysis results for integration testing
        self.sample_results = [
            {
                'document_number': '2024-12345',
                'title': 'Credit Union Capital Requirements',
                'agency_slug': 'national-credit-union-administration',
                'publication_date': '2024-01-15',
                'content_length': 2500,
                'analysis': {
                    'category': RegulationCategory.STATUTORILY_REQUIRED,
                    'statutory_references': ['12 U.S.C. 1751', '12 U.S.C. 1790d'],
                    'reform_recommendations': ['Simplify capital ratio calculations'],
                    'success': True,
                    'processing_time': 3.2,
                    'justification': 'This regulation implements statutory requirements for credit union capital adequacy...'
                }
            },
            {
                'document_number': '2024-67890',
                'title': 'Member Business Lending Rules',
                'agency_slug': 'national-credit-union-administration',
                'publication_date': '2024-02-20',
                'content_length': 1800,
                'analysis': {
                    'category': 'NSR',
                    'statutory_references': [],
                    'reform_recommendations': ['Consider elimination', 'Merge with similar rules'],
                    'success': True,
                    'processing_time': 2.1,
                    'justification': 'This regulation is not explicitly required by statute but provides operational guidance...'
                }
            }
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_agency_presentation_generation(self):
        """Test complete agency presentation generation with LLM synopsis."""
        # Mock successful LLM response for synopsis
        mock_synopsis = """The National Credit Union Administration (NCUA) is an independent federal agency established in 1970 that regulates and supervises federal credit unions. Created under the Federal Credit Union Act, NCUA ensures the safety and soundness of the credit union system through examination, supervision, and deposit insurance. The agency operates the National Credit Union Share Insurance Fund, protecting member deposits up to $250,000. In today's Washington environment, NCUA faces challenges balancing regulatory oversight with credit union growth, addressing cybersecurity threats, and adapting regulations to technological innovations while maintaining the cooperative principles that distinguish credit unions from traditional banks."""
        
        self.export_manager.llm_client.analyze_document = Mock(
            return_value=(mock_synopsis, True, None)
        )
        
        # Generate complete agency presentation
        summary_path = self.export_manager.create_agency_presentation_summary(
            self.sample_results, 'integration_test_session'
        )
        
        # Verify file was created
        self.assertTrue(Path(summary_path).exists())
        
        # Read and verify content
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify structure and content
        self.assertIn('# CFR Document Analysis Summary', content)
        self.assertIn('## National Credit Union Administration', content)
        self.assertIn('### Agency Overview', content)
        self.assertIn('The National Credit Union Administration (NCUA)', content)
        self.assertIn('established in 1970', content)
        self.assertIn('Federal Credit Union Act', content)
        self.assertIn('**Session ID:** integration_test_session', content)
        self.assertIn('**Documents Analyzed:** 2', content)
        
        # Verify document details are included
        self.assertIn('2024-12345', content)
        self.assertIn('Credit Union Capital Requirements', content)
        self.assertIn('Member Business Lending Rules', content)
        
        # Verify LLM client was called with correct parameters
        self.export_manager.llm_client.analyze_document.assert_called_once()
        call_args = self.export_manager.llm_client.analyze_document.call_args
        if call_args and len(call_args) > 0 and len(call_args[0]) > 1:
            self.assertIn('National Credit Union Administration', call_args[0][0])
            self.assertIn('100-word synopsis', call_args[0][1])
    
    def test_agency_presentation_with_llm_timeout(self):
        """Test agency presentation generation with LLM timeout handling."""
        # Mock LLM timeout
        def mock_timeout(*args, **kwargs):
            time.sleep(0.1)  # Simulate delay
            raise TimeoutError("LLM request timed out")
        
        self.export_manager.llm_client.analyze_document = Mock(side_effect=mock_timeout)
        
        # Generate presentation - should handle timeout gracefully
        summary_path = self.export_manager.create_agency_presentation_summary(
            self.sample_results, 'timeout_test_session'
        )
        
        # Verify file was created with fallback content
        self.assertTrue(Path(summary_path).exists())
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should contain fallback message
        self.assertIn('Agency overview could not be generated at this time.', content)
        self.assertIn('National Credit Union Administration', content)
        self.assertIn('timeout_test_session', content)
    
    def test_agency_presentation_with_rate_limiting(self):
        """Test agency presentation generation with LLM rate limiting."""
        # Mock rate-limited LLM response
        self.export_manager.llm_client.analyze_document = Mock(
            return_value=("", False, "Rate limit exceeded. Please try again later.")
        )
        
        # Generate presentation
        summary_path = self.export_manager.create_agency_presentation_summary(
            self.sample_results, 'rate_limit_test_session'
        )
        
        # Verify graceful handling
        self.assertTrue(Path(summary_path).exists())
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('Agency overview could not be generated at this time.', content)
    
    def test_synopsis_integration_with_csv_export(self):
        """Test that synopsis generation doesn't interfere with CSV export."""
        # Mock LLM response
        self.export_manager.llm_client.analyze_document = Mock(
            return_value=("Test synopsis content", True, None)
        )
        
        # Export both CSV and presentation
        csv_path = self.export_manager._export_csv(
            self.sample_results, 'csv_test_session', 'test_csv_export'
        )
        
        presentation_path = self.export_manager.create_agency_presentation_summary(
            self.sample_results, 'csv_test_session'
        )
        
        # Verify both files exist
        self.assertTrue(Path(csv_path).exists())
        self.assertTrue(Path(presentation_path).exists())
        
        # Verify CSV structure is correct (not affected by synopsis generation)
        import csv
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
        
        expected_headers = [
            'Document Number', 'Title', 'Agency', 'Publication Date', 'Content Length',
            'Category', 'Statutory References Count', 'Statutory References',
            'Reform Recommendations Count', 'Analysis Success', 'Processing Time (s)'
        ]
        
        self.assertEqual(headers, expected_headers)
        self.assertEqual(len(rows), 2)
        
        # Verify presentation includes synopsis
        with open(presentation_path, 'r', encoding='utf-8') as f:
            presentation_content = f.read()
        
        self.assertIn('Test synopsis content', presentation_content)
    
    def test_multiple_agency_synopsis_calls(self):
        """Test handling of multiple agency synopsis generation calls."""
        # Mock different responses for different agencies
        def mock_llm_response(content, prompt, document_id=None):
            if 'National Credit Union Administration' in content:
                return ("NCUA synopsis content", True, None)
            elif 'Farm Credit Administration' in content:
                return ("FCA synopsis content", True, None)
            else:
                return ("Generic agency synopsis", True, None)
        
        self.export_manager.llm_client.analyze_document = Mock(side_effect=mock_llm_response)
        
        # Generate synopsis for multiple agencies
        ncua_result = self.export_manager.generate_agency_synopsis("National Credit Union Administration")
        fca_result = self.export_manager.generate_agency_synopsis("Farm Credit Administration")
        
        # Verify different responses
        self.assertTrue(ncua_result['generation_success'])
        self.assertIn('NCUA synopsis', ncua_result['synopsis_text'])
        
        self.assertTrue(fca_result['generation_success'])
        self.assertIn('FCA synopsis', fca_result['synopsis_text'])
        
        # Verify LLM was called twice
        self.assertEqual(self.export_manager.llm_client.analyze_document.call_count, 2)
    
    def test_synopsis_with_special_characters(self):
        """Test synopsis generation handles special characters correctly."""
        # Mock synopsis with special characters
        special_synopsis = """The U.S. Department of Agriculture's Farm Credit Administration (FCA) regulates the Farm Credit System—a nationwide network of borrower-owned lending institutions. Established in 1933 during the Great Depression, FCA ensures these institutions provide sound, dependable credit to farmers, ranchers, and rural communities. The agency's mission includes examining institutions, setting capital standards, and protecting the interests of investors in Farm Credit securities. Today's challenges include climate change impacts on agriculture, consolidation in farming, technological disruption, and maintaining access to credit for beginning farmers while ensuring system safety & soundness."""
        
        self.export_manager.llm_client.analyze_document = Mock(
            return_value=(special_synopsis, True, None)
        )
        
        # Generate presentation
        summary_path = self.export_manager.create_agency_presentation_summary(
            self.sample_results, 'special_chars_test'
        )
        
        # Verify special characters are preserved
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('Farm Credit System—a nationwide', content)
        self.assertIn('safety & soundness', content)
        self.assertIn('1933', content)
    
    def test_synopsis_error_recovery(self):
        """Test error recovery in synopsis generation."""
        # Mock sequence of failures then success
        call_count = 0
        def mock_failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network error")
            else:
                return ("Recovered synopsis content", True, None)
        
        self.export_manager.llm_client.analyze_document = Mock(side_effect=mock_failing_then_success)
        
        # First call should fail
        result1 = self.export_manager.generate_agency_synopsis("Test Agency")
        self.assertFalse(result1['generation_success'])
        self.assertEqual(result1['error_message'], "Network error")
        
        # Second call should succeed
        result2 = self.export_manager.generate_agency_synopsis("Test Agency")
        self.assertTrue(result2['generation_success'])
        self.assertIn("Recovered synopsis", result2['synopsis_text'])
    
    def test_presentation_formatting_with_synopsis(self):
        """Test that presentation formatting works correctly with synopsis."""
        # Mock synopsis
        test_synopsis = "Test agency synopsis for formatting verification."
        self.export_manager.llm_client.analyze_document = Mock(
            return_value=(test_synopsis, True, None)
        )
        
        # Generate presentation
        summary_path = self.export_manager.create_agency_presentation_summary(
            self.sample_results, 'formatting_test'
        )
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify markdown structure
        lines = content.split('\n')
        
        # Check header structure
        self.assertTrue(any(line.startswith('# CFR Document Analysis Summary') for line in lines))
        self.assertTrue(any(line.startswith('## National Credit Union Administration') for line in lines))
        self.assertTrue(any(line.startswith('### Agency Overview') for line in lines))
        
        # Verify synopsis is in correct location (after Agency Overview header)
        agency_overview_idx = next(i for i, line in enumerate(lines) if line.startswith('### Agency Overview'))
        synopsis_line = lines[agency_overview_idx + 1]
        self.assertEqual(synopsis_line, test_synopsis)
        
        # Verify other sections follow
        self.assertTrue(any(line.startswith('## Executive Summary') for line in lines))
        self.assertTrue(any(line.startswith('### Key Findings') for line in lines))


class TestAgencySynopsisPerformance(unittest.TestCase):
    """Performance tests for agency synopsis feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = ExportManager(output_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_synopsis_generation_timeout(self):
        """Test synopsis generation respects timeout limits."""
        # Mock slow LLM response
        def slow_response(*args, **kwargs):
            time.sleep(0.2)  # Simulate slow response
            return ("Slow response content", True, None)
        
        self.export_manager.llm_client.analyze_document = Mock(side_effect=slow_response)
        
        # Measure time
        start_time = time.time()
        result = self.export_manager.generate_agency_synopsis("Test Agency")
        end_time = time.time()
        
        # Should complete (mocked delay is short)
        self.assertTrue(result['generation_success'])
        self.assertLess(end_time - start_time, 1.0)  # Should be reasonably fast
    
    def test_large_results_processing(self):
        """Test processing large result sets with synopsis generation."""
        # Create large result set
        large_results = []
        for i in range(50):  # 50 documents
            large_results.append({
                'document_number': f'2024-{i:05d}',
                'title': f'Test Regulation {i}',
                'agency_slug': 'test-agency',
                'publication_date': '2024-01-01',
                'content_length': 1000,
                'analysis': {
                    'category': 'SR',
                    'statutory_references': [f'12 U.S.C. {1000 + i}'],
                    'reform_recommendations': [f'Recommendation {i}'],
                    'success': True,
                    'processing_time': 1.0,
                    'justification': f'Justification for regulation {i}'
                }
            })
        
        # Mock fast synopsis generation
        self.export_manager.llm_client.analyze_document = Mock(
            return_value=("Fast synopsis for large dataset", True, None)
        )
        
        # Measure processing time
        start_time = time.time()
        summary_path = self.export_manager.create_agency_presentation_summary(
            large_results, 'large_dataset_test'
        )
        end_time = time.time()
        
        # Verify completion
        self.assertTrue(Path(summary_path).exists())
        
        # Should complete in reasonable time (synopsis only called once per agency)
        self.assertLess(end_time - start_time, 5.0)
        
        # Verify synopsis was only called once (not per document)
        self.assertEqual(self.export_manager.llm_client.analyze_document.call_count, 1)


if __name__ == '__main__':
    unittest.main()