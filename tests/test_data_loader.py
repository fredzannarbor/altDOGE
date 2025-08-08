"""Tests for the data loader module."""

import pytest
import tempfile
import csv
from pathlib import Path
from cfr_agency_counter.data_loader import AgencyDataLoader
from cfr_agency_counter.models import Agency


class TestAgencyDataLoader:
    """Test cases for the AgencyDataLoader class."""
    
    def create_test_csv(self, data: list) -> str:
        """Create a temporary CSV file with test data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        
        fieldnames = ['active', 'cfr_citation', 'parent_agency_name', 'agency_name', 'description']
        writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in data:
            writer.writerow(row)
        
        temp_file.close()
        return temp_file.name
    
    def test_load_valid_agencies(self):
        """Test loading valid agencies from CSV."""
        test_data = [
            {
                'active': '1',
                'cfr_citation': '12 CFR 100-199',
                'parent_agency_name': 'Treasury Department',
                'agency_name': 'Test Agency',
                'description': 'A test agency'
            },
            {
                'active': '0',
                'cfr_citation': '',
                'parent_agency_name': '',
                'agency_name': 'Inactive Agency',
                'description': 'An inactive agency'
            }
        ]
        
        csv_file = self.create_test_csv(test_data)
        
        try:
            loader = AgencyDataLoader()
            agencies = loader.load_agencies(csv_file)
            
            assert len(agencies) == 2
            assert agencies[0].name == 'Test Agency'
            assert agencies[0].active is True
            assert agencies[0].cfr_citation == '12 CFR 100-199'
            assert agencies[0].slug == 'test-agency'
            
            assert agencies[1].name == 'Inactive Agency'
            assert agencies[1].active is False
            assert agencies[1].cfr_citation == ''
        finally:
            Path(csv_file).unlink()
    
    def test_load_nonexistent_file(self):
        """Test loading from a nonexistent file."""
        loader = AgencyDataLoader()
        
        with pytest.raises(FileNotFoundError, match="Agencies file not found"):
            loader.load_agencies("nonexistent.csv")
    
    def test_load_invalid_csv_headers(self):
        """Test loading CSV with missing required headers."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        
        # Write CSV with missing required columns
        writer = csv.DictWriter(temp_file, fieldnames=['name', 'status'])
        writer.writeheader()
        writer.writerow({'name': 'Test', 'status': 'active'})
        
        temp_file.close()
        
        try:
            loader = AgencyDataLoader()
            with pytest.raises(ValueError, match="Missing required columns"):
                loader.load_agencies(temp_file.name)
        finally:
            Path(temp_file.name).unlink()
    
    def test_generate_slug(self):
        """Test slug generation from agency names."""
        loader = AgencyDataLoader()
        
        assert loader._generate_slug("Test Agency") == "test-agency"
        assert loader._generate_slug("Department of Agriculture") == "department-of-agriculture"
        assert loader._generate_slug("U.S. Treasury") == "u-s-treasury"
        assert loader._generate_slug("Agency with Multiple   Spaces") == "agency-with-multiple-spaces"
        assert loader._generate_slug("Agency-with-Hyphens") == "agency-with-hyphens"
    
    def test_filter_cfr_agencies(self):
        """Test filtering agencies with CFR citations."""
        test_data = [
            {
                'active': '1',
                'cfr_citation': '12 CFR 100-199',
                'parent_agency_name': '',
                'agency_name': 'Agency with CFR',
                'description': 'Has CFR citation'
            },
            {
                'active': '1',
                'cfr_citation': '',
                'parent_agency_name': '',
                'agency_name': 'Agency without CFR',
                'description': 'No CFR citation'
            }
        ]
        
        csv_file = self.create_test_csv(test_data)
        
        try:
            loader = AgencyDataLoader()
            agencies = loader.load_agencies(csv_file)
            cfr_agencies = loader.filter_cfr_agencies(agencies)
            
            assert len(cfr_agencies) == 1
            assert cfr_agencies[0].name == 'Agency with CFR'
            assert cfr_agencies[0].cfr_citation == '12 CFR 100-199'
        finally:
            Path(csv_file).unlink()
    
    def test_get_active_agencies(self):
        """Test filtering for active agencies."""
        test_data = [
            {
                'active': '1',
                'cfr_citation': '12 CFR 100-199',
                'parent_agency_name': '',
                'agency_name': 'Active Agency',
                'description': 'Active agency'
            },
            {
                'active': '0',
                'cfr_citation': '13 CFR 200-299',
                'parent_agency_name': '',
                'agency_name': 'Inactive Agency',
                'description': 'Inactive agency'
            }
        ]
        
        csv_file = self.create_test_csv(test_data)
        
        try:
            loader = AgencyDataLoader()
            agencies = loader.load_agencies(csv_file)
            active_agencies = loader.get_active_agencies(agencies)
            
            assert len(active_agencies) == 1
            assert active_agencies[0].name == 'Active Agency'
            assert active_agencies[0].active is True
        finally:
            Path(csv_file).unlink()
    
    def test_get_cfr_active_agencies(self):
        """Test getting agencies that are both active and have CFR citations."""
        test_data = [
            {
                'active': '1',
                'cfr_citation': '12 CFR 100-199',
                'parent_agency_name': '',
                'agency_name': 'Active CFR Agency',
                'description': 'Active with CFR'
            },
            {
                'active': '0',
                'cfr_citation': '13 CFR 200-299',
                'parent_agency_name': '',
                'agency_name': 'Inactive CFR Agency',
                'description': 'Inactive with CFR'
            },
            {
                'active': '1',
                'cfr_citation': '',
                'parent_agency_name': '',
                'agency_name': 'Active Non-CFR Agency',
                'description': 'Active without CFR'
            }
        ]
        
        csv_file = self.create_test_csv(test_data)
        
        try:
            loader = AgencyDataLoader()
            cfr_active_agencies = loader.get_cfr_active_agencies(csv_file)
            
            assert len(cfr_active_agencies) == 1
            assert cfr_active_agencies[0].name == 'Active CFR Agency'
            assert cfr_active_agencies[0].active is True
            assert cfr_active_agencies[0].cfr_citation == '12 CFR 100-199'
        finally:
            Path(csv_file).unlink()
    
    def test_get_agency_statistics(self):
        """Test getting statistics about loaded agencies."""
        test_data = [
            {
                'active': '1',
                'cfr_citation': '12 CFR 100-199',
                'parent_agency_name': 'Treasury',
                'agency_name': 'Active CFR Agency',
                'description': 'Active with CFR'
            },
            {
                'active': '0',
                'cfr_citation': '',
                'parent_agency_name': '',
                'agency_name': 'Inactive Non-CFR Agency',
                'description': 'Inactive without CFR'
            }
        ]
        
        csv_file = self.create_test_csv(test_data)
        
        try:
            loader = AgencyDataLoader()
            agencies = loader.load_agencies(csv_file)
            stats = loader.get_agency_statistics(agencies)
            
            assert stats['total_agencies'] == 2
            assert stats['active_agencies'] == 1
            assert stats['inactive_agencies'] == 1
            assert stats['agencies_with_cfr'] == 1
            assert stats['agencies_without_cfr'] == 1
            assert stats['agencies_with_parent'] == 1
            assert stats['agencies_without_parent'] == 1
        finally:
            Path(csv_file).unlink()
    
    def test_skip_empty_agency_names(self):
        """Test that rows with empty agency names are skipped."""
        test_data = [
            {
                'active': '1',
                'cfr_citation': '12 CFR 100-199',
                'parent_agency_name': '',
                'agency_name': '',  # Empty name should be skipped
                'description': 'Empty name'
            },
            {
                'active': '1',
                'cfr_citation': '13 CFR 200-299',
                'parent_agency_name': '',
                'agency_name': 'Valid Agency',
                'description': 'Valid agency'
            }
        ]
        
        csv_file = self.create_test_csv(test_data)
        
        try:
            loader = AgencyDataLoader()
            agencies = loader.load_agencies(csv_file)
            
            assert len(agencies) == 1
            assert agencies[0].name == 'Valid Agency'
        finally:
            Path(csv_file).unlink()