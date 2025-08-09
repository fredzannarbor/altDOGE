"""
Unit tests for CFR Document Analyzer ExportManager.

Tests CSV restructuring functionality including column structure,
category extraction, and statutory references formatting.
"""

import unittest
import tempfile
import csv
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cfr_document_analyzer.export_manager import ExportManager
from cfr_document_analyzer.models import RegulationCategory


class TestExportManager(unittest.TestCase):
    """Test cases for ExportManager CSV restructuring functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = ExportManager(output_dir=self.temp_dir)
        
        # Mock LLM client to avoid actual API calls
        self.export_manager.llm_client = Mock()
        
        # Sample analysis results for testing
        self.sample_results = [
            {
                'document_number': '2024-12345',
                'title': 'Test Regulation 1',
                'agency_slug': 'national-credit-union-administration',
                'publication_date': '2024-01-15',
                'content_length': 1500,
                'analysis': {
                    'category': RegulationCategory.STATUTORILY_REQUIRED,
                    'statutory_references': ['12 U.S.C. 1751', '12 U.S.C. 1752(a)'],
                    'reform_recommendations': ['Simplify reporting requirements'],
                    'success': True,
                    'processing_time': 2.5,
                    'justification': json.dumps({
                        'category': 'SR',
                        'analysis': 'This regulation is required by statute',
                        'legal_basis': '12 U.S.C. 1751',
                        'recommendation': 'Maintain current structure'
                    })
                }
            },
            {
                'document_number': '2024-67890',
                'title': 'Test Regulation 2',
                'agency_slug': 'national-credit-union-administration',
                'publication_date': '2024-02-20',
                'content_length': 800,
                'analysis': {
                    'category': 'NSR',
                    'statutory_references': [],
                    'reform_recommendations': ['Consider elimination', 'Merge with similar rules'],
                    'success': True,
                    'processing_time': 1.8,
                    'justification': json.dumps({
                        'category': 'NSR',
                        'analysis': 'This regulation is not statutorily required',
                        'summary': 'Can be eliminated or simplified'
                    })
                }
            }
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_csv_column_structure(self):
        """Test that CSV has correct column headers in new structure."""
        # Export CSV
        filepath = self.export_manager._export_csv(
            self.sample_results, 'test_session', 'test_export'
        )
        
        # Read and verify headers
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
        
        # Base expected headers (without Category column)
        expected_base_headers = [
            'Document Number',
            'Title',
            'Agency',
            'Publication Date',
            'Content Length',
            'Statutory References Count',
            'Statutory References',
            'Reform Recommendations Count',
            'Analysis Success',
            'Processing Time (s)'
        ]
        
        # Verify base headers are present
        for header in expected_base_headers:
            self.assertIn(header, headers)
        
        # Verify Category column is NOT in headers (removed)
        self.assertNotIn('Category', headers)
        
        # Verify Justification Preview is NOT in headers
        self.assertNotIn('Justification Preview', headers)
        
        # Verify justification-derived columns are present
        justification_columns = ['analysis', 'category', 'legal_basis', 'recommendation', 'summary']
        for col in justification_columns:
            if col in ['analysis', 'category', 'legal_basis']:  # These should be in our test data
                self.assertIn(col, headers)
    
    def test_justification_json_parsing(self):
        """Test parsing of justification field as JSON."""
        # Test valid JSON parsing
        json_justification = json.dumps({
            'category': 'SR',
            'analysis': 'Test analysis',
            'legal_basis': 'Test statute'
        })
        
        parsed = self.export_manager._parse_justification_json(json_justification)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['category'], 'SR')
        self.assertEqual(parsed['analysis'], 'Test analysis')
        self.assertEqual(parsed['legal_basis'], 'Test statute')
    
    def test_justification_text_parsing(self):
        """Test parsing of justification field as structured text."""
        text_justification = """
        CATEGORY: NRAN
        ANALYSIS: This is a test analysis
        LEGAL BASIS: 12 U.S.C. 1751
        """
        
        parsed = self.export_manager._parse_justification_json(text_justification)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['category'], 'NRAN')
        self.assertEqual(parsed['analysis'], 'This is a test analysis')
        self.assertEqual(parsed['legal_basis'], '12 U.S.C. 1751')
    
    def test_justification_parsing_failure(self):
        """Test handling of unparseable justification data."""
        # Test with plain text that has no structure
        plain_text = "This is just plain text with no structure"
        parsed = self.export_manager._parse_justification_json(plain_text)
        self.assertIsNone(parsed)
        
        # Test with None
        parsed = self.export_manager._parse_justification_json(None)
        self.assertIsNone(parsed)
        
        # Test with empty string
        parsed = self.export_manager._parse_justification_json("")
        self.assertIsNone(parsed)
    
    def test_category_extraction_fallback(self):
        """Test category extraction fallback to UNKNOWN."""
        # Missing category
        analysis = {}
        category = self.export_manager._extract_category(analysis)
        self.assertEqual(category, 'UNKNOWN')
        
        # Invalid category
        analysis = {'category': 'INVALID_CATEGORY'}
        category = self.export_manager._extract_category(analysis)
        self.assertEqual(category, 'UNKNOWN')
        
        # Non-string, non-enum category
        analysis = {'category': 123}
        category = self.export_manager._extract_category(analysis)
        self.assertEqual(category, 'UNKNOWN')
    
    def test_statutory_references_formatting_empty(self):
        """Test statutory references formatting with empty list."""
        refs = []
        formatted = self.export_manager._format_statutory_references(refs)
        self.assertEqual(formatted, '')
    
    def test_statutory_references_formatting_single(self):
        """Test statutory references formatting with single reference."""
        refs = ['12 U.S.C. 1751']
        formatted = self.export_manager._format_statutory_references(refs)
        self.assertEqual(formatted, '12 U.S.C. 1751')
    
    def test_statutory_references_formatting_multiple(self):
        """Test statutory references formatting with multiple references."""
        refs = ['12 U.S.C. 1751', '12 U.S.C. 1752(a)', '15 U.S.C. 1601']
        formatted = self.export_manager._format_statutory_references(refs)
        expected = '12 U.S.C. 1751|12 U.S.C. 1752(a)|15 U.S.C. 1601'
        self.assertEqual(formatted, expected)
    
    def test_statutory_references_formatting_with_pipes(self):
        """Test statutory references formatting removes existing pipes."""
        refs = ['12 U.S.C. 1751|invalid', '15 U.S.C. 1601']
        formatted = self.export_manager._format_statutory_references(refs)
        expected = '12 U.S.C. 1751 invalid|15 U.S.C. 1601'
        self.assertEqual(formatted, expected)
    
    def test_statutory_references_formatting_with_whitespace(self):
        """Test statutory references formatting handles whitespace."""
        refs = ['  12 U.S.C. 1751  ', '', '   ', '15 U.S.C. 1601']
        formatted = self.export_manager._format_statutory_references(refs)
        expected = '12 U.S.C. 1751|15 U.S.C. 1601'
        self.assertEqual(formatted, expected)
    
    def test_csv_data_extraction(self):
        """Test complete CSV data extraction and formatting."""
        # Export CSV
        filepath = self.export_manager._export_csv(
            self.sample_results, 'test_session', 'test_export'
        )
        
        # Read and verify data
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
        
        self.assertEqual(len(rows), 2)
        
        # Verify first row
        row1 = rows[0]
        self.assertEqual(row1[0], '2024-12345')  # Document Number
        self.assertEqual(row1[1], 'Test Regulation 1')  # Title
        self.assertEqual(row1[2], 'National Credit Union Administration')  # Agency
        self.assertEqual(row1[3], '2024-01-15')  # Publication Date
        self.assertEqual(row1[4], '1500')  # Content Length
        self.assertEqual(row1[5], 'SR')  # Category
        self.assertEqual(row1[6], '2')  # Statutory References Count
        self.assertEqual(row1[7], '12 U.S.C. 1751|12 U.S.C. 1752(a)')  # Statutory References
        self.assertEqual(row1[8], '1')  # Reform Recommendations Count
        self.assertEqual(row1[9], 'Yes')  # Analysis Success
        self.assertEqual(row1[10], '2.50')  # Processing Time
        
        # Verify second row
        row2 = rows[1]
        self.assertEqual(row2[0], '2024-67890')  # Document Number
        self.assertEqual(row2[5], 'NSR')  # Category
        self.assertEqual(row2[6], '0')  # Statutory References Count
        self.assertEqual(row2[7], '')  # Statutory References (empty)
        self.assertEqual(row2[8], '2')  # Reform Recommendations Count
    
    def test_csv_error_handling(self):
        """Test CSV export handles missing or invalid data gracefully."""
        # Create result with missing/invalid data
        problematic_result = {
            'document_number': '2024-ERROR',
            'title': 'Error Test',
            'agency_slug': 'test-agency',
            'analysis': {
                'category': None,
                'statutory_references': None,
                'reform_recommendations': None,
                'success': False,
                'processing_time': None
            }
        }
        
        # Should not raise exception
        filepath = self.export_manager._export_csv(
            [problematic_result], 'test_session', 'test_export'
        )
        
        # Verify file was created and has expected fallback values
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            row = next(reader)
        
        self.assertEqual(row[5], 'UNKNOWN')  # Category fallback
        self.assertEqual(row[6], '0')  # Statutory References Count
        self.assertEqual(row[7], '')  # Statutory References (empty)
        self.assertEqual(row[8], '0')  # Reform Recommendations Count
        self.assertEqual(row[9], 'No')  # Analysis Success
        self.assertEqual(row[10], '0.00')  # Processing Time fallback


class TestAgencySynopsisGeneration(unittest.TestCase):
    """Test cases for agency synopsis generation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = ExportManager(output_dir=self.temp_dir)
        
        # Mock LLM client
        self.mock_llm_client = Mock()
        self.export_manager.llm_client = self.mock_llm_client
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_agency_synopsis_success(self):
        """Test successful agency synopsis generation."""
        # Mock successful LLM response
        self.mock_llm_client.analyze_document.return_value = (
            "The National Credit Union Administration (NCUA) is an independent federal agency...",
            True,
            None
        )
        
        result = self.export_manager.generate_agency_synopsis("National Credit Union Administration")
        
        self.assertTrue(result['generation_success'])
        self.assertEqual(result['agency_name'], "National Credit Union Administration")
        self.assertIn("NCUA", result['synopsis_text'])
        self.assertIsNone(result['error_message'])
    
    def test_agency_synopsis_llm_failure(self):
        """Test agency synopsis generation with LLM failure."""
        # Mock LLM failure
        self.mock_llm_client.analyze_document.return_value = (
            "",
            False,
            "API rate limit exceeded"
        )
        
        result = self.export_manager.generate_agency_synopsis("Test Agency")
        
        self.assertFalse(result['generation_success'])
        self.assertEqual(result['agency_name'], "Test Agency")
        self.assertEqual(result['synopsis_text'], '')
        self.assertEqual(result['error_message'], "API rate limit exceeded")
    
    def test_agency_synopsis_exception(self):
        """Test agency synopsis generation with exception."""
        # Mock exception
        self.mock_llm_client.analyze_document.side_effect = Exception("Network error")
        
        result = self.export_manager.generate_agency_synopsis("Test Agency")
        
        self.assertFalse(result['generation_success'])
        self.assertEqual(result['agency_name'], "Test Agency")
        self.assertEqual(result['synopsis_text'], '')
        self.assertEqual(result['error_message'], "Network error")
    
    @patch('cfr_document_analyzer.export_manager.datetime')
    def test_agency_presentation_with_synopsis(self, mock_datetime):
        """Test agency presentation includes generated synopsis."""
        # Mock datetime for consistent output
        mock_now = Mock()
        mock_now.strftime.return_value = '2024-01-15'
        mock_datetime.now.return_value = mock_now
        
        # Mock successful synopsis generation
        self.mock_llm_client.analyze_document.return_value = (
            "The National Credit Union Administration (NCUA) regulates federal credit unions...",
            True,
            None
        )
        
        # Sample results
        results = [{
            'document_number': '2024-12345',
            'title': 'Test Regulation',
            'agency_slug': 'national-credit-union-administration',
            'publication_date': '2024-01-15',
            'content_length': 1500,
            'analysis': {
                'category': 'SR',
                'statutory_references': ['12 U.S.C. 1751'],
                'reform_recommendations': ['Simplify requirements'],
                'success': True,
                'processing_time': 2.5,
                'justification': 'This regulation is required...'
            }
        }]
        
        # Generate presentation
        summary_path = self.export_manager.create_agency_presentation_summary(
            results, 'test_session'
        )
        
        # Verify file was created and contains synopsis
        self.assertTrue(Path(summary_path).exists())
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('### Agency Overview', content)
        self.assertIn('The National Credit Union Administration (NCUA) regulates', content)
        self.assertIn('National Credit Union Administration', content)
    
    @patch('cfr_document_analyzer.export_manager.datetime')
    def test_agency_presentation_synopsis_failure(self, mock_datetime):
        """Test agency presentation handles synopsis generation failure."""
        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = '2024-01-15'
        mock_datetime.now.return_value = mock_now
        
        # Mock failed synopsis generation
        self.mock_llm_client.analyze_document.return_value = (
            "",
            False,
            "API error"
        )
        
        # Sample results
        results = [{
            'document_number': '2024-12345',
            'title': 'Test Regulation',
            'agency_slug': 'test-agency',
            'analysis': {
                'category': 'SR',
                'statutory_references': [],
                'reform_recommendations': [],
                'success': True,
                'processing_time': 1.0,
                'justification': 'Test justification'
            }
        }]
        
        # Generate presentation
        summary_path = self.export_manager.create_agency_presentation_summary(
            results, 'test_session'
        )
        
        # Verify file contains fallback message
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('### Agency Overview', content)
        self.assertIn('Agency overview could not be generated at this time.', content)


if __name__ == '__main__':
    unittest.main()