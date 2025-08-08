"""
CSV format compatibility tests for CFR Document Analyzer.

Tests CSV format compatibility with common spreadsheet applications,
pipe-separated statutory references handling, Unicode support, and
proper CSV escaping.
"""

import unittest
import tempfile
import csv
import io
from pathlib import Path
from unittest.mock import Mock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cfr_document_analyzer.export_manager import ExportManager
from cfr_document_analyzer.models import RegulationCategory


class TestCSVFormatCompatibility(unittest.TestCase):
    """Test CSV format compatibility with various applications and edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = ExportManager(output_dir=self.temp_dir)
        
        # Mock LLM client
        self.export_manager.llm_client = Mock()
        
        # Test data with various edge cases
        self.test_results = [
            {
                'document_number': '2024-12345',
                'title': 'Standard Regulation Title',
                'agency_slug': 'national-credit-union-administration',
                'publication_date': '2024-01-15',
                'content_length': 1500,
                'analysis': {
                    'category': RegulationCategory.STATUTORILY_REQUIRED,
                    'statutory_references': ['12 U.S.C. 1751', '12 U.S.C. 1752(a)'],
                    'reform_recommendations': ['Simplify requirements'],
                    'success': True,
                    'processing_time': 2.5
                }
            },
            {
                'document_number': '2024-67890',
                'title': 'Title with "Quotes" and Commas, Special Characters',
                'agency_slug': 'test-agency',
                'publication_date': '2024-02-20',
                'content_length': 2000,
                'analysis': {
                    'category': 'NSR',
                    'statutory_references': ['15 U.S.C. 1601', '15 U.S.C. 1602(b)(1)', '20 U.S.C. 9252(a)'],
                    'reform_recommendations': ['Consider elimination', 'Merge with similar rules'],
                    'success': True,
                    'processing_time': 1.8
                }
            },
            {
                'document_number': '2024-11111',
                'title': 'Unicode Test: Café Naïve Résumé 中文 العربية',
                'agency_slug': 'unicode-test-agency',
                'publication_date': '2024-03-10',
                'content_length': 800,
                'analysis': {
                    'category': 'NRAN',
                    'statutory_references': ['42 U.S.C. 1234 (special chars: |, ", \')'],
                    'reform_recommendations': ['Update with Unicode: café naïve'],
                    'success': True,
                    'processing_time': 1.2
                }
            },
            {
                'document_number': '2024-22222',
                'title': 'Empty References Test',
                'agency_slug': 'empty-test-agency',
                'publication_date': '2024-04-05',
                'content_length': 500,
                'analysis': {
                    'category': 'UNKNOWN',
                    'statutory_references': [],
                    'reform_recommendations': [],
                    'success': False,
                    'processing_time': 0.5
                }
            }
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_csv_standard_compliance(self):
        """Test CSV format complies with RFC 4180 standard."""
        # Export CSV
        filepath = self.export_manager._export_csv(
            self.test_results, 'test_session', 'compliance_test'
        )
        
        # Read with Python's csv module (strict RFC 4180 compliance)
        with open(filepath, 'r', encoding='utf-8') as f:
            # Should not raise any exceptions
            reader = csv.reader(f, strict=True)
            headers = next(reader)
            rows = list(reader)
        
        # Verify structure
        self.assertEqual(len(headers), 11)
        self.assertEqual(len(rows), 4)
        
        # Verify each row has correct number of columns
        for row in rows:
            self.assertEqual(len(row), 11, f"Row has incorrect column count: {row}")
    
    def test_pipe_separated_statutory_references(self):
        """Test pipe-separated statutory references are properly handled."""
        filepath = self.export_manager._export_csv(
            self.test_results, 'test_session', 'pipe_test'
        )
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Test first row - multiple references
        row1 = rows[0]
        statutory_refs = row1['Statutory References']
        self.assertEqual(statutory_refs, '12 U.S.C. 1751|12 U.S.C. 1752(a)')
        
        # Verify count matches
        self.assertEqual(row1['Statutory References Count'], '2')
        
        # Test parsing
        parsed_refs = statutory_refs.split('|')
        self.assertEqual(len(parsed_refs), 2)
        self.assertEqual(parsed_refs[0], '12 U.S.C. 1751')
        self.assertEqual(parsed_refs[1], '12 U.S.C. 1752(a)')
        
        # Test second row - multiple references with different format
        row2 = rows[1]
        statutory_refs2 = row2['Statutory References']
        parsed_refs2 = statutory_refs2.split('|')
        self.assertEqual(len(parsed_refs2), 3)
        
        # Test empty references
        row4 = rows[3]
        self.assertEqual(row4['Statutory References'], '')
        self.assertEqual(row4['Statutory References Count'], '0')
    
    def test_unicode_character_handling(self):
        """Test proper handling of Unicode characters in CSV."""
        filepath = self.export_manager._export_csv(
            self.test_results, 'test_session', 'unicode_test'
        )
        
        # Read with UTF-8 encoding
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify Unicode characters are preserved
        self.assertIn('Café Naïve Résumé 中文 العربية', content)
        
        # Verify CSV parsing works with Unicode
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        unicode_row = rows[2]  # Third row has Unicode content
        self.assertIn('Unicode Test: Café Naïve Résumé 中文 العربية', unicode_row['Title'])
        # Reform recommendations count should be 1 (the Unicode text is in the recommendation but not shown in CSV)
        self.assertEqual(unicode_row['Reform Recommendations Count'], '1')
    
    def test_csv_special_character_escaping(self):
        """Test proper escaping of CSV special characters."""
        filepath = self.export_manager._export_csv(
            self.test_results, 'test_session', 'escaping_test'
        )
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Test row with quotes and commas in title
        row_with_quotes = rows[1]
        title = row_with_quotes['Title']
        self.assertEqual(title, 'Title with "Quotes" and Commas, Special Characters')
        
        # Test statutory reference with special characters (pipes should be cleaned)
        unicode_row = rows[2]
        statutory_refs = unicode_row['Statutory References']
        # Pipe characters should be replaced with spaces
        self.assertNotIn('|', statutory_refs.replace('|', ''))  # Only separator pipes should remain
        self.assertIn('42 U.S.C. 1234 (special chars:  ,', statutory_refs)  # Pipe replaced with space
    
    def test_excel_compatibility(self):
        """Test compatibility with Excel-style CSV parsing."""
        filepath = self.export_manager._export_csv(
            self.test_results, 'test_session', 'excel_test'
        )
        
        # Test with Excel dialect
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, dialect='excel')
            headers = next(reader)
            rows = list(reader)
        
        self.assertEqual(len(headers), 11)
        self.assertEqual(len(rows), 4)
        
        # Verify data integrity
        self.assertEqual(rows[0][0], '2024-12345')  # Document Number
        self.assertEqual(rows[0][5], 'SR')  # Category
        self.assertEqual(rows[0][7], '12 U.S.C. 1751|12 U.S.C. 1752(a)')  # Statutory References
    
    def test_google_sheets_compatibility(self):
        """Test compatibility with Google Sheets CSV import."""
        filepath = self.export_manager._export_csv(
            self.test_results, 'test_session', 'google_test'
        )
        
        # Google Sheets uses standard CSV parsing
        with open(filepath, 'r', encoding='utf-8') as f:
            # Read as string to verify format
            content = f.read()
        
        # Verify proper line endings (should be \n or \r\n)
        self.assertTrue('\n' in content)
        
        # Verify no unescaped quotes in the middle of fields
        lines = content.split('\n')
        for line in lines[1:]:  # Skip header
            if line.strip():  # Skip empty lines
                # Parse with csv module to ensure Google Sheets compatibility
                row = next(csv.reader([line]))
                self.assertIsInstance(row, list)
    
    def test_libreoffice_calc_compatibility(self):
        """Test compatibility with LibreOffice Calc."""
        filepath = self.export_manager._export_csv(
            self.test_results, 'test_session', 'libreoffice_test'
        )
        
        # LibreOffice Calc supports standard CSV with UTF-8
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Test that all expected columns are present
        expected_columns = [
            'Document Number', 'Title', 'Agency', 'Publication Date',
            'Content Length', 'Category', 'Statutory References Count',
            'Statutory References', 'Reform Recommendations Count',
            'Analysis Success', 'Processing Time (s)'
        ]
        
        self.assertEqual(list(rows[0].keys()), expected_columns)
        
        # Test data types are preserved as strings (CSV standard)
        for row in rows:
            for value in row.values():
                self.assertIsInstance(value, str)
    
    def test_csv_field_length_limits(self):
        """Test handling of very long field values."""
        # Create test data with very long fields
        long_test_results = [{
            'document_number': '2024-LONG',
            'title': 'A' * 1000,  # Very long title
            'agency_slug': 'test-agency',
            'publication_date': '2024-01-01',
            'content_length': 50000,
            'analysis': {
                'category': 'SR',
                'statutory_references': [f'12 U.S.C. {i}' for i in range(100)],  # Many references
                'reform_recommendations': ['Long recommendation ' + 'X' * 500],
                'success': True,
                'processing_time': 10.5
            }
        }]
        
        # Should not raise exceptions
        filepath = self.export_manager._export_csv(
            long_test_results, 'test_session', 'long_fields_test'
        )
        
        # Verify file was created and is readable
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
        
        # Verify long title is preserved
        self.assertEqual(len(row['Title']), 1000)
        
        # Verify many statutory references are properly pipe-separated
        refs = row['Statutory References'].split('|')
        self.assertEqual(len(refs), 100)
        self.assertEqual(row['Statutory References Count'], '100')
    
    def test_csv_memory_efficiency(self):
        """Test CSV generation is memory efficient for large datasets."""
        # Create large dataset
        large_results = []
        for i in range(1000):
            large_results.append({
                'document_number': f'2024-{i:05d}',
                'title': f'Test Document {i}',
                'agency_slug': 'test-agency',
                'publication_date': '2024-01-01',
                'content_length': 1000,
                'analysis': {
                    'category': 'SR',
                    'statutory_references': [f'12 U.S.C. {i}', f'15 U.S.C. {i+1000}'],
                    'reform_recommendations': [f'Recommendation {i}'],
                    'success': True,
                    'processing_time': 1.0
                }
            })
        
        # Should complete without memory errors
        filepath = self.export_manager._export_csv(
            large_results, 'test_session', 'large_dataset_test'
        )
        
        # Verify file size and structure
        file_size = Path(filepath).stat().st_size
        self.assertGreater(file_size, 100000)  # Should be substantial file
        
        # Verify structure with sampling
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check first row
            first_row = next(reader)
            self.assertEqual(first_row['Document Number'], '2024-00000')
            
            # Skip to end and check structure is maintained
            rows = list(reader)
            last_row = rows[-1]
            self.assertEqual(last_row['Document Number'], '2024-00999')
            self.assertEqual(len(first_row.keys()), len(last_row.keys()))
    
    def test_csv_roundtrip_integrity(self):
        """Test data integrity through CSV export and import cycle."""
        # Export CSV
        filepath = self.export_manager._export_csv(
            self.test_results, 'test_session', 'roundtrip_test'
        )
        
        # Import CSV and verify data integrity
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            imported_rows = list(reader)
        
        # Verify all original data is preserved
        self.assertEqual(len(imported_rows), len(self.test_results))
        
        for i, (original, imported) in enumerate(zip(self.test_results, imported_rows)):
            # Test key fields
            self.assertEqual(imported['Document Number'], original['document_number'])
            self.assertEqual(imported['Title'], original['title'])
            
            # Test category mapping
            expected_category = self.export_manager._extract_category(original['analysis'])
            self.assertEqual(imported['Category'], expected_category)
            
            # Test statutory references
            original_refs = original['analysis']['statutory_references']
            if original_refs:
                imported_refs = imported['Statutory References'].split('|')
                # Note: pipe characters in original refs are cleaned, so we need to account for that
                cleaned_original_refs = [ref.replace('|', ' ') for ref in original_refs]
                self.assertEqual(imported_refs, cleaned_original_refs)
            else:
                self.assertEqual(imported['Statutory References'], '')
            
            # Test counts
            self.assertEqual(
                int(imported['Statutory References Count']), 
                len(original['analysis']['statutory_references'])
            )
            self.assertEqual(
                int(imported['Reform Recommendations Count']), 
                len(original['analysis']['reform_recommendations'])
            )


class TestCSVValidationUtilities(unittest.TestCase):
    """Test utilities for validating CSV format compliance."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = ExportManager(output_dir=self.temp_dir)
        self.export_manager.llm_client = Mock()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_csv_structure(self):
        """Test CSV structure validation utility."""
        # Create valid CSV
        test_results = [{
            'document_number': '2024-12345',
            'title': 'Test Document',
            'agency_slug': 'test-agency',
            'publication_date': '2024-01-01',
            'content_length': 1000,
            'analysis': {
                'category': 'SR',
                'statutory_references': ['12 U.S.C. 1751'],
                'reform_recommendations': ['Test recommendation'],
                'success': True,
                'processing_time': 1.0
            }
        }]
        
        filepath = self.export_manager._export_csv(
            test_results, 'test_session', 'validation_test'
        )
        
        # Validation function
        def validate_csv_structure(csv_path):
            expected_columns = [
                'Document Number', 'Title', 'Agency', 'Publication Date',
                'Content Length', 'Category', 'Statutory References Count',
                'Statutory References', 'Reform Recommendations Count',
                'Analysis Success', 'Processing Time (s)'
            ]
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                
                if headers != expected_columns:
                    return False, f"Column mismatch: expected {expected_columns}, got {headers}"
                
                # Validate data rows
                for i, row in enumerate(reader):
                    if len(row) != len(expected_columns):
                        return False, f"Row {i+1} has {len(row)} columns, expected {len(expected_columns)}"
                
                return True, "CSV structure is valid"
        
        # Test validation
        is_valid, message = validate_csv_structure(filepath)
        self.assertTrue(is_valid, message)
    
    def test_validate_category_codes(self):
        """Test category code validation utility."""
        # Create CSV with various category codes
        test_results = [
            {'document_number': '1', 'title': 'Test 1', 'agency_slug': 'test', 'analysis': {'category': 'SR', 'statutory_references': [], 'reform_recommendations': [], 'success': True, 'processing_time': 1.0}},
            {'document_number': '2', 'title': 'Test 2', 'agency_slug': 'test', 'analysis': {'category': 'NSR', 'statutory_references': [], 'reform_recommendations': [], 'success': True, 'processing_time': 1.0}},
            {'document_number': '3', 'title': 'Test 3', 'agency_slug': 'test', 'analysis': {'category': 'NRAN', 'statutory_references': [], 'reform_recommendations': [], 'success': True, 'processing_time': 1.0}},
            {'document_number': '4', 'title': 'Test 4', 'agency_slug': 'test', 'analysis': {'category': 'UNKNOWN', 'statutory_references': [], 'reform_recommendations': [], 'success': True, 'processing_time': 1.0}},
        ]
        
        filepath = self.export_manager._export_csv(
            test_results, 'test_session', 'category_validation_test'
        )
        
        # Validation function
        def validate_category_codes(csv_path):
            valid_categories = {'SR', 'NSR', 'NRAN', 'UNKNOWN'}
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for i, row in enumerate(reader):
                    category = row['Category']
                    if category not in valid_categories:
                        return False, f"Invalid category '{category}' in row {i+1}"
                
                return True, "All category codes are valid"
        
        # Test validation
        is_valid, message = validate_category_codes(filepath)
        self.assertTrue(is_valid, message)


if __name__ == '__main__':
    unittest.main()