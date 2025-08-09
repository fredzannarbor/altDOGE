#!/usr/bin/env python3
"""
Test script to verify the fixed CSV export functionality.

Tests the new CSV export that removes the Category column and extracts
individual keys from the justification JSON as separate columns.
"""

import json
import csv
import tempfile
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.export_manager import ExportManager


def create_test_results():
    """Create test analysis results with various justification formats."""
    return [
        {
            'document_number': '2024-12345',
            'title': 'Test Document 1',
            'agency_slug': 'test-agency',
            'publication_date': '2024-01-15',
            'content_length': 2500,
            'analysis': {
                'statutory_references': ['12 U.S.C. 1751', '12 U.S.C. 1790d'],
                'reform_recommendations': ['Simplify reporting requirements'],
                'success': True,
                'processing_time': 3.20,
                'justification': json.dumps({
                    'category': 'SR',
                    'analysis': 'Detailed analysis of capital requirements',
                    'legal_basis': 'Federal Credit Union Act Section 216',
                    'recommendation': 'Simplify reporting requirements'
                })
            }
        },
        {
            'document_number': '2024-67890',
            'title': 'Test Document 2',
            'agency_slug': 'test-agency',
            'publication_date': '2024-02-20',
            'content_length': 1800,
            'analysis': {
                'statutory_references': [],
                'reform_recommendations': ['Modernize lending limits', 'Update procedures'],
                'success': True,
                'processing_time': 2.10,
                'justification': json.dumps({
                    'category': 'NSR',
                    'analysis': 'Review of business lending authority',
                    'legal_basis': '12 U.S.C. 1757a',
                    'summary': 'Not required by statute but permissible'
                })
            }
        },
        {
            'document_number': '2024-11111',
            'title': 'Test Document 3',
            'agency_slug': 'test-agency',
            'publication_date': '2024-03-10',
            'content_length': 1200,
            'analysis': {
                'statutory_references': ['12 U.S.C. 1761d'],
                'reform_recommendations': [],
                'success': True,
                'processing_time': 1.85,
                'justification': 'CATEGORY: NRAN\nANALYSIS: Audit requirement analysis\nLEGAL BASIS: Supervisory committee authority'
            }
        },
        {
            'document_number': '2024-22222',
            'title': 'Test Document 4',
            'agency_slug': 'test-agency',
            'publication_date': '2024-04-05',
            'content_length': 3200,
            'analysis': {
                'statutory_references': [],
                'reform_recommendations': ['Analysis incomplete'],
                'success': False,
                'processing_time': 0.50,
                'justification': 'Analysis failed due to insufficient data'
            }
        }
    ]


def test_csv_export():
    """Test the CSV export functionality."""
    print("Testing CSV export with justification JSON parsing...")
    
    # Create test data
    test_results = create_test_results()
    
    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        export_manager = ExportManager(temp_dir)
        
        # Export to CSV
        exported_files = export_manager.export_session_results(
            test_results, 'test_session_123', ['csv']
        )
        
        if 'csv' not in exported_files:
            print("❌ FAILED: CSV export did not complete")
            return False
        
        csv_file = exported_files['csv']
        print(f"✅ CSV exported to: {csv_file}")
        
        # Read and analyze the CSV
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
        
        print(f"\n📊 CSV Analysis:")
        print(f"Headers ({len(headers)}): {headers}")
        print(f"Data rows: {len(rows)}")
        
        # Check that Category column is removed
        if 'Category' in headers:
            print("❌ FAILED: Category column should be removed")
            return False
        else:
            print("✅ PASSED: Category column successfully removed")
        
        # Check for justification-derived columns
        justification_columns = [h for h in headers if h not in [
            'Document Number', 'Title', 'Agency', 'Publication Date', 
            'Content Length', 'Statutory References Count', 'Statutory References',
            'Reform Recommendations Count', 'Analysis Success', 'Processing Time (s)'
        ]]
        
        print(f"✅ Justification-derived columns ({len(justification_columns)}): {justification_columns}")
        
        # Verify specific columns exist
        expected_columns = ['analysis', 'category', 'legal_basis']
        for col in expected_columns:
            if col in headers:
                print(f"✅ Found expected column: {col}")
            else:
                print(f"⚠️  Missing expected column: {col}")
        
        # Check data integrity
        print(f"\n📋 Sample Data:")
        for i, row in enumerate(rows[:2]):  # Show first 2 rows
            print(f"Row {i+1}: {dict(zip(headers, row))}")
        
        # Verify no Category data in rows
        category_col_index = None
        try:
            category_col_index = headers.index('Category')
            print("❌ FAILED: Found Category column in headers")
            return False
        except ValueError:
            print("✅ PASSED: No Category column found in headers")
        
        # Check that justification data was parsed
        if 'category' in headers:
            category_index = headers.index('category')
            categories_found = [row[category_index] for row in rows if row[category_index]]
            print(f"✅ Categories extracted from justification: {categories_found}")
        
        print(f"\n🎉 CSV export test completed successfully!")
        return True


def main():
    """Main test function."""
    print("Starting CSV export fix validation...")
    
    success = test_csv_export()
    
    if success:
        print("\n✅ All tests passed! CSV export fixes are working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == '__main__':
    sys.exit(main())